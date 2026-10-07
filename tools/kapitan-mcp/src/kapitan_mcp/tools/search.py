"""kapitan_search_inventory: locate where a parameter is defined or overridden.

Searches the raw inventory YAML line by line. Use it to answer "where does this value
come from?" across the class hierarchy, then confirm the resolved winner with
kapitan_inventory_target.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from kapitan_mcp.models import SearchMatch, SearchResult

Kind = Literal["key", "value", "regex"]
Scope = Literal["classes", "targets", "all"]

_SCOPE_DIRS = {
    "classes": ("inventory/classes",),
    "targets": ("inventory/targets",),
    "all": ("inventory/classes", "inventory/targets"),
}


def _pattern(query: str, kind: Kind) -> re.Pattern[str]:
    if kind == "regex":
        return re.compile(query)
    if kind == "key":
        # Match "<query>:" as a mapping key, ignoring leading indentation.
        return re.compile(rf"^\s*{re.escape(query)}\s*:")
    return re.compile(re.escape(query))  # value: literal substring


def search_inventory(
    root: Path,
    query: str,
    *,
    kind: Kind = "key",
    scope: Scope = "all",
) -> SearchResult:
    """Find ``query`` across raw inventory YAML.

    ``kind``: ``key`` matches mapping keys, ``value`` matches a literal substring,
    ``regex`` matches a regular expression. ``scope`` limits the search to class files,
    target files, or both.
    """
    root = root.resolve()
    pattern = _pattern(query, kind)
    matches: list[SearchMatch] = []

    for rel_dir in _SCOPE_DIRS[scope]:
        base = root / rel_dir
        if not base.exists():
            continue
        for path in sorted(base.glob("**/*.y*ml")):
            for lineno, line in enumerate(path.read_text().splitlines(), start=1):
                if pattern.search(line):
                    matches.append(
                        SearchMatch(
                            path=path.relative_to(root).as_posix(),
                            line=lineno,
                            snippet=line.strip(),
                        )
                    )
    return SearchResult(matches=matches)
