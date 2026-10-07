"""Compile tools: run kapitan compile and diff the result against committed output.

``compile_targets`` runs a compile, writing to the project's ``compiled/`` only when
``apply`` is true. ``compile_diff`` compiles into a temp directory and reports a unified
diff against the committed output, so an agent can review a change before applying it.
"""

from __future__ import annotations

import difflib
import re
import tempfile
from collections.abc import Callable
from pathlib import Path

from kapitan_mcp import runner
from kapitan_mcp.errors import KapitanCliError, enrich
from kapitan_mcp.models import (
    ChangedFile,
    CompileDiff,
    CompileResult,
    CompileTargetResult,
)
from kapitan_mcp.project import resolve_kapitan
from kapitan_mcp.tools.inventory import _read_backend

RunFn = Callable[..., runner.CommandResult]

_COMPILED_RE = re.compile(r"Compiled (\S+) \(([\d.]+)s\)")
_MAX_DIFF_BYTES = 200_000


def _run_kapitan(run: RunFn, argv: list[str], cwd: Path) -> runner.CommandResult:
    """Run a kapitan command, upgrading any failure into an actionable typed error."""
    try:
        return run(argv, cwd=cwd)
    except KapitanCliError as exc:
        raise enrich(exc) from exc


def _compile_argv(root: Path, targets: list[str], *, fetch: bool, output_path: Path) -> list[str]:
    argv = [
        resolve_kapitan(root),
        "compile",
        "--targets",
        *targets,
        "--inventory-backend",
        _read_backend(root),
        "--output-path",
        str(output_path),
    ]
    if fetch:
        argv.append("--fetch")
    return argv


def _parse_results(targets: list[str], stdout: str) -> list[CompileTargetResult]:
    durations = {name: float(secs) for name, secs in _COMPILED_RE.findall(stdout)}
    return [
        CompileTargetResult(target=t, ok=t in durations, duration_s=durations.get(t))
        for t in targets
    ]


def compile_targets(
    root: Path,
    targets: list[str],
    *,
    fetch: bool = False,
    apply: bool = True,
    run: RunFn = runner.run,
) -> CompileResult:
    """Compile ``targets``. Writes into the project only when ``apply`` is true.

    ``fetch`` (remote dependencies) is off by default and must be opted into explicitly.
    """
    root = root.resolve()
    output_path = root if apply else Path(tempfile.mkdtemp(prefix="kapitan-compile-"))
    argv = _compile_argv(root, targets, fetch=fetch, output_path=output_path)
    result = _run_kapitan(run, argv, root)
    return CompileResult(results=_parse_results(targets, result.stdout + result.stderr))


def _diff_trees(
    committed: Path, candidate: Path, targets: list[str] | None = None
) -> tuple[list[ChangedFile], int]:
    """Unified diff of two ``compiled/`` trees.

    When ``targets`` is given, only the ``compiled/<target>/`` subtrees are compared, so
    compiling a subset of targets does not report the others as removed.
    """
    allowed = set(targets) if targets else None

    def collect(base: Path) -> dict[Path, Path]:
        found = {}
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(base)
            if allowed is None or (rel.parts and rel.parts[0] in allowed):
                found[rel] = p
        return found

    committed_files = collect(committed)
    candidate_files = collect(candidate)

    changed: list[ChangedFile] = []
    unchanged = 0
    for rel in sorted(set(committed_files) | set(candidate_files)):
        old_p = committed_files.get(rel)
        new_p = candidate_files.get(rel)
        old = old_p.read_text().splitlines(keepends=True) if old_p else []
        new = new_p.read_text().splitlines(keepends=True) if new_p else []
        if old == new:
            unchanged += 1
            continue
        diff = "".join(difflib.unified_diff(old, new, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
        changed.append(ChangedFile(path=rel.as_posix(), diff=diff))
    return changed, unchanged


def compile_diff(
    root: Path,
    targets: list[str],
    *,
    run: RunFn = runner.run,
) -> CompileDiff:
    """Compile ``targets`` into a temp dir and diff against the committed ``compiled/``.

    Never writes into the project's ``compiled/``. Use this to review what a change would
    produce before applying it.
    """
    root = root.resolve()
    tmp = Path(tempfile.mkdtemp(prefix="kapitan-diff-"))
    _run_kapitan(run, _compile_argv(root, targets, fetch=False, output_path=tmp), root)

    changed, unchanged = _diff_trees(root / "compiled", tmp / "compiled", targets)
    kept, truncated = _cap_diffs(changed, _MAX_DIFF_BYTES)
    return CompileDiff(changed_files=kept, unchanged_count=unchanged, truncated=truncated)


def _cap_diffs(changed: list[ChangedFile], max_bytes: int) -> tuple[list[ChangedFile], bool]:
    """Keep changed-file diffs until the cumulative size passes ``max_bytes``."""
    kept: list[ChangedFile] = []
    total = 0
    for cf in changed:
        total += len(cf.diff)
        if total > max_bytes:
            return kept, True
        kept.append(cf)
    return kept, False
