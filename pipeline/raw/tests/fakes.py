from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.raw.models import EdgarFetch


class FakeEdgarPayloadRepository:
    """Keeps payloads in memory, keyed by sha256, with ids counting from 1."""

    def __init__(self) -> None:
        self.payloads: dict[bytes, tuple[int, str]] = {}

    async def insert_if_absent(self, *, sha256: bytes, payload_json: str) -> int | None:
        if sha256 in self.payloads:
            return None
        payload_id = len(self.payloads) + 1
        self.payloads[sha256] = (payload_id, payload_json)
        return payload_id

    async def get_id_by_sha256(self, sha256: bytes) -> int:
        payload_id, _ = self.payloads[sha256]
        return payload_id


class FakeEdgarFetchRepository:
    """Keeps the added fetches in memory, in order."""

    def __init__(self) -> None:
        self.fetches: list[EdgarFetch] = []

    async def add(self, fetch: EdgarFetch) -> None:
        self.fetches.append(fetch)
