from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.validate_repo import validate_repository


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_repo(tmp_path: Path) -> Path:
    write(
        tmp_path / "vibio.manifest.yaml",
        yaml.safe_dump(
            {
                "schema_version": 1,
                "skills": [{"path": "sample-skill", "name": "sample-skill", "role": "test"}],
                "reference_policy": {"canonical_root": "references", "forbidden_paths": ["old-playbook.md"]},
                "external_capabilities": [
                    {"name": "seo-google", "optional": True, "fallback": "Use exported data."}
                ],
            },
            sort_keys=False,
        ),
    )
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["skill_name", "evals"],
        "properties": {
            "skill_name": {"type": "string"},
            "evals": {"type": "array", "minItems": 3},
        },
    }
    write(tmp_path / "evals/schema/evals.schema.json", json.dumps(schema))
    write(tmp_path / "references/example.md", "# Example\n")
    write(
        tmp_path / "sample-skill/SKILL.md",
        "---\nname: sample-skill\ndescription: Use for a realistic sample task.\n---\n\n"
        "# Sample\n\nRead `references/example.md`. Route optional data work to `seo-google`.\n",
    )
    write(tmp_path / "sample-skill/references/example.md", "# Example\n")
    evals = {
        "skill_name": "sample-skill",
        "evals": [
            {"id": 1, "name": "one", "prompt": "Run realistic sample one", "expected_output": "A useful result", "files": [], "expectations": ["Produces a result"], "assertions": []},
            {"id": 2, "name": "two", "prompt": "Run realistic sample two", "expected_output": "A useful result", "files": [], "expectations": ["Produces a result"], "assertions": []},
            {"id": 3, "name": "three", "prompt": "Run realistic sample three", "expected_output": "A useful result", "files": [], "expectations": ["Produces a result"], "assertions": []},
        ],
    }
    write(tmp_path / "sample-skill/evals/evals.json", json.dumps(evals))
    return tmp_path


def codes(findings):
    return {finding.code for finding in findings}


def test_valid_repository_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    assert validate_repository(root, strict=True) == []


def test_broken_frontmatter_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    write(root / "sample-skill/SKILL.md", "# No frontmatter\n")
    assert "frontmatter.missing" in codes(validate_repository(root, strict=True))


def test_missing_reference_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    (root / "sample-skill/references/example.md").unlink()
    assert "reference.missing" in codes(validate_repository(root, strict=True))


def test_undeclared_dependency_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    skill = root / "sample-skill/SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nUse `seo-schema`.\n", encoding="utf-8")
    assert "dependency.undeclared" in codes(validate_repository(root, strict=True))


def test_forbidden_reference_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    skill = root / "sample-skill/SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nRead `old-playbook.md`.\n", encoding="utf-8")
    assert "reference.forbidden" in codes(validate_repository(root, strict=True))
