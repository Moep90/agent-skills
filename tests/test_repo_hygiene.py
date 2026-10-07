"""The home-path pre-commit hook (docs/specs/marketplace.md MKT-9, AC-4).

The regex is read from .pre-commit-config.yaml so the test checks the hook as configured.
Failing inputs are built at test time, so no committed file contains a real home path.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _home_path_regex() -> re.Pattern[str]:
    config = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text())
    for repo in config["repos"]:
        for hook in repo["hooks"]:
            if hook["id"] == "no-home-paths":
                return re.compile(hook["entry"])
    raise AssertionError("no-home-paths hook not configured")


@pytest.mark.parametrize("prefix", ["/home", "/Users"])
def test_hook_rejects_a_real_home_path(prefix: str) -> None:
    sample = "see " + prefix + "/" + "alice" + "/project for details"

    assert _home_path_regex().search(sample)


@pytest.mark.parametrize("text", ["`/home/`", "/home/<user>/x", "/Users/<user>", "~/.agents"])
def test_hook_accepts_bare_prefixes_and_placeholders(text: str) -> None:
    assert not _home_path_regex().search(text)
