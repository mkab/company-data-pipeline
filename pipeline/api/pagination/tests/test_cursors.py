from datetime import date

import pytest

from pipeline.api.pagination.cursors import decode_cursor, encode_cursor
from pipeline.api.pagination.exceptions import InvalidCursorError
from pipeline.api.pagination.tests.types import FactSortKey, FilingSortKey


def test_a_cursor_round_trips_its_sort_key() -> None:
    sort_key = FilingSortKey(filing_date=date(2025, 8, 1), accession_number="0000320193-25-000073")

    assert decode_cursor(encode_cursor(sort_key), FilingSortKey) == sort_key


def test_a_cursor_round_trips_a_null_in_its_sort_key() -> None:
    sort_key = FactSortKey(period_end=date(2025, 9, 27), period_start=None)

    assert decode_cursor(encode_cursor(sort_key), FactSortKey) == sort_key


@pytest.mark.parametrize(
    "cursor",
    [
        "not base64!",
        # Valid base64 of text that is not JSON
        "bm90IGpzb24=",
        # Valid base64 of JSON missing `accession_number`
        "eyJmaWxpbmdfZGF0ZSI6ICIyMDI1LTA4LTAxIn0=",
    ],
)
def test_a_tampered_cursor_does_not_decode(cursor: str) -> None:
    with pytest.raises(InvalidCursorError):
        decode_cursor(cursor, FilingSortKey)
