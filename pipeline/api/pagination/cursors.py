import base64

from pydantic import BaseModel

from pipeline.api.pagination.exceptions import InvalidCursorError


def encode_cursor(sort_key: BaseModel) -> str:
    return base64.urlsafe_b64encode(sort_key.model_dump_json().encode()).decode()


def decode_cursor[SortKey: BaseModel](cursor: str, sort_key_type: type[SortKey]) -> SortKey:
    """Return the sort key the cursor holds.

    Raises `InvalidCursorError` when it is not base64 of a valid `sort_key_type`.
    """
    try:
        return sort_key_type.model_validate_json(base64.urlsafe_b64decode(cursor))
    # binascii.Error (bad base64) and pydantic.ValidationError (bad JSON or key) are both ValueErrors
    except ValueError as error:
        raise InvalidCursorError(cursor) from error
