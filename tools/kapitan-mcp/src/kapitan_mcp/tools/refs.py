"""kapitan_refs_list: enumerate secret refs without revealing any values.

Scans the raw inventory for ``?{backend:path}`` ref tokens and reports the backend, the
ref path, and whether a ref file exists under ``refs/``. There is deliberately no tool
that reveals a ref value.
"""

from __future__ import annotations

import re
from pathlib import Path

from kapitan_mcp.models import RefEntry, RefsList

# Matches kapitan ref tokens like ?{gpg:targets/prod/tls_key} or ?{vaultkv:foo/bar}.
# The path may itself contain a ${...} interpolation, whose closing brace must not end
# the token, so those are matched as a unit before falling back to any non-brace char.
_REF_RE = re.compile(r"\?\{([a-z0-9]+):((?:\$\{[^}]*\}|[^}])+)\}")

_INVENTORY = "inventory"
_REFS_DIR = "refs"


def refs_list(root: Path) -> RefsList:
    """List secret refs found in the inventory. Metadata only, never values."""
    root = root.resolve()
    inventory = root / _INVENTORY
    seen: dict[str, RefEntry] = {}

    for path in sorted(inventory.glob("**/*.y*ml")):
        for backend, ref_path in _REF_RE.findall(path.read_text()):
            token = f"?{{{backend}:{ref_path}}}"
            if token in seen:
                continue
            seen[token] = RefEntry(
                token=token,
                backend=backend,
                path=ref_path,
                exists=(root / _REFS_DIR / ref_path).exists(),
            )

    return RefsList(refs=list(seen.values()))
