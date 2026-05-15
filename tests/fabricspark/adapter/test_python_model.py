from dbt.tests.adapter.python_model.test_python_model import (
    BasePythonEmptyTests,
    BasePythonIncrementalTests,
    BasePythonMetaGetTests,
    BasePythonModelTests,
    BasePythonSampleTests,
)
from dbt.tests.adapter.python_model.test_spark import BasePySparkTests


class TestPythonModelTestsFabricSpark(BasePythonModelTests):
    pass


class TestPythonIncrementalTestsFabricSpark(BasePythonIncrementalTests):
    pass


class TestPySparkTestsFabricSpark(BasePySparkTests):
    pass


class TestPythonEmptyTestsFabricSpark(BasePythonEmptyTests):
    pass


class TestPythonSampleTestsFabricSpark(BasePythonSampleTests):
    pass


class TestPythonMetaGetTestsFabricSpark(BasePythonMetaGetTests):
    pass
