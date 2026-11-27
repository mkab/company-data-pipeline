from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class FetchedResponse:
    """One response from a source, with its body exactly as received."""

    url: str
    status: int
    fetched_at: datetime
    body: bytes
