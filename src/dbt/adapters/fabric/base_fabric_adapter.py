import abc
from typing import Any, Type

from dbt.adapters.base import available
from dbt.adapters.base.impl import PythonJobHelper
from dbt.adapters.contracts.connection import AdapterResponse
from dbt.adapters.events.logging import AdapterLogger
from dbt.adapters.fabric.fabric_livy_helper import FabricLivyHelper
from dbt.adapters.fabric.fabric_livy_session import LivySubmissionResult
from dbt.adapters.fabric.purview_sync import PurviewSync, extract_syncable_models
from dbt.adapters.sql.impl import SQLAdapter

logger = AdapterLogger("fabric")


class BaseFabricAdapter(SQLAdapter, metaclass=abc.ABCMeta):
    @property
    def default_python_submission_method(self) -> str:
        return "livy"

    @property
    def python_submission_helpers(self) -> dict[str, Type[PythonJobHelper]]:
        return {
            "livy": FabricLivyHelper,
        }

    def generate_python_submission_response(
        self, submission_result: LivySubmissionResult | None
    ) -> AdapterResponse:
        if not submission_result:
            return AdapterResponse(_message="ERROR")
        elif not submission_result.success:
            assert submission_result.error_message is not None
            return AdapterResponse(
                _message=submission_result.error_message, query_id=submission_result.run_id
            )
        return AdapterResponse(_message="OK", query_id=submission_result.run_id)

    @available
    def purview_sync(
        self,
        graph: Any,
        results: Any = None,
        sync_descriptions: bool = True,
        sync_lineage: bool = True,
        sync_metadata: bool = True,
    ) -> str:
        """Sync dbt model metadata to Microsoft Purview.

        Callable from dbt macros via adapter.purview_sync(). Matches dbt models to Purview
        entities, then pushes descriptions, business metadata, and/or lineage depending on flags.
        """
        credentials = self.config.credentials
        if not credentials.purview_endpoint:
            logger.warning("Purview sync skipped: purview_endpoint not configured in profiles.yml")
            return ""

        client = self.connections.get_purview_client(credentials)
        fabric_client = self.connections.get_fabric_api_client(credentials)
        sync = PurviewSync(client, fabric_client, graph)

        if sync_metadata or sync_lineage:
            if not client.ensure_type_definitions():
                logger.warning(
                    "Purview sync: type definitions could not be registered, "
                    "skipping metadata and lineage"
                )
                sync_metadata = False
                sync_lineage = False

        models = extract_syncable_models(graph, results)
        if not models:
            logger.info("Purview sync: no syncable models found")
            return ""

        logger.info(f"Purview sync: syncing {len(models)} models")
        resolved = sync.resolve_entities(models)

        if not resolved:
            logger.warning("Purview sync: no models could be matched to Purview entities")
            return ""

        if sync_descriptions:
            sync.push_descriptions(models, resolved)
        if sync_metadata:
            sync.push_business_metadata(models, resolved, results)
        if sync_lineage:
            sync.push_lineage(models, resolved)

        logger.info("Purview sync completed")
        return ""
