from datetime import date

from pipeline.api.pagination.cursors import encode_cursor
from pipeline.api.pagination.pages import build_page
from pipeline.api.pagination.tests.types import Filing, FilingSortKey
from pipeline.api.pagination.types import Page, PageRequest

FIRST_FILING = Filing(
    filing_date=date(2025, 10, 31), accession_number="0000320193-25-000079", form="10-K"
)
SECOND_FILING = Filing(
    filing_date=date(2025, 8, 1), accession_number="0000320193-25-000073", form="10-Q"
)
THIRD_FILING = Filing(
    filing_date=date(2025, 5, 2), accession_number="0000320193-25-000057", form="10-Q"
)


def test_build_page_with_an_extra_row_points_at_the_last_row_kept() -> None:
    request = PageRequest[FilingSortKey](limit=2, after=None)

    page = build_page([FIRST_FILING, SECOND_FILING, THIRD_FILING], request, Filing.sort_key)

    assert page.data == [FIRST_FILING, SECOND_FILING]
    assert page.next_cursor == encode_cursor(
        FilingSortKey(filing_date=date(2025, 8, 1), accession_number="0000320193-25-000073")
    )


def test_build_page_without_an_extra_row_is_the_last_page() -> None:
    request = PageRequest[FilingSortKey](limit=2, after=None)

    page = build_page([FIRST_FILING, SECOND_FILING], request, Filing.sort_key)

    assert page == Page(data=[FIRST_FILING, SECOND_FILING], next_cursor=None)
