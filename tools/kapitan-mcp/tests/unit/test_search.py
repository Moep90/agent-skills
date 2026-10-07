"""Unit tests for kapitan_search_inventory raw-YAML search."""

from __future__ import annotations

from pathlib import Path

from kapitan_mcp.tools.search import search_inventory


def test_search__key_scope_classes__finds_all_definitions(mini_inventory: Path) -> None:
    result = search_inventory(mini_inventory, "image", kind="key", scope="classes")

    paths = {m.path for m in result.matches}
    assert "inventory/classes/common.yml" in paths
    assert "inventory/classes/component/mysql.yml" in paths


def test_search__reports_line_numbers_and_snippet(mini_inventory: Path) -> None:
    result = search_inventory(mini_inventory, "mysql:5.7", kind="regex", scope="classes")

    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.path == "inventory/classes/common.yml"
    assert match.line > 0
    assert "mysql:5.7" in match.snippet


def test_search__scope_targets__excludes_class_files(mini_inventory: Path) -> None:
    result = search_inventory(mini_inventory, "image", kind="key", scope="targets")

    paths = {m.path for m in result.matches}
    assert paths == {"inventory/targets/prod.yml"}  # only prod overrides image


def test_search__scope_all__covers_targets_and_classes(mini_inventory: Path) -> None:
    result = search_inventory(mini_inventory, "parameters", kind="key", scope="all")

    paths = {m.path for m in result.matches}
    assert any("targets/" in p for p in paths)
    assert any("classes/" in p for p in paths)
