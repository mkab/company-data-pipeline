"""Lint the offline SQL of every migration revision with Squawk, one revision at a time.

Squawk does not apply its locking rules to a table created earlier in the same SQL.
Linting the whole chain as one script would let a blocking change to an existing table through,
so each revision is linted on its own.

Usage: `make lint-migrations`.
It needs no database, only a placeholder `MIGRATIONS_DATABASE_URL`.
"""

import io
import subprocess
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

ALEMBIC_CONFIG_PATH = Path(__file__).resolve().parent.parent / "alembic.ini"

# The first revision's SQL also creates Alembic's own version table, whose varchar column is not ours to change.
# A Squawk ignore comment covers the line after it only
VERSION_COLUMN_DDL = "version_num VARCHAR(32)"
VERSION_COLUMN_IGNORE = "-- squawk-ignore prefer-text-field\n"


def revision_sql(revision: str, down_revision: str | None) -> str:
    """Return the SQL that upgrading from `down_revision` (or base) to `revision` runs."""
    output = io.StringIO()
    config = Config(ALEMBIC_CONFIG_PATH, output_buffer=output)
    command.upgrade(config, f"{down_revision or 'base'}:{revision}", sql=True)
    return output.getvalue().replace(
        VERSION_COLUMN_DDL, VERSION_COLUMN_IGNORE + VERSION_COLUMN_DDL
    )


def main() -> int:
    has_failed = False
    for script in ScriptDirectory.from_config(Config(ALEMBIC_CONFIG_PATH)).walk_revisions():
        if not isinstance(script.down_revision, str | None):
            raise NotImplementedError(f"merge revision {script.revision} is not linted yet")
        result = subprocess.run(
            ["squawk", "--stdin-filepath", script.path],
            input=revision_sql(script.revision, script.down_revision),
            text=True,
            check=False,
        )
        has_failed = has_failed or result.returncode != 0
    return 1 if has_failed else 0


if __name__ == "__main__":
    sys.exit(main())
