import logging
from typing import TYPE_CHECKING

import pytest

from pipeline.ingest.__main__ import ingest, main
from pipeline.sources.edgar.client import submissions_url

if TYPE_CHECKING:
    from pipeline.ingest.tests.fakes import FakeEdgar
    from pipeline.ingest.tracked_companies import TrackedCompany
    from pipeline.sources.edgar.client import EdgarClient


@pytest.mark.anyio
@pytest.mark.usefixtures("database_url_as_ingest")
async def test_a_run_that_records_every_fetch_exits_with_zero(
    edgar: EdgarClient, tracked_companies: list[TrackedCompany]
) -> None:
    assert await ingest(edgar, tracked_companies) == 0


@pytest.mark.anyio
@pytest.mark.usefixtures("database_url_as_ingest")
async def test_a_run_with_a_failed_fetch_exits_with_one(
    edgar: EdgarClient, fake_edgar: FakeEdgar, tracked_companies: list[TrackedCompany]
) -> None:
    fake_edgar.answer(submissions_url(320193), status=403, body=b"<html>Forbidden</html>")

    assert await ingest(edgar, tracked_companies) == 1


def test_the_cli_refuses_to_start_without_an_edgar_user_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EDGAR_USER_AGENT", raising=False)

    assert main() == 1


def test_the_cli_says_why_it_refuses_to_start(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("EDGAR_USER_AGENT", raising=False)

    with caplog.at_level(logging.ERROR):
        main()

    [record] = caplog.records
    assert record.getMessage() == (
        "EDGAR_USER_AGENT is required: "
        'set it to a name and a contact email, such as "Jane Doe jane@example.com"'
    )
