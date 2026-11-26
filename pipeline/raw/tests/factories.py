from datetime import UTC, datetime
from http import HTTPStatus

from factory.base import Factory

from pipeline.sources.http import FetchedResponse


class FetchedResponseFactory(Factory[FetchedResponse]):
    class Meta:
        model = FetchedResponse

    url = "https://data.sec.gov/submissions/CIK0000320193.json"
    status = HTTPStatus.OK
    fetched_at = datetime(2026, 11, 26, 9, 30, tzinfo=UTC)
    body = b'{"cik": "0000320193", "name": "Apple Inc."}'
