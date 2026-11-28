from typing import TYPE_CHECKING

import pytest
import stamina

if TYPE_CHECKING:
    from collections.abc import Iterator

    from stamina.instrumentation import RetryDetails


@pytest.fixture(autouse=True)
def stamina_testing_mode() -> Iterator[None]:
    """Retry without waiting, up to the attempts each retry block configures."""
    with stamina.set_testing(True, attempts=100, cap=True):
        yield


@pytest.fixture
def retry_waits() -> Iterator[list[float]]:
    """Run stamina for real, and collect the wait it schedules before each retry."""
    waits: list[float] = []

    def record_wait(details: RetryDetails) -> None:
        waits.append(details.wait_for)

    stamina.instrumentation.set_on_retry_hooks([record_wait])
    with stamina.set_testing(False):
        yield waits
    stamina.instrumentation.set_on_retry_hooks(None)
