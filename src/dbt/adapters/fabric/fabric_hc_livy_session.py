import contextlib
import hashlib
import json
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

import requests

from dbt.adapters.events.logging import AdapterLogger
from dbt.adapters.fabric.fabric_api_client import FabricApiClient, FabricApiError
from dbt.adapters.fabric.livy_result import LivySessionResult

logger = AdapterLogger("fabricspark")

_TERMINAL_BAD_STATES = frozenset({"Dead", "Killed", "Failed", "Error"})
_TRANSIENT_EXCEPTIONS = (
    FabricApiError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
    json.JSONDecodeError,
)


def derive_session_tag(workspace_id: str, lakehouse_id: str) -> str:
    """Deterministic session tag from (workspace_id, lakehouse_id).

    All dbt threads in the same process produce the same tag, so Fabric packs
    their REPLs onto one underlying Livy session. Successive dbt invocations
    targeting the same workspace + lakehouse also produce the same tag, letting
    Fabric snap-attach new REPLs onto the still-warm session.
    """
    material = f"{workspace_id}|{lakehouse_id}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"dbt-fabricspark-{digest}"


@dataclass
class HCSessionState:
    hc_id: str | None = None
    session_id: str | None = None
    repl_id: str | None = None
    is_dead: bool = False


class HighConcurrencyLivySession:
    """One HC REPL per dbt thread.

    Acquires an HC session via ``POST /highConcurrencySessions``, polls until
    the underlying Livy session is idle and a REPL is allocated, then submits
    statements through the REPL endpoint.

    Sessions are pooled at the process level (keyed by session tag) to avoid
    re-acquiring an HC REPL on every dbt invocation (seed/run/test/snapshot).
    ``close()`` returns a healthy session to the pool; dead sessions are
    deleted in Fabric immediately.

    The pool lives for the lifetime of the process — no ``atexit`` handler,
    no out-of-band cleanup. Sessions still in the pool at interpreter exit
    are reaped server-side by Fabric on the standard HC REPL idle timeout.
    This keeps the implementation aligned with dbt's open/close lifecycle
    and avoids the fragility of ``atexit`` handlers that the upstream
    adapter relies on (see ``docs/comparison-dbt-fabricspark.md``).

    The underlying Spark session is managed by Fabric and stays alive for
    other REPLs and processes — closing or deleting an HC slot here only
    releases this instance's REPL, not the shared Spark session.
    """

    _POLLING_INTERVAL = 3
    _POLL_BACKOFF_SCHEDULE: tuple[float, ...] = (0.5, 1.0, 2.0)
    _MAX_CONSECUTIVE_TRANSIENT_ERRORS = 5
    _TERMINAL_STATEMENT_STATES = frozenset({"available", "error", "cancelled", "cancelling"})

    _pool: dict[str, deque["HighConcurrencyLivySession"]] = {}
    _pool_lock = threading.Lock()

    def __init__(self, fabric_api_client: FabricApiClient) -> None:
        self._fabric_api_client = fabric_api_client
        self._state = HCSessionState()
        self._session_tag: str | None = None

    @classmethod
    def _poll_interval_for_attempt(cls, attempt: int) -> float:
        """Exponential backoff for polling: 0.5s, 1s, 2s, then 3s steady-state.

        HC sessions on a warm Spark cluster typically reach Idle within a
        second; short statements complete sub-second. Starting at the floor
        wastes most of that latency on a fixed 3s sleep.
        """
        if attempt < len(cls._POLL_BACKOFF_SCHEDULE):
            return cls._POLL_BACKOFF_SCHEDULE[attempt]
        return cls._POLLING_INTERVAL

    def _get_session_tag(self) -> str:
        if self._session_tag is None:
            workspace_id = self._fabric_api_client.get_workspace_id()
            lakehouse_id = self._fabric_api_client.get_lakehouse_id()
            self._session_tag = derive_session_tag(workspace_id, lakehouse_id)
        return self._session_tag

    def get_logs_url(self) -> str:
        """Build the Fabric Portal URL to the Spark monitor logs for this session."""
        api_uri = self._fabric_api_client._credentials.fabric_base_api_uri
        portal_host = api_uri.replace("://api.", "://app.").split("/v")[0]
        lakehouse_id = self._fabric_api_client.get_lakehouse_id()
        session_id = self._state.session_id or "unknown"
        return f"{portal_host}/workloads/de-ds/sparkmonitor/{lakehouse_id}/{session_id}"

    # ---- acquire -----------------------------------------------------------

    def wait_for_session_ready(self) -> None:
        """Acquire an HC session and poll until the REPL is ready."""
        tag = self._get_session_tag()
        logger.debug(f"Acquiring HC session (sessionTag={tag})")

        max_attempts = 3
        backoff_seconds = 5
        last_exception: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                body = self._fabric_api_client.acquire_hc_session(tag)
                break
            except _TRANSIENT_EXCEPTIONS as e:
                is_api_error = isinstance(e, FabricApiError)
                if is_api_error and not (e.status_code == 404 or 500 <= e.status_code < 600):
                    raise
                if attempt == max_attempts:
                    raise
                last_exception = e
                wait_time = backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    f"HC session acquire returned a transient error "
                    f"(attempt {attempt}/{max_attempts}), retrying in {wait_time}s: {e}"
                )
                time.sleep(wait_time)
        else:
            assert last_exception is not None
            raise last_exception

        hc_id = body.get("id")
        if not hc_id:
            raise RuntimeError(f"HC acquire response missing 'id': {body}")

        self._state.hc_id = str(hc_id)
        try:
            self._poll_until_idle()
        except Exception:
            with contextlib.suppress(Exception):
                self._fabric_api_client.delete_hc_session(str(hc_id))
            self._state = HCSessionState()
            raise
        self._state.is_dead = False
        logger.debug(
            f"HC session ready: hc_id={self._state.hc_id} "
            f"sessionId={self._state.session_id} replId={self._state.repl_id}"
        )

    def _poll_until_idle(self) -> None:
        start_time = time.time()
        timeout = self._fabric_api_client._credentials.spark_session_timeout
        consecutive_errors = 0
        attempt = 0

        while True:
            if time.time() - start_time >= timeout:
                raise TimeoutError(
                    f"Timeout ({timeout}s) waiting for HC session {self._state.hc_id} "
                    f"to become Idle. Increase `spark_session_timeout` in profiles.yml."
                )

            try:
                body = self._fabric_api_client.get_hc_session(self._state.hc_id)
                consecutive_errors = 0
            except _TRANSIENT_EXCEPTIONS as e:
                consecutive_errors += 1
                if consecutive_errors >= self._MAX_CONSECUTIVE_TRANSIENT_ERRORS:
                    raise
                logger.warning(
                    f"Transient error polling HC session {self._state.hc_id} "
                    f"({consecutive_errors}/{self._MAX_CONSECUTIVE_TRANSIENT_ERRORS}): {e}"
                )
                time.sleep(self._poll_interval_for_attempt(attempt))
                attempt += 1
                continue

            state = body.get("state", "")

            if state in _TERMINAL_BAD_STATES:
                err = body.get("fabricSessionStateInfo", {}).get("errorMessage") or state
                raise RuntimeError(f"HC session {self._state.hc_id} state={state}: {err}")

            if state == "Idle" and body.get("sessionId") and body.get("replId"):
                self._state.session_id = str(body["sessionId"])
                self._state.repl_id = str(body["replId"])
                return

            time.sleep(self._poll_interval_for_attempt(attempt))
            attempt += 1

    def _ensure_repl(self) -> None:
        """Re-acquire this thread's HC session if it was marked dead."""
        if self._state.is_dead or self._state.hc_id is None:
            logger.debug("HC REPL marked stale — re-acquiring")
            if self._state.hc_id is not None:
                with contextlib.suppress(Exception):
                    self._fabric_api_client.delete_hc_session(self._state.hc_id)
                self._state = HCSessionState()
            self.wait_for_session_ready()

    def cancel_statement(self, statement_id: int) -> None:
        """Cancel a running statement via the HC REPL endpoint."""
        assert self._state.session_id is not None
        assert self._state.repl_id is not None
        self._fabric_api_client.cancel_hc_statement(
            self._state.session_id, self._state.repl_id, statement_id
        )

    # ---- statement execution -----------------------------------------------

    def run_statement(
        self, statement_code: str, statement_language: str, wait_for_result: bool = True
    ) -> LivySessionResult | int:
        """Submit a statement and optionally wait for its result.

        Same interface as ``LivySession.run_statement``.
        """
        self._ensure_repl()
        assert self._state.session_id is not None
        assert self._state.repl_id is not None

        try:
            if statement_language == "sql":
                statement_id = self._fabric_api_client.submit_hc_sql_statement(
                    self._state.session_id, self._state.repl_id, statement_code
                )
            else:
                statement_id = self._fabric_api_client.submit_hc_python_statement(
                    self._state.session_id, self._state.repl_id, statement_code
                )
        except FabricApiError as e:
            if e.status_code == 404:
                self._state.is_dead = True
                logger.debug("HC statement submit returned 404 — flagging REPL for re-acquire")
            return LivySessionResult(success=False, error_message=str(e))

        if wait_for_result:
            return self.wait_and_get_statement_result(statement_id)
        else:
            return statement_id

    def wait_for_statement_ready(self, statement_id: int) -> dict[str, Any]:
        """Poll an HC REPL statement until it reaches a terminal state."""
        assert self._state.session_id is not None
        assert self._state.repl_id is not None

        start_time = time.time()
        attempt = 0
        while True:
            response = self._fabric_api_client.get_hc_statement(
                self._state.session_id, self._state.repl_id, statement_id
            )
            statement_state = response.get("state", "unknown")
            if statement_state in self._TERMINAL_STATEMENT_STATES:
                return response
            if time.time() - start_time >= self._fabric_api_client._credentials.query_timeout:
                raise TimeoutError("HC Livy statement did not become available in time.")
            time.sleep(self._poll_interval_for_attempt(attempt))
            attempt += 1

    def wait_and_get_statement_result(self, statement_id: int) -> LivySessionResult:
        """Wait for a statement to complete and return its result."""
        try:
            response = self.wait_for_statement_ready(statement_id)
            output = response.get("output", {})
            success = response["state"] == "available" and output.get("status") == "ok"
            error_message = output.get("evalue")
            if not success and not error_message:
                error_message = f"Statement ended with state '{response.get('state')}'"
            return LivySessionResult(
                statement_id=statement_id,
                success=success,
                error_message=error_message,
                status_code=output.get("status"),
                json_data=output.get("data", {}).get("application/json", {}),
            )
        except FabricApiError as e:
            if e.status_code == 404:
                self._state.is_dead = True
                logger.debug("HC statement poll returned 404 — flagging REPL for re-acquire")
            logger.error(
                f"Error while waiting for HC statement to be ready. "
                f"Logs URL: {self.get_logs_url()}"
            )
            logger.exception(e)
            return LivySessionResult(
                statement_id=statement_id, success=False, error_message=str(e)
            )
        except Exception as e:
            logger.error(
                f"Error while waiting for HC statement to be ready. "
                f"Logs URL: {self.get_logs_url()}"
            )
            logger.exception(e)
            return LivySessionResult(
                statement_id=statement_id, success=False, error_message=str(e)
            )

    # ---- pool + cleanup ----------------------------------------------------

    @classmethod
    def acquire(cls, fabric_api_client: FabricApiClient) -> "HighConcurrencyLivySession":
        """Get a verified-ready HC session from the pool, or create one fresh.

        Pool key is the session tag (workspace + lakehouse). Each pooled
        candidate is checked against Fabric before being handed out — Fabric
        may have reaped an idle session between releases, and a stale
        ``hc_id`` would surface as a 404 on the next statement and fail the
        dbt op. Reaped sessions are discarded and the next candidate is
        tried; the pool empties out to a fresh acquire.
        """
        workspace_id = fabric_api_client.get_workspace_id()
        lakehouse_id = fabric_api_client.get_lakehouse_id()
        tag = derive_session_tag(workspace_id, lakehouse_id)
        while True:
            with cls._pool_lock:
                pool = cls._pool.get(tag)
                session = pool.popleft() if pool else None
            if session is None:
                session = cls(fabric_api_client)
                session.wait_for_session_ready()
                return session
            # Pool key locks workspace + lakehouse, so swapping in the
            # caller's client is safe — credentials still target the same
            # Fabric endpoint.
            session._fabric_api_client = fabric_api_client
            if session._verify_alive():
                logger.debug(f"Reusing pooled HC session {session._state.hc_id}")
                return session
            session._delete()

    def _verify_alive(self) -> bool:
        """Return False if Fabric has reaped this HC session or it is not Idle."""
        if self._state.hc_id is None:
            return False
        try:
            body = self._fabric_api_client.get_hc_session(self._state.hc_id)
        except FabricApiError as e:
            if e.status_code == 404:
                return False
            raise
        return body.get("state", "") == "Idle"

    def close(self) -> None:
        """Return this session to the pool, or delete it in Fabric if unhealthy.

        The HC REPL slot stays warm in the pool for the next ``open()``; the
        pool is drained at interpreter exit via :meth:`drain_pool`.
        """
        if self._state.hc_id is None:
            return
        if self._state.is_dead:
            self._delete()
            return
        tag = self._get_session_tag()
        with self._pool_lock:
            self._pool.setdefault(tag, deque()).append(self)
        logger.debug(f"Returned HC session {self._state.hc_id} to pool")

    def _delete(self) -> None:
        """Actually DELETE this HC session in Fabric, releasing the REPL slot."""
        if self._state.hc_id is None:
            return
        try:
            self._fabric_api_client.delete_hc_session(self._state.hc_id)
            logger.debug(f"Deleted HC session {self._state.hc_id}")
        except Exception as ex:
            logger.warning(f"Failed to delete HC session {self._state.hc_id}: {ex}")
        finally:
            self._state = HCSessionState()
