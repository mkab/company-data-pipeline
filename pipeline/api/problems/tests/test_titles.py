import pytest

from pipeline.api.problems.titles import sentence_case


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("Not Found", "Not found"),
        ("Service Unavailable", "Service unavailable"),
        ("HTTP Version Not Supported", "HTTP version not supported"),
        ("The database is unreachable", "The database is unreachable"),
    ],
)
def test_sentence_case_lowers_every_word_but_the_first_and_acronyms(
    phrase: str, expected: str
) -> None:
    assert sentence_case(phrase) == expected
