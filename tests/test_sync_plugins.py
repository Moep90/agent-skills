"""Unit tests for the plugin-manifest generator (scripts/sync_plugins.py).

These lock the invariants that matter for distribution (docs/specs/marketplace.md): every
marketplace lists every plugin, versions are SemVer with a changelog section, the committed
tree matches the generator, and changed plugins carry a version bump.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import sync_plugins


def test_every_marketplace_lists_all_plugins() -> None:
    markets = {
        path: content
        for path, content in sync_plugins._manifests().items()
        if path.name == "marketplace.json"
    }

    assert len(markets) == 3
    for content in markets.values():
        names = {plugin["name"] for plugin in content["plugins"]}
        assert names == set(sync_plugins.PLUGINS)


def test_every_plugin_manifest_carries_the_registry_version() -> None:
    for path, content in sync_plugins._manifests().items():
        if path.name == "plugin.json":
            name = path.parent.parent.name
            assert content["version"] == sync_plugins.PLUGINS[name]["version"], path


def test_render_is_deterministic_and_newline_terminated() -> None:
    first = sync_plugins._render(sync_plugins._cursor_marketplace())
    second = sync_plugins._render(sync_plugins._cursor_marketplace())

    assert first == second
    assert first.endswith("\n")


def test_check_mode_passes_on_the_committed_tree() -> None:
    # Guards that the committed manifests match the generator (CI's gate).
    assert sync_plugins.sync(check=True) == 0


def _plugin_tree(root: Path, name: str, version: str, changelog: str | None) -> None:
    skill = root / "plugins" / name / "skills" / "demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\n---\n")
    if changelog is not None:
        (root / "plugins" / name / "CHANGELOG.md").write_text(changelog)


@pytest.fixture
def one_plugin(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    plugin = dict(sync_plugins.PLUGINS["kapitan-generators"])
    monkeypatch.setattr(sync_plugins, "PLUGINS", {"demo-plugin": plugin})
    return plugin


def test_check_fails_on_a_non_semver_version(tmp_path: Path, one_plugin: dict[str, object]) -> None:
    one_plugin["version"] = "1.0"
    _plugin_tree(tmp_path, "demo-plugin", "1.0", "## 1.0\n")
    sync_plugins.sync(check=False, root=tmp_path)

    assert sync_plugins.sync(check=True, root=tmp_path) == 1


def test_check_fails_without_changelog_section(
    tmp_path: Path, one_plugin: dict[str, object]
) -> None:
    one_plugin["version"] = "0.2.0"
    _plugin_tree(tmp_path, "demo-plugin", "0.2.0", "## 0.1.0\n")
    sync_plugins.sync(check=False, root=tmp_path)

    assert sync_plugins.sync(check=True, root=tmp_path) == 1


def test_check_fails_on_a_stale_generated_file(
    tmp_path: Path, one_plugin: dict[str, object]
) -> None:
    one_plugin["version"] = "0.1.0"
    _plugin_tree(tmp_path, "demo-plugin", "0.1.0", "## 0.1.0\n")
    sync_plugins.sync(check=False, root=tmp_path)
    assert sync_plugins.sync(check=True, root=tmp_path) == 0

    (tmp_path / ".claude-plugin" / "marketplace.json").write_text("{}\n")
    assert sync_plugins.sync(check=True, root=tmp_path) == 1


# --- version-bump check (spec MKT-5, MKT-5a, AC-2) -------------------------------------


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _write_plugin(root: Path, name: str, version: str, body: str = "v1") -> None:
    base = root / "plugins" / name
    (base / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (base / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": name, "version": version})
    )
    (base / "skills" / "s").mkdir(parents=True, exist_ok=True)
    (base / "skills" / "s" / "SKILL.md").write_text(body)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    _write_plugin(tmp_path, "kapitan-core", "0.1.0")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "switch", "-qc", "feature")
    return tmp_path


def _commit(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "change")


def test_bump_check_fails_on_skill_change_without_bump(repo: Path) -> None:
    _write_plugin(repo, "kapitan-core", "0.1.0", body="v2")
    _commit(repo)

    assert sync_plugins.check_bump("main", root=repo) == 1


def test_bump_check_passes_on_skill_change_with_bump(repo: Path) -> None:
    _write_plugin(repo, "kapitan-core", "0.2.0", body="v2")
    _commit(repo)

    assert sync_plugins.check_bump("main", root=repo) == 0


def test_bump_check_ignores_test_only_changes(repo: Path) -> None:
    (repo / "plugins" / "kapitan-core" / "tests").mkdir()
    (repo / "plugins" / "kapitan-core" / "tests" / "t.sh").write_text("v2\n")
    _commit(repo)

    assert sync_plugins.check_bump("main", root=repo) == 0


def test_bump_check_accepts_a_new_plugin(repo: Path) -> None:
    _write_plugin(repo, "brand-new", "0.1.0")
    _commit(repo)

    assert sync_plugins.check_bump("main", root=repo) == 0


def test_bump_check_accepts_a_deleted_plugin(repo: Path) -> None:
    _git(repo, "rm", "-rq", "plugins/kapitan-core")
    _commit(repo)

    assert sync_plugins.check_bump("main", root=repo) == 0


def test_bump_check_compares_with_the_target_tip(repo: Path) -> None:
    _write_plugin(repo, "kapitan-core", "0.2.0", body="v2")
    _commit(repo)
    _git(repo, "switch", "-q", "main")
    _write_plugin(repo, "kapitan-core", "0.3.0", body="v3")
    _commit(repo)
    _git(repo, "switch", "-q", "feature")

    assert sync_plugins.check_bump("main", root=repo) == 1
