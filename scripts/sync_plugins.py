#!/usr/bin/env python3
"""Generate the plugin manifests and skill bundles from one registry.

Every plugin is described once in ``PLUGINS`` below. From that we generate:

- the three root marketplace manifests, one per client that discovers plugins from a git
  repo: ``.claude-plugin/``, ``.cursor-plugin/``, and ``.agents/plugins/`` (Codex);
- the per-plugin manifests each client reads: ``.claude-plugin/plugin.json``,
  ``.cursor-plugin/plugin.json``, ``.codex-plugin/plugin.json``;
- the skill bundles: skills live once under ``skills/`` and are copied into each plugin
  (copied, not symlinked, so bundles work on Windows).

The MCP server command (and its git URL) lives in exactly one hand-written file per plugin,
``plugins/<name>/.mcp.json``; the manifests only reference it with ``mcpServers``. So the
git URL is never duplicated.

Run without arguments to sync; run with ``--check`` to fail on drift (used in CI). Stdlib
only.
"""

from __future__ import annotations

import filecmp
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
PLUGINS_DIR = ROOT / "plugins"

# No manifest version field: the project ships rolling from main. Clients fall back to the
# git commit SHA for update detection, so every commit counts as a new version.
REPO_URL = "https://github.com/Moep90/agent-toolkit-for-kapitan"
MARKET_NAME = "agent-toolkit-for-kapitan"
MARKET_DESCRIPTION = "Agent plugins that make AI coding agents good at Kapitan projects."
MARKET_DISPLAY = "Agent Toolkit for Kapitan"
OWNER = "Moep90"
AUTHOR = "kapicorp"
LICENSE = "Apache-2.0"
CATEGORY = "devops"  # Claude/Cursor marketplaces
CATEGORY_TITLE = "DevOps"  # Codex/agents marketplace

# The one source of truth for every plugin. Descriptions are echoed into all manifests
# below; edit them here, then run this script.
PLUGINS: dict[str, dict[str, object]] = {
    "kapitan-core": {
        "displayName": "Kapitan Core",
        "description": (
            "Kapitan MCP server plus core skills: the inventory model, secret refs, and "
            "compile debugging."
        ),
        "keywords": [
            "kapitan",
            "inventory",
            "reclass",
            "omegaconf",
            "secrets",
            "refs",
            "compile",
            "kubernetes",
            "config-management",
            "gitops",
        ],
        "has_mcp": True,
        "skills": [
            "kapitan-inventory-model",
            "kapitan-input-types",
            "kapitan-secrets-refs",
            "kapitan-debugging-compile",
        ],
    },
    "kapitan-generators": {
        "displayName": "Kapitan Generators",
        "description": (
            "Skills for the kapicorp Kubernetes and Terraform generators, kadet authoring, "
            "and project scaffolding."
        ),
        "keywords": [
            "kapitan",
            "kadet",
            "generators",
            "kubernetes",
            "terraform",
            "scaffolding",
            "manifests",
            "config-management",
        ],
        "has_mcp": False,
        "skills": [
            "kapitan-kubernetes-generator",
            "kapitan-terraform-generator",
            "kapitan-helm-input",
            "kapitan-omegaconf-resolvers",
            "kapitan-authoring-generator",
            "kapitan-generator-wiring",
            "kapitan-writing-kadet",
            "kapitan-project-scaffolding",
        ],
    },
}


def _claude_marketplace() -> dict[str, object]:
    return {
        "name": MARKET_NAME,
        "owner": {"name": OWNER},
        "metadata": {"description": MARKET_DESCRIPTION},
        "plugins": [
            {
                "name": name,
                "source": f"./plugins/{name}",
                "description": p["description"],
                "category": CATEGORY,
                "keywords": p["keywords"],
            }
            for name, p in PLUGINS.items()
        ],
    }


def _cursor_marketplace() -> dict[str, object]:
    return {
        "name": MARKET_NAME,
        "owner": {"name": OWNER},
        "metadata": {"description": MARKET_DESCRIPTION},
        "plugins": [
            {"name": name, "source": f"./plugins/{name}", "description": p["description"]}
            for name, p in PLUGINS.items()
        ],
    }


