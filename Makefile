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
	@echo "                 	(the downgrade empties the development database)"
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
	@# The round trip fails when a downgrade raises or an upgrade cannot run twice (see docs/migrations.md)
	$(APP_RUN) sh -c "alembic upgrade head && alembic check && alembic downgrade base && alembic upgrade head"

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
	@# Calls SEC EDGAR for real, so it is run by hand and never in CI
	$(APP_RUN) sh -c 'test -n "$$EDGAR_USER_AGENT" || { echo "EDGAR_USER_AGENT is required in .env"; exit 1; }; pytest -v -m vcr --record-mode=rewrite pipeline/sources/edgar'
