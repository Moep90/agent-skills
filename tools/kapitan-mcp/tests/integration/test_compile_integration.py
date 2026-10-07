"""Integration tests for compile and compile-diff against the real kapitan CLI."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from kapitan_mcp.tools.compile import compile_diff, compile_targets

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini-inventory"
OMEGA = Path(__file__).parent.parent / "fixtures" / "omega-inventory"


@pytest.fixture(autouse=True)
def _require_kapitan() -> None:
    if shutil.which("kapitan") is None:
        pytest.skip("kapitan CLI not installed")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    dest = tmp_path / "proj"
    shutil.copytree(FIXTURE, dest)
    return dest


@pytest.fixture
def omega_project(tmp_path: Path) -> Path:
    dest = tmp_path / "proj"
    shutil.copytree(OMEGA, dest)
    return dest


def test_compile__apply_false__leaves_committed_output_untouched(project: Path) -> None:
    before = (project / "compiled/dev/config.yml.j2").read_text()

    result = compile_targets(project, ["dev"], apply=False)

    assert all(r.ok for r in result.results)
    assert (project / "compiled/dev/config.yml.j2").read_text() == before


def test_compile_diff__no_source_change__empty_diff(project: Path) -> None:
    result = compile_diff(project, ["dev", "prod"])

    assert result.changed_files == []
    assert result.unchanged_count >= 2


def test_compile_diff__inventory_change__shows_only_affected_target(project: Path) -> None:
    # Bump prod's image; dev is unaffected, so only prod's rendered file should differ.
    prod = project / "inventory/targets/prod.yml"
    prod.write_text(prod.read_text().replace("mysql:8.0-prod", "mysql:9.9-prod"))

    result = compile_diff(project, ["dev", "prod"])

    changed_paths = {c.path for c in result.changed_files}
    assert any("prod" in p for p in changed_paths)
    assert not any("dev" in p for p in changed_paths)
    prod_diff = next(c.diff for c in result.changed_files if "prod" in c.path)
    assert "mysql:9.9-prod" in prod_diff


def test_compile_diff__single_target_subset__ignores_other_targets(project: Path) -> None:
    # Compiling only dev must not report the un-compiled prod tree as removed.
    result = compile_diff(project, ["dev"])

    assert result.changed_files == []


def test_compile_diff__never_writes_into_committed_compiled(project: Path) -> None:
    before = sorted(p.name for p in (project / "compiled").rglob("*"))

    compile_diff(project, ["dev"])

    after = sorted(p.name for p in (project / "compiled").rglob("*"))
    assert before == after


def test_compile_diff__reclass_family_backend__no_source_change__empty_diff(
    backend_project,
) -> None:
    _, root = backend_project

    result = compile_diff(root, ["dev", "prod"])

    assert result.changed_files == []
    assert result.unchanged_count >= 2


def test_compile_diff__omegaconf_backend__no_source_change__empty_diff(
    omega_project: Path,
) -> None:
    result = compile_diff(omega_project, ["dev", "prod"])

    assert result.changed_files == []
    assert result.unchanged_count >= 2
