import os

import pytest

from pipeline.settings import EdgarSettings
from pipeline.sources.edgar.client import EdgarClient

# Replaying a cassette matches requests on method and URL only, so any User-Agent does
REPLAY_USER_AGENT = "Replay replay@example.com"


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, object]:
    """Keep the User-Agent (a name and an email) out of the cassettes, and their bodies readable."""
    return {"filter_headers": ["user-agent"], "decode_compressed_response": True}


@pytest.fixture
def edgar() -> EdgarClient:
    """Return an EDGAR client for cassette tests.

    `make record-cassettes` records with the real `EDGAR_USER_AGENT` from the environment.
    """
    user_agent = os.environ.get("EDGAR_USER_AGENT") or REPLAY_USER_AGENT
    return EdgarClient.from_settings(EdgarSettings(edgar_user_agent=user_agent))
