# Coding standards

Code is read far more often than it is written.
Write it for the next person who has to change it: someone who knows Python and FastAPI but not this module, reading it in a hurry, months from now.

These are judgement calls a reviewer checks on every diff, and a reviewer flags cleverness and readability costs as findings, not only bugs.
Mechanical rules (formatting, import shape, raw SQL, types) are listed in `CLAUDE.md`, which is the more detailed source where the two overlap.

## Readable over clever

- **Choose the obvious version.** If the shorter version needs a second read to understand, write the longer one.
- **Names say what a thing is or does**, in the domain language of `GLOSSARY.md`. Avoid abbreviations other than the universal ones (`id`, `url`). A boolean reads as a yes/no question (`is_active`, `has_filings`, `can_retry`).
- **One function, one job.** If describing a function needs "and", it is probably two functions.
- **Keep control flow flat.** Return early from guard clauses rather than nesting `if`/`else` blocks.
- **Comprehensions are for a simple map or filter.** A nested comprehension, one with side effects, or one with a conditional expression inside becomes a plain loop.
- **No metaprogramming where plain code works.** No `getattr`/`setattr` on computed names, dynamically built classes, monkeypatching or `__getattr__` tricks to save a few lines.
- **No hidden behaviour.** A property, `__str__` or a function named like a query (`get_`, `is_`) does not write to the database, send anything or change state.
- **No implicit hooks.** New behaviour is an explicit call where it happens, never an ORM event listener, a signal or a similar callback: a side effect hidden in a hook is hard to find and hard to debug.
- **Be explicit at the call site.** Pass booleans and same-typed arguments by keyword: `load_companies(batch, replace_existing=False)`, not `load_companies(batch, False)`.
- **Name magic values.** A literal that carries meaning becomes a constant or an enum member, placed where `CLAUDE.md` says.
- **No abstraction before it is needed.** Do not add parameters, base classes or hooks for a case nobody has asked for. Three similar lines are fine. Extract shared logic once it is genuinely repeated, and name the extraction after what it means, not what it does mechanically.
- **Delete dead code.** No commented-out code and no unused functions kept "just in case": Git keeps the history.
- **Comments explain why, not what.** If a comment has to explain what the code does, rename or restructure the code instead. Keep a comment for the reason a non-obvious choice was made.
- **Fix inconsistencies where they live.** When a fixture, value, name or doc contradicts what it claims to be, fix it at the source in the same PR and mention it in the PR, rather than working around it. A real bug that type-checking work surfaces is fixed in the same PR too, in its own `fix:` commit called out in the PR body, so no behaviour change hides in a `chore:` commit.

## Comments and docstrings

- A `#` comment does not end with a full stop (sentences inside it keep theirs, only the last one drops it). A docstring does end with one.
- Never use `;` in a comment or docstring. Start a new sentence or line, or rewrite.
- Every sentence starts on its own line, never mid-line after the previous one.
- Break lines at clause boundaries (before "which", "because", "so", after a colon), even when the line ends well short of the limit. The line length is a ceiling, not a fill target: never split a phrase to fill a line.
- A docstring describes the contract (what goes in, what comes back), not side effects such as logging.
- Split a longer explanation into short paragraphs separated by a blank line (or a blank `#` line).

## Current Python and FastAPI idioms

- Use the modern syntax: built-in generics (`list[str]`), `X | None`, `enum.StrEnum`, f-strings, `pathlib`.
- Pass structured data as a dataclass or pydantic model, not a loose `dict` whose keys every caller has to know. Data from an external source is parsed into a pydantic model at the boundary, not passed around raw.
- Use `match` when it reads better than an `if` chain over the shape of the data, not as a replacement for every `if`.
- Business rules live in the domain module (a service function or a model method), not in route handlers. A route parses the request, calls the domain code and builds the response. Shared request plumbing (a database session, auth, pagination) is a FastAPI dependency.
- Filter, aggregate and order in the database, not in Python. No N+1 queries: load related rows in the same query.
- Wrap operations that make several writes in one transaction, and send anything outward (a notification, a queued task) only after it commits, so nothing goes out for a rolled-back change.
- Datetimes are timezone-aware: `datetime.now(UTC)`, never a naive `datetime.now()` or `datetime.utcnow()`.
- Raise a specific exception. Never use a bare `except` or an `except Exception` that swallows the error silently.

## Project rules

- **Every table starts with the standard columns**: `id` (bigint identity primary key, internal only), `uuid` (server default `gen_random_uuid()`, unique, not null), then `created_at` and `modified_at` (timestamptz, not null, server default `now()`). A table that gets updates sets `modified_at` through SQLAlchemy `onupdate`, never a trigger. Column names are lowercase `snake_case`.
- **Every migration is backward compatible**: the application works with the latest schema and the one before it. A deploy migrates before it rolls the services, so for a few minutes the previous release runs against the new schema, and a rollback runs it there for longer. `docs/migrations.md` has the rules and the PostgreSQL recipes.
- **A column that cannot be null, added to a table the previous release writes, has a server default** in its migration, because the previous release still inserts rows without it. A Python-side default does not help those inserts. A nullable column, and any column of a table this release creates, needs nothing.
- **Dropping a column, table or enum value takes several releases**: deprecate it, stop the application using it, make sure the system runs stable without it, then drop it in a later cleanup release. Until the drop, it stays nullable or keeps a server default, so inserts that leave it out still work.
- **Every migration has a rollback plan**, even one with complex steps. A controlled short downtime is better than an uncontrolled breakdown.
- **A migration never backfills large amounts of data.** A long run hits the migration timeout and fails the deployment. The backfill runs as its own job, in batches, outside the deployment.
- **Time** is stored in UTC.
- **Resources are exposed by a unique identity** (a company number, a ticker), never by an auto-increment primary key.
- **An exposed identifier is named `id`, or `<thing>_id` for another resource, and holds the UUID**, in response and request fields, query parameters and path parameters. Never `uuid` or `<thing>_uuid`.
- **Long work runs outside the request.** Collection runs, loads and dbt runs happen in a job or worker, never inside an API request.
- **Responses** should average under 150ms.
- **Logging never interrupts the work**: a logging failure must not fail a request or a pipeline run. A secret (an API key, a password, a token) never reaches the logs. A request we send an external source is logged with no query string, and with the value of every key naming a secret filtered, so a key it takes in the URL or body stays out of the logs.
- **Every external source call respects that source's rate limit and quota.** Retries back off and have a cap, and a source's limits are written down next to its client.
- **Dependencies** are managed with `uv` (`pyproject.toml` and `uv.lock`).
- **Tests** change with the code they cover and follow the rules in the `CLAUDE.md` Testing section. Coverage stays above the `fail_under` threshold in `pyproject.toml`.
- **A rule is tested at the module that owns it.** Its cases are direct tests of the service function or model, with literal expected values. An endpoint's tests cover only what the route adds: one test per outcome (the success and each kind of refusal), its auth and its status codes.
