# 0001: Routers, usecases, services and repositories

Accepted, 2026-11-27.

## Context

The pipeline has two entry points that change data, the API and the ingest CLI, and both reach PostgreSQL.
Without a fixed shape, business rules end up in route handlers or next to the SQL, where they are hard to find and to test.

## Decision

Code is split into four layers, each calling only the one below it:

```text
router      parses the request, builds the response            (FastAPI, gets the layers below through Depends)
usecase     one application action that coordinates services  (only when there is more than one service)
service     the business rules of one area                    (calls repositories)
repository  reads and writes the database, nothing else       (no business rules or logic)
```

- A router calls a usecase, or a service directly when the action needs only one.
- Business rules live in usecases and services, never in routers or repositories.
- Models are declarative: every table is a class inheriting from `pipeline.database.ModelBase` (a `DeclarativeBase`), which carries the standard columns.
- Repositories and services are small classes that take their dependencies in `__init__`, so a FastAPI dependency and the CLI build them the same way.
- **Transactions**: `pipeline.database.session_scope()` is the one place a session is opened, committed on success and rolled back on error (the error is re-raised, never swallowed).
  The outermost caller opens it: a `get_session` dependency for a route, the usecase for the CLI.
  Services and repositories take the session and never commit, so a usecase that calls two services stays one transaction.

## Testing

- A service's rules are unit tested with mocked repositories.
- What PostgreSQL enforces (`ON CONFLICT`, check constraints, grants) is tested against the test database: repositories directly, and the service end to end for its acceptance cases.
- A route's tests cover only what the route adds (see `CLAUDE.md`).

## Consequences

- More files for a small feature (`models.py`, `repositories.py`, `services.py`), in exchange for one obvious place for each kind of code.
- Tests can pass in a session for any role, since nothing below the outermost caller opens one: the raw tests run as `ingest`.
