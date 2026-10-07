.PHONY: help sync lint format test test-plugin-cli sync-plugins check-plugins check-bump \
        validate-skills all

help:
	@echo "Targets: sync lint format test test-plugin-cli all"
	@echo "         sync-plugins check-plugins check-bump validate-skills"

sync:
	uv sync --locked

lint:
	uv run --locked ruff check .
	uv run --locked ruff format --check .

format:
	uv run --locked ruff format .
	uv run --locked ruff check --fix .

test:
	uv run --locked pytest -m "not plugin_cli"

test-plugin-cli:
	uv run --locked pytest -m plugin_cli

validate-skills:
	python3 scripts/validate_skills.py

sync-plugins:
	python3 scripts/sync_plugins.py

check-plugins:
	python3 scripts/sync_plugins.py --check

check-bump:
	python3 scripts/sync_plugins.py --check-bump $${BASE:-origin/main}

all: lint test validate-skills check-plugins
