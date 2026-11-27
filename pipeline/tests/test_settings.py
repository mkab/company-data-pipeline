import pydantic
import pytest

from pipeline.settings import EdgarSettings


def test_the_edgar_user_agent_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EDGAR_USER_AGENT", "Jane Doe jane@example.com")

    assert EdgarSettings().edgar_user_agent == "Jane Doe jane@example.com"  # type: ignore[call-arg]  # pydantic-settings fills the field from env vars


def test_a_missing_edgar_user_agent_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EDGAR_USER_AGENT", raising=False)

    with pytest.raises(pydantic.ValidationError, match="edgar_user_agent"):
        EdgarSettings()  # type: ignore[call-arg]  # pydantic-settings fills the field from env vars


def test_an_empty_edgar_user_agent_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EDGAR_USER_AGENT", "")

    with pytest.raises(pydantic.ValidationError, match="edgar_user_agent"):
        EdgarSettings()  # type: ignore[call-arg]  # pydantic-settings fills the field from env vars
