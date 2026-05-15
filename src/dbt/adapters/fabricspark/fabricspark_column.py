from dataclasses import dataclass

from dbt.adapters.spark.column import SparkColumn


@dataclass
class FabricSparkColumn(SparkColumn):
    table_catalog: str | None = None
    table_comment: str | None = None
    column_comment: str | None = None
