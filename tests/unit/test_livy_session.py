import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from dbt.adapters.fabric.fabric_livy_session import LivySession, LivySessionResult


@pytest.fixture
def credentials():
    mock = MagicMock()
    mock.spark_session_timeout = 60
    mock.query_timeout = 120
    return mock


@pytest.fixture
def fabric_api_client(credentials):
    mock = MagicMock()
    mock._credentials = credentials
    mock.get_lakehouse_id.return_value = "lakehouse-id"
    mock.get_livy_session_id.return_value = "session-id"
    return mock


@pytest.fixture
def session(fabric_api_client):
    return LivySession(fabric_api_client)


class TestWaitForSessionReady:
    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_returns_immediately_when_idle(self, mock_sleep, session, fabric_api_client):
        fabric_api_client.get_livy_session_state.return_value = "idle"

        session.wait_for_session_ready()

        fabric_api_client.get_livy_session_state.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("dbt.adapters.fabric.fabric_livy_session.time.time")
    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_polls_through_non_idle_states(
        self, mock_sleep, mock_time, session, fabric_api_client
    ):
        fabric_api_client.get_livy_session_state.side_effect = ["starting", "busy", "idle"]
        mock_time.side_effect = [0, 10, 20, 30]

        session.wait_for_session_ready()

        assert fabric_api_client.get_livy_session_state.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("dbt.adapters.fabric.fabric_livy_session.time.time")
    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_raises_timeout_error_when_session_timeout_exceeded(
        self, mock_sleep, mock_time, session, fabric_api_client, credentials
    ):
        credentials.spark_session_timeout = 30
        fabric_api_client.get_livy_session_state.return_value = "starting"
        mock_time.side_effect = [0, 31]

        with pytest.raises(TimeoutError, match="did not become idle"):
            session.wait_for_session_ready()

    @patch("dbt.adapters.fabric.fabric_livy_session.time.time")
    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_tolerates_transient_errors_below_threshold(
        self, mock_sleep, mock_time, session, fabric_api_client
    ):
        fabric_api_client.get_livy_session_state.side_effect = [
            requests.exceptions.ConnectionError("conn refused"),
            requests.exceptions.Timeout("timed out"),
            requests.exceptions.ChunkedEncodingError("chunked"),
            json.JSONDecodeError("bad json", "", 0),
            "idle",
        ]
        mock_time.side_effect = [0, 5, 10, 15, 20]

        session.wait_for_session_ready()

        assert fabric_api_client.get_livy_session_state.call_count == 5

    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_reraises_after_max_consecutive_transient_errors(
        self, mock_sleep, session, fabric_api_client
    ):
        fabric_api_client.get_livy_session_state.side_effect = requests.exceptions.ConnectionError(
            "conn refused"
        )

        with pytest.raises(requests.exceptions.ConnectionError):
            session.wait_for_session_ready()

        assert fabric_api_client.get_livy_session_state.call_count == 5

    @patch("dbt.adapters.fabric.fabric_livy_session.time.time")
    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_resets_error_counter_on_success(
        self, mock_sleep, mock_time, session, fabric_api_client
    ):
        fabric_api_client.get_livy_session_state.side_effect = [
            requests.exceptions.ConnectionError("err1"),
            requests.exceptions.ConnectionError("err2"),
            requests.exceptions.ConnectionError("err3"),
            requests.exceptions.ConnectionError("err4"),
            "starting",
            requests.exceptions.ConnectionError("err5"),
            requests.exceptions.ConnectionError("err6"),
            requests.exceptions.ConnectionError("err7"),
            requests.exceptions.ConnectionError("err8"),
            "idle",
        ]
        mock_time.side_effect = [0, 5, 10, 15, 20, 25, 30, 35, 40]

        session.wait_for_session_ready()

        assert fabric_api_client.get_livy_session_state.call_count == 10


