import asyncio
import logging
from datetime import UTC
from typing import TYPE_CHECKING

import httpx2
import pytest

from pipeline.sources.exceptions import SourceRefusedError, SourceUnavailableError
from pipeline.sources.http import SourceClient, retry_after_backoff
from pipeline.sources.tests.fakes import FakeClock, ScriptedSource
from pipeline.sources.types import SourceSettings

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    type Handler = (
        Callable[[httpx2.Request], httpx2.Response]
        | Callable[[httpx2.Request], Coroutine[None, None, httpx2.Response]]
    )

URL = "https://example.com/data.json"


def make_settings(
    *, requests_per_second: float = 5, max_in_flight: int = 5, wait_initial: float = 1.0
) -> SourceSettings:
    return SourceSettings(
        name="Example",
        user_agent="Jane Doe jane@example.com",
        requests_per_second=requests_per_second,
        max_in_flight=max_in_flight,
        wait_initial=wait_initial,
    )


def make_client(
    handler: Handler, clock: FakeClock | None = None, settings: SourceSettings | None = None
) -> SourceClient:
    """Return a client served by `handler`, whose waits only move `clock`."""
    clock = clock or FakeClock()
    return SourceClient(
        settings or make_settings(),
        transport=httpx2.MockTransport(handler),
        clock=clock,
        sleep=clock.sleep,
    )


@pytest.mark.anyio
async def test_a_success_returns_the_body_as_received() -> None:
    source = ScriptedSource([httpx2.Response(200, content=b'{"cik": 1}')])

    async with make_client(source) as client:
        response = await client.get("https://example.com/data.json?page=2")

    assert response.url == "https://example.com/data.json?page=2"
    assert response.status == 200
    assert response.body == b'{"cik": 1}'
    assert response.fetched_at.tzinfo is UTC


@pytest.mark.anyio
async def test_every_request_sends_the_user_agent_and_accepts_json() -> None:
    source = ScriptedSource([httpx2.Response(200, content=b"{}")])

    async with make_client(source) as client:
        await client.get(URL)

    assert source.requests[0].headers["User-Agent"] == "Jane Doe jane@example.com"
    assert source.requests[0].headers["Accept"] == "application/json"


@pytest.mark.anyio
@pytest.mark.parametrize("status", [400, 401, 403, 404, 410])
async def test_a_client_error_is_refused_without_a_retry(status: int) -> None:
    source = ScriptedSource([httpx2.Response(status)])

    async with make_client(source) as client:
        with pytest.raises(SourceRefusedError) as refusal:
            await client.get(URL)

    assert refusal.value.response.status == status
    assert len(source.requests) == 1


@pytest.mark.anyio
async def test_a_404_refusal_keeps_the_response_url_and_time() -> None:
    source = ScriptedSource([httpx2.Response(404, content=b"Not found")])

    async with make_client(source) as client:
        with pytest.raises(SourceRefusedError) as refusal:
            await client.get(URL)

    assert refusal.value.response.url == URL
    assert refusal.value.response.body == b"Not found"
    assert refusal.value.response.fetched_at.tzinfo is UTC


@pytest.mark.anyio
async def test_a_403_refusal_points_at_the_user_agent_or_an_ip_block() -> None:
    source = ScriptedSource([httpx2.Response(403)])

    async with make_client(source) as client:
        with pytest.raises(SourceRefusedError, match=r"User-Agent.*IP address"):
            await client.get(URL)


@pytest.mark.anyio
@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
async def test_a_rate_limit_or_server_error_is_retried(status: int) -> None:
    source = ScriptedSource([httpx2.Response(status), httpx2.Response(200, content=b"{}")])

    async with make_client(source) as client:
        response = await client.get(URL)

    assert response.status == 200
    assert len(source.requests) == 2


@pytest.mark.anyio
async def test_the_wait_a_429_asks_for_replaces_the_backoff(retry_waits: list[float]) -> None:
    # A 60s first backoff would time the test out if the Retry-After of 0 were ignored
    source = ScriptedSource(
        [
            httpx2.Response(429, headers={"Retry-After": "0"}),
            httpx2.Response(200, content=b"{}"),
        ]
    )

    async with make_client(source, settings=make_settings(wait_initial=60)) as client:
        await client.get(URL)

    assert retry_waits == [0.0]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "transport_error", [httpx2.ConnectError("refused"), httpx2.ReadTimeout("too slow")]
)
async def test_a_transport_error_is_retried(transport_error: httpx2.TransportError) -> None:
    source = ScriptedSource([transport_error, httpx2.Response(200, content=b"{}")])

    async with make_client(source) as client:
        response = await client.get(URL)

    assert response.status == 200


