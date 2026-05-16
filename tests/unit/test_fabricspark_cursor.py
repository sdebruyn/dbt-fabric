from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest
from dbt_common.exceptions import DbtRuntimeError

from dbt.adapters.fabric.fabric_livy_session import LivySessionResult
from dbt.adapters.fabricspark.fabricspark_cursor import FabricSparkCursor

SAMPLE_FIELDS = [
    {"name": "id", "type": "int", "nullable": False},
    {"name": "name", "type": "string", "nullable": True},
    {"name": "score", "type": "double", "nullable": True},
]

SAMPLE_ROWS = [
    (1, "alice", 9.5),
    (2, "bob", 8.0),
    (3, "carol", 7.5),
]


def _make_cursor_with_rows(
    rows: list[tuple[Any, ...]], fields: list[dict[str, Any]]
) -> FabricSparkCursor:
    cursor = FabricSparkCursor(connection=object())
    cursor._result = LivySessionResult(
        statement_id=1,
        success=True,
        json_data={"data": [], "schema": {"fields": fields}},
    )
    cursor._rows = [tuple(r) for r in rows]
    cursor._position = 0
    return cursor


class TestConvertValue:
    @pytest.mark.parametrize(
        "spark_type",
        ["long", "bigint", "int", "integer", "short", "smallint", "byte", "tinyint"],
    )
    def test_integer_types(self, spark_type: str):
        assert FabricSparkCursor._convert_value("42", spark_type) == 42
        assert isinstance(FabricSparkCursor._convert_value("42", spark_type), int)

    @pytest.mark.parametrize("spark_type", ["float", "double"])
    def test_float_types(self, spark_type: str):
        assert FabricSparkCursor._convert_value("3.14", spark_type) == 3.14
        assert isinstance(FabricSparkCursor._convert_value("3.14", spark_type), float)

    def test_decimal(self):
        result = FabricSparkCursor._convert_value("12.34", "decimal(10,2)")
        assert result == Decimal("12.34")
        assert isinstance(result, Decimal)

    def test_decimal_without_params(self):
        result = FabricSparkCursor._convert_value("99", "decimal")
        assert result == Decimal("99")
        assert isinstance(result, Decimal)

    @pytest.mark.parametrize(
        ("input_val", "expected"),
        [
            (True, True),
            (False, False),
            ("true", True),
            ("false", False),
            ("1", True),
            ("TRUE", True),
            ("False", False),
            ("0", False),
        ],
    )
    def test_boolean(self, input_val: Any, expected: bool):
        result = FabricSparkCursor._convert_value(input_val, "boolean")
        assert result is expected

    def test_date_from_string(self):
        result = FabricSparkCursor._convert_value("2024-03-15", "date")
        assert result == date(2024, 3, 15)
        assert isinstance(result, date)

    def test_date_passthrough(self):
        d = date(2024, 3, 15)
        result = FabricSparkCursor._convert_value(d, "date")
        assert result is d

    def test_timestamp_from_string(self):
        result = FabricSparkCursor._convert_value("2024-03-15T10:30:00", "timestamp")
        assert result == datetime(2024, 3, 15, 10, 30, 0)
        assert isinstance(result, datetime)

    def test_timestamp_passthrough(self):
        dt = datetime(2024, 3, 15, 10, 30, 0)
        result = FabricSparkCursor._convert_value(dt, "timestamp")
        assert result is dt

    def test_binary_from_hex_string(self):
        result = FabricSparkCursor._convert_value("deadbeef", "binary")
        assert result == bytes.fromhex("deadbeef")
        assert isinstance(result, bytes)

    def test_binary_passthrough(self):
        b = b"\xde\xad"
        result = FabricSparkCursor._convert_value(b, "binary")
        assert result is b

    @pytest.mark.parametrize("spark_type", ["string", "void", "unknown_type", "array<int>"])
    def test_passthrough_types(self, spark_type: str):
        assert FabricSparkCursor._convert_value("hello", spark_type) == "hello"

    @pytest.mark.parametrize(
        "spark_type",
        [
            "int",
            "long",
            "float",
            "double",
            "decimal(10,2)",
            "boolean",
            "date",
            "timestamp",
            "binary",
            "string",
            "void",
        ],
    )
    def test_none_returns_none(self, spark_type: str):
        assert FabricSparkCursor._convert_value(None, spark_type) is None

    def test_case_insensitive_type(self):
        assert FabricSparkCursor._convert_value("42", "INT") == 42
        assert FabricSparkCursor._convert_value("42", "Long") == 42


