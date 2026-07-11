from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.validate_repo import validate_repository
from scripts.build_skills import build_bundle, build_schemas, build_tools


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


def add_tool_bundle(root: Path) -> None:
    manifest_path = root / "vibio.manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["tool_policy"] = {
        "canonical_root": "runtime",
        "generated_directory": "scripts",
        "generated_marker": ".vibio-tools.json",
        "bundles": {"sample-skill": ["sample.py"]},
    }
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    write(root / "runtime/sample.py", "print('ok')\n")
    build_tools(root, manifest["skills"][0], clean=True)


def add_schema_bundle(root: Path) -> None:
    manifest_path = root / "vibio.manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_policy"] = {
        "canonical_root": "schemas",
        "generated_directory": "schemas",
        "generated_marker": ".vibio-schemas.json",
        "bundles": {"sample-skill": ["sample.report.schema.json"]},
    }
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    write(
        root / "schemas/sample.report.schema.json",
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": ["schema_version"],
                "properties": {"schema_version": {"const": "1.0"}},
            }
        ),
    )
    build_schemas(root, manifest["skills"][0], clean=True)


def add_reference_bundle(root: Path, mode: str = "closure") -> None:
    manifest = load_manifest(root)
    manifest["reference_policy"].update(
        {
            "generated_copies": True,
            "generated_marker": ".vibio-generated.json",
            "bundles": {"sample-skill": mode},
        }
    )
    save_manifest(root, manifest)
    build_bundle(root, manifest["skills"][0], clean=True)


def codes(findings):
    return {finding.code for finding in findings}


def load_manifest(root: Path) -> dict:
    return yaml.safe_load((root / "vibio.manifest.yaml").read_text(encoding="utf-8"))


