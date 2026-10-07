"""kapitan_lint: run kapitan's built-in lint (yamllint, orphan-class checks).

A non-zero exit means lint found problems, which is a normal result here rather than a
tool failure, so we report it as ``ok=False`` with the output instead of raising.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from kapitan_mcp import runner
from kapitan_mcp.errors import KapitanCliError
from kapitan_mcp.models import LintResult
from kapitan_mcp.project import resolve_kapitan

RunFn = Callable[..., runner.CommandResult]


def lint(root: Path, *, run: RunFn = runner.run) -> LintResult:
    """Run ``kapitan lint`` and report whether it passed, with the raw output."""
    root = root.resolve()
    try:
        result = run([resolve_kapitan(root), "lint"], cwd=root)
        return LintResult(ok=True, output=(result.stdout + result.stderr).strip())
    except KapitanCliError as exc:
        return LintResult(ok=False, output=(exc.stdout + exc.stderr).strip())
