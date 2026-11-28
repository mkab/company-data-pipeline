from pydantic import BaseModel


class Page[Row](BaseModel):
    """A list response: `next_cursor` is `None` on the last page."""

    data: list[Row]
    next_cursor: str | None
