from dataclasses import dataclass

from dbt.adapters.base.relation import Policy
from dbt_common.dataclass_schema import StrEnum


class FabricRelationType(StrEnum):
    Table = "table"
    View = "view"
    CTE = "cte"


class FabricIncludePolicy(Policy):
    database: bool = True
    schema: bool = True
    identifier: bool = True


@dataclass
class FabricQuotePolicy(Policy):
    database: bool = False
    schema: bool = False
    identifier: bool = False
