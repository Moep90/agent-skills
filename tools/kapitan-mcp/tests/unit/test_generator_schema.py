"""Unit tests for the schema-by-example tool.

It reads the resolved inventory, collects the key set actually used under a top-level block
(``components`` by default), and reports each key's usage plus the rare keys (used by exactly
one block) that are likely typos. Canned resolved YAML through ``stub_run`` keeps it offline.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from kapitan_mcp.tools.generators import generator_schema


def _resolved(block_key: str, blocks: dict) -> str:
    node: dict = {}
    cursor = node
    parts = block_key.split(".")
    for part in parts[:-1]:
        cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = blocks
    return yaml.safe_dump({"parameters": node})


def test_collects_key_usage_across_blocks(mini_inventory: Path, stub_run) -> None:
    run = stub_run(
        stdout=_resolved(
            "components",
            {"web": {"image": "nginx", "ports": {}}, "api": {"image": "go", "env": {}}},
        )
    )

    schema = generator_schema(mini_inventory, "components", ["prod"], run=run)

    by_key = {k.key: k for k in schema.keys}
    assert by_key["image"].count == 2
    assert set(by_key["image"].examples) == {"web", "api"}
    assert by_key["ports"].count == 1
    assert schema.blocks_examined == 2


def test_rare_key_is_flagged_as_suspect(mini_inventory: Path, stub_run) -> None:
    run = stub_run(
        stdout=_resolved(
            "components",
            {"web": {"image": "nginx"}, "api": {"image": "go", "imgae": "typo"}},
        )
    )

    schema = generator_schema(mini_inventory, "components", ["prod"], run=run)

    assert "imgae" in schema.rare_keys
    assert "image" not in schema.rare_keys


def test_dotted_key_navigates_nested_collection(mini_inventory: Path, stub_run) -> None:
    run = stub_run(
        stdout=_resolved(
            "generators.multus.networks",
            {"net-a": {"type": "bridge"}, "net-b": {"type": "macvlan"}},
        )
    )

    schema = generator_schema(mini_inventory, "generators.multus.networks", ["prod"], run=run)

    assert schema.blocks_examined == 2
    assert {k.key for k in schema.keys} == {"type"}


def test_block_names_deduped_across_targets(mini_inventory: Path, stub_run) -> None:
    # dev and prod both resolve to the same block: it counts once, not twice.
    run = stub_run(stdout=_resolved("components", {"web": {"image": "nginx"}}))

    schema = generator_schema(mini_inventory, "components", None, run=run)

    image = next(k for k in schema.keys if k.key == "image")
    assert image.count == 1
    assert image.examples == ["web"]


def test_missing_key_yields_empty_schema(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout=_resolved("something_else", {"x": {"a": 1}}))

    schema = generator_schema(mini_inventory, "components", ["prod"], run=run)

    assert schema.blocks_examined == 0
    assert schema.keys == []
    assert schema.rare_keys == []


def test_non_dict_block_values_are_ignored(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout=_resolved("components", {"web": {"image": "nginx"}, "flag": "scalar"}))

    schema = generator_schema(mini_inventory, "components", ["prod"], run=run)

    assert schema.blocks_examined == 1


def test_builds_correct_argv(mini_inventory: Path, stub_run) -> None:
    run = stub_run(stdout=_resolved("components", {}))

    generator_schema(mini_inventory, "components", ["prod"], run=run)

    argv = run.calls[0]["argv"]
    assert "inventory" in argv
    assert "prod" in argv
