import hashlib
from http import HTTPStatus
from typing import TYPE_CHECKING

from pipeline.raw.models import EdgarFetch
from pipeline.raw.repositories import EdgarFetchRepository, EdgarPayloadRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pipeline.raw.models import EdgarDataset
    from pipeline.sources.http import FetchedResponse


class EdgarFetchService:
    def __init__(self, payloads: EdgarPayloadRepository, fetches: EdgarFetchRepository) -> None:
        self.payloads = payloads
        self.fetches = fetches

    @classmethod
    def from_session(cls, session: AsyncSession) -> EdgarFetchService:
        return cls(EdgarPayloadRepository(session), EdgarFetchRepository(session))

    async def record_fetch(
        self, response: FetchedResponse, *, dataset: EdgarDataset, cik: int | None
    ) -> None:
        """Record one fetch, and its payload unless it is already stored.

        `cik` is `None` for the tickers file only.
        A 404 is recorded with no payload.
        The caller's session holds both writes in one transaction.
        """
        payload_id = None
        if response.status != HTTPStatus.NOT_FOUND:
            payload_id = await self._store_payload(response.body)
        await self.fetches.add(
            EdgarFetch(
                dataset=dataset,
                cik=cik,
                url=response.url,
                http_status=response.status,
                fetched_at=response.fetched_at,
                payload_id=payload_id,
            )
        )

    async def _store_payload(self, body: bytes) -> int:
        """Return the id of the payload with this body, inserting it when it is new.

        The hash is over the body bytes exactly as received,
        since `jsonb` does not keep the original formatting or key order.
        """
        sha256 = hashlib.sha256(body).digest()
        inserted_id = await self.payloads.insert_if_absent(
            sha256=sha256, payload_json=body.decode()
        )
        if inserted_id is not None:
            return inserted_id
        return await self.payloads.get_id_by_sha256(sha256)
