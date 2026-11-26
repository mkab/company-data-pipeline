import hashlib
from http import HTTPStatus
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, insert

from pipeline.raw.tables import edgar_fetches, edgar_payloads

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

    from pipeline.raw.tables import EdgarDataset
    from pipeline.sources.http import FetchedResponse


async def record_fetch(
    engine: AsyncEngine, response: FetchedResponse, *, dataset: EdgarDataset, cik: int | None
) -> None:
    """Record one fetch, and its payload unless it is already stored, in one transaction.

    `cik` is `None` for the tickers file only.
    A 404 is recorded with no payload.
    """
    async with engine.begin() as connection:
        payload_id = None
        if response.status != HTTPStatus.NOT_FOUND:
            payload_id = await store_payload(connection, response.body)
        await connection.execute(
            sa.insert(edgar_fetches).values(
                dataset=dataset,
                cik=cik,
                url=response.url,
                http_status=response.status,
                fetched_at=response.fetched_at,
                payload_id=payload_id,
            )
        )


async def store_payload(connection: AsyncConnection, body: bytes) -> int:
    """Return the id of the payload with this body, inserting it when it is new.

    The hash is over the body bytes exactly as received,
    since `jsonb` does not keep the original formatting or key order.
    """
    sha256 = hashlib.sha256(body).digest()
    inserted_id: int | None = await connection.scalar(
        insert(edgar_payloads)
        .values(
            sha256=sha256,
            # Cast in the database, so the body is parsed once and never re-serialised in Python
            payload=sa.cast(sa.literal(body.decode(), sa.Text), JSONB),
        )
        .on_conflict_do_nothing(index_elements=[edgar_payloads.c.sha256])
        .returning(edgar_payloads.c.id)
    )
    if inserted_id is not None:
        return inserted_id
    existing = await connection.execute(
        sa.select(edgar_payloads.c.id).where(edgar_payloads.c.sha256 == sha256)
    )
    existing_id: int = existing.scalar_one()
    return existing_id
