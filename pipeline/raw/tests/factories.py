from datetime import UTC, datetime
from http import HTTPStatus

from factory.base import Factory

from pipeline.raw.models import EdgarDataset, EdgarFetch, EdgarPayload


class EdgarPayloadFactory(Factory[EdgarPayload]):
    class Meta:
        model = EdgarPayload

    sha256 = b"\x01"
    payload: object = {"cik": "0000320193"}


class EdgarFetchFactory(Factory[EdgarFetch]):
    """A recorded companyfacts 404, the one fetch that needs no payload row."""

    class Meta:
        model = EdgarFetch

    dataset = EdgarDataset.COMPANY_FACTS
    cik: int | None = 1000045
    url = "https://data.sec.gov/api/xbrl/companyfacts/CIK0001000045.json"
    http_status = HTTPStatus.NOT_FOUND.value
    fetched_at = datetime(2026, 11, 26, 9, 30, tzinfo=UTC)
    payload_id = None
