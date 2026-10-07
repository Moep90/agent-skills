"""Integration tests that drive the real kapitan CLI against the mini-inventory fixture.

Marked ``integration`` so the default unit run skips them. They need a real ``kapitan``
on PATH (installed via the ``kapitan`` optional dependency).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from kapitan_mcp.errors import KapitanCliError
from kapitan_mcp.tools.inventory import inventory_target, project_info
from kapitan_mcp.tools.lint import lint

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini-inventory"
OMEGA = Path(__file__).parent.parent / "fixtures" / "omega-inventory"


@pytest.fixture(autouse=True)
def _require_kapitan() -> None:
    if shutil.which("kapitan") is None:
        pytest.skip("kapitan CLI not installed")


def test_inventory_target__dev__resolves_merge_and_interpolation() -> None:
    result = inventory_target(FIXTURE, "dev")

    assert result.parameters is not None
    # component default wins for dev (no target-level override)
    assert result.parameters["mysql"]["image"] == "mysql:8.0"
    # ${target_name} interpolated after the full merge
    assert result.parameters["namespace"] == "dev"


def test_inventory_target__prod__target_override_wins_last() -> None:
    result = inventory_target(FIXTURE, "prod")

    assert result.parameters is not None
    assert result.parameters["mysql"]["image"] == "mysql:8.0-prod"


def test_inventory_target__parameter_path__returns_subtree() -> None:
    result = inventory_target(FIXTURE, "prod", parameter_path="mysql.image")

    assert result.subtree == "mysql:8.0-prod"


def test_project_info__reports_real_kapitan_version() -> None:
    info = project_info(FIXTURE)

    assert info.kapitan_version is not None
    assert info.backend == "reclass"


def test_project_info__reports_selected_reclass_backend(backend_project) -> None:
    backend, root = backend_project
    info = project_info(root)
    assert info.backend == backend


def test_inventory_target__reclass_family__resolves_merge_and_interpolation(
    backend_project,
) -> None:
    _, root = backend_project
    result = inventory_target(root, "dev")
    assert result.parameters is not None
    assert result.parameters["mysql"]["image"] == "mysql:8.0"
    assert result.parameters["namespace"] == "dev"


def test_inventory_target__missing_class__raises_class_not_found(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    shutil.copytree(FIXTURE, proj)
    target = proj / "inventory/targets/dev.yml"
    target.write_text("classes:\n  - does.not.exist\nparameters:\n  target_name: dev\n")

    with pytest.raises(KapitanCliError) as excinfo:
        inventory_target(proj, "dev")

    assert excinfo.value.code == "CLASS_NOT_FOUND"
    assert excinfo.value.remediation


def test_lint__clean_project__passes() -> None:
    result = lint(FIXTURE)

    assert result.ok is True
    assert "orphan" in result.output.lower()


def test_project_info__omegaconf_backend() -> None:
    info = project_info(OMEGA)
    assert info.backend == "omegaconf"


def test_inventory_target__omegaconf__resolves_dot_interpolation() -> None:
    result = inventory_target(OMEGA, "dev")
    assert result.parameters is not None
    assert result.parameters["mysql"]["image"] == "mysql:8.0"
    assert result.parameters["namespace"] == "dev"
    assert result.parameters["env_label"] == "DEV"


def test_inventory_target__omegaconf__prod_override_wins() -> None:
    result = inventory_target(OMEGA, "prod")
    assert result.parameters["mysql"]["image"] == "mysql:8.0-prod"
