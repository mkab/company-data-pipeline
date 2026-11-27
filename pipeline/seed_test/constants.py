from pathlib import Path

# The trimmed EDGAR bodies `make seed-test` loads, and the manifest listing them
SEED_FIXTURES_DIR = Path(__file__).parent / "fixtures"
SEED_FETCHES_PATH = SEED_FIXTURES_DIR / "fetches.toml"