class TestWaitForStatementReady:
    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_returns_when_state_is_available(self, mock_sleep, session, fabric_api_client):
        fabric_api_client.get_livy_statement.return_value = {
            "state": "available",
            "output": {"status": "ok", "data": {}},
        }

        result = session.wait_for_statement_ready(42)

        assert result["state"] == "available"
        mock_sleep.assert_not_called()

    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_returns_when_state_is_error(self, mock_sleep, session, fabric_api_client):
        fabric_api_client.get_livy_statement.return_value = {
            "state": "error",
            "output": {"status": "error", "evalue": "something went wrong"},
        }

        result = session.wait_for_statement_ready(42)

        assert result["state"] == "error"
        mock_sleep.assert_not_called()

    @patch("dbt.adapters.fabric.fabric_livy_session.time.time")
    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_polls_through_non_terminal_states(
        self, mock_sleep, mock_time, session, fabric_api_client
    ):
        fabric_api_client.get_livy_statement.side_effect = [
            {"state": "waiting"},
            {"state": "running"},
            {"state": "available", "output": {"status": "ok"}},
        ]
        mock_time.side_effect = [0, 10, 20, 30]

        result = session.wait_for_statement_ready(42)

        assert result["state"] == "available"
        assert mock_sleep.call_count == 2

    @patch("dbt.adapters.fabric.fabric_livy_session.time.time")
    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_raises_timeout_error_when_query_timeout_exceeded(
        self, mock_sleep, mock_time, session, fabric_api_client, credentials
    ):
        credentials.query_timeout = 60
        fabric_api_client.get_livy_statement.return_value = {"state": "running"}
        mock_time.side_effect = [0, 61]

        with pytest.raises(TimeoutError, match="did not become available"):
            session.wait_for_statement_ready(42)


class TestWaitAndGetStatementResult:
    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_available_with_status_ok_returns_success(
        self, mock_sleep, session, fabric_api_client
    ):
        fabric_api_client.get_livy_statement.return_value = {
            "state": "available",
            "output": {
                "status": "ok",
                "data": {"application/json": {"key": "value"}},
            },
        }

        result = session.wait_and_get_statement_result(7)

        assert result.success is True
        assert result.statement_id == 7
        assert result.status_code == "ok"
        assert result.json_data == {"key": "value"}
        assert result.error_message is None

    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_available_with_status_not_ok_returns_failure(
        self, mock_sleep, session, fabric_api_client
    ):
        fabric_api_client.get_livy_statement.return_value = {
            "state": "available",
            "output": {
                "status": "error",
                "evalue": "NameError: name 'x' is not defined",
            },
        }

        result = session.wait_and_get_statement_result(7)

        assert result.success is False
        assert result.error_message == "NameError: name 'x' is not defined"
        assert result.status_code == "error"

    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_error_state_returns_failure(self, mock_sleep, session, fabric_api_client):
        fabric_api_client.get_livy_statement.return_value = {
            "state": "error",
            "output": {
                "status": "error",
                "evalue": "session crashed",
            },
        }

        result = session.wait_and_get_statement_result(7)

        assert result.success is False
        assert result.error_message == "session crashed"

    @patch("dbt.adapters.fabric.fabric_livy_session.time.time")
    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_catches_timeout_error_and_returns_failed_result(
        self, mock_sleep, mock_time, session, fabric_api_client, credentials
    ):
        credentials.query_timeout = 10
        fabric_api_client.get_livy_statement.return_value = {"state": "running"}
        mock_time.side_effect = [0, 11]

        result = session.wait_and_get_statement_result(7)

        assert result.success is False
        assert result.statement_id == 7
        assert "did not become available" in result.error_message

    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_catches_generic_exception_and_returns_failed_result(
        self, mock_sleep, session, fabric_api_client
    ):
        fabric_api_client.get_livy_statement.side_effect = RuntimeError("unexpected failure")

        result = session.wait_and_get_statement_result(7)

        assert result.success is False
        assert result.statement_id == 7
        assert "unexpected failure" in result.error_message

    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_extracts_json_data_from_output(self, mock_sleep, session, fabric_api_client):
        fabric_api_client.get_livy_statement.return_value = {
            "state": "available",
            "output": {
                "status": "ok",
                "data": {"application/json": {"rows": [1, 2, 3], "schema": "test"}},
            },
        }

        result = session.wait_and_get_statement_result(7)

        assert result.json_data == {"rows": [1, 2, 3], "schema": "test"}


