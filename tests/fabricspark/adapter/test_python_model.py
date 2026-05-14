import pytest

from dbt.tests.adapter.python_model.test_python_model import (
    BasePythonEmptyTests,
    BasePythonIncrementalTests,
    BasePythonModelTests,
    BasePythonSampleTests,
)
from dbt.tests.adapter.python_model.test_spark import BasePySparkTests


class TestPythonModelTestsFabricSpark(BasePythonModelTests):
    pass


class TestPythonIncrementalTestsFabricSpark(BasePythonIncrementalTests):
    pass


class TestPySparkTestsFabricSpark(BasePySparkTests):
    @pytest.mark.skip(
        "TODO: FabricSpark PySpark dataframe type handling differs from standard Spark"
    )
    def test_different_dataframes(self):
        pass


class TestPythonEmptyTestsFabricSpark(BasePythonEmptyTests):
    pass


class TestPythonSampleTestsFabricSpark(BasePythonSampleTests):
    pass
