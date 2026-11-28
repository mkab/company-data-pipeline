import asyncio
import logging
import time
from datetime import UTC, datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Self

import httpx2
import stamina

from pipeline.sources.exceptions import (
    RetryableStatusError,
    SourceRefusedError,
    SourceUnavailableError,
)
from pipeline.sources.types import FetchedResponse
from pipeline.sources.urls import url_without_query

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from types import TracebackType

    from pipeline.sources.types import SourceSettings

logger = logging.getLogger(__name__)
# httpx2 logs every request at INFO with its query string: the line per attempt below replaces it
logging.getLogger("httpx2").setLevel(logging.WARNING)

# A source sends these when it may answer differently later
RETRYABLE_STATUSES = frozenset(
    {
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    }
)
# Only these two say how long to wait in `Retry-After`
RETRY_AFTER_STATUSES = frozenset({HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.SERVICE_UNAVAILABLE})


def retry_after_backoff(status: int, retry_after: str | None, *, wait_max: float) -> float | None:
    """Return the wait a 429 or 503 asks for in seconds, capped at `wait_max`.

    None means the normal backoff applies:
    another status, no header, or a value that is not a number of seconds (such as an HTTP date).
    """
    if status not in RETRY_AFTER_STATUSES or retry_after is None:
        return None
    if not retry_after.isdigit():
        return None
    return min(float(retry_after), wait_max)


class MinimumIntervalLimiter:
    """Spaces the starts of requests at least `interval` seconds apart, across tasks."""

    def __init__(
        self,
        interval: float,
        *,
        clock: Callable[[], float],
        sleep: Callable[[float], Awaitable[None]],
    ) -> None:
        self._interval = interval
        self._clock = clock
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._next_start: float | None = None

    async def wait_turn(self) -> None:
        """Return once the next request may start."""
        async with self._lock:
            now = self._clock()
            if self._next_start is not None and now < self._next_start:
                await self._sleep(self._next_start - now)
                now = self._next_start
            self._next_start = now + self._interval


class SourceClient:
    """An HTTP client for one source.

    `transport` replaces the network, and `clock` and `sleep` the passing of time, for tests.
    """

    def __init__(
        self,
        settings: SourceSettings,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._clock = clock
        self._limiter = MinimumIntervalLimiter(
            1 / settings.requests_per_second, clock=clock, sleep=sleep
        )
        self._in_flight = asyncio.Semaphore(settings.max_in_flight)
        self._client = httpx2.AsyncClient(
            headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
            timeout=httpx2.Timeout(
                connect=settings.connect_timeout,
                read=settings.read_timeout,
                write=settings.write_timeout,
                pool=settings.pool_timeout,
            ),
            transport=transport,
        )

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.__aexit__(exc_type, exc_value, traceback)

    async def get(self, url: str) -> FetchedResponse:
        """Fetch `url` and return the successful response.

        Raises `SourceRefusedError` on a status retrying will not change,
        and `SourceUnavailableError` once the retries are spent.
        """
        settings = self._settings
        try:
            async for attempt in stamina.retry_context(
                on=self._backoff_for,
                attempts=settings.attempts,
                timeout=settings.retry_timeout,
                wait_initial=settings.wait_initial,
                wait_max=settings.wait_max,
                wait_jitter=settings.wait_jitter,
                name=f"{settings.name} GET {url_without_query(url)}",
            ):
                with attempt:
                    return await self._attempt(url, attempt_number=attempt.num)
        except httpx2.TransportError as error:
            raise SourceUnavailableError(
                f"{settings.name} is unavailable at {url_without_query(url)}: "
                f"{type(error).__name__}"
            ) from error
        except RetryableStatusError as error:
            raise SourceUnavailableError(
                f"{settings.name} is unavailable at {url_without_query(url)}: {error}"
            ) from error
        # stamina either returns from an attempt or raises its last error
        raise AssertionError  # pragma: no cover

    async def _attempt(self, url: str, *, attempt_number: int) -> FetchedResponse:
        async with self._in_flight:
            await self._limiter.wait_turn()
            started = self._clock()
            try:
                response = await self._client.get(url)
            except httpx2.TransportError as error:
                self._log_attempt(url, type(error).__name__, started, attempt_number)
                raise
            self._log_attempt(url, str(response.status_code), started, attempt_number)
        fetched = FetchedResponse(
            url=url,
            status=response.status_code,
            fetched_at=datetime.now(UTC),
            body=response.content,
        )
        if response.status_code in RETRYABLE_STATUSES:
            raise RetryableStatusError(fetched, response.headers.get("Retry-After"))
        if not response.is_success:
            raise SourceRefusedError(self._settings.name, fetched)
        return fetched

    def _log_attempt(self, url: str, outcome: str, started: float, attempt_number: int) -> None:
        elapsed_ms = round((self._clock() - started) * 1000)
        logger.info(
            "GET %s %s in %d ms (attempt %d)",
            url_without_query(url),
            outcome,
            elapsed_ms,
            attempt_number,
        )

    def _backoff_for(self, error: BaseException) -> bool | float:
        """Tell stamina whether to retry `error`, and how long to wait when the source said."""
        if isinstance(error, httpx2.TransportError):
            return True
        if not isinstance(error, RetryableStatusError):
            return False
        backoff = retry_after_backoff(
            error.response.status, error.retry_after, wait_max=self._settings.wait_max
        )
        if backoff is None:
            return True
        return backoff
