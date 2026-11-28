import pytest

from pipeline.api.tests.apps import app_with_a_cik_path
from pipeline.api.tests.clients import client_for

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    ("path_cik", "response_cik"),
    [
        ("320193", "0000320193"),
        ("0000320193", "0000320193"),
        ("0", "0000000000"),
        ("9999999999", "9999999999"),
    ],
)
async def test_a_cik_is_normalised_and_returned_padded(path_cik: str, response_cik: str) -> None:
    async with client_for(app_with_a_cik_path()) as client:
        response = await client.get(f"/companies/{path_cik}")

    assert response.status_code == 200
    assert response.json() == {"cik": response_cik}


@pytest.mark.parametrize(
    "path_cik",
    [
        "AAPL",
        "00003201930",
        "-320193",
        "3201.93",
        # 320193 in fullwidth digits, which `\d` would accept
        "\uff13\uff12\uff10\uff11\uff19\uff13",
    ],
)
async def test_a_cik_that_is_not_1_to_10_digits_is_a_422(path_cik: str) -> None:
    async with client_for(app_with_a_cik_path()) as client:
        response = await client.get(f"/companies/{path_cik}")

    assert response.status_code == 422
    assert response.json()["errors"][0]["location"] == ["path", "cik"]
