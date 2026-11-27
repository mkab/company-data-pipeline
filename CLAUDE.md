# CLAUDE.md

## Stack

Python 3.14 + FastAPI, PostgreSQL 19 (Alembic migrations), dbt (raw, staging and curated layers). `uv` manages dependencies.

## Commands

```sh
uv sync                  # install dependencies on the host (main plus dev groups)
pre-commit install       # once per clone: installs the pre-commit and commit-msg hooks
make help                # list every target
make env                 # copy .env.example to .env when .env is missing
make up                  # start db and api (api on localhost:8001, db on localhost:5433)
make up-build            # rebuild the images, then start db and api
make down                # stop the containers
make destroy             # stop the containers, remove their local images and volumes
make clean               # remove caches and coverage output
make outdated            # list direct dependencies with a newer release
make upgrade [PACKAGE=]  # upgrade the lock (one package or all), sync, rebuild
make migrate             # alembic upgrade head, in the app container
make migration MSG=      # autogenerate a migration, in the app container
make migrations-check    # upgrade head, alembic check, downgrade base, upgrade head (empties the dev database)
make lint                # ruff format --check, ruff check, mypy (no fixes), lint-migrations, on the host
make lint-migrations     # Squawk over each revision's offline SQL (`.squawk.toml`), on the host
make format              # ruff format, ruff check --fix, on the host
make tests [ARGS=]       # pytest -v, in the app container, against pipeline_test
make covtest [ARGS=]     # coverage HTML report -> htmlcov/index.html (fail_under = 96), in the app container
make record-cassettes    # re-record the EDGAR cassettes against the real SEC (needs EDGAR_USER_AGENT), by hand only
```

Everything that touches the database runs in a container, and `make up` never starts the one-off `ingest` and `dbt` services (they sit behind Compose profiles).
Each service connects with its own role (`ingest`, `dbt`, `api`, created by `docker/initdb` on an empty volume) through `DATABASE_URL`, and Alembic connects as the owner through `MIGRATIONS_DATABASE_URL`.

CI (`.github/workflows/ci.yml`) runs the jobs `lint`, `tests` and `pr-title` on every PR, and `tests` again on the merge to `main`; the ruleset on `main` requires all three. A job renamed in the workflow is renamed in the ruleset too.

The pre-commit hook runs `make format` and mypy on any commit touching Python, `make lint-migrations` on any commit touching `migrations/`, and the commit-msg hook (`bin/check-commit-msg.sh`) refuses a message without an allowed prefix. Never bypass them with `--no-verify`.

## Code conventions

Ruff (`pyproject.toml`) enforces most of these, plus no naive datetimes (`DTZ`), no blind `except Exception` (`BLE`) and no commented-out code (`ERA`).

- **Layers: router, usecase, service, repository** (`docs/adr/0001-routers-usecases-services-repositories.md`). Business rules live in usecases and services; repositories only query.
- **Tables are declarative models** inheriting from `pipeline.database.ModelBase`, never Core `sa.Table`s. `ModelBase` and `DeclarativeBase` are in ruff's `runtime-evaluated-base-classes`, since SQLAlchemy reads `Mapped[...]` at runtime.
- **Never build SQL from strings.** Every value reaches the database as a bound parameter, never by f-string, `%` or `.format()` into the statement (ruff `S608`). This covers the Python code; dbt models are SQL by design and take values through `ref`, `source` and `var`, not string building.
- **Types: strict mypy.** Every first-party module is fully annotated, and no module is relaxed by a `[[tool.mypy.overrides]]` entry. Overrides are only for third-party packages that ship no types. A `# type: ignore` names its error code and a comment says why.
- **Names used only in type hints are imported under `if TYPE_CHECKING:`**, and the annotation stays unquoted (ruff strict `TC001`-`TC004`, `UP037`). Exception: FastAPI and pydantic read annotations at runtime, so a name in a route or dependency signature, or in a pydantic model, must be a real import. `pydantic.BaseModel` is listed in ruff's `runtime-evaluated-base-classes`; a new runtime reader is added there.
- **Imports go at the top of the module**, absolute only (no relative imports). Keep a function-level import only when a real cycle forces it, with a comment naming it. Import a name from the module that defines it, never from one that merely imports it.
- **Enums go in their package's `enums.py`, and constants in its `constants.py`** (a constant used by one module only may sit at the top of it, directly under the imports). Never partway down a file between classes.
- **No `print`** in application code (ruff `T20`): use the logger.
- **User-facing copy is sentence case**: every error message and response text. Proper nouns and acronyms keep their case.

