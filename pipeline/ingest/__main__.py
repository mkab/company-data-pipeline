"""The ingest CLI: `python -m pipeline.ingest`, run by `make ingest` as the ingest role."""

import asyncio
import logging
import sys
from typing import TYPE_CHECKING

import pydantic

from pipeline.database import get_engine
from pipeline.ingest.constants import TRACKED_COMPANIES_PATH
from pipeline.ingest.tracked_companies import load_tracked_companies
from pipeline.ingest.usecases import run_ingest
from pipeline.settings import EdgarSettings
from pipeline.sources.edgar.client import EdgarClient

if TYPE_CHECKING:
    from pipeline.ingest.tracked_companies import TrackedCompany

EXIT_SUCCESS = 0
EXIT_FAILURE = 1

logger = logging.getLogger(__name__)


async def ingest(edgar: EdgarClient, tracked_companies: list[TrackedCompany]) -> int:
    """Run one ingest through `edgar`, and return the exit status.

    It is `EXIT_FAILURE` when any fetch could not be recorded.
    """
    try:
        async with edgar:
            failed_fetches = await run_ingest(edgar, tracked_companies)
    finally:
        # The run created the engine,
        # so it closes its connections before the event loop ends
        await get_engine().dispose()
    if failed_fetches:
        logger.error("Ingest finished with %d failed fetches", len(failed_fetches))
        return EXIT_FAILURE
    logger.info("Ingest finished: every fetch was recorded")
    return EXIT_SUCCESS


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    try:
        settings = EdgarSettings()  # type: ignore[call-arg]  # pydantic-settings fills the field from env vars
    except pydantic.ValidationError:
        logger.error(
            "EDGAR_USER_AGENT is required: "
            'set it to a name and a contact email, such as "Jane Doe jane@example.com"'
        )
        return EXIT_FAILURE
    tracked_companies = load_tracked_companies(TRACKED_COMPANIES_PATH)
    return asyncio.run(ingest(EdgarClient.from_settings(settings), tracked_companies))


if __name__ == "__main__":
    sys.exit(main())