def _agents_marketplace() -> dict[str, object]:
    return {
        "name": MARKET_NAME,
        "interface": {"displayName": MARKET_DISPLAY},
        "plugins": [
            {
                "name": name,
                "source": {"source": "local", "path": f"./plugins/{name}"},
                "policy": {"installation": "AVAILABLE"},
                "category": CATEGORY_TITLE,
            }
            for name in PLUGINS
        ],
    }


def _claude_plugin(name: str, p: dict[str, object]) -> dict[str, object]:
    return {
        "name": name,
        "description": p["description"],
        "author": {"name": AUTHOR},
    }


def _cursor_plugin(name: str, p: dict[str, object]) -> dict[str, object]:
    manifest: dict[str, object] = {
        "name": name,
        "displayName": p["displayName"],
        "description": p["description"],
        "author": {"name": AUTHOR},
        "homepage": REPO_URL,
        "repository": REPO_URL,
        "license": LICENSE,
        "category": "developer-tools",
        "keywords": p["keywords"],
        "skills": "./skills/",
    }
    if p["has_mcp"]:
        manifest["mcpServers"] = "./.mcp.json"
    return manifest


def _codex_plugin(name: str, p: dict[str, object]) -> dict[str, object]:
    has_mcp = bool(p["has_mcp"])
    short = "Kapitan agent plugin with skills" + (" and an MCP server" if has_mcp else "")
    manifest: dict[str, object] = {
        "name": name,
        "description": p["description"],
        "author": {"name": AUTHOR, "url": REPO_URL},
        "homepage": REPO_URL,
        "repository": REPO_URL,
        "license": LICENSE,
        "keywords": p["keywords"],
        "skills": "./skills/",
    }
    if has_mcp:
        manifest["mcpServers"] = "./.mcp.json"
    manifest["interface"] = {
        "displayName": p["displayName"],
        "shortDescription": short,
        "longDescription": p["description"],
        "developerName": AUTHOR,
        "category": CATEGORY_TITLE,
        "capabilities": ["Read", "Write"] if has_mcp else ["Read"],
        "websiteURL": REPO_URL,
    }
    return manifest


def _manifests() -> dict[Path, dict[str, object]]:
    """Map every generated manifest path to its content."""
    files: dict[Path, dict[str, object]] = {
        ROOT / ".claude-plugin" / "marketplace.json": _claude_marketplace(),
        ROOT / ".cursor-plugin" / "marketplace.json": _cursor_marketplace(),
        ROOT / ".agents" / "plugins" / "marketplace.json": _agents_marketplace(),
    }
    for name, p in PLUGINS.items():
        base = PLUGINS_DIR / name
        files[base / ".claude-plugin" / "plugin.json"] = _claude_plugin(name, p)
        files[base / ".cursor-plugin" / "plugin.json"] = _cursor_plugin(name, p)
        files[base / ".codex-plugin" / "plugin.json"] = _codex_plugin(name, p)
    return files


def _render(content: dict[str, object]) -> str:
    return json.dumps(content, indent=2) + "\n"


def _trees_differ(a: Path, b: Path) -> bool:
    if not b.exists():
        return True
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return True
    return any(_trees_differ(a / sub, b / sub) for sub in cmp.common_dirs)


def sync(check: bool) -> int:
    problems: list[str] = []

    for path, content in _manifests().items():
        rendered = _render(content)
        rel = path.relative_to(ROOT)
        if check:
            if not path.exists() or path.read_text() != rendered:
                problems.append(f"drift: {rel} is stale (run make sync-plugins)")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered)

    for name, p in PLUGINS.items():
        for skill in p["skills"]:
            src = SKILLS / skill
            dst = PLUGINS_DIR / name / "skills" / skill
            if not src.is_dir():
                problems.append(f"missing source skill: {skill}")
                continue
            if check:
                if _trees_differ(src, dst):
                    problems.append(f"drift: plugins/{name}/skills/{skill} != skills/{skill}")
            else:
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

    if problems:
        for problem in problems:
            print(f"FAIL {problem}")
        return 1
    print("plugins in sync" if check else "plugins synced")
    return 0


if __name__ == "__main__":
    raise SystemExit(sync(check="--check" in sys.argv))
