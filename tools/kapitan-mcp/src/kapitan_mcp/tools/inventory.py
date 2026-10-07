"""Read-only inventory tools.

Discovery tools read the raw YAML directly. The resolved-inventory tools shell out to
the kapitan CLI via ``runner.run`` so the agent sees the merged, interpolated result
instead of guessing at YAML merge order.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

from kapitan_mcp import runner
from kapitan_mcp.errors import (
    InvalidInventoryError,
    KapitanCliError,
    UnknownTargetError,
    enrich,
)
from kapitan_mcp.models import (
    ClassEntry,
    ClassHierarchy,
    ClassList,
    ClassNode,
    InventoryTarget,
    ProjectInfo,
    Target,
    TargetList,
)
from kapitan_mcp.project import resolve_kapitan

RunFn = Callable[..., runner.CommandResult]

_DEFAULT_MAX_BYTES = 1_000_000
_TARGETS_DIR = "inventory/targets"
_CLASSES_DIR = "inventory/classes"


def _load_yaml(path: Path) -> Any:
    """Parse a YAML file, translating parse errors into a typed, actionable error."""
    try:
        return yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise InvalidInventoryError(f"Invalid YAML in {path.name}: {exc}") from exc


def _read_backend(root: Path) -> str:
    """Read the configured inventory backend from ``.kapitan``.

    kapitan looks up the ``inventory-backend`` flag in a per-command section first, then
    the ``global`` section, defaulting to reclass. We check the same places.
    """
    dotkapitan = root / ".kapitan"
    if dotkapitan.exists():
        data = yaml.safe_load(dotkapitan.read_text()) or {}
        for section in ("inventory", "compile", "global"):
            value = data.get(section, {})
            if isinstance(value, dict):
                backend = value.get("inventory-backend")
                if isinstance(backend, str) and backend:
                    return backend
    return "reclass"


def _detect_wrapper(root: Path) -> bool:
    """True if a ``./kapitan`` wrapper script shadows the real CLI."""
    wrapper = root / "kapitan"
    import os

    return wrapper.is_file() and os.access(wrapper, os.X_OK)


def _dotted_name(rel_to_classes: Path) -> str:
    return rel_to_classes.with_suffix("").as_posix().replace("/", ".")


def _class_path(root: Path, dotted: str) -> Path | None:
    base = root / _CLASSES_DIR / Path(*dotted.split("."))
    for suffix in (".yml", ".yaml"):
        candidate = base.with_suffix(suffix)
        if candidate.exists():
            return candidate
    # Directory class: the folder's init.yml stands in for the dotted name.
    for suffix in (".yml", ".yaml"):
        candidate = base / f"init{suffix}"
        if candidate.exists():
            return candidate
    return None


def project_info(root: Path, *, run: RunFn = runner.run) -> ProjectInfo:
    """Detect the project root's backend, kapitan version, and target count.

    Prefer this before any other tool: it tells you which inventory backend is in
    effect, which changes interpolation syntax.
    """
    root = root.resolve()
    version: str | None = None
    warnings: list[str] = []
    try:
        result = run([resolve_kapitan(root), "--version"], cwd=root, timeout=30)
        version = result.stdout.strip().split()[-1] if result.stdout.strip() else None
    except Exception as exc:
        warnings.append(f"could not determine kapitan version: {exc}")

    targets = list((root / _TARGETS_DIR).glob("**/*.yml")) if (root / _TARGETS_DIR).exists() else []
    return ProjectInfo(
        root=str(root),
        kapitan_version=version,
        backend=_read_backend(root),
        wrapper_detected=_detect_wrapper(root),
        targets_count=len(targets),
        warnings=warnings,
    )


def list_targets(root: Path, pattern: str | None = None) -> TargetList:
    """List targets (name + inventory-relative path). Filter by glob ``pattern``."""
    root = root.resolve()
    targets_dir = root / _TARGETS_DIR
    found: list[Target] = []
    for path in sorted(targets_dir.glob("**/*.yml")):
        name = path.stem
        if pattern and not fnmatch(name, pattern):
            continue
        found.append(Target(name=name, path=path.relative_to(root).as_posix()))
    return TargetList(targets=found)


def list_classes(root: Path, pattern: str | None = None) -> ClassList:
    """List classes, mapping dotted names to their inventory-relative file paths."""
    root = root.resolve()
    classes_dir = root / _CLASSES_DIR
    found: list[ClassEntry] = []
    for path in sorted(classes_dir.glob("**/*.yml")):
        dotted = _dotted_name(path.relative_to(classes_dir))
        if pattern and not fnmatch(dotted, pattern):
            continue
        found.append(ClassEntry(dotted_name=dotted, path=path.relative_to(root).as_posix()))
    return ClassList(classes=found)


def inventory_target(
    root: Path,
    target: str,
    *,
    parameter_path: str | None = None,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    run: RunFn = runner.run,
) -> InventoryTarget:
    """Return the fully resolved (merged + interpolated) inventory for one target.

    Use this instead of mentally merging classes. Pass ``parameter_path`` (dotted, e.g.
    ``mysql.image``) to fetch just a subtree and keep the response small; resolved
    inventories can be tens of MB.
    """
    root = root.resolve()
    backend = _read_backend(root)
    try:
        result = run(
            [resolve_kapitan(root), "inventory", "-t", target, "--inventory-backend", backend],
            cwd=root,
        )
    except KapitanCliError as exc:
        raise enrich(exc, target=target) from exc
    data = yaml.safe_load(result.stdout) or {}
    parameters: dict[str, Any] = data.get("parameters", data)

    if parameter_path:
        subtree: Any = parameters
        for key in parameter_path.split("."):
            subtree = subtree[key]
        return InventoryTarget(target=target, backend=backend, subtree=subtree)

    serialized = json.dumps(parameters)
    if len(serialized) > max_bytes:
        return InventoryTarget(
            target=target,
            backend=backend,
            truncated=True,
            hint=(
                "Response too large; call again with a parameter_path "
                "(e.g. 'mysql.image') to fetch a subtree."
            ),
        )
    return InventoryTarget(target=target, backend=backend, parameters=parameters)


def class_hierarchy(root: Path, target: str) -> ClassHierarchy:
    """Show the ordered class include tree for a target.

    Lets you see which class contributes or overrides a value, which matters because
    parameters deep-merge in include order and the target wins last.
    """
    root = root.resolve()
    target_file = root / _TARGETS_DIR / f"{target}.yml"
    if not target_file.is_file():
        raise UnknownTargetError(f"No target {target!r} in the inventory.")
    nodes: list[ClassNode] = []
    visited: set[str] = set()

    def walk(dotted: str, depth: int) -> None:
        if dotted in visited:
            return
        visited.add(dotted)
        path = _class_path(root, dotted)
        nodes.append(
            ClassNode(
                dotted_name=dotted,
                path=path.relative_to(root).as_posix() if path else "",
                depth=depth,
            )
        )
        if path:
            data = _load_yaml(path)
            for child in data.get("classes", []) or []:
                walk(child, depth + 1)

    top = _load_yaml(target_file)
    for dotted in top.get("classes", []) or []:
        walk(dotted, 0)

    return ClassHierarchy(target=target, includes=nodes)
