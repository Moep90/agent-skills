"""Unit tests for project-root discovery and path sandboxing."""

from pathlib import Path

import pytest

from kapitan_mcp.errors import PathOutsideProjectError, ProjectNotFoundError
from kapitan_mcp.project import find_project_root, resolve_kapitan, resolve_within


def _make_exe(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)


def test_resolve_kapitan__prefers_project_venv(tmp_path: Path) -> None:
    venv_bin = tmp_path / ".venv" / "bin" / "kapitan"
    _make_exe(venv_bin)
    _make_exe(tmp_path / "kapitan")  # wrapper also present; venv still wins

    assert resolve_kapitan(tmp_path) == str(venv_bin.resolve())


def test_resolve_kapitan__falls_back_to_wrapper(tmp_path: Path) -> None:
    wrapper = tmp_path / "kapitan"
    _make_exe(wrapper)

    assert resolve_kapitan(tmp_path) == str(wrapper.resolve())


def test_resolve_kapitan__non_executable_wrapper_ignored(tmp_path: Path) -> None:
    wrapper = tmp_path / "kapitan"
    wrapper.write_text("not executable\n")  # exists but no +x

    assert resolve_kapitan(tmp_path) == "kapitan"


def test_resolve_kapitan__no_local_binary__falls_back_to_path(tmp_path: Path) -> None:
    assert resolve_kapitan(tmp_path) == "kapitan"


def test_resolve_within__path_inside_root__returns_resolved_absolute(tmp_path: Path) -> None:
    (tmp_path / "inventory").mkdir()
    target = tmp_path / "inventory" / "targets" / "dev.yml"

    result = resolve_within(tmp_path, "inventory/targets/dev.yml")

    assert result == target.resolve()


def test_resolve_within__parent_traversal__raises(tmp_path: Path) -> None:
    with pytest.raises(PathOutsideProjectError):
        resolve_within(tmp_path, "../../etc/passwd")


def test_resolve_within__absolute_path_outside__raises(tmp_path: Path) -> None:
    with pytest.raises(PathOutsideProjectError):
        resolve_within(tmp_path, "/etc/passwd")


def test_resolve_within__symlink_escape__raises(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-secret"
    outside.mkdir(exist_ok=True)
    root = tmp_path / "project"
    root.mkdir()
    (root / "link").symlink_to(outside)

    with pytest.raises(PathOutsideProjectError):
        resolve_within(root, "link/secret.txt")


def test_find_project_root__marked_by_dot_kapitan__found_walking_up(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "inventory").mkdir(parents=True)
    (root / ".kapitan").write_text("inventory_backend: reclass\n")
    nested = root / "inventory" / "classes"
    nested.mkdir()

    assert find_project_root(nested) == root.resolve()


def test_find_project_root__marked_by_inventory_dir__found(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "inventory").mkdir(parents=True)

    assert find_project_root(root / "inventory") == root.resolve()


def test_find_project_root__no_marker__raises(tmp_path: Path) -> None:
    with pytest.raises(ProjectNotFoundError):
        find_project_root(tmp_path)