class TestRunStatement:
    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_dispatches_sql_to_submit_livy_sql_statement(
        self, mock_sleep, session, fabric_api_client
    ):
        fabric_api_client.get_livy_session_state.return_value = "idle"
        fabric_api_client.submit_livy_sql_statement.return_value = 10
        fabric_api_client.get_livy_statement.return_value = {
            "state": "available",
            "output": {"status": "ok", "data": {}},
        }

        session.run_statement("SELECT 1", "sql", wait_for_result=True)

        fabric_api_client.submit_livy_sql_statement.assert_called_once_with("SELECT 1")
        fabric_api_client.submit_livy_python_statement.assert_not_called()

    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_dispatches_python_to_submit_livy_python_statement(
        self, mock_sleep, session, fabric_api_client
    ):
        fabric_api_client.get_livy_session_state.return_value = "idle"
        fabric_api_client.submit_livy_python_statement.return_value = 11
        fabric_api_client.get_livy_statement.return_value = {
            "state": "available",
            "output": {"status": "ok", "data": {}},
        }

        session.run_statement("print('hello')", "python", wait_for_result=True)

        fabric_api_client.submit_livy_python_statement.assert_called_once_with("print('hello')")
        fabric_api_client.submit_livy_sql_statement.assert_not_called()

    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_wait_for_result_true_returns_livy_session_result(
        self, mock_sleep, session, fabric_api_client
    ):
        fabric_api_client.get_livy_session_state.return_value = "idle"
        fabric_api_client.submit_livy_sql_statement.return_value = 10
        fabric_api_client.get_livy_statement.return_value = {
            "state": "available",
            "output": {"status": "ok", "data": {}},
        }

        result = session.run_statement("SELECT 1", "sql", wait_for_result=True)

        assert isinstance(result, LivySessionResult)
        assert result.success is True

    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_wait_for_result_false_returns_statement_id(
        self, mock_sleep, session, fabric_api_client
    ):
        fabric_api_client.get_livy_session_state.return_value = "idle"
        fabric_api_client.submit_livy_sql_statement.return_value = 10

        result = session.run_statement("SELECT 1", "sql", wait_for_result=False)

        assert result == 10
        assert isinstance(result, int)

    @patch("dbt.adapters.fabric.fabric_livy_session.time.sleep")
    def test_returns_failed_result_on_submission_error(
        self, mock_sleep, session, fabric_api_client
    ):
        fabric_api_client.get_livy_session_state.return_value = "idle"
        fabric_api_client.submit_livy_sql_statement.side_effect = RuntimeError("API down")

        result = session.run_statement("SELECT 1", "sql", wait_for_result=True)

        assert isinstance(result, LivySessionResult)
        assert result.success is False
        assert "API down" in result.error_message


class TestLivySessionResultToSubmissionResult:
    def test_maps_fields_correctly(self):
        result = LivySessionResult(
            statement_id=42,
            success=True,
            error_message=None,
            status_code="ok",
            json_data={"key": "value"},
        )

        submission = result.to_submission_result("print('hello')")

        assert submission.run_id == "42"
        assert submission.compiled_code == "print('hello')"
        assert submission.success is True
        assert submission.error_message is None

    def test_maps_failed_result(self):
        result = LivySessionResult(
            statement_id=7,
            success=False,
            error_message="something broke",
            status_code="error",
        )

        submission = result.to_submission_result("bad code")

        assert submission.run_id == "7"
        assert submission.compiled_code == "bad code"
        assert submission.success is False
        assert submission.error_message == "something broke"
