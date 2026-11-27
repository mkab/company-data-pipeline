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
service     the business rules of one area                    (calls repository Protocols)
repository  reads and writes the database, nothing else       (no business rules or logic)
```

- A router calls a usecase, or a service directly when the action needs only one.
- Business rules live in usecases and services, never in routers or repositories.
- A service depends on repository `Protocol`s, never on a concrete repository. The Postgres implementations (`Postgres...Repository`) satisfy them in the application, and in-memory fakes (`Fake...Repository`, in the package's `tests/fakes.py`) in unit tests.
- Models are declarative: every table is a class inheriting from `pipeline.database.ModelBase` (a `DeclarativeBase`), which carries the standard columns.
- Repositories and services are small classes that take their dependencies in `__init__`, so a FastAPI dependency and the CLI build them the same way.
  A service may add a `from_session(session)` classmethod that builds its repositories over one session, the shortcut both callers use.
- **Transactions**: `pipeline.database.session_scope()` is the one place a session is opened, committed on success and rolled back on error (the error is re-raised, never swallowed).
  The outermost caller opens it: for a route, a `get_session` dependency (added with the first route that reads the database, #24), and for the CLI, its entry point (a usecase, or the command itself when it calls one service).
  Services and repositories take the session and never commit, so a usecase that calls two services stays one transaction.

## Testing

- A service's rules are unit tested with fake repositories, asserting what they hold afterwards.
- What PostgreSQL enforces (`ON CONFLICT`, check constraints, grants) is tested against the test database: repositories directly, and the service end to end for its acceptance cases.
- A route's tests cover only what the route adds (see `CLAUDE.md`).

## Consequences

- More files for a small feature (`models.py`, `repositories.py`, `services.py`), in exchange for one obvious place for each kind of code.
- Tests can pass in a session for any role, since nothing below the outermost caller opens one: the raw tests open their own session as `ingest`, the one place outside `session_scope()` a session is opened.
