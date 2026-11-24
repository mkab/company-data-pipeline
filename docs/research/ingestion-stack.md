# Ingestion and dbt stack options

Research for issue #6. Question: which libraries fit a stack on Python 3.14 and PostgreSQL 19 (FastAPI, SQLAlchemy and Alembic already chosen, `uv` for dependencies, Docker Compose for local dev and CI) for four areas: fetching and loading raw payloads, dbt, orchestration, and recorded-response HTTP tests?

Checked 2026-11-24. Versions and metadata come from the PyPI JSON API (`https://pypi.org/pypi/<name>/json`) that day; behaviour claims cite the project's own docs, source or issue tracker ([S1] to [S24]). Local checks made that day are marked **[probe]**: dependency resolution with `uv pip compile --python-version 3.14` (uv 0.13.0) and small smoke tests in Python 3.14.10 venvs.

## Sources

- [S1] PostgreSQL versioning policy: https://www.postgresql.org/support/versioning/
- [S2] httpx repository and releases: https://github.com/encode/httpx, https://github.com/encode/httpx/releases
- [S3] httpx2 (Pydantic) README: https://github.com/pydantic/httpx2
- [S4] stamina docs: https://stamina.hynek.me/en/stable/
- [S5] dlt Postgres destination: https://dlthub.com/docs/dlt-ecosystem/destinations/postgres
- [S6] dlt Postgres type mapping (source): https://github.com/dlt-hub/dlt/blob/devel/dlt/destinations/impl/postgres/factory.py
- [S7] dlt destination tables: https://dlthub.com/docs/general-usage/destination-tables
- [S8] dlt sources, "Reduce the nesting level of generated tables": https://dlthub.com/docs/general-usage/source
- [S9] dlt REST API source: https://dlthub.com/docs/dlt-ecosystem/verified-sources/rest_api/basic
- [S10] dbt v1 (Core) versions and support windows: https://docs.getdbt.com/docs/dbt-versions/core
- [S11] dbt install page (v2 default): https://docs.getdbt.com/docs/local/install-dbt
- [S12] dbt v2 supported features and adapters: https://docs.getdbt.com/docs/fusion/supported-features, https://docs.getdbt.com/docs/supported-data-platforms
- [S13] dbt v2 license agreement: https://www.getdbt.com/dbt-fusion-engine-license-agreement
- [S14] "Release Postgres adapter support" (dbt-labs/dbt #13123): https://github.com/dbt-labs/dbt/issues/13123
- [S15] "Adapter packages missing dbt-core<2.0 upper bound" (dbt-labs/dbt-adapters #2010, and #1992): https://github.com/dbt-labs/dbt-adapters/issues/2010
- [S16] dbt-adapters integration test workflow: https://github.com/dbt-labs/dbt-adapters/blob/main/.github/workflows/_integration-tests.yml
- [S17] uv resolution docs, `requires-python`: https://docs.astral.sh/uv/concepts/resolution/
- [S18] GitHub Actions `schedule` event: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- [S19] Dagster changelog: https://github.com/dagster-io/dagster/blob/master/CHANGES.md
- [S20] dagster-dbt `pyproject.toml`: https://github.com/dagster-io/dagster/blob/master/python_modules/libraries/dagster-dbt/pyproject.toml
- [S21] respx releases, noxfile and issues #316, #324: https://github.com/lundberg/respx
- [S22] vcrpy supported libraries and releases: https://github.com/kevin1024/vcrpy/blob/master/docs/installation.rst, https://github.com/kevin1024/vcrpy/releases
- [S23] pytest-recording changelog and tox matrix: https://github.com/kiwicom/pytest-recording/blob/master/CHANGELOG.md
- [S24] pytest-httpx metadata: https://pypi.org/project/pytest-httpx/

## Baseline: PostgreSQL 19 and Python 3.14

- PostgreSQL 19.0 was first released on November 19, 2026, supported until November 19, 2031 [S1]. It is five days old at the time of writing, so **no library below documents PostgreSQL 19 explicitly**. Everything here talks to Postgres through libpq-compatible drivers (psycopg 3, psycopg2) over the stable wire protocol, so the practical risk is low, but it is untested by us.
- One indirect signal: dbt-adapters runs its dbt-postgres integration tests against the untagged `postgres` Docker image (`image: postgres`) [S16], which is `latest`, so its CI moves to 19 on its own.
- uv caveat: "When evaluating `requires-python` ranges for dependencies, uv only considers lower bounds and ignores upper bounds entirely" [S17]. So a package capped below 3.14 still installs under uv on 3.14 without a warning (seen with dagster-dbt, below). Python support has to be read from metadata, not inferred from a successful `uv sync`.

## Versions table (PyPI, 2026-11-24)

| Package | Latest | Released | `requires-python` | Python 3.14 | License |
|---|---|---|---|---|---|
| httpx | 0.28.1 | 2024-12-06 | >=3.8 | not in classifiers; added to CI 2026-11-16 [S2]; **[probe]** works | BSD-3-Clause |
| httpx2 | 2.16.2 | 2026-11-16 | >=3.11 | yes | BSD-3-Clause |
| tenacity | 9.2.1 | 2026-10-07 | >=3.10 | yes | Apache-2.0 |
| stamina | 26.2.0 | 2026-11-15 | >=3.11 | yes (3.11 to 3.15) | MIT |
| SQLAlchemy | 2.1.9 | 2026-11-16 | >=3.11 | yes | MIT |
| alembic | 1.20.1 | 2026-10-22 | >=3.10 | yes | MIT |
| psycopg | 3.3.9 | 2026-11-12 | >=3.10 | yes | LGPL-3.0-only |
| dlt | 1.32.0 | 2026-10-29 | >=3.10,<3.15 | yes | Apache-2.0 |
| dbt-core | 1.12.7 | 2026-11-12 | >=3.10 | yes | Apache-2.0 |
| dbt-postgres | 1.11.0 | 2026-07-16 | >=3.10.0 | yes | Apache-2.0 |
| dbt (v2, Fusion) | 2.0.12 | 2026-11-16 | >=3.10 | n/a (Rust binary) | dbt v2 license agreement [S13] |
| dbt-oss (v2 open runtime) | 2.0.11 | 2026-11-03 | >=3.10 | n/a | Apache-2.0, "Development Status :: 3 - Alpha" |
| psycopg2-binary | 2.9.13 | 2026-09-09 | >=3.10 | cp314 wheels | LGPL |
| prefect | 3.9.4 | 2026-11-19 | >=3.11,<3.16 | yes | Apache-2.0 |
| dagster | 1.13.31 | 2026-11-19 | >=3.11,<3.15 | yes since 1.12.9 [S19] | Apache-2.0 |
| dagster-dbt | 0.29.31 | 2026-11-19 | **>=3.11,<3.14** | **no** | Apache-2.0 |
| respx | 0.23.1 | 2026-04-08 | >=3.8 | yes | BSD-3-Clause |
| vcrpy | 9.4.2 | 2026-11-02 | >=3.11 | yes | MIT |
| pytest-recording | 0.15.0 | 2026-11-15 | >=3.10 | yes (3.10 to 3.15) | MIT |
| pytest-httpx | 0.36.2 | 2026-04-09 | >=3.10 | yes; pins `httpx==0.28.*`, `pytest==9.*` | MIT |
| pytest | 9.2.0 | 2026-10-27 | >=3.10 | yes | MIT |

## 1. Fetch and load raw JSON: hand-rolled vs dlt

### Hand-rolled: httpx + stamina (or tenacity) + SQLAlchemy 2

- **httpx**: last release 0.28.1 on 2024-12-06, nearly two years old [S2]. The repo is not archived and is active again (Python 3.14 added to its test matrix on 2026-11-16, contributing guidelines revised the same day) [S2]. **[probe]** 0.28.1 works on 3.14.10.
- **httpx2**: Pydantic's continuation of httpx, "With HTTPX itself seeing limited activity recently, Pydantic is picking up stewardship under the HTTPX2 name so that users have a reliably maintained path forward - including timely security updates" [S3]. Different import name (`import httpx2`), 24 releases, latest 2.16.2. stamina's own docs example now uses `httpx2.HTTPError` [S4]. respx does not support it yet: open issues "User question: respx and the httpx forks" (#316) and "Allow fork response types (e.g. httpx2.Response)" (#324) [S21]; vcrpy does list it [S22].
- **stamina vs tenacity**: stamina is "an opinionated wrapper around the great-but-unopinionated Tenacity package" [S4] (it depends on `tenacity>=8.3.0`). It gives exponential backoff with jitter by default, caps on attempts and total time, retry only on named exceptions (`on=`), a testing mode that disables retries or backoff globally, and "Flexible instrumentation with Prometheus, structlog, and standard library's logging support out-of-the-box" [S4]. Tenacity gives the same building blocks with no defaults. **[probe]** `stamina.set_testing(True, attempts=3)` with a respx mock returning 429 then 200 retried once and passed under pytest 9.2.0.
- **SQLAlchemy 2.1.9 + psycopg 3.3.9**: already in the stack; a `JSONB` column (`sqlalchemy.dialects.postgresql.JSONB`) plus a Core `insert()` with bound parameters covers the raw load, and Alembic owns the table's DDL like every other table.
- Pros: one driver (psycopg 3), one HTTP client, schema under Alembic and `docs/migrations.md`, raw table shaped exactly as issue #4 asks (payload JSONB, fetched-at, source URL, payload hash for the change detection found in issue #5); small dependency surface; fully typed (all of the above ship types), which suits strict mypy.
- Cons: we write pagination, rate limiting (EDGAR caps at 10 req/s, issue #5), incremental state and run bookkeeping ourselves. For one or two sources that is a few hundred lines; it does not scale to dozens of sources.

### dlt (dlthub)

- Mature and active: 1.32.0 on 2026-10-29, Apache-2.0, Python 3.10 to 3.14 (`<3.15`).
- Postgres destination: the `postgres` extra installs `psycopg2` [S5]; "All write dispositions are supported", merge strategies delete-insert, upsert, scd2, insert-only and cdc [S5]. dlt's `json` type maps to `jsonb` on Postgres [S6], except Parquet/ADBC loads where "`JSONB` is not supported so we use `JSON` instead" [S5].
- By default it flattens: it "maps the structure of Python objects (i.e., from parsed JSON files) into nested tables" with `_dlt_parent_id` and `_dlt_list_idx` links [S7]. To keep the payload whole, `max_table_nesting=0` "will not generate nested tables and will not flatten dicts into columns at all. All nested data will be represented as JSON." [S8]
- It adds `_dlt_id` and `_dlt_load_id` to every table and creates its own `_dlt_loads`, `_dlt_pipeline_state` and `_dlt_version` tables [S7]; it creates and evolves destination tables itself, including variant columns such as `id__v_text` on type clashes (schema docs).
- The REST API source gives declarative pagination, auth and incremental cursors [S9]; it is built on `requests` (its `session` option is a `requests.Session`) [S9], not httpx.
- Pros: incremental state, retries, pagination, schema evolution and load bookkeeping out of the box; good fit for many sources.
- Cons for this project: (a) dlt owns DDL for the tables it loads, which bypasses Alembic and the migration recipe in `docs/migrations.md`; (b) a second Postgres driver (psycopg2) and a second HTTP client (requests) next to psycopg 3 and httpx; (c) `_dlt_*` columns and tables become part of the raw layer that dbt reads; (d) with `max_table_nesting=0` most of what dlt adds (normalisation into tables) is switched off, leaving mainly state and bookkeeping; (e) recorded tests would go through vcrpy (requests), not respx.
- **[probe]** `fastapi sqlalchemy alembic psycopg[binary] dlt[postgres] dbt-core~=1.12.0 dbt-postgres` resolves on 3.14 (dlt 1.32.0, SQLAlchemy 2.1.9, FastAPI 0.165.0).

### Recommendation

**Hand-rolled: httpx 0.28.1 + stamina + SQLAlchemy 2.1 Core into a JSONB raw table under Alembic.** The raw layer is "store the payload as-is" (issue #4), which is the part dlt adds least to, and keeping DDL in Alembic matches the project's migration rules. Use stamina over bare tenacity for the safe defaults and its testing switch. Stay on `httpx` for now (respx compatibility, active repo again); revisit `httpx2` if httpx stalls again or respx gains fork support. dlt is the right call if the project later adds many heterogeneous sources.

## 2. dbt: dbt-core + dbt-postgres vs dbt v2 (Fusion)

### Naming in November 2026

dbt Labs now calls Fusion "dbt v2": "dbt v2 is the current generation of dbt and uses the 2.x release series. dbt v1 is the Python-based generation and stays on the 1.x series." [S10] "Installing dbt gives you dbt v2 by default" [S11]; v2 installs via `pip install dbt`, Homebrew or a curl/winget installer that drops a binary in `~/.local/bin/dbt` [S11]. A dbt Labs comment on [S14] confirms "v2 (fka Fusion)". The Apache-2.0 runtime is published as `dbt-oss` (alpha) and "`dbt-oss` and `dbt` cannot share a Python environment" [S11].

### dbt v2 (Fusion)

- **No Postgres.** The v2 adapter list is Snowflake, BigQuery, Databricks, Redshift (GA), DuckDB (CLI only, GA), Apache Spark (CLI only, beta) and ClickHouse (private beta) [S12]. The tracking issue "Release Postgres adapter support" is open; on 2026-11-12 dbt Labs wrote "tl;dr We'll put effort into support Postgres in the new year!", that Postgres is "on the roadmap -- not date yet", and that community forks are "the correct approach currently while it is still officially unsupported" [S14]. Running a v2 project on Postgres fails with "The 'postgres' adapter is not yet supported by dbt Fusion" [S15].
- License: the binary is under the dbt v2 license agreement, a "limited, non-exclusive, non-transferable, non-sublicensable license" with no reverse engineering; only the dbt OSS source is named as Apache 2.0 [S13]. Free to use, but not open source.
- Verdict: not usable for this project today.

### dbt-core 1.12 + dbt-postgres 1.11

- dbt-core 1.12 released Jul 16, 2026, "Active support, through July 15, 2027"; 1.11 is in critical support through Dec 18, 2026; 1.13 is in beta (1.13.0rc1 on 2026-11-04) [S10].
- dbt-postgres 1.11.0 (2026-07-16) requires `dbt-core>=1.8.0rc1,<2.0`, `dbt-adapters<2.0` and `psycopg2-binary>=2.9,<3.0`; psycopg2-binary 2.9.13 ships cp314 wheels.
- Python 3.14: dbt-core, dbt-adapters and dbt-postgres all list 3.14 in their classifiers.
- PostgreSQL 19: not documented by dbt; see the baseline (their CI uses `postgres:latest`) [S16].
- Pitfall: when dbt-core 2.0.0-alpha.1 hit PyPI (2026-06-01), `pip install dbt-<adapter>` resolved dbt-core to 2.x and broke, because adapters' lower bounds are pre-release specifiers that make pip consider pre-releases [S15] (issue #2010 still open). dbt-postgres 1.11.0 now caps `<2.0`, and uv does not pick pre-releases unless asked, but pin dbt-core explicitly anyway (`dbt-core~=1.12.0`).
- Pros: the only maintained Postgres path; Apache-2.0; mature.
- Cons: v1 is now the "previous generation"; long-term it will be v2 plus a Postgres adapter, so expect a migration once that adapter is GA.

### Same venv or its own container?

- dbt-core pins a lot of shared libraries: `click<9`, `protobuf>=6,<8`, `mashumaro[msgpack]<3.18`, `pathspec<1.1`, `sqlparse<0.7`, `pydantic<3`, `jsonschema<5`, plus `agate`, `metricflow` and `snowplow-tracker` (PyPI `requires_dist`). dbt-postgres brings psycopg2-binary next to the app's psycopg 3 (they coexist; different import names).
- **[probe]** On 3.14 today these co-resolve with the app: `fastapi sqlalchemy alembic psycopg[binary] httpx stamina dbt-core~=1.12.0 dbt-postgres` gives FastAPI 0.165.0, SQLAlchemy 2.1.9, pydantic 2.14.4, protobuf 6.33.6, mashumaro 3.17 with no conflict.
- So there is no conflict forcing a split today. The risk is future drift: dbt's caps can hold back an app upgrade (and dbt v2 later cannot share a Python env with dbt-oss at all [S11]).

### Recommendation

**dbt-core 1.12 + dbt-postgres 1.11, pinned `dbt-core~=1.12.0`.** Put dbt in its own `uv` dependency group (e.g. `dbt`) in the same lockfile, and run it as its own Docker Compose service (same base image, `uv sync --only-group dbt` or `--group dbt`), so the app image does not carry dbt and a future conflict, or the move to v2 binary, only touches that service. Re-check the v2 Postgres adapter in early 2027 [S14].

## 3. Orchestration: none, Prefect, Dagster

### None: CLI + cron / GitHub Actions

- `make ingest` then `make dbt` (or one CLI command) run locally, in Compose, and on a GitHub Actions `schedule`.
- GitHub limits: "The shortest interval you can run scheduled workflows is once every 5 minutes"; "The `schedule` event can be delayed during periods of high loads"; "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days." [S18]
- Pros: no extra service, no extra dependencies, logs in Actions; fits issue #4's "CLI job" and "Production deployment: out of scope". Cons: no UI, retries and run history beyond what we log ourselves (issue #4 already lists run tracking as an open question).

### Prefect 3.9.4

- Python 3.11 to 3.15, Apache-2.0, very active (2026-11-19). Flows are decorated Python functions; local runs need no server, a UI needs a Prefect server (another Compose service).
- **Conflict:** prefect requires `fastapi>=0.139.0,<0.151` (PyPI `requires_dist`). **[probe]** Adding prefect to the app resolves FastAPI down from 0.165.0 to 0.150.0. In the app's environment Prefect would hold FastAPI back; it would need its own group or container.

### Dagster 1.13.31

- Core supports 3.14 since 1.12.9 ("The core `dagster` package (and most libraries) are now compatible with Python 3.14") [S19], `requires-python <3.15`.
- **dagster-dbt 0.29.31 declares `requires-python = ">=3.11,<3.14"`** [S20]: not supported on 3.14. Its own uv environments stop at `<3.14` and its dbt-core extra is `dbt-core>=1.7,<1.13` [S20]. **[probe]** uv installs it on 3.14 anyway because uv ignores the upper bound [S17], so this would be running an unsupported combination silently.
- Pros: asset graph, dbt model lineage, rich UI. Cons: heaviest option (webserver, daemon, storage DB), the dbt integration is unsupported on our Python, and it is the most conceptual surface for a small project.

### Recommendation

**No orchestrator: a CLI entry point wrapped by the Makefile, scheduled by GitHub Actions `schedule` (and runnable by cron locally).** Record runs in our own table if run tracking is decided (issue #4). If an orchestrator is wanted later for the portfolio story, Prefect is the lighter fit, in its own dependency group or container because of its FastAPI cap; avoid Dagster until dagster-dbt supports 3.14.

## 4. Recorded-response HTTP tests: respx, vcrpy, pytest-recording

- **respx 0.23.1** (2026-04-08): mocks httpx at the transport level; routes match method, URL, params and so on; ships a `respx_mock` pytest fixture via a `pytest11` entry point [S21]. Its nox matrix runs Python 3.8 to 3.14 against unpinned `pytest` [S21]. No recording: responses are written by hand or loaded from saved JSON fixtures. Not yet httpx2-aware (#316, #324) [S21]. **[probe]** works with pytest 9.2.0 and httpx 0.28.1 on 3.14.
- **vcrpy 9.4.2** (2026-11-02): records real HTTP interactions to YAML cassettes and replays them; supports Python 3.11+ and, among others, `httpx` and `httpx2` [S22]. Active (three releases on 2026-11-01/02) [S22].
- **pytest-recording 0.15.0** (2026-11-15): pytest plugin over vcrpy: `@pytest.mark.vcr`, `--record-mode` (`none`, `once`, `rewrite`, ...), `--block-network` and `allowed_hosts`; 0.14.0 added "Support for Python 3.14 and 3.15" [S23]. Requires `pytest>=6.2.5`, `vcrpy>=4.0.2`; its tox matrix runs py310 to py315 with unpinned pytest [S23].
- **pytest-httpx 0.36.2** (alternative to respx): a fixture that mocks httpx, pinned to `httpx==0.28.*` and `pytest==9.*` [S24], so it must move in lockstep with both.
- **[probe]** pytest 9.2.0, httpx 0.28.1, pytest-recording 0.15.0, vcrpy 9.4.2 on 3.14.10: a `@pytest.mark.vcr` test recorded an httpx GET with `--record-mode=once`, then replayed it with `--record-mode=none --block-network` and the server stopped. Passed.
- Pros and cons: cassettes capture real EDGAR payload shapes (good for the "tests against recorded responses" goal in issue #4) but can be large (issue #5: companyfacts for Apple is 3.9 MB) and must have the User-Agent contact email filtered out (`filter_headers`). respx is better for the cases you cannot record on demand: 429, 403, 5xx, timeouts, which the retry logic needs.

### Recommendation

**pytest-recording (vcrpy) for recorded source responses, plus respx for error and retry cases.** Run CI with `--record-mode=none --block-network` so a missing cassette fails instead of calling EDGAR (matching CLAUDE.md "Tests never call a real external source"). Filter the `User-Agent` header in cassettes, and trim large payloads to a few companies. Skip pytest-httpx (lockstep pins) unless respx stalls.

## Summary

| Area | Recommendation | Main reason |
|---|---|---|
| Fetch and load | httpx 0.28.1 + stamina 26.2 + SQLAlchemy 2.1 Core, JSONB raw table under Alembic | raw layer is "payload as-is"; dlt would own DDL, add psycopg2 and requests |
| dbt | dbt-core ~=1.12.0 + dbt-postgres 1.11.0, own uv group and Compose service | dbt v2 (Fusion) has no Postgres adapter yet (planned "in the new year") |
| Orchestration | none: CLI + Makefile + GitHub Actions `schedule` | Prefect caps FastAPI <0.151; dagster-dbt does not support 3.14 |
| HTTP tests | pytest-recording (vcrpy) + respx | recorded real payloads plus hand-made error cases; both verified on pytest 9.2 |

## Open points

- PostgreSQL 19 compatibility is inferred, not documented by any library; the first Compose run against `postgres:19` will confirm it.
- dbt v2 Postgres adapter: re-check [S14] in 2027; the move to v2 will need a project config review (v2 rejects some v1 configs [S15]).
- httpx vs httpx2: watch httpx releases and respx fork support (#316, #324).
