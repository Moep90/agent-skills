"""Unit tests for scripts/validate_skills.py: frontmatter category and evals shape."""

from __future__ import annotations

import json
from pathlib import Path

import validate_skills


def _make_skill(
    tmp_path: Path, *, name: str = "demo-skill", category: str = "core", evals: bool = True
) -> Path:
    skill_dir = tmp_path / name
    (skill_dir / "evals").mkdir(parents=True)
    frontmatter = (
        f"---\nname: {name}\ncategory: {category}\ndescription: A demo skill.\n---\nBody.\n"
    )
    (skill_dir / "SKILL.md").write_text(frontmatter)
    if evals:
        (skill_dir / "evals" / "evals.json").write_text(
            json.dumps({"skill": name, "cases": [{"prompt": "p", "expect": ["x"]}]})
        )
    return skill_dir


def test_valid_skill_has_no_problems(tmp_path: Path) -> None:
    assert validate_skills.validate_skill(_make_skill(tmp_path)) == []


def test_missing_category_is_flagged(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path)
    text = (skill_dir / "SKILL.md").read_text().replace("category: core\n", "")
    (skill_dir / "SKILL.md").write_text(text)

    assert any("missing 'category'" in p for p in validate_skills.validate_skill(skill_dir))


def test_unknown_category_is_flagged(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path, category="bogus")

    assert any("not in" in p for p in validate_skills.validate_skill(skill_dir))


def test_missing_evals_file_is_flagged(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path, evals=False)

    assert any("missing evals" in p for p in validate_skills.validate_skill(skill_dir))


def test_evals_skill_name_must_match_directory(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path)
    (skill_dir / "evals" / "evals.json").write_text(
        json.dumps({"skill": "wrong", "cases": [{"prompt": "p", "expect": ["x"]}]})
    )

    assert any(
        "must equal the directory name" in p for p in validate_skills.validate_skill(skill_dir)
    )


def test_empty_expect_list_is_flagged(tmp_path: Path) -> None:
    skill_dir = _make_skill(tmp_path)
    (skill_dir / "evals" / "evals.json").write_text(
        json.dumps({"skill": skill_dir.name, "cases": [{"prompt": "p", "expect": []}]})
    )

    assert any("'expect'" in p for p in validate_skills.validate_skill(skill_dir))


def test_the_committed_skills_all_validate() -> None:
    skills = Path(validate_skills.__file__).resolve().parent.parent / "skills"
    assert validate_skills.main(["validate_skills.py", str(skills)]) == 0
