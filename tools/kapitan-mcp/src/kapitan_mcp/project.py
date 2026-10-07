"""Project-root discovery and path sandboxing.

Every filesystem path that originates from the model must pass through
:func:`resolve_within` before use. This is the single choke point that blocks
``../`` traversal and symlink escapes out of the sandboxed project root.
"""

from __future__ import annotations

import os
from pathlib import Path

from kapitan_mcp.errors import PathOutsideProjectError, ProjectNotFoundError

# Files/dirs that mark the root of a Kapitan project.
_ROOT_MARKERS = (".kapitan", "inventory")


def resolve_kapitan(root: Path) -> str:
    """Pick the kapitan executable for ``root``, preferring the project's own toolchain.

    Order: the in-project ``.venv/bin/kapitan``, then a ``./kapitan`` wrapper, then bare
    ``kapitan`` from PATH. The first two must exist and be executable. Using the project's
    pinned kapitan avoids version drift against a bundled or global CLI. ``root`` is fixed
    at server start, so this never runs a binary the model chose.
    """
    for candidate in (root / ".venv" / "bin" / "kapitan", root / "kapitan"):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
    return "kapitan"


def find_project_root(start: Path) -> Path:
    """Walk up from ``start`` until a Kapitan root marker is found.

    Returns the resolved project root. Raises :class:`ProjectNotFoundError` if no
    ``.kapitan`` file or ``inventory/`` directory is found in ``start`` or any parent.
    """
    current = start.resolve()
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in _ROOT_MARKERS):
            return candidate
    raise ProjectNotFoundError(f"No Kapitan project found at or above {start}")


def resolve_within(root: Path, user_path: str | Path) -> Path:
    """Resolve ``user_path`` and guarantee the result stays inside ``root``.

    Raises :class:`PathOutsideProjectError` for absolute paths outside the root,
    ``..`` traversal, or symlinks that point outside the root.
    """
    root_resolved = root.resolve()
    candidate = (root_resolved / user_path).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise PathOutsideProjectError(
            f"Path {user_path!r} resolves to {candidate}, outside project root {root_resolved}"
        )
    return candidate
