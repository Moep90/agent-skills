"""End-to-end install checks against the real client CLIs.

These drive the actual `claude` and `codex` binaries to prove the generated marketplace and
plugin manifests are ones each client accepts. They are opt-in (marked ``plugin_cli``) and
skip when the CLI is absent, since neither binary is on CI runners. Cursor has no headless
plugin CLI, so it cannot be covered here.

Run locally with: ``make test-plugin-cli``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import sync_plugins

pytestmark = pytest.mark.plugin_cli

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAMES = set(sync_plugins.PLUGINS)


@pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI not installed")
@pytest.mark.parametrize(
    "path",
    [
        REPO_ROOT,  # the marketplace manifest at .claude-plugin/marketplace.json
        REPO_ROOT / "plugins" / "kapitan-core",
        REPO_ROOT / "plugins" / "kapitan-generators",
    ],
)
def test_claude_validates_marketplace_and_plugins(path: Path) -> None:
    result = subprocess.run(
        ["claude", "plugin", "validate", str(path), "--strict"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI not installed")
def test_claude_adds_the_marketplace_and_installs_every_plugin(tmp_path: Path) -> None:
    # validate --strict does not reject a reserved marketplace name; a real add does
    # (spec MKT-3a). An isolated config dir keeps the user's real plugins untouched.
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(tmp_path / "claude")}

    def claude(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["claude", "plugin", *args],
            capture_output=True,
            text=True,
            env=env,
            stdin=subprocess.DEVNULL,
            timeout=120,
        )

    added = claude("marketplace", "add", str(REPO_ROOT))
    assert added.returncode == 0, added.stdout + added.stderr
    for name in sorted(PLUGIN_NAMES):
        installed = claude("install", f"{name}@{sync_plugins.MARKET_NAME}")
        assert installed.returncode == 0, installed.stdout + installed.stderr


@pytest.mark.skipif(shutil.which("codex") is None, reason="codex CLI not installed")
def test_codex_marketplace_lists_our_plugins(tmp_path: Path) -> None:
    # Isolate CODEX_HOME so the real ~/.codex config is never touched. It must already exist.
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    env = {**os.environ, "CODEX_HOME": str(codex_home)}

    added = subprocess.run(
        ["codex", "plugin", "marketplace", "add", str(REPO_ROOT)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert added.returncode == 0, added.stdout + added.stderr

    listed = subprocess.run(
        [
            "codex",
            "plugin",
            "list",
            "--marketplace",
            sync_plugins.MARKET_NAME,
            "--available",
            "--json",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert listed.returncode == 0, listed.stdout + listed.stderr

    data = json.loads(listed.stdout)
    names = {p["name"] for p in data.get("installed", []) + data.get("available", [])}
    assert PLUGIN_NAMES <= names, names
