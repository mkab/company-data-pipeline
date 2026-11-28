"""Keyset pagination: a page holds up to `limit` rows, and `next_cursor` resumes after its last one.

A cursor is the last row's sort key, as base64 of its JSON, opaque to the client.
Each list declares its sort key as a pydantic model,
and its query fetches `limit + 1` rows after the key,
so `build_page` knows whether another page follows.
"""

import base64
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

from fastapi import Query
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 1000

INVALID_CURSOR_MESSAGE = "Cursor is not one a previous page returned"


class InvalidCursorError(ValueError):
    pass


@dataclass(frozen=True)
class PageRequest[SortKey: BaseModel]:
    """The page a request asks for: at most `limit` rows, sorted after `after` (from the start when `None`)."""

    limit: int
    after: SortKey | None


class Page[Row](BaseModel):
    """A list response: `next_cursor` is `None` on the last page."""

    data: list[Row]
    next_cursor: str | None


def encode_cursor(sort_key: BaseModel) -> str:
    return base64.urlsafe_b64encode(sort_key.model_dump_json().encode()).decode()


def decode_cursor[SortKey: BaseModel](cursor: str, sort_key_type: type[SortKey]) -> SortKey:
    """Return the sort key the cursor holds.

    Raises `InvalidCursorError` when it is not base64 of a valid `sort_key_type`,
    such as a cursor edited by hand.
    """
    try:
        return sort_key_type.model_validate_json(base64.urlsafe_b64decode(cursor))
    # binascii.Error (bad base64) and pydantic.ValidationError (bad JSON or key) are both ValueErrors
    except ValueError as error:
        raise InvalidCursorError(cursor) from error


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