class TestFormatParam:
    def test_none(self):
        assert FabricSparkCursor._format_param(None) == "NULL"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (True, "TRUE"),
            (False, "FALSE"),
        ],
    )
    def test_bool(self, value: bool, expected: str):
        assert FabricSparkCursor._format_param(value) == expected

    def test_int(self):
        assert FabricSparkCursor._format_param(42) == "42"

    def test_decimal(self):
        assert FabricSparkCursor._format_param(Decimal("12.34")) == "12.34"

    def test_float(self):
        assert FabricSparkCursor._format_param(1.5) == "1.5"

    def test_float_precision(self):
        result = FabricSparkCursor._format_param(0.1 + 0.2)
        assert result == repr(0.1 + 0.2)

    def test_datetime(self):
        dt = datetime(2024, 3, 15, 10, 30, 0)
        assert FabricSparkCursor._format_param(dt) == "'2024-03-15T10:30:00'"

    def test_date(self):
        d = date(2024, 3, 15)
        assert FabricSparkCursor._format_param(d) == "'2024-03-15'"

    def test_bytes(self):
        assert FabricSparkCursor._format_param(b"\xde\xad") == "X'dead'"

    def test_string(self):
        assert FabricSparkCursor._format_param("hello") == "'hello'"

    def test_string_with_single_quotes(self):
        assert FabricSparkCursor._format_param("it's a test") == "'it''s a test'"

    def test_bool_before_int(self):
        assert FabricSparkCursor._format_param(True) == "TRUE"
        assert FabricSparkCursor._format_param(1) == "1"


