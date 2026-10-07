"""Unit tests for the generator-trace tool.

The tool reads the *resolved* inventory (via the runner seam) and flags any
components/generators block that no kadet compile entry consumes: the silent no-op. Tests
feed canned resolved YAML through ``stub_run`` so no real kapitan is needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from kapitan_mcp.errors import KapitanCliError
from kapitan_mcp.tools.generators import generator_trace


def _resolved(components=None, generators=None, compile_entries=None) -> str:
    """Build a canned `kapitan inventory -t` YAML document."""
    params: dict = {}
    if components is not None:
        params["components"] = components
    if generators is not None:
        params["generators"] = generators
    params["kapitan"] = {"compile": compile_entries or []}
    return yaml.safe_dump({"parameters": params})


def _kadet(*input_paths: str) -> dict:
    return {"input_type": "kadet", "input_paths": list(input_paths)}


def test_component_with_no_kadet_entry_is_orphan(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout=_resolved(components={"web": {"image": "nginx"}}, compile_entries=[]))

    trace = generator_trace(mini_inventory, ["prod"], run=run)

    block = trace.targets[0].blocks[0]
    assert block.path == "components.web"
    assert block.kind == "component"
    assert block.wired is False
    assert "prod: components.web" in trace.orphans


def test_component_with_kubernetes_kadet_entry_is_wired(mini_inventory: Path, stub_run) -> None:
    run = stub_run(
        stdout=_resolved(
            components={"web": {"image": "nginx"}},
            compile_entries=[_kadet("system/generators/kubernetes")],
        )
    )

    trace = generator_trace(mini_inventory, ["prod"], run=run)

    block = trace.targets[0].blocks[0]
    assert block.wired is True
    assert block.matched_input_path == "system/generators/kubernetes"
    assert trace.orphans == []


def test_generator_block_wired_by_matching_lib_basename(mini_inventory: Path, stub_run) -> None:
    run = stub_run(
        stdout=_resolved(
            generators={"multus": {"networks": {"a": {}}}},
            compile_entries=[_kadet("lib/multus")],
        )
    )

    trace = generator_trace(mini_inventory, ["prod"], run=run)

    block = trace.targets[0].blocks[0]
    assert block.path == "generators.multus"
    assert block.kind == "generator"
    assert block.wired is True


def test_unknown_generator_with_only_kubernetes_entry_is_orphan(
    mini_inventory: Path, stub_run
) -> None:
    run = stub_run(
        stdout=_resolved(
            generators={"mynewthing": {"items": {}}},
            compile_entries=[_kadet("system/generators/kubernetes")],
        )
    )

    trace = generator_trace(mini_inventory, ["prod"], run=run)

    block = trace.targets[0].blocks[0]
    assert block.wired is False
    assert block.hint is not None
    assert "prod: generators.mynewthing" in trace.orphans


def test_known_kubernetes_subkey_generator_is_wired(mini_inventory: Path, stub_run) -> None:
    run = stub_run(
        stdout=_resolved(
            generators={"argocd": {"configs": {}}},
            compile_entries=[_kadet("system/generators/kubernetes")],
        )
    )

    trace = generator_trace(mini_inventory, ["prod"], run=run)

    assert trace.targets[0].blocks[0].wired is True
    assert trace.orphans == []


def test_no_generator_blocks_yields_empty_trace(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout=_resolved(compile_entries=[_kadet("system/generators/kubernetes")]))

    trace = generator_trace(mini_inventory, ["prod"], run=run)

    assert trace.targets[0].blocks == []
    assert trace.orphans == []


def test_targets_none_enumerates_all_targets(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout=_resolved(components={"web": {"image": "nginx"}}, compile_entries=[]))

    trace = generator_trace(mini_inventory, None, run=run)

    assert {t.target for t in trace.targets} == {"dev", "prod"}


def test_component_wired_by_fallback_when_only_custom_kadet_entry(
    mini_inventory: Path, stub_run
) -> None:
    # No kubernetes-family basename, but a kadet entry exists: fall back to it as the
    # plausible components generator rather than crying orphan.
    run = stub_run(
        stdout=_resolved(
            components={"web": {"image": "nginx"}},
            compile_entries=[_kadet("lib/customgen")],
        )
    )

    trace = generator_trace(mini_inventory, ["prod"], run=run)

    block = trace.targets[0].blocks[0]
    assert block.wired is True
    assert block.matched_input_path == "lib/customgen"


def test_cli_error_is_enriched_and_raised(mini_inventory: Path) -> None:
    def failing_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise KapitanCliError("boom", exit_code=1, stdout="", stderr="target broke")

    with pytest.raises(KapitanCliError):
        generator_trace(mini_inventory, ["prod"], run=failing_run)


def test_builds_correct_argv_with_backend(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout=_resolved(compile_entries=[]))

    generator_trace(mini_inventory, ["prod"], run=run)

    argv = run.calls[0]["argv"]
    assert "inventory" in argv
    assert "-t" in argv
    assert "prod" in argv
    assert "--inventory-backend" in argv
