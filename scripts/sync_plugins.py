#!/usr/bin/env python3
"""Generate the marketplace and plugin manifests from one registry, and check versions.

Every plugin is described once in ``PLUGINS`` below. From that we generate:

- the three root marketplace manifests, one per client that discovers plugins from a git
  repo: ``.claude-plugin/``, ``.cursor-plugin/``, and ``.agents/plugins/`` (Codex);
- the per-plugin manifests each client reads: ``.claude-plugin/plugin.json``,
  ``.cursor-plugin/plugin.json``, ``.codex-plugin/plugin.json``.

Skills live only in ``plugins/<name>/skills/``; nothing is copied.

Usage (stdlib only):

- no arguments: write all generated files;
- ``--check``: fail on drift, a non-SemVer version, or a version without changelog section;
- ``--check-bump <ref>``: fail when a plugin's files changed since the merge base with
  ``<ref>`` but its version is not higher than the version on ``<ref>``.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR_NAME = "plugins"

REPO_URL = "https://github.com/Moep90/agent-skills"
MARKET_NAME = "moep90-skills"
MARKET_DESCRIPTION = "Agent plugins for Claude Code, Codex CLI, Cursor and OpenCode."
MARKET_DISPLAY = "Moep90 Skills"
OWNER = "Moep90"
LICENSE = "Apache-2.0"

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

# The one source of truth for every plugin. Edit here, then run this script.
PLUGINS: dict[str, dict[str, object]] = {
    "kapitan-core": {
        "version": "0.1.0",
        "displayName": "Kapitan Core",
        "description": (
            "Core Kapitan skills: the inventory model, input types, secret refs, and "
            "compile debugging."
        ),
        "author": "kapicorp",
        "category": "devops",
        "categoryTitle": "DevOps",
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
    },
    "kapitan-generators": {
        "version": "0.1.0",
        "displayName": "Kapitan Generators",
        "description": (
            "Skills for the kapicorp Kubernetes and Terraform generators, kadet authoring, "
            "and project scaffolding."
        ),
        "author": "kapicorp",
        "category": "devops",
        "categoryTitle": "DevOps",
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
                "source": f"./{PLUGINS_DIR_NAME}/{name}",
                "description": p["description"],
                "category": p["category"],
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
            {
                "name": name,
                "source": f"./{PLUGINS_DIR_NAME}/{name}",
                "description": p["description"],
            }
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
                "source": {"source": "local", "path": f"./{PLUGINS_DIR_NAME}/{name}"},
                "policy": {"installation": "AVAILABLE"},
                "category": p["categoryTitle"],
            }
            for name, p in PLUGINS.items()
        ],
    }


def _claude_plugin(name: str, p: dict[str, object]) -> dict[str, object]:
    return {
        "name": name,
        "version": p["version"],
        "description": p["description"],
        "author": {"name": p["author"]},
        "homepage": REPO_URL,
        "repository": REPO_URL,
        "license": LICENSE,
        "keywords": p["keywords"],
    }


def _cursor_plugin(name: str, p: dict[str, object]) -> dict[str, object]:
    return {
        "name": name,
        "version": p["version"],
        "displayName": p["displayName"],
        "description": p["description"],
        "author": {"name": p["author"]},
        "homepage": REPO_URL,
        "repository": REPO_URL,
        "license": LICENSE,
        "category": "developer-tools",
        "keywords": p["keywords"],
        "skills": "./skills/",
    }


def _codex_plugin(name: str, p: dict[str, object]) -> dict[str, object]:
    return {
        "name": name,
        "version": p["version"],
        "description": p["description"],
        "author": {"name": p["author"], "url": REPO_URL},
        "homepage": REPO_URL,
        "repository": REPO_URL,
        "license": LICENSE,
        "keywords": p["keywords"],
        "skills": "./skills/",
        "interface": {
            "displayName": p["displayName"],
            "shortDescription": "Agent plugin with skills",
            "longDescription": p["description"],
            "developerName": p["author"],
            "category": p["categoryTitle"],
            "capabilities": ["Read"],
            "websiteURL": REPO_URL,
        },
    }


def _manifests(root: Path = ROOT) -> dict[Path, dict[str, object]]:
    """Map every generated manifest and marketplace path to its content."""
    files: dict[Path, dict[str, object]] = {
        root / ".claude-plugin" / "marketplace.json": _claude_marketplace(),
        root / ".cursor-plugin" / "marketplace.json": _cursor_marketplace(),
        root / ".agents" / "plugins" / "marketplace.json": _agents_marketplace(),
    }
    for name, p in PLUGINS.items():
        base = root / PLUGINS_DIR_NAME / name
        files[base / ".claude-plugin" / "plugin.json"] = _claude_plugin(name, p)
        files[base / ".cursor-plugin" / "plugin.json"] = _cursor_plugin(name, p)
        files[base / ".codex-plugin" / "plugin.json"] = _codex_plugin(name, p)
    return files


def _render(content: dict[str, object]) -> str:
    return json.dumps(content, indent=2) + "\n"


def _version_problems(root: Path = ROOT) -> list[str]:
    problems: list[str] = []
    for name, p in PLUGINS.items():
        version = str(p["version"])
        if not _SEMVER.match(version):
            problems.append(f"{name}: version '{version}' is not MAJOR.MINOR.PATCH")
        changelog = root / PLUGINS_DIR_NAME / name / "CHANGELOG.md"
        heading = re.compile(rf"^## {re.escape(version)}\s*$", re.MULTILINE)
        if not changelog.exists() or not heading.search(changelog.read_text()):
            problems.append(f"{name}: CHANGELOG.md has no '## {version}' section")
        skills = root / PLUGINS_DIR_NAME / name / "skills"
        if not any(skills.glob("*/SKILL.md")):
            problems.append(f"{name}: no skills under {PLUGINS_DIR_NAME}/{name}/skills/")
    return problems


def sync(check: bool, root: Path = ROOT) -> int:
    problems: list[str] = []
    for path, content in _manifests(root).items():
        rendered = _render(content)
        rel = path.relative_to(root)
        if check:
            if not path.exists() or path.read_text() != rendered:
                problems.append(f"drift: {rel} is stale (run make sync-plugins)")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered)

    problems += _version_problems(root)
    return _report(problems, "plugins in sync" if check else "plugins synced")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed git argv, no shell
        ["git", *args],  # noqa: S607 - git from PATH is intended
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _is_plugin_file(path: str, name: str) -> bool:
    """Whether a change to ``path`` requires a version bump of ``name`` (spec MKT-5a)."""
    prefix = f"{PLUGINS_DIR_NAME}/{name}/"
    return path.startswith(prefix) and not path.startswith(f"{prefix}tests/")


def check_bump(ref: str, root: Path = ROOT) -> int:
    base = _git(root, "merge-base", ref, "HEAD")
    if base.returncode != 0:
        return _report([f"cannot find merge base with {ref}: {base.stderr.strip()}"], "")
    changed = _git(root, "diff", "--name-only", base.stdout.strip(), "HEAD").stdout.split()

    problems: list[str] = []
    plugins_dir = root / PLUGINS_DIR_NAME
    for manifest in sorted(plugins_dir.glob("*/.claude-plugin/plugin.json")):
        name = manifest.parent.parent.name
        if not any(_is_plugin_file(f, name) for f in changed):
            continue
        rel = manifest.relative_to(root).as_posix()
        old = _git(root, "show", f"{ref}:{rel}")
        if old.returncode != 0:
            continue  # new plugin: any SemVer passes (MKT-4 is checked by --check)
        old_version = str(json.loads(old.stdout).get("version", "0.0.0"))
        new_version = str(json.loads(manifest.read_text()).get("version", "0.0.0"))
        if not (_SEMVER.match(old_version) and _SEMVER.match(new_version)):
            problems.append(f"{name}: cannot compare '{old_version}' with '{new_version}'")
        elif _version_tuple(new_version) <= _version_tuple(old_version):
            problems.append(
                f"{name}: files changed but version {new_version} is not higher than "
                f"{old_version} on {ref}"
            )
    return _report(problems, "version bumps ok")


def _report(problems: list[str], ok: str) -> int:
    if problems:
        for problem in problems:
            print(f"FAIL {problem}")
        return 1
    print(ok)
    return 0


def main(argv: list[str]) -> int:
    if "--check-bump" in argv:
        index = argv.index("--check-bump")
        if index + 1 >= len(argv):
            print("usage: sync_plugins.py --check-bump <ref>", file=sys.stderr)
            return 2
        return check_bump(argv[index + 1])
    return sync(check="--check" in argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
