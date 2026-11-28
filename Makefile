# Everything that touches the database runs in a container of the `api` service, built from the `app` image.
# lint and format run on the host through uv, since the pre-commit hook calls `make format`
APP_RUN = docker compose run --rm api

.PHONY: help
help:
	@echo "Please use 'make <target>' where <target> is one of:"
	@echo ""
	@echo "  env            	copy .env.example to .env when .env is missing"
	@echo "  up             	spin up the Docker containers (db and api)"
	@echo "  up-build       	rebuild the Docker images and spin up the Docker containers"
	@echo "  down           	stop the Docker containers"
	@echo "  destroy        	stop the Docker containers and remove their local images and volumes"
	@echo "  clean          	remove all temporary and bytecode files/folders"
	@echo "  outdated       	list the direct dependencies that have a newer release"
	@echo "  upgrade        	upgrade the locked dependencies within the pyproject.toml constraints and rebuild the images"
	@echo "                 	(PACKAGE=<name> upgrades only that package)"
	@echo "  migrate        	apply the migrations (alembic upgrade head)"
	@echo "  migration      	autogenerate a migration file (MSG=<message> is required)"
	@echo "  migrations-check	run the migrations up, check none is missing, then down to base and up again"
	@echo "                 	(the downgrade empties the development database, and drops dbt's staging and curated)"
	@echo "  ingest         	fetch the tickers file and every tracked company's datasets from SEC EDGAR into raw"
	@echo "                 	(EDGAR_USER_AGENT is required in .env)"
	@echo "  seed-test      	migrate the test database and load the committed EDGAR fixtures into its raw tables"
	@echo "                 	(\`make tests\` empties them again)"
	@echo "  dbt            	run dbt in its container (ARGS=<dbt command and options>, build by default)"
	@echo "                 	(ARGS=\"build --target test\" builds against the test database, after seed-test)"
	@echo "  curated-drift  	compare the test database's curated columns with their Python declaration"
	@echo "                 	(after \`make dbt ARGS="build --target test"\`, as CI does)"
	@echo "  pipeline       	ingest, then dbt build"
	@echo "  lint           	run the code linters, without fixing anything (lint-migrations included)"
	@echo "  lint-migrations	lint the SQL of every migration revision with Squawk"
	@echo "  format         	reformat code and apply the safe lint fixes"
	@echo "  tests          	run all the tests (ARGS=<pytest options> are passed on)"
	@echo "  covtest        	run all the tests with coverage in HTML mode. The coverage can be viewed in the file htmlcov/index.html"
	@echo "                 	(ARGS=<pytest options> are passed on)"
	@echo "  record-cassettes	re-record the EDGAR cassettes against the real SEC (EDGAR_USER_AGENT is required in .env)"
	@echo ""
	@echo "Check the Makefile to know exactly what each target is doing."

.PHONY: env
env:
	@test -f .env && echo ".env already exists, leaving it as it is" || (cp .env.example .env && echo "Created .env from .env.example")

.PHONY: up
up:
	docker compose up -d

.PHONY: up-build
up-build:
	docker compose up -d --build

.PHONY: down
down:
	docker compose down

.PHONY: destroy
destroy:
	docker compose down --rmi local --volumes

.PHONY: clean
clean:
	find . -depth -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -r "{}" +
	find . -depth -type d -name ".mypy_cache" -exec rm -r "{}" +
	find . -depth -type d -name ".pytest_cache" -exec rm -r "{}" +
	find . -depth -type d -name ".ruff_cache" -exec rm -r "{}" +
	rm -rf htmlcov .coverage

.PHONY: outdated
outdated:
	@# Lists every direct dependency whose latest release is newer than the locked one,
	@# including those held back by a cap or pin in pyproject.toml
	uv tree --all-groups --depth 1 --outdated | grep latest || echo "Every direct dependency is on its latest release"

.PHONY: upgrade
upgrade:
	@# Raising a cap or pin is done by hand in pyproject.toml first: this stays within the constraints
	uv lock $(if $(PACKAGE),--upgrade-package $(PACKAGE),--upgrade)
	uv sync
	docker compose up -d --build

.PHONY: migrate
migrate:
	$(APP_RUN) alembic upgrade head

.PHONY: migration
migration:
	@test -n "$(MSG)" || (echo 'MSG is required, such as: make migration MSG="add raw tables"' && exit 1)
	$(APP_RUN) alembic revision --autogenerate -m "$(MSG)"

.PHONY: migrations-check
migrations-check:
	@# `alembic check` fails when the models differ from the migrations (a migration is missing), and needs the database at head.
	@# The round trip fails when a downgrade raises or an upgrade cannot run twice (see docs/migrations.md).
	@# dbt's views over raw would block the downgrade, so its schemas go first (`make dbt` rebuilds them)
	docker compose exec -T db sh -c 'psql --username "$$POSTGRES_USER" --dbname "$$POSTGRES_DB" --command "DROP SCHEMA IF EXISTS staging, curated CASCADE"'
	$(APP_RUN) sh -c "alembic upgrade head && alembic check && alembic downgrade base && alembic upgrade head"

.PHONY: ingest
ingest:
	@# The `ingest` service connects as the ingest role, the one that may write raw
	docker compose run --rm ingest python -m pipeline.ingest

.PHONY: seed-test
seed-test:
	@# The `seed-test` service points both URLs at pipeline_test.
	@# raw is append-only, so a second seed adds fetches of the same payloads and staging reads the same rows
	docker compose run --rm seed-test sh -c "alembic upgrade head && python -m pipeline.seed_test"

.PHONY: dbt
dbt:
	@# The `dbt` service connects as the dbt role, which reads raw and owns staging and curated
	docker compose run --rm dbt dbt $(or $(ARGS),build)

.PHONY: curated-drift
curated-drift:
	@# As the api role, which reads every curated table, on the test database dbt built.
	@# The password reaches the container through `.env`
	$(APP_RUN) sh -c 'DATABASE_URL="postgresql+psycopg://api:$$API_DB_PASSWORD@db:5432/pipeline_test" python -m pipeline.curated.drift'

.PHONY: pipeline
pipeline:
	$(MAKE) ingest
	$(MAKE) dbt ARGS=build

.PHONY: lint
lint:
	uv run ruff format --check --diff .
	uv run ruff check .
	uv run mypy .
	$(MAKE) lint-migrations

.PHONY: lint-migrations
lint-migrations:
	@# Offline (`alembic upgrade --sql`), so no database is needed: the URL only picks the dialect
	MIGRATIONS_DATABASE_URL=postgresql+psycopg://offline@localhost/offline uv run python bin/lint_migrations.py

.PHONY: format
format:
	uv run ruff format .
	uv run ruff check --fix .

.PHONY: tests
tests:
	$(APP_RUN) pytest -v $(ARGS)

.PHONY: covtest
covtest:
	$(APP_RUN) pytest -v --cov --cov-report=html $(ARGS)

.PHONY: record-cassettes
record-cassettes:
	@# Calls SEC EDGAR for real,
	@# so it is run by hand and never in CI
	$(APP_RUN) sh -c 'test -n "$$EDGAR_USER_AGENT" || { echo "EDGAR_USER_AGENT is required in .env"; exit 1; }; pytest -v -m vcr --record-mode=rewrite pipeline/sources/edgar'
