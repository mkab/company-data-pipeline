from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pipeline.raw.models import EdgarFetch


class EdgarPayloadRepository(Protocol):
    """The payload storage a service depends on: Postgres in the application, a fake in unit tests."""

    async def insert_if_absent(self, *, sha256: bytes, payload_json: str) -> int | None:
        """Insert a payload and return its id, or `None` when one with this sha256 exists."""
        ...

    async def get_id_by_sha256(self, sha256: bytes) -> int:
        """Return the id of the payload with this sha256, which must exist."""
        ...


class EdgarFetchRepository(Protocol):
    """The fetch storage a service depends on: Postgres in the application, a fake in unit tests."""

    async def add(self, fetch: EdgarFetch) -> None:
        """Insert a fetch row, raising on a constraint violation."""
        ...
