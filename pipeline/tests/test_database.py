from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa

from pipeline.database import include_managed_schemas, session_scope
from pipeline.raw.models import EdgarPayload
from pipeline.raw.tests.factories import EdgarPayloadFactory

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


class SessionScopeError(Exception):
    pass


async def count_payloads() -> int:
    async with session_scope() as session:
        result = await session.execute(sa.select(sa.func.count()).select_from(EdgarPayload))
        count: int = result.scalar_one()
    return count


async def add_a_payload_then_fail() -> None:
    async with session_scope() as session:
        session.add(EdgarPayloadFactory.build())
        await session.flush()
        raise SessionScopeError


@pytest.mark.anyio
@pytest.mark.usefixtures("database_url_as_ingest")
async def test_session_scope_commits_on_success() -> None:
    async with session_scope() as session:
        session.add(EdgarPayloadFactory.build())

    assert await count_payloads() == 1


@pytest.mark.anyio
@pytest.mark.usefixtures("database_url_as_ingest")
async def test_session_scope_rolls_back_and_reraises_on_error() -> None:
    with pytest.raises(SessionScopeError):
        await add_a_payload_then_fail()

    assert await count_payloads() == 0
