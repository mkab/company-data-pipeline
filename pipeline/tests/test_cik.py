import pytest

from pipeline.tests.types import CikResponse


@pytest.mark.parametrize(
    ("cik", "serialised"),
    [(320193, "0000320193"), (0, "0000000000"), (9999999999, "9999999999")],
)
def test_a_padded_cik_serialises_as_10_digits(cik: int, serialised: str) -> None:
    assert CikResponse(cik=cik).model_dump(mode="json") == {"cik": serialised}
