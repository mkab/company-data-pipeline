.PHONY: lint
lint:
	uv run ruff format --check --diff .
	uv run ruff check .
	uv run mypy .


.PHONY: format
format:
	uv run ruff format .
	uv run ruff check --fix .


.PHONY: tests
tests:
	uv run pytest -v


.PHONY: covtest
covtest:
	uv run pytest -v --cov --cov-report=html
