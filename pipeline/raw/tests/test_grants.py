from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

# Each role's rights on raw, as the migration grants them: ingest appends, dbt reads, api has none
pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    ("role_engine", "statement"),
    [
        ("ingest", "SELECT count(*) FROM raw.edgar_fetches"),
        ("ingest", "SELECT count(*) FROM raw.edgar_payloads"),
        ("ingest", "INSERT INTO raw.edgar_payloads (sha256, payload) VALUES ('\\x00', '{}')"),
        ("dbt", "SELECT count(*) FROM raw.edgar_fetches"),
        ("dbt", "SELECT count(*) FROM raw.edgar_payloads"),
    ],
    indirect=["role_engine"],
)
async def test_a_role_may_run_what_its_grants_allow(
    role_engine: AsyncEngine, statement: str
) -> None:
    async with role_engine.begin() as connection:
        await connection.execute(sa.text(statement))


@pytest.mark.parametrize(
    ("role_engine", "statement"),
    [
        ("ingest", "UPDATE raw.edgar_fetches SET url = ''"),
        ("ingest", "UPDATE raw.edgar_payloads SET payload = '{}'"),
        ("ingest", "DELETE FROM raw.edgar_fetches"),
        ("ingest", "DELETE FROM raw.edgar_payloads"),
        ("ingest", "TRUNCATE raw.edgar_fetches"),
        ("dbt", "INSERT INTO raw.edgar_payloads (sha256, payload) VALUES ('\\x00', '{}')"),
        ("dbt", "UPDATE raw.edgar_fetches SET url = ''"),
        ("dbt", "DELETE FROM raw.edgar_payloads"),
        ("api", "SELECT count(*) FROM raw.edgar_fetches"),
        ("api", "SELECT count(*) FROM raw.edgar_payloads"),
    ],
    indirect=["role_engine"],
)
async def test_a_role_is_refused_what_its_grants_do_not_allow(
    role_engine: AsyncEngine, statement: str
) -> None:
    async with role_engine.begin() as connection:
        with pytest.raises(ProgrammingError, match="permission denied"):
            await connection.execute(sa.text(statement))
