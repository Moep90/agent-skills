"""Unit tests for the plugin-manifest generator (scripts/sync_plugins.py).

These lock the invariants that matter for distribution (docs/specs/marketplace.md): every
marketplace lists every plugin, the server git URL lives only in the generated .mcp.json and
is pinned to the plugin's release tag, versions are SemVer with a changelog section, the
committed tree matches the generator, and changed plugins carry a version bump.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import sync_plugins


def _rendered_manifests() -> dict[str, str]:
    return {
        str(path): sync_plugins._render(content)
        for path, content in sync_plugins._manifests().items()
    }


def test_core_plugin_references_the_shared_mcp_file() -> None:
    manifest = sync_plugins._cursor_plugin("kapitan-core", sync_plugins.PLUGINS["kapitan-core"])

    assert manifest["mcpServers"] == "./.mcp.json"


def test_generators_plugin_ships_no_mcp_server() -> None:
    manifest = sync_plugins._cursor_plugin(
        "kapitan-generators", sync_plugins.PLUGINS["kapitan-generators"]
    )

    assert "mcpServers" not in manifest


def test_codex_capabilities_track_mcp_presence() -> None:
    core = sync_plugins._codex_plugin("kapitan-core", sync_plugins.PLUGINS["kapitan-core"])
    gens = sync_plugins._codex_plugin(
        "kapitan-generators", sync_plugins.PLUGINS["kapitan-generators"]
    )

    assert core["interface"]["capabilities"] == ["Read", "Write"]
    assert gens["interface"]["capabilities"] == ["Read"]


def test_no_plugin_manifest_embeds_the_server_git_url() -> None:
    # The git+ URL lives only in the generated .mcp.json, never in a manifest.
    for path, rendered in _rendered_manifests().items():
        assert "git+" not in rendered, path


def test_mcp_server_is_pinned_to_the_plugin_release_tag() -> None:
    p = sync_plugins.PLUGINS["kapitan-core"]
    config = sync_plugins._mcp_config("kapitan-core", p)
    args = config["mcpServers"]["kapitan"]["args"]
    source = args[args.index("--from") + 1]

    assert source == (
        "git+https://github.com/Moep90/agent-skills.git"
        f"@kapitan-core--v{p['version']}#subdirectory=tools/kapitan-mcp"
    )


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
    subprocess.run(  # noqa: S603 - fixed git argv in a temp repo
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],  # noqa: S607
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
    server = tmp_path / "tools" / "kapitan-mcp"
    (server / "src").mkdir(parents=True)
    (server / "src" / "server.py").write_text("v1\n")
    (server / "tests").mkdir()
    (server / "tests" / "test_x.py").write_text("v1\n")
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


def test_bump_check_counts_server_files_for_kapitan_core(repo: Path) -> None:
    (repo / "tools" / "kapitan-mcp" / "src" / "server.py").write_text("v2\n")
    _commit(repo)

    assert sync_plugins.check_bump("main", root=repo) == 1


def test_bump_check_ignores_test_only_changes(repo: Path) -> None:
    (repo / "tools" / "kapitan-mcp" / "tests" / "test_x.py").write_text("v2\n")
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
