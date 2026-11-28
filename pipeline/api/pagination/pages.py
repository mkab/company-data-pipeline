from typing import TYPE_CHECKING

from pydantic import BaseModel

from pipeline.api.pagination.cursors import encode_cursor
from pipeline.api.pagination.types import Page

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pipeline.pagination.types import PageRequest


def build_page[Row, SortKey: BaseModel](
    rows: Sequence[Row], request: PageRequest[SortKey], sort_key: Callable[[Row], SortKey]
) -> Page[Row]:
    """Return the page of `rows`, the up to `limit + 1` rows the query fetched after the cursor.

    The extra row only says another page follows, so it is left out.
    """
    page_rows = list(rows[: request.limit])
    if len(rows) <= request.limit:
        return Page(data=page_rows, next_cursor=None)
    return Page(data=page_rows, next_cursor=encode_cursor(sort_key(page_rows[-1])))