@pytest.mark.anyio
async def test_retries_stop_after_five_attempts_and_the_source_is_unavailable() -> None:
    source = ScriptedSource([httpx2.Response(503)] * 6)

    async with make_client(source) as client:
        with pytest.raises(SourceUnavailableError, match="status 503"):
            await client.get(URL)

    assert len(source.requests) == 5


@pytest.mark.anyio
async def test_a_transport_error_on_every_attempt_makes_the_source_unavailable() -> None:
    source = ScriptedSource([httpx2.ConnectError("refused")] * 5)

    async with make_client(source) as client:
        with pytest.raises(SourceUnavailableError, match="ConnectError"):
            await client.get(URL)


@pytest.mark.parametrize(
    ("status", "retry_after", "backoff"),
    [
        (429, "7", 7.0),
        (503, "7", 7.0),
        (429, "120", 30.0),
        (503, "30", 30.0),
    ],
)
def test_a_seconds_retry_after_on_429_or_503_sets_the_backoff_capped_at_wait_max(
    status: int, retry_after: str, backoff: float
) -> None:
    assert retry_after_backoff(status, retry_after, wait_max=30.0) == backoff


@pytest.mark.parametrize(
    ("status", "retry_after"),
    [
        (429, None),
        (429, "Wed, 26 Nov 2026 09:30:00 GMT"),
        (503, "-5"),
        (500, "7"),
        (502, "7"),
    ],
)
def test_other_retries_keep_the_normal_backoff(status: int, retry_after: str | None) -> None:
    assert retry_after_backoff(status, retry_after, wait_max=30.0) is None


@pytest.mark.anyio
async def test_requests_are_spaced_by_the_minimum_interval() -> None:
    clock = FakeClock()
    source = ScriptedSource([httpx2.Response(200, content=b"{}")] * 3)

    async with make_client(source, clock) as client:
        await client.get(URL)
        await client.get(URL)
        await client.get(URL)

    assert clock.sleeps == pytest.approx([0.2, 0.2])


@pytest.mark.anyio
async def test_a_retry_waits_its_turn_like_any_request() -> None:
    clock = FakeClock()
    source = ScriptedSource([httpx2.Response(503), httpx2.Response(200, content=b"{}")])

    async with make_client(source, clock) as client:
        await client.get(URL)

    assert clock.sleeps == pytest.approx([0.2])


@pytest.mark.anyio
async def test_no_more_requests_are_in_flight_than_the_source_allows() -> None:
    in_flight = 0
    peak_in_flight = 0

    async def respond(request: httpx2.Request) -> httpx2.Response:
        nonlocal in_flight, peak_in_flight
        in_flight += 1
        peak_in_flight = max(peak_in_flight, in_flight)
        # Hands control to the other tasks, so every request the semaphore lets in is in flight
        await asyncio.sleep(0)
        in_flight -= 1
        return httpx2.Response(200, content=b"{}")

    client = make_client(respond, settings=make_settings(max_in_flight=2))
    async with client, asyncio.TaskGroup() as task_group:
        task_group.create_task(client.get(URL))
        task_group.create_task(client.get(URL))
        task_group.create_task(client.get(URL))
        task_group.create_task(client.get(URL))

    assert peak_in_flight == 2


@pytest.mark.anyio
async def test_each_attempt_logs_one_line_without_the_query_string(
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock = FakeClock()

    def respond_after_250_ms(request: httpx2.Request) -> httpx2.Response:
        clock.now += 0.25
        return httpx2.Response(200, content=b'{"secret": "body"}')

    client = make_client(respond_after_250_ms, clock)
    with caplog.at_level(logging.INFO):
        async with client:
            await client.get("https://example.com/data.json?token=secret")

    assert [record.getMessage() for record in caplog.records] == [
        "GET https://example.com/data.json 200 in 250 ms (attempt 1)"
    ]


@pytest.mark.anyio
async def test_a_retried_fetch_logs_every_attempt_and_the_scheduled_retry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    source = ScriptedSource([httpx2.ConnectError("refused"), httpx2.Response(200, content=b"{}")])

    with caplog.at_level(logging.INFO):
        async with make_client(source) as client:
            await client.get(URL)

    assert [(record.name, record.getMessage()) for record in caplog.records] == [
        (
            "pipeline.sources.http",
            "GET https://example.com/data.json ConnectError in 0 ms (attempt 1)",
        ),
        ("stamina", "stamina.retry_scheduled"),
        ("pipeline.sources.http", "GET https://example.com/data.json 200 in 0 ms (attempt 2)"),
    ]
