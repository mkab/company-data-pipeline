from typing import TYPE_CHECKING

import httpx2
import pytest
import stamina

from pipeline.ingest.tests.fakes import FakeEdgar
from pipeline.ingest.tracked_companies import TrackedCompany
from pipeline.sources.edgar.client import EdgarClient, edgar_source_settings
from pipeline.sources.http import SourceClient
from pipeline.sources.tests.fakes import FakeClock

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def stamina_testing_mode() -> Iterator[None]:
    """Retry without waiting, so a source that stays down fails fast."""
    with stamina.set_testing(True, attempts=3):
        yield


@pytest.fixture
def fake_edgar() -> FakeEdgar:
    return FakeEdgar()


@pytest.fixture
def edgar(fake_edgar: FakeEdgar) -> EdgarClient:
    """Return an EDGAR client over `fake_edgar`, whose rate limit waits on a fake clock."""
    clock = FakeClock()
    return EdgarClient(
        SourceClient(
            edgar_source_settings("Jane Doe jane@example.com"),
            transport=httpx2.MockTransport(fake_edgar),
            clock=clock,
            sleep=clock.sleep,
        )
    )


@pytest.fixture
def tracked_companies() -> list[TrackedCompany]:
    """Apple, and Generation Essentials Group, which has no company facts."""
    return [
        TrackedCompany(cik=320193, name="Apple Inc."),
        TrackedCompany(cik=2053456, name="Generation Essentials Group"),
    ]
