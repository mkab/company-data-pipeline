"""The test seed: `python -m pipeline.seed_test`, run by `make seed-test` as the ingest role."""

import asyncio
import logging

from pipeline.database import get_engine
from pipeline.seed_test.constants import SEED_FETCHES_PATH, SEED_FIXTURES_DIR
from pipeline.seed_test.manifest import load_seed_fetches
from pipeline.seed_test.usecases import seed_raw

logger = logging.getLogger(__name__)


async def seed() -> None:
    try:
        await seed_raw(load_seed_fetches(SEED_FETCHES_PATH), fixtures_dir=SEED_FIXTURES_DIR)
    finally:
        # The seed created the engine,
        # so it closes its connections before the event loop ends
        await get_engine().dispose()
    logger.info("Seeded raw from %s", SEED_FETCHES_PATH)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    asyncio.run(seed())


if __name__ == "__main__":
    main()
