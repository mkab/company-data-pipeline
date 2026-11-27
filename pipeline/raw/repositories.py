from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, insert

from pipeline.raw.models import EdgarPayload

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pipeline.raw.models import EdgarFetch


class EdgarPayloadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_if_absent(self, *, sha256: bytes, payload_json: str) -> int | None:
        """Insert a payload and return its id, or `None` when one with this sha256 exists."""
        inserted_id: int | None = await self.session.scalar(
            insert(EdgarPayload)
            .values(
                sha256=sha256,
                # Cast in the database, so the JSON is parsed once and never re-serialised in Python
                payload=sa.cast(sa.literal(payload_json, sa.Text), JSONB),
            )
            .on_conflict_do_nothing(index_elements=[EdgarPayload.sha256])
            .returning(EdgarPayload.id)
        )
        return inserted_id

    async def get_id_by_sha256(self, sha256: bytes) -> int:
        """Return the id of the payload with this sha256, which must exist."""
        result = await self.session.execute(
            sa.select(EdgarPayload.id).where(EdgarPayload.sha256 == sha256)
        )
        return result.scalar_one()


class EdgarFetchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, fetch: EdgarFetch) -> None:
        """Insert a fetch row, flushed so a constraint violation is raised here."""
        self.session.add(fetch)
        await self.session.flush()
