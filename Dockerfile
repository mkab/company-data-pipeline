# The one place the uv version is set: every stage copies uv from this image
FROM ghcr.io/astral-sh/uv:0.13.10 AS uv


FROM python:3.14-slim-trixie AS base

COPY --from=uv /uv /uvx /bin/

# The venv lives outside /app, so the bind mount of the source in Compose does not hide it
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app


# The application, its tests and its tooling: main plus dev groups
FROM base AS app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . .


# dbt and its Postgres adapter only
FROM base AS dbt

# Outside /app, like the venv, so the bind mount of the source in Compose does not hide them
ENV DBT_PACKAGES_INSTALL_PATH=/opt/dbt_packages

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --only-group dbt

COPY . .

# The packages pinned in dbt/packages.yml and dbt/package-lock.yml
RUN dbt deps --project-dir dbt
