#!/usr/bin/env python3
"""Validate skill packages: frontmatter, description length, reference links, and evals.

Stdlib only. Exits non-zero on the first batch of problems, printing each. Run from the
repo root or pass a skills directory.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_LINK = re.compile(r"\]\((references/[^)]+)\)")
_MAX_DESCRIPTION = 1024

# Grouping metadata (item 4). Flat directories stay flat; the category is a frontmatter
# field so docs and the installer can group skills without a directory reorg.
_CATEGORIES = frozenset({"core", "generators", "authoring", "scaffolding"})


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    key = None
    for line in match.group(1).splitlines():
        if re.match(r"^\w[\w-]*:", line):
            key, _, value = line.partition(":")
            key = key.strip()
            fields[key] = value.strip()
        elif key and line.strip():
            fields[key] += " " + line.strip()
    return fields


def validate_skill(skill_dir: Path) -> list[str]:
    problems: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"{skill_dir.name}: missing SKILL.md"]

    text = skill_md.read_text()
    fields = _parse_frontmatter(text)

    if not fields.get("name"):
        problems.append(f"{skill_dir.name}: frontmatter missing 'name'")
    elif fields["name"] != skill_dir.name:
        problems.append(f"{skill_dir.name}: name '{fields['name']}' does not match directory")

    description = fields.get("description", "").strip("> ").strip()
    if not description:
        problems.append(f"{skill_dir.name}: frontmatter missing 'description'")
    elif len(description) > _MAX_DESCRIPTION:
        problems.append(
            f"{skill_dir.name}: description {len(description)} > {_MAX_DESCRIPTION} chars"
        )

    category = fields.get("category", "").strip()
    if not category:
        problems.append(f"{skill_dir.name}: frontmatter missing 'category'")
    elif category not in _CATEGORIES:
        allowed = ", ".join(sorted(_CATEGORIES))
        problems.append(f"{skill_dir.name}: category '{category}' not in {{{allowed}}}")

    for rel in _LINK.findall(text):
        if not (skill_dir / rel).exists():
            problems.append(f"{skill_dir.name}: broken reference link {rel}")

    problems.extend(validate_evals(skill_dir))

    return problems


def validate_evals(skill_dir: Path) -> list[str]:
    """Check that the skill ships a well-formed evals/evals.json.

    Structure only, no LLM: the harness that scores trigger rate needs the file to parse
    and to name real cases, so a malformed or empty eval file fails the build early.
    """
    name = skill_dir.name
    evals_file = skill_dir / "evals" / "evals.json"
    if not evals_file.exists():
        return [f"{name}: missing evals/evals.json"]

    try:
        data = json.loads(evals_file.read_text())
    except json.JSONDecodeError as exc:
        return [f"{name}: evals.json is not valid JSON ({exc})"]

    problems: list[str] = []
    if data.get("skill") != name:
        problems.append(f"{name}: evals.json 'skill' must equal the directory name")

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        problems.append(f"{name}: evals.json 'cases' must be a non-empty list")
        return problems

    for i, case in enumerate(cases):
        if not isinstance(case, dict) or not str(case.get("prompt", "")).strip():
            problems.append(f"{name}: evals.json case {i} missing a non-empty 'prompt'")
        expect = case.get("expect") if isinstance(case, dict) else None
        if not isinstance(expect, list) or not expect:
            problems.append(f"{name}: evals.json case {i} missing a non-empty 'expect' list")

    return problems


def main(argv: list[str]) -> int:
    skills_root = Path(argv[1]) if len(argv) > 1 else Path("skills")
    if not skills_root.is_dir():
        print(f"no skills directory at {skills_root}", file=sys.stderr)
        return 1

    all_problems: list[str] = []
    skills = sorted(d for d in skills_root.iterdir() if (d / "SKILL.md").exists())
    for skill_dir in skills:
        all_problems.extend(validate_skill(skill_dir))

    if all_problems:
        for p in all_problems:
            print(f"FAIL {p}")
        return 1

    print(f"ok: {len(skills)} skills valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
