from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True)
class PageRequest[SortKey: BaseModel]:
    """The page a request asks for: at most `limit` rows, sorted after `after` (from the start when `None`)."""

    limit: int
    after: SortKey | None


class Page[Row](BaseModel):
    """A list response: `next_cursor` is `None` on the last page."""

    data: list[Row]
    next_cursor: str | None
