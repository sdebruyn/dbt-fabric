import threading
from typing import Any

from dbt_common.exceptions import DbtRuntimeError

from dbt.adapters.base.impl import PythonJobHelper
from dbt.adapters.fabric.fabric_api_client import FabricApiClient
from dbt.adapters.fabric.fabric_credentials import FabricCredentials
from dbt.adapters.fabric.fabric_hc_livy_session import HighConcurrencyLivySession
from dbt.adapters.fabric.fabric_token_provider import FabricTokenProvider
from dbt.adapters.fabric.livy_result import LivySessionResult

_thread_local = threading.local()


class FabricLivyHelper(PythonJobHelper):
    _sql_endpoint: str | None = None

    def __init__(self, parsed_model: dict, credential: FabricCredentials) -> None:
        fabric_api_client: FabricApiClient = FabricApiClient.create(
            credential, FabricTokenProvider(credential)
        )

        if not getattr(_thread_local, "livy_session", None):
            _thread_local.livy_session = HighConcurrencyLivySession(fabric_api_client)

        if not self._sql_endpoint:
            self._sql_endpoint = fabric_api_client.get_warehouse_connection_string()

    # The synapsesql connector holds JDBC sessions to the DW alive past the
    # write call (per #238). Those sessions keep Sch-S on the target table's
    # metadata and block any subsequent Sch-M-acquiring DDL (sp_rename, DROP,
    # CREATE VIEW), causing minutes-long LCK_M_SCH_M waits.
    #
    # Forcing a JVM GC reliably tears the connections down within ~3-4s
    # (empirically verified — see #271). The earlier fire-and-forget variant
    # (#239) submitted the GC but didn't wait, so the next dbt op could
    # start before the GC actually ran. Await the GC so the connections are
    # closed before submit() returns.
    _GC_CODE = "spark._jvm.java.lang.System.gc()"

    def submit(self, compiled_code: str) -> Any:
        livy_session: HighConcurrencyLivySession = _thread_local.livy_session
        assert self._sql_endpoint is not None
        compiled_code = compiled_code.replace("DBT_FABRIC_REPLACED_WITH_HOST", self._sql_endpoint)
        result = livy_session.run_statement(compiled_code, "python")
        assert isinstance(result, LivySessionResult)
        if not result.success:
            raise DbtRuntimeError(
                f"Python statement execution failed. "
                f"Logs URL: {livy_session.get_logs_url()}. "
                f"Error: {result.error_message}"
            )
        livy_session.run_statement(self._GC_CODE, "python")
        return result.to_submission_result(compiled_code)