class TestCursorFetch:
    def test_fetchone_returns_rows_sequentially(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        assert cursor.fetchone() == (1, "alice", 9.5)
        assert cursor.fetchone() == (2, "bob", 8.0)
        assert cursor.fetchone() == (3, "carol", 7.5)

    def test_fetchone_returns_none_at_end(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        for _ in range(3):
            cursor.fetchone()
        assert cursor.fetchone() is None

    def test_fetchone_empty_result(self):
        cursor = _make_cursor_with_rows([], SAMPLE_FIELDS)
        assert cursor.fetchone() is None

    def test_fetchmany_respects_size(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        result = cursor.fetchmany(2)
        assert len(result) == 2
        assert result[0] == (1, "alice", 9.5)
        assert result[1] == (2, "bob", 8.0)

    def test_fetchmany_defaults_to_arraysize(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.arraysize = 2
        result = cursor.fetchmany()
        assert len(result) == 2

    def test_fetchmany_at_end(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.fetchall()
        result = cursor.fetchmany(2)
        assert result == []

    def test_fetchmany_partial_at_end(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.fetchmany(2)
        result = cursor.fetchmany(5)
        assert len(result) == 1
        assert result[0] == (3, "carol", 7.5)

    def test_fetchall_returns_all_rows(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        result = cursor.fetchall()
        assert len(result) == 3
        assert result == list(SAMPLE_ROWS)

    def test_fetchall_returns_remaining_rows(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.fetchone()
        result = cursor.fetchall()
        assert len(result) == 2
        assert result[0] == (2, "bob", 8.0)

    def test_fetchall_at_end(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.fetchall()
        result = cursor.fetchall()
        assert result == []

    def test_check_result_raises_without_execute(self):
        cursor = FabricSparkCursor(connection=object())
        with pytest.raises(DbtRuntimeError, match="No result set"):
            cursor.fetchone()

    def test_check_result_raises_for_fetchmany(self):
        cursor = FabricSparkCursor(connection=object())
        with pytest.raises(DbtRuntimeError, match="No result set"):
            cursor.fetchmany()

    def test_check_result_raises_for_fetchall(self):
        cursor = FabricSparkCursor(connection=object())
        with pytest.raises(DbtRuntimeError, match="No result set"):
            cursor.fetchall()


class TestCursorScroll:
    def test_scroll_relative_forward(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.scroll(2, mode="relative")
        assert cursor.fetchone() == (3, "carol", 7.5)

    def test_scroll_relative_backward(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.fetchall()
        cursor.scroll(-2, mode="relative")
        assert cursor.fetchone() == (2, "bob", 8.0)

    def test_scroll_absolute(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.fetchall()
        cursor.scroll(1, mode="absolute")
        assert cursor.fetchone() == (2, "bob", 8.0)

    def test_scroll_absolute_to_start(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.fetchall()
        cursor.scroll(0, mode="absolute")
        assert cursor.fetchone() == (1, "alice", 9.5)

    def test_scroll_relative_out_of_range(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        with pytest.raises(IndexError):
            cursor.scroll(10, mode="relative")

    def test_scroll_relative_negative_out_of_range(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        with pytest.raises(IndexError):
            cursor.scroll(-1, mode="relative")

    def test_scroll_absolute_out_of_range(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        with pytest.raises(IndexError):
            cursor.scroll(10, mode="absolute")

    def test_scroll_absolute_negative(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        with pytest.raises(IndexError):
            cursor.scroll(-1, mode="absolute")

    def test_scroll_without_result_raises(self):
        cursor = FabricSparkCursor(connection=object())
        with pytest.raises(DbtRuntimeError, match="No result set"):
            cursor.scroll(1)


class TestCursorState:
    def test_rowcount_before_execute(self):
        cursor = FabricSparkCursor(connection=object())
        assert cursor.rowcount == -1

    def test_rowcount_after_result(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        assert cursor.rowcount == 3

    def test_rowcount_empty_result(self):
        cursor = _make_cursor_with_rows([], SAMPLE_FIELDS)
        assert cursor.rowcount == 0

    def test_description_before_execute(self):
        cursor = FabricSparkCursor(connection=object())
        assert cursor.description is None

    def test_description_returns_field_tuples(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        desc = cursor.description
        assert desc is not None
        assert len(desc) == 3
        assert desc[0] == ("id", "int", None, None, None, None, False)
        assert desc[1] == ("name", "string", None, None, None, None, True)
        assert desc[2] == ("score", "double", None, None, None, None, True)

    def test_description_no_schema(self):
        cursor = FabricSparkCursor(connection=object())
        cursor._result = LivySessionResult(
            statement_id=1,
            success=True,
            json_data={"data": []},
        )
        assert cursor.description is None

    def test_arraysize_default(self):
        cursor = FabricSparkCursor(connection=object())
        assert cursor.arraysize == 1

    def test_arraysize_setter(self):
        cursor = FabricSparkCursor(connection=object())
        cursor.arraysize = 10
        assert cursor.arraysize == 10

    def test_rownumber_before_execute(self):
        cursor = FabricSparkCursor(connection=object())
        assert cursor.rownumber is None

    def test_rownumber_tracks_position(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        assert cursor.rownumber == 0
        cursor.fetchone()
        assert cursor.rownumber == 1
        cursor.fetchone()
        assert cursor.rownumber == 2

    def test_close_clears_state(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.close()
        assert cursor._connection is None
        assert cursor._result is None
        assert cursor._rows is None
        assert cursor._position == 0
        assert cursor._statement_id is None

    def test_statement_id_before_execute(self):
        cursor = FabricSparkCursor(connection=object())
        assert cursor.statement_id is None

    def test_statement_id_after_result(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        assert cursor.statement_id == 1

    def test_status_code_before_execute(self):
        cursor = FabricSparkCursor(connection=object())
        assert cursor.status_code is None

    def test_messages_returns_empty_list(self):
        cursor = FabricSparkCursor(connection=object())
        assert cursor.messages == []


class TestCursorIterator:
    def test_iter_returns_self(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        assert iter(cursor) is cursor

    def test_next_returns_rows(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        assert next(cursor) == (1, "alice", 9.5)
        assert next(cursor) == (2, "bob", 8.0)

    def test_next_raises_stop_iteration(self):
        cursor = _make_cursor_with_rows([], SAMPLE_FIELDS)
        with pytest.raises(StopIteration):
            next(cursor)

    def test_for_loop_iteration(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        collected = list(cursor)
        assert collected == list(SAMPLE_ROWS)

    def test_iteration_after_partial_fetch(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.fetchone()
        remaining = list(cursor)
        assert len(remaining) == 2
        assert remaining[0] == (2, "bob", 8.0)


class TestCursorContextManager:
    def test_enter_returns_cursor(self):
        cursor = FabricSparkCursor(connection=object())
        assert cursor.__enter__() is cursor

    def test_exit_closes_cursor(self):
        cursor = _make_cursor_with_rows(SAMPLE_ROWS, SAMPLE_FIELDS)
        cursor.__exit__(None, None, None)
        assert cursor._connection is None
        assert cursor._result is None
        assert cursor._rows is None

    def test_with_statement(self):
        cursor = FabricSparkCursor(connection=object())
        with cursor as c:
            assert c is cursor
        assert cursor._connection is None

    def test_exit_propagates_exceptions(self):
        cursor = FabricSparkCursor(connection=object())
        result = cursor.__exit__(ValueError, ValueError("test"), None)
        assert result is False
