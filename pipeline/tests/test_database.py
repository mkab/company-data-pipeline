from typing import TYPE_CHECKING

import pytest

from pipeline.database import include_managed_schemas

if TYPE_CHECKING:
    from alembic.runtime.environment import NameFilterType


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ("raw", True),
        (None, True),
        ("staging", False),
        ("curated", False),
    ],
)
def test_include_managed_schemas_keeps_only_the_alembic_schemas(
    schema: str | None, expected: bool
) -> None:
    assert include_managed_schemas(schema, "schema", {}) is expected


@pytest.mark.parametrize("type_", ["table", "column", "index"])
def test_include_managed_schemas_keeps_every_name_below_a_schema(type_: NameFilterType) -> None:
    assert include_managed_schemas("company", type_, {"schema_name": "raw"}) is True
