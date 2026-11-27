from pathlib import Path

# Committed at the repo root,
# so a change to the tracked companies is a reviewed PR
TRACKED_COMPANIES_PATH = Path(__file__).parents[2] / "config" / "tracked_companies.toml"