def save_manifest(root: Path, manifest: dict) -> None:
    (root / "vibio.manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )


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


def test_reference_bundle_detects_missing_nested_generated_copy(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    example = "# Example\n\nRead `references/nested.md`.\n"
    write(root / "references/example.md", example)
    write(root / "sample-skill/references/example.md", example)
    write(root / "references/nested.md", "# Nested\n")
    add_reference_bundle(root)
    (root / "sample-skill/references/nested.md").unlink()

    assert "references.copy-missing" in codes(validate_repository(root, strict=True))


def test_reference_bundle_marker_must_match_recomputed_closure(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_reference_bundle(root)
    marker = root / "sample-skill/references/.vibio-generated.json"
    marker_data = json.loads(marker.read_text(encoding="utf-8"))
    marker_data["files"] = {}
    write(marker, json.dumps(marker_data))

    assert "references.marker-drift" in codes(validate_repository(root, strict=True))


def test_reference_bundle_rejects_stale_canonical_copy_outside_closure(
    tmp_path: Path,
) -> None:
    root = make_repo(tmp_path)
    add_reference_bundle(root)
    write(root / "references/stale.md", "# Stale canonical\n")
    write(root / "sample-skill/references/stale.md", "# Stale canonical\n")

    assert "references.unexpected-copy" in codes(
        validate_repository(root, strict=True)
    )


def test_reference_bundle_rejects_invalid_mode(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    manifest = load_manifest(root)
    manifest["reference_policy"]["bundles"] = {"sample-skill": "partial"}
    save_manifest(root, manifest)

    assert "references.bundle-mode" in codes(validate_repository(root, strict=True))


def test_ci_rejects_untracked_generated_bundle_files() -> None:
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/validate.yml").read_text(
        encoding="utf-8"
    )

    assert "git status --porcelain --untracked-files=all" in workflow
    assert ":(glob)vibio*/references/**" in workflow


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


def test_generated_tool_bundle_passes_and_drift_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)

    assert validate_repository(root, strict=True) == []
    write(root / "sample-skill/scripts/sample.py", "print('changed')\n")
    assert "tools.drift" in codes(validate_repository(root, strict=True))


def test_missing_tool_marker_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    (root / "sample-skill/scripts/.vibio-tools.json").unlink()

    assert "tools.marker-missing" in codes(validate_repository(root, strict=True))


def test_tool_bundle_rejects_unowned_canonical_copy_outside_manifest(
    tmp_path: Path,
) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    write(root / "runtime/stale.py", "print('stale')\n")
    write(root / "sample-skill/scripts/stale.py", "print('stale')\n")

    assert "tools.unexpected-copy" in codes(validate_repository(root, strict=True))


def test_empty_tool_bundle_rejects_leftover_marker(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    manifest = load_manifest(root)
    manifest["tool_policy"]["bundles"]["sample-skill"] = []
    save_manifest(root, manifest)
    (root / "sample-skill/scripts/sample.py").unlink()
    marker = root / "sample-skill/scripts/.vibio-tools.json"
    marker_data = json.loads(marker.read_text(encoding="utf-8"))
    marker_data["files"] = {}
    write(marker, json.dumps(marker_data))

    assert "tools.marker-unexpected" in codes(validate_repository(root, strict=True))


def test_generated_schema_bundle_passes_and_drift_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_schema_bundle(root)

    assert validate_repository(root, strict=True) == []
    write(root / "sample-skill/schemas/sample.report.schema.json", "{}\n")
    assert "schemas.drift" in codes(validate_repository(root, strict=True))


def test_missing_schema_marker_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_schema_bundle(root)
    (root / "sample-skill/schemas/.vibio-schemas.json").unlink()

    assert "schemas.marker-missing" in codes(validate_repository(root, strict=True))


def test_invalid_canonical_schema_is_reported(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_schema_bundle(root)
    write(
        root / "schemas/sample.report.schema.json",
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema", "type": 7}),
    )

    assert "schemas.canonical-invalid" in codes(validate_repository(root, strict=True))


def test_strict_validation_rejects_unconsumed_canonical_tool(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    write(root / "runtime/orphan.py", "print('not distributed')\n")

    strict_findings = validate_repository(root, strict=True)
    relaxed_findings = validate_repository(root, strict=False)

    assert any(
        finding.code == "tools.orphan" and finding.severity == "error"
        for finding in strict_findings
    )
    assert any(
        finding.code == "tools.orphan" and finding.severity == "warning"
        for finding in relaxed_findings
    )


def test_strict_validation_rejects_unconsumed_canonical_schema(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_schema_bundle(root)
    write(
        root / "schemas/orphan.schema.json",
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema"}),
    )

    assert "schemas.orphan" in codes(validate_repository(root, strict=True))


def test_clean_removes_only_marker_owned_tool_files(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    user_file = root / "sample-skill/scripts/user-helper.py"
    write(user_file, "print('user owned')\n")
    manifest = load_manifest(root)
    manifest["tool_policy"]["bundles"]["sample-skill"] = []
    save_manifest(root, manifest)

    build_tools(root, manifest["skills"][0], clean=True)

    assert not (root / "sample-skill/scripts/sample.py").exists()
    assert user_file.read_text(encoding="utf-8") == "print('user owned')\n"
    assert not (root / "sample-skill/scripts/.vibio-tools.json").exists()


def test_reference_clean_preserves_unowned_user_files(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    skill = load_manifest(root)["skills"][0]
    build_bundle(root, skill, clean=True)
    user_file = root / "sample-skill/references/editorial-notes.md"
    write(user_file, "# User notes\n")
    write(
        root / "sample-skill/SKILL.md",
        "---\nname: sample-skill\ndescription: Use for a realistic sample task.\n---\n\n"
        "# Sample\n\nRoute optional data work to `seo-google`.\n",
    )

    build_bundle(root, skill, clean=True)

    assert not (root / "sample-skill/references/example.md").exists()
    assert user_file.read_text(encoding="utf-8") == "# User notes\n"


def test_clean_refuses_to_delete_modified_marker_owned_file(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    manifest = load_manifest(root)
    manifest["tool_policy"]["bundles"]["sample-skill"] = []
    save_manifest(root, manifest)
    generated = root / "sample-skill/scripts/sample.py"
    write(generated, "print('manually changed')\n")

    with pytest.raises(ValueError, match="Refusing to delete modified generated file"):
        build_tools(root, manifest["skills"][0], clean=True)

    assert generated.read_text(encoding="utf-8") == "print('manually changed')\n"


def test_build_refuses_to_overwrite_modified_marker_owned_tool(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    generated = root / "sample-skill/scripts/sample.py"
    write(generated, "print('manually changed')\n")
    write(root / "runtime/sample.py", "print('new canonical')\n")
    manifest = load_manifest(root)

    with pytest.raises(ValueError, match="Refusing to overwrite modified generated file"):
        build_tools(root, manifest["skills"][0], clean=True)

    assert generated.read_text(encoding="utf-8") == "print('manually changed')\n"


def test_build_refuses_to_overwrite_modified_marker_owned_reference(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    skill = load_manifest(root)["skills"][0]
    build_bundle(root, skill, clean=True)
    generated = root / "sample-skill/references/example.md"
    write(generated, "# Manual notes\n")
    write(root / "references/example.md", "# New canonical\n")

    with pytest.raises(ValueError, match="Refusing to overwrite modified generated file"):
        build_bundle(root, skill, clean=True)

    assert generated.read_text(encoding="utf-8") == "# Manual notes\n"


@pytest.mark.parametrize("bundle_path", ["../outside.py", "C:/outside.py", "nested\\outside.py"])
def test_bundle_path_traversal_is_rejected(tmp_path: Path, bundle_path: str) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    manifest = load_manifest(root)
    manifest["tool_policy"]["bundles"]["sample-skill"] = [bundle_path]
    save_manifest(root, manifest)

    assert "tools.path-boundary" in codes(validate_repository(root, strict=True))
    with pytest.raises(ValueError, match="Invalid tool bundle path"):
        build_tools(root, manifest["skills"][0], clean=True)


def test_marker_policy_path_traversal_is_rejected(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    manifest = load_manifest(root)
    manifest["tool_policy"]["generated_marker"] = "../../outside.json"
    save_manifest(root, manifest)

    assert "tools.policy-path" in codes(validate_repository(root, strict=True))
    with pytest.raises(ValueError, match="Invalid tool marker path"):
        build_tools(root, manifest["skills"][0], clean=True)


def test_marker_owned_path_traversal_is_rejected_before_clean(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    marker = root / "sample-skill/scripts/.vibio-tools.json"
    marker_data = json.loads(marker.read_text(encoding="utf-8"))
    marker_data["files"] = {"../outside.py": "0" * 64}
    write(marker, json.dumps(marker_data))
    outside = root / "sample-skill/outside.py"
    write(outside, "print('keep')\n")
    manifest = load_manifest(root)

    assert "tools.marker-path" in codes(validate_repository(root, strict=True))
    with pytest.raises(ValueError, match="Invalid marker-owned file path"):
        build_tools(root, manifest["skills"][0], clean=True)
    assert outside.read_text(encoding="utf-8") == "print('keep')\n"


def test_forged_marker_identity_cannot_claim_files_for_clean(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    marker = root / "sample-skill/scripts/.vibio-tools.json"
    marker_data = json.loads(marker.read_text(encoding="utf-8"))
    marker_data["generated_by"] = "untrusted-script.py"
    write(marker, json.dumps(marker_data))
    manifest = load_manifest(root)
    manifest["tool_policy"]["bundles"]["sample-skill"] = []
    save_manifest(root, manifest)
    generated = root / "sample-skill/scripts/sample.py"

    assert "tools.marker-identity" in codes(validate_repository(root, strict=True))
    with pytest.raises(ValueError, match="marker identity"):
        build_tools(root, manifest["skills"][0], clean=True)
    assert generated.is_file()


def test_symbolic_link_in_canonical_bundle_is_rejected(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    add_tool_bundle(root)
    canonical = root / "runtime/sample.py"
    target = root / "outside.py"
    write(target, "print('outside')\n")
    canonical.unlink()
    try:
        canonical.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"Symbolic links are unavailable: {exc}")
    manifest = load_manifest(root)

    assert "tools.symlink" in codes(validate_repository(root, strict=True))
    with pytest.raises(ValueError, match="symbolic link"):
        build_tools(root, manifest["skills"][0], clean=True)


def test_unowned_destination_collision_is_not_overwritten(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    manifest = load_manifest(root)
    manifest["tool_policy"] = {
        "canonical_root": "runtime",
        "generated_directory": "scripts",
        "generated_marker": ".vibio-tools.json",
        "bundles": {"sample-skill": ["sample.py"]},
    }
    save_manifest(root, manifest)
    write(root / "runtime/sample.py", "print('canonical')\n")
    destination = root / "sample-skill/scripts/sample.py"
    write(destination, "print('user file')\n")

    with pytest.raises(ValueError, match="Refusing to overwrite unowned file"):
        build_tools(root, manifest["skills"][0], clean=True)

    assert destination.read_text(encoding="utf-8") == "print('user file')\n"
