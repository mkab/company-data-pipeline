from http import HTTPStatus
from typing import TYPE_CHECKING

from pipeline.sources.urls import url_without_query

if TYPE_CHECKING:
    from pipeline.sources.types import FetchedResponse


class SourceUnavailableError(Exception):
    """Every attempt failed on a transport error, a rate limit or a server error."""


class SourceRefusedError(Exception):
    """The source answered with a status that retrying will not change.

    `response` is that answer, so a caller can still record it.
    """

    def __init__(self, source_name: str, response: FetchedResponse) -> None:
        message = f"{source_name} refused {url_without_query(response.url)} with status {response.status}"
        if response.status == HTTPStatus.FORBIDDEN:
            message += (
                ": check the User-Agent the source asks for,"
                " or whether it has blocked this IP address"
            )
        super().__init__(message)
        self.response = response


class RetryableStatusError(Exception):
    """A response worth another attempt.

    Internal to `SourceClient`: raised and caught inside its retry block only,
    and never reaches a caller (who gets `SourceUnavailableError` once the retries are spent).
    """

    def __init__(self, response: FetchedResponse, retry_after: str | None) -> None:
        super().__init__(f"status {response.status}")
        self.response = response
        self.retry_after = retry_after
