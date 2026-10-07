"""Unit tests for the plugin-manifest generator (scripts/sync_plugins.py).

These lock the invariants that matter for distribution: the git URL never leaks into a
generated manifest, the MCP reference tracks whether a plugin ships a server, and the
committed tree matches what the generator would produce.
"""

from __future__ import annotations

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


def test_no_generated_manifest_embeds_the_server_git_url() -> None:
    # The git+ URL must live only in the hand-written .mcp.json, never in a generated file.
    for path, rendered in _rendered_manifests().items():
        assert "git+" not in rendered, path


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


def test_render_is_deterministic_and_newline_terminated() -> None:
    first = sync_plugins._render(sync_plugins._cursor_marketplace())
    second = sync_plugins._render(sync_plugins._cursor_marketplace())

    assert first == second
    assert first.endswith("\n")


def test_all_manifest_versions_come_from_the_single_version_constant() -> None:
    # Every version string in the generated manifests must equal sync_plugins.VERSION, so the
    # release workflow only has to rewrite that one constant.
    def _versions(obj: object) -> list[str]:
        if isinstance(obj, dict):
            found = [v for k, v in obj.items() if k == "version" and isinstance(v, str)]
            return found + [v for value in obj.values() for v in _versions(value)]
        if isinstance(obj, list):
            return [v for item in obj for v in _versions(item)]
        return []

    for content in sync_plugins._manifests().values():
        for version in _versions(content):
            assert version == sync_plugins.VERSION


def test_check_mode_passes_on_the_committed_tree() -> None:
    # Guards that the committed manifests and bundles match the generator (CI's gate).
    assert sync_plugins.sync(check=True) == 0
