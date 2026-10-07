MCP_DIR := tools/kapitan-mcp
UV := uv --directory $(MCP_DIR)

.PHONY: help sync lint format typecheck test test-integration test-plugin-cli evals all \
        sync-plugins check-plugins validate-skills

help:
	@echo "Targets: sync lint format typecheck test test-integration test-plugin-cli evals all"
	@echo "         sync-plugins check-plugins validate-skills"

sync:
	$(UV) sync

lint:
	$(UV) run ruff check . ../../scripts --config pyproject.toml
	$(UV) run ruff format --check . ../../scripts --config pyproject.toml

format:
	$(UV) run ruff format . ../../scripts --config pyproject.toml
	$(UV) run ruff check --fix . ../../scripts --config pyproject.toml

typecheck:
	$(UV) run mypy

test:
	$(UV) run pytest -m "not integration and not e2e and not plugin_cli"

test-integration:
	$(UV) run --extra kapitan --extra test-backends pytest -m integration --no-cov

test-plugin-cli:
	$(UV) run pytest -m plugin_cli --no-cov

validate-skills:
	python3 scripts/validate_skills.py

sync-plugins:
	python3 scripts/sync_plugins.py

check-plugins:
	python3 scripts/sync_plugins.py --check

evals:
	@echo "trigger-rate evals run via the skill-creator harness with an API key"

all: lint typecheck test validate-skills check-plugins
