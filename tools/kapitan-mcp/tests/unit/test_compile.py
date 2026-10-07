"""Unit tests for the compile tool's command building and output parsing."""

from __future__ import annotations

from pathlib import Path

from kapitan_mcp.tools.compile import compile_targets


def test_compile__builds_targets_and_backend_argv(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout="Compiled dev (0.01s)\n")

    compile_targets(mini_inventory, ["dev"], run=run)

    argv = run.calls[0]["argv"]
    assert argv[:2] == ["kapitan", "compile"]
    assert "--targets" in argv
    assert "dev" in argv
    assert "--inventory-backend" in argv


def test_compile__fetch_off_by_default(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout="Compiled dev (0.01s)\n")

    compile_targets(mini_inventory, ["dev"], run=run)

    assert "--fetch" not in run.calls[0]["argv"]


def test_compile__fetch_opt_in_adds_flag(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout="Compiled dev (0.01s)\n")

    compile_targets(mini_inventory, ["dev"], fetch=True, run=run)

    assert "--fetch" in run.calls[0]["argv"]


def test_compile__apply_false_writes_to_temp_not_project(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout="Compiled dev (0.01s)\n")

    compile_targets(mini_inventory, ["dev"], apply=False, run=run)

    argv = run.calls[0]["argv"]
    idx = argv.index("--output-path")
    output = argv[idx + 1]
    assert Path(output).resolve() != mini_inventory.resolve()


def test_compile__parses_per_target_durations(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout="Compiled dev (0.01s)\nCompiled prod (0.02s)\n")

    result = compile_targets(mini_inventory, ["dev", "prod"], run=run)

    by_name = {r.target: r for r in result.results}
    assert by_name["dev"].ok is True
    assert by_name["dev"].duration_s == 0.01
    assert by_name["prod"].duration_s == 0.02
