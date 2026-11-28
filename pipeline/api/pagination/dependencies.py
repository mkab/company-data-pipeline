from typing import TYPE_CHECKING, Annotated

from fastapi import Query
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from pipeline.api.pagination.constants import (
    DEFAULT_PAGE_LIMIT,
    INVALID_CURSOR_MESSAGE,
    MAX_PAGE_LIMIT,
)
from pipeline.api.pagination.cursors import decode_cursor
from pipeline.api.pagination.exceptions import InvalidCursorError
from pipeline.api.pagination.types import PageRequest

if TYPE_CHECKING:
    from collections.abc import Callable


def page_request[SortKey: BaseModel](
    sort_key_type: type[SortKey],
) -> Callable[[int, str | None], PageRequest[SortKey]]:
    """Return the dependency that reads `limit` and `cursor` for a list sorted by `sort_key_type`.

    A cursor that does not decode is a 422, like any other bad query parameter.
    """

    def read_page_request(
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
        cursor: Annotated[
            str | None, Query(description="The `next_cursor` of the previous page")
        ] = None,
    ) -> PageRequest[SortKey]:
        if cursor is None:
            return PageRequest(limit=limit, after=None)
        try:
            after = decode_cursor(cursor, sort_key_type)
        except InvalidCursorError as error:
            raise RequestValidationError(
                [
                    {
                        "type": "value_error",
                        "loc": ("query", "cursor"),
                        "msg": INVALID_CURSOR_MESSAGE,
                        "input": cursor,
                    }
                ]
            ) from error
        return PageRequest(limit=limit, after=after)

    return read_page_request
