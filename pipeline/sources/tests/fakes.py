import httpx2


class FakeClock:
    """A monotonic clock that only moves when the client sleeps or a response takes time."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class ScriptedSource:
    """Answers each request with the next outcome: a response to return or an error to raise.

    Served through `httpx2.MockTransport`, it keeps the requests it saw.
    """

    def __init__(self, outcomes: list[httpx2.Response | httpx2.TransportError]) -> None:
        self.outcomes = outcomes
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, httpx2.TransportError):
            raise outcome
        return outcome
