import httpx2

from pipeline.sources.edgar.client import TICKERS_URL, company_facts_url, submissions_url

TICKERS_BODY = (
    b'{"fields":["cik","name","ticker","exchange"],'
    b'"data":[[320193,"Apple Inc.","AAPL","Nasdaq"],'
    b'[2053456,"Generation Essentials Group","TGE","NYSE"]]}'
)


def submissions_body(cik: int, name: str) -> bytes:
    return f'{{"cik":"{cik:010d}","name":"{name}","filings":{{"recent":{{}}}}}}'.encode()


def company_facts_body(cik: int, name: str) -> bytes:
    return f'{{"cik":{cik},"entityName":"{name}","facts":{{"dei":{{}}}}}}'.encode()


class FakeEdgar:
    """Answers each EDGAR URL with its own response, whatever order the requests come in.

    Served through `httpx2.MockTransport`.
    Apple (320193) has submissions and facts,
    and Generation Essentials Group (2053456) has submissions and a facts 404.
    `answer` replaces the response to one URL, with a status and a body.
    """

    def __init__(self) -> None:
        self.responses: dict[str, tuple[int, bytes]] = {
            TICKERS_URL: (200, TICKERS_BODY),
            submissions_url(320193): (200, submissions_body(320193, "Apple Inc.")),
            company_facts_url(320193): (200, company_facts_body(320193, "Apple Inc.")),
            submissions_url(2053456): (
                200,
                submissions_body(2053456, "Generation Essentials Group"),
            ),
            company_facts_url(2053456): (404, b"<html>Not found</html>"),
        }

    def answer(self, url: str, *, status: int, body: bytes) -> None:
        self.responses[url] = (status, body)

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        status, body = self.responses[str(request.url)]
        return httpx2.Response(status, content=body)