## Migrations

The judgement rules (backward compatibility, drops over several releases, a rollback plan, no large backfills) are in `CODING_STANDARDS.md`. Every DDL change on an existing table follows the recipe in `docs/migrations.md`:

- **Indexes are created and dropped `CONCURRENTLY`**, inside `op.get_context().autocommit_block()`.
- **A big index gets its own migration revision**, with no other DDL, following the guarded recipe in the doc.
- **A foreign key takes three migrations**: add it `NOT VALID`, then `VALIDATE CONSTRAINT`, then create the index on the referencing column concurrently.
- **An enum value is added with `ALTER TYPE ... ADD VALUE IF NOT EXISTS`** (`op.execute`), never by letting Alembic recreate the enum. An unused value stays deprecated rather than dropped; the rare real drop follows the new-column recipe in the doc.
- **A column is made not null in two migrations**: `ADD CONSTRAINT <name> NOT NULL <column> NOT VALID`, then `VALIDATE CONSTRAINT`. Never `SET NOT NULL` on an existing table.
- **Every migration has a `downgrade()` that runs**: `make migrations-check` (in CI) round-trips them. A downgrade never raises: an irreversible one restores the structure (or is a commented no-op with an idempotent upgrade) and its docstring says how the data is recovered.
- **Lint every migration with Squawk**: `make lint-migrations`, in `make lint` and the pre-commit hook. A rule turned off in `.squawk.toml` has a comment saying why.

## Git workflow

- **Never commit or push directly to `main`.** Every change, however small, goes on its own branch: fetch latest `main`, branch from it, commit, push, then open a PR back to `main`.
- **Bring a branch up to date with `main` by rebasing, never by merging.** `git fetch origin` then `git rebase origin/main`. Force-push the rebased branch with `git push --force-with-lease`; force-pushing a feature branch is fine, force-pushing `main` never is.
- Once a PR is merged, that branch is done. Start the next piece of work from a fresh branch off `main`.
- Commit messages start with `feat: `, `fix: ` or `chore: `, nothing else. So `git commit --fixup` fails the commit-msg hook: fold a late change in as its own prefixed commit, or `git commit --amend` when the target is HEAD.
- **Never add `Co-Authored-By` lines to commit messages**, and never add "Generated with Claude Code" attribution to PR descriptions.
- **Never use em dashes anywhere**: not in code, comments, documentation, commit messages, PR descriptions, or this file. Use a colon, a semicolon, parentheses, or reword.

## Testing

pytest. Test data comes from factories (factory_boy), in a `factories.py` next to the tests of the package whose rows they build. A test calls a factory with the fields it relies on, as literals. A fixture is a named scenario several tests reuse; the root `conftest.py` holds no test data, only global patches and shared utilities.

Tests never call a real external source: they run against recorded or mocked responses.

**A rule is tested at the deepest module that owns it.** An HTTP test covers only what the route adds: the response shape, auth, status codes and the wiring to that module, not every case of the rule behind it.

**A test asserts one clear scenario, with no conditional logic anywhere in it.** No `if`/`else` in the body, no computed expected value in the assertion, and no comprehension or filtering in the `@pytest.mark.parametrize` parameters. Use `parametrize` wherever possible, with hard-coded literal lists. When one parametrized test would need a condition to express both outcomes, write two, one per outcome. If splitting loses a property the computed version enforced (such as "a new enum member cannot be silently missed"), assert that property directly in its own small test.

## Project rules

`CODING_STANDARDS.md` (repo root) holds the judgement-call standards every diff is reviewed against. Write new code to it.

## Agent skills

### Issue tracker

Issues tracked in GitHub Issues (mkab/company-data-pipeline) via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical labels (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `GLOSSARY.md` + `docs/adr/`. See `docs/agents/domain.md`.

### Claude Code hooks

`.claude/settings.json` defines two project hooks that enforce the conventions above: a `PostToolUse` em dash check on every `Edit`/`Write`, and a `PreToolUse` guard that blocks a commit while the branch is `main`. Setup prerequisites (`jq` on `PATH`, Git Bash on Windows) are in `docs/agents/hooks.md`.
