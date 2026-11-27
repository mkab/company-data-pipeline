from typing import TYPE_CHECKING

import pytest
import stamina

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def stamina_testing_mode() -> Iterator[None]:
    """Retry without waiting, up to the attempts each retry block configures."""
    with stamina.set_testing(True, attempts=100, cap=True):
        yield
