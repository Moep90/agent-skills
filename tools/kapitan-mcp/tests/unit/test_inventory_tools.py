"""Unit tests for the read-only inventory tools.

Discovery tools run against the real mini-inventory fixture. Tools that wrap the kapitan
CLI use the ``stub_run`` seam to assert argv and parse canned output, without needing a
real kapitan install (that is the integration layer).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kapitan_mcp.tools.inventory import (
    class_hierarchy,
    inventory_target,
    list_classes,
    list_targets,
    project_info,
)


def test_project_info__reads_backend_and_counts_targets(mini_inventory: Path, stub_run) -> None:
    info = project_info(mini_inventory, run=stub_run(stdout="0.36.1\n"))

    assert info.root == str(mini_inventory.resolve())
    assert info.backend == "reclass"
    assert info.targets_count == 2
    assert info.kapitan_version == "0.36.1"
    assert info.wrapper_detected is False
    assert info.schema_version >= 1


def test_project_info__reads_backend_from_global_section(tmp_path: Path, stub_run) -> None:
    (tmp_path / "inventory/targets").mkdir(parents=True)
    (tmp_path / ".kapitan").write_text("global:\n  inventory-backend: reclass-rs\n")

    info = project_info(tmp_path, run=stub_run(stdout="0.36.2\n"))

    assert info.backend == "reclass-rs"


def test_project_info__version_lookup_failure__recorded_as_warning(mini_inventory: Path) -> None:
    def failing_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("kapitan not on PATH")

    info = project_info(mini_inventory, run=failing_run)

    assert info.kapitan_version is None
    assert any("kapitan version" in w for w in info.warnings)


def test_list_targets__enumerates_target_files_with_paths(mini_inventory: Path) -> None:
    result = list_targets(mini_inventory)

    names = {t.name for t in result.targets}
    assert names == {"dev", "prod"}
    dev = next(t for t in result.targets if t.name == "dev")
    assert dev.path == "inventory/targets/dev.yml"


def test_list_targets__pattern_filters(mini_inventory: Path) -> None:
    result = list_targets(mini_inventory, pattern="pro*")

    assert {t.name for t in result.targets} == {"prod"}


def test_list_classes__maps_dotted_names_to_paths(mini_inventory: Path) -> None:
    result = list_classes(mini_inventory)

    by_name = {c.dotted_name: c.path for c in result.classes}
    assert by_name["common"] == "inventory/classes/common.yml"
    assert by_name["component.mysql"] == "inventory/classes/component/mysql.yml"


def test_inventory_target__builds_correct_argv_and_parses_json(
    mini_inventory: Path, stub_run
) -> None:
    resolved = {"parameters": {"mysql": {"image": "mysql:8.0-prod"}, "target_name": "prod"}}
    run = stub_run(stdout=json.dumps(resolved))

    result = inventory_target(mini_inventory, "prod", run=run)

    argv = run.calls[0]["argv"]
    assert argv[0] == "kapitan"
    assert "inventory" in argv
    assert "-t" in argv
    assert "prod" in argv
    assert run.calls[0]["cwd"] == mini_inventory.resolve()
    assert result.parameters["mysql"]["image"] == "mysql:8.0-prod"
    assert result.truncated is False


def test_inventory_target__parameter_path_filters_subtree(mini_inventory: Path, stub_run) -> None:
    resolved = {"parameters": {"mysql": {"image": "mysql:8.0-prod", "port": 3306}}}
    run = stub_run(stdout=json.dumps(resolved))

    result = inventory_target(mini_inventory, "prod", parameter_path="mysql.image", run=run)

    assert result.subtree == "mysql:8.0-prod"


def test_inventory_target__truncates_oversized_payload(mini_inventory: Path, stub_run) -> None:
    big = {"parameters": {"blob": "x" * 5000}}
    run = stub_run(stdout=json.dumps(big))

    result = inventory_target(mini_inventory, "prod", max_bytes=1000, run=run)

    assert result.truncated is True
    assert result.hint is not None


def test_class_hierarchy__corrupt_class_yaml__raises_typed_actionable_error(
    tmp_path: Path, mini_inventory: Path
) -> None:
    import shutil

    from kapitan_mcp.errors import InvalidInventoryError

    proj = tmp_path / "proj"
    shutil.copytree(mini_inventory, proj)
    (proj / "inventory/classes/common.yml").write_text("parameters: [unclosed\n")

    with pytest.raises(InvalidInventoryError) as excinfo:
        class_hierarchy(proj, "dev")

    assert excinfo.value.remediation  # actionable, not a bare stack trace
    assert "common.yml" in str(excinfo.value)


def test_class_hierarchy__unknown_target__raises_typed_error_without_leaking_path(
    mini_inventory: Path,
) -> None:
    from kapitan_mcp.errors import UnknownTargetError

    with pytest.raises(UnknownTargetError) as excinfo:
        class_hierarchy(mini_inventory, "nope")

    assert excinfo.value.remediation  # actionable, not a bare FileNotFoundError
    assert "nope" in str(excinfo.value)
    assert str(mini_inventory) not in str(excinfo.value)  # no absolute sandbox path leak


def test_class_hierarchy__reports_ordered_includes(mini_inventory: Path) -> None:
    result = class_hierarchy(mini_inventory, "prod")

    dotted = [n.dotted_name for n in result.includes]
    assert dotted == ["common", "component.mysql"]


def test_class_hierarchy__resolves_and_recurses_into_directory_init_class(
    tmp_path: Path,
) -> None:
    (tmp_path / "inventory/targets").mkdir(parents=True)
    (tmp_path / "inventory/classes/stack").mkdir(parents=True)
    (tmp_path / "inventory/targets/t.yml").write_text("classes:\n  - stack\n")
    # `stack` is a directory class defined by init.yml, which itself includes a child.
    (tmp_path / "inventory/classes/stack/init.yml").write_text("classes:\n  - stack.child\n")
    (tmp_path / "inventory/classes/stack/child.yml").write_text("parameters: {}\n")

    result = class_hierarchy(tmp_path, "t")

    by_name = {n.dotted_name: n for n in result.includes}
    assert by_name["stack"].path == "inventory/classes/stack/init.yml"
    assert "stack.child" in by_name  # recursion followed the init.yml include
