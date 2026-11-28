from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True)
class PageRequest[SortKey: BaseModel]:
    """The page a request asks for: at most `limit` rows, sorted after `after` (from the start when `None`)."""

    limit: int
    after: SortKey | None
