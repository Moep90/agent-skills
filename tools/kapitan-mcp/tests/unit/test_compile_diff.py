"""Unit tests for the pure diff logic behind compile_diff (no kapitan needed)."""

from __future__ import annotations

from pathlib import Path

from kapitan_mcp.models import ChangedFile
from kapitan_mcp.tools.compile import _cap_diffs, _diff_trees


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_diff_trees__identical__no_changes(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    _write(a, "dev/x.yml", "same\n")
    _write(b, "dev/x.yml", "same\n")

    changed, unchanged = _diff_trees(a, b)

    assert changed == []
    assert unchanged == 1


def test_diff_trees__modified_file__reports_unified_diff(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    _write(a, "dev/x.yml", "old\n")
    _write(b, "dev/x.yml", "new\n")

    changed, _unchanged = _diff_trees(a, b)

    assert len(changed) == 1
    assert changed[0].path == "dev/x.yml"
    assert "-old" in changed[0].diff
    assert "+new" in changed[0].diff


def test_diff_trees__added_and_removed_files(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    _write(a, "only_old.yml", "x\n")
    _write(b, "only_new.yml", "y\n")

    changed, _unchanged = _diff_trees(a, b)

    paths = {c.path for c in changed}
    assert paths == {"only_old.yml", "only_new.yml"}


def test_cap_diffs__over_budget__truncates(tmp_path: Path) -> None:
    big = [ChangedFile(path=f"f{i}.yml", diff="x" * 100) for i in range(5)]

    kept, truncated = _cap_diffs(big, max_bytes=250)

    assert truncated is True
    assert len(kept) < 5


def test_cap_diffs__under_budget__keeps_all(tmp_path: Path) -> None:
    small = [ChangedFile(path="f.yml", diff="x" * 10)]

    kept, truncated = _cap_diffs(small, max_bytes=1000)

    assert truncated is False
    assert kept == small
