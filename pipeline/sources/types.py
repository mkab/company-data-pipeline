from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class SourceSettings:
    """How one source is called: who we are, how fast, and how patiently.

    Durations are in seconds.
    `retry_timeout` caps the time spent on all the attempts of one fetch.
    """

    name: str
    user_agent: str
    requests_per_second: float
    max_in_flight: int
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    write_timeout: float = 5.0
    pool_timeout: float = 5.0
    attempts: int = 5
    retry_timeout: float = 60.0
    wait_initial: float = 1.0
    wait_max: float = 30.0
    wait_jitter: float = 1.0


@dataclass(frozen=True)
class FetchedResponse:
    """One response from a source, with its body exactly as received."""

    url: str
    status: int
    fetched_at: datetime
    body: bytes
