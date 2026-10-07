"""Generator-trace tool: catch the silent no-op.

A component/generator block emits nothing unless a kadet compile entry consumes it, the
class is included, and a target inherits the chain. Kapitan does not validate this, so a
block no generator reads just disappears. This tool inspects the *resolved* inventory
(backend-agnostic, since it reads kapitan's merged output, not raw classes) and flags every
generator-input block that no kadet compile entry plausibly consumes.

Detection is a heuristic on compile-entry input paths, not a compile: it catches an unwired
block, not a mistyped key *inside* a block (a snake_case/camelCase typo that the generator
silently drops). For that, compile and inspect with ``kapitan_compile_diff``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from kapitan_mcp import runner
from kapitan_mcp.errors import KapitanCliError, enrich
from kapitan_mcp.models import (
    GeneratorBlock,
    GeneratorSchema,
    GeneratorTrace,
    SchemaKey,
    TargetTrace,
)
from kapitan_mcp.project import resolve_kapitan
from kapitan_mcp.tools.inventory import _read_backend, list_targets

RunFn = Callable[..., runner.CommandResult]

# Input-path basenames that identify the kubernetes/manifest generator (the one that reads
# the top-level ``components`` key). Fetched into different dir names across projects.
_KUBERNETES_BASENAMES = frozenset({"kubernetes", "manifests", "kstmz", "components"})

# ``generators.<name>`` sub-keys that are configuration namespaces of the kubernetes-family
# generator rather than standalone domain generators with their own lib. If a kubernetes
# entry is present, these are considered wired by it.
_KUBERNETES_SUBKEYS = frozenset({"kubernetes", "argocd", "ingress", "ingresses", "namespace"})


def _resolved_parameters(root: Path, target: str, run: RunFn) -> tuple[str, dict[str, Any]]:
    """Return ``(backend, resolved parameters)`` for one target via the kapitan CLI."""
    backend = _read_backend(root)
    try:
        result = run(
            [resolve_kapitan(root), "inventory", "-t", target, "--inventory-backend", backend],
            cwd=root,
        )
    except KapitanCliError as exc:
        raise enrich(exc, target=target) from exc
    data = yaml.safe_load(result.stdout) or {}
    params = data.get("parameters", data)
    return backend, params if isinstance(params, dict) else {}


def _kadet_input_basenames(params: dict[str, Any]) -> list[str]:
    """Basenames of every ``input_type: kadet`` compile entry's input paths."""
    compile_entries = (params.get("kapitan") or {}).get("compile") or []
    basenames: list[str] = []
    for entry in compile_entries:
        if not isinstance(entry, dict) or entry.get("input_type") != "kadet":
            continue
        for path in entry.get("input_paths") or []:
            basenames.append(str(path))
    return basenames


def _match_component(basenames: list[str]) -> str | None:
    """The input path that wires the kubernetes generator, or None."""
    for path in basenames:
        if Path(path).name in _KUBERNETES_BASENAMES:
            return path
    # Fallback: any kadet entry at all may be the components generator under a custom name.
    return basenames[0] if basenames else None


def _match_generator(name: str, basenames: list[str]) -> str | None:
    """The input path that wires ``generators.<name>``, or None."""
    for path in basenames:
        base = Path(path).name
        if base == name or name in base or base in name:
            return path
    if name in _KUBERNETES_SUBKEYS:
        return _match_component(basenames)
    return None


def _blocks_for_target(params: dict[str, Any]) -> list[GeneratorBlock]:
    basenames = _kadet_input_basenames(params)
    blocks: list[GeneratorBlock] = []

    components = params.get("components")
    if isinstance(components, dict):
        for name in components:
            matched = _match_component(basenames)
            blocks.append(
                GeneratorBlock(
                    path=f"components.{name}",
                    kind="component",
                    wired=matched is not None,
                    matched_input_path=matched,
                    hint=None
                    if matched
                    else "No input_type: kadet compile entry found. Add one for the "
                    "kubernetes generator and include the class in the target.",
                )
            )

    generators = params.get("generators")
    if isinstance(generators, dict):
        for name in generators:
            matched = _match_generator(name, basenames)
            blocks.append(
                GeneratorBlock(
                    path=f"generators.{name}",
                    kind="generator",
                    wired=matched is not None,
                    matched_input_path=matched,
                    hint=None
                    if matched
                    else f"No kadet compile entry whose input path matches '{name}'. If this "
                    "generator is emitted by another lib, verify with kapitan_compile_diff.",
                )
            )

    return blocks


def generator_trace(
    root: Path,
    targets: list[str] | None = None,
    *,
    run: RunFn = runner.run,
) -> GeneratorTrace:
    """Flag generator-input blocks that no kadet compile entry consumes (the silent no-op).

    Reads the resolved inventory for each target (all targets when ``targets`` is None) and,
    for every ``components.<name>`` and ``generators.<name>`` block, checks whether a kadet
    compile entry plausibly consumes it. Run after editing a component/generator block, then
    ``kapitan_compile_diff`` to review the output. Detects unwired blocks, not mistyped keys
    inside a block.
    """
    root = root.resolve()
    names = targets if targets else [t.name for t in list_targets(root).targets]

    target_traces: list[TargetTrace] = []
    orphans: list[str] = []
    for name in names:
        backend, params = _resolved_parameters(root, name, run)
        blocks = _blocks_for_target(params)
        target_traces.append(TargetTrace(target=name, backend=backend, blocks=blocks))
        orphans.extend(f"{name}: {b.path}" for b in blocks if not b.wired)

    return GeneratorTrace(targets=target_traces, orphans=orphans)


_MAX_EXAMPLES = 3


def _dig(params: dict[str, Any], dotted: str) -> Any:
    """Walk a dotted key path; return None if any segment is missing or not a dict."""
    node: Any = params
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def generator_schema(
    root: Path,
    key: str = "components",
    targets: list[str] | None = None,
    *,
    run: RunFn = runner.run,
) -> GeneratorSchema:
    """Report the keys actually used under a generator block, learned from the project itself.

    Reads the resolved inventory for each target (all targets when ``targets`` is None),
    navigates the dotted ``key`` (default ``components``) to a mapping of blocks, and reports
    every key those blocks use with the count of distinct blocks and example block names. Keys
    used by exactly one block are returned in ``rare_keys`` as likely typos or new fields.
    This is schema-by-example: it shows what is known-good in this project, not the full
    generator schema, so a never-yet-used valid key will not appear.
    """
    root = root.resolve()
    names = targets if targets else [t.name for t in list_targets(root).targets]

    # key -> set of distinct block names using it (deduped across targets).
    usage: dict[str, set[str]] = {}
    block_names: set[str] = set()
    for name in names:
        _backend, params = _resolved_parameters(root, name, run)
        blocks = _dig(params, key)
        if not isinstance(blocks, dict):
            continue
        for block_name, config in blocks.items():
            if not isinstance(config, dict):
                continue
            block_names.add(block_name)
            for field in config:
                usage.setdefault(field, set()).add(block_name)

    keys = [
        SchemaKey(key=k, count=len(blocks), examples=sorted(blocks)[:_MAX_EXAMPLES])
        for k, blocks in sorted(usage.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ]
    rare_keys = sorted(k for k, blocks in usage.items() if len(blocks) == 1)

    return GeneratorSchema(
        key=key,
        blocks_examined=len(block_names),
        keys=keys,
        rare_keys=rare_keys,
    )
