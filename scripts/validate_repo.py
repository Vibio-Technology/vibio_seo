#!/usr/bin/env python3
"""Validate the Vibio SEO skill pack without executing any skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REFERENCE_RE = re.compile(r"(?<![\w./-])(references/[A-Za-z0-9_./<>-]+)")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
CAPABILITY_NAME_RE = re.compile(r"^(?:seo|b2b)-[a-z0-9-]+$")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: Path
    message: str

    def render(self, root: Path) -> str:
        try:
            display_path = self.path.relative_to(root)
        except ValueError:
            display_path = self.path
        return f"{self.severity.upper():7} {self.code:24} {display_path}: {self.message}"


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_skill(path: Path) -> tuple[dict[str, Any] | None, str, list[Finding]]:
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        findings.append(Finding("error", "frontmatter.missing", path, "Missing or malformed YAML frontmatter."))
        return None, text, findings

    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        findings.append(Finding("error", "frontmatter.yaml", path, str(exc)))
        return None, text[match.end() :], findings

    if not isinstance(frontmatter, dict):
        findings.append(Finding("error", "frontmatter.type", path, "Frontmatter must be a mapping."))
        return None, text[match.end() :], findings
    return frontmatter, text[match.end() :], findings


def normalize_reference(raw: str) -> str:
    return raw.rstrip("`'\".,:;)]}")


def referenced_paths(skill_md: Path, body: str) -> Iterable[tuple[str, Path]]:
    seen: set[str] = set()
    for raw in REFERENCE_RE.findall(body):
        value = normalize_reference(raw)
        if value in seen or "<" in value or ">" in value or "/xxx." in value:
            continue
        seen.add(value)
        yield value, skill_md.parent / value

    for raw in MARKDOWN_LINK_RE.findall(body):
        value = raw.strip().split("#", 1)[0]
        if not value or value.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if value in seen:
            continue
        seen.add(value)
        yield value, skill_md.parent / value


def validate_skill(
    root: Path,
    entry: dict[str, Any],
    eval_schema: dict[str, Any],
    strict: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    skill_dir = root / str(entry["path"])
    skill_md = skill_dir / "SKILL.md"
    expected_name = str(entry["name"])

    if not skill_md.is_file():
        return [Finding("error", "skill.missing", skill_md, "SKILL.md does not exist.")]

    frontmatter, body, parse_findings = parse_skill(skill_md)
    findings.extend(parse_findings)
    if frontmatter is None:
        return findings

    allowed = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
    unexpected = sorted(set(frontmatter) - allowed)
    if unexpected:
        findings.append(
            Finding("error", "frontmatter.keys", skill_md, f"Unexpected keys: {', '.join(unexpected)}")
        )

    name = frontmatter.get("name")
    if name != expected_name:
        findings.append(
            Finding("error", "skill.name", skill_md, f"Expected name '{expected_name}', found '{name}'.")
        )
    if not isinstance(name, str) or not KEBAB_RE.fullmatch(name):
        findings.append(Finding("error", "skill.name-format", skill_md, "Name must be kebab-case."))
    elif len(name) > 64:
        findings.append(Finding("error", "skill.name-length", skill_md, "Name exceeds 64 characters."))

    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        findings.append(Finding("error", "skill.description", skill_md, "Description must be non-empty text."))
    elif len(description.strip()) > 1024:
        findings.append(
            Finding(
                "error",
                "skill.description-length",
                skill_md,
                f"Description is {len(description.strip())} characters; maximum is 1024.",
            )
        )

    compatibility = frontmatter.get("compatibility")
    if compatibility is not None and (not isinstance(compatibility, str) or len(compatibility) > 500):
        findings.append(
            Finding("error", "skill.compatibility", skill_md, "Compatibility must be text <= 500 characters.")
        )

    body_lines = len(body.splitlines())
    if body_lines > 500:
        findings.append(
            Finding("error" if strict else "warning", "skill.body-length", skill_md, f"Body has {body_lines} lines; target is <= 500.")
        )

    for raw, target in referenced_paths(skill_md, body):
        if not target.exists():
            findings.append(Finding("error", "reference.missing", skill_md, f"'{raw}' resolves to missing path '{target}'."))

    eval_path = skill_dir / "evals" / "evals.json"
    if not eval_path.is_file():
        findings.append(Finding("error", "eval.missing", eval_path, "Every shipped skill needs at least three evals."))
        return findings

    try:
        eval_data = load_json(eval_path)
    except (json.JSONDecodeError, OSError) as exc:
        findings.append(Finding("error", "eval.json", eval_path, str(exc)))
        return findings

    validator = Draft202012Validator(eval_schema)
    for error in sorted(validator.iter_errors(eval_data), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "root"
        severity = "error" if strict else "warning"
        findings.append(Finding(severity, "eval.schema", eval_path, f"{location}: {error.message}"))

    if isinstance(eval_data, dict):
        if eval_data.get("skill_name") != expected_name:
            findings.append(
                Finding(
                    "error",
                    "eval.skill-name",
                    eval_path,
                    f"Expected skill_name '{expected_name}', found '{eval_data.get('skill_name')}'.",
                )
            )
        evals = eval_data.get("evals")
        if isinstance(evals, list):
            ids = [case.get("id") for case in evals if isinstance(case, dict)]
            if len(ids) != len(set(ids)):
                findings.append(Finding("error", "eval.duplicate-id", eval_path, "Eval IDs must be unique."))
            for case in evals:
                if not isinstance(case, dict):
                    continue
                for raw_file in case.get("files", []):
                    file_path = (skill_dir / raw_file).resolve()
                    try:
                        file_path.relative_to(skill_dir.resolve())
                    except ValueError:
                        findings.append(
                            Finding("error", "eval.file-boundary", eval_path, f"Fixture escapes skill directory: {raw_file}")
                        )
                        continue
                    if not file_path.exists():
                        findings.append(Finding("error", "eval.file-missing", eval_path, f"Fixture does not exist: {raw_file}"))
    return findings


def validate_dependencies(root: Path, manifest: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    declared = {
        str(item["name"])
        for item in manifest.get("external_capabilities", [])
        if isinstance(item, dict) and "name" in item
    }
    for item in manifest.get("external_capabilities", []):
        if not isinstance(item, dict):
            continue
        if item.get("optional") and not str(item.get("fallback", "")).strip():
            findings.append(
                Finding("error", "dependency.fallback", root / "vibio.manifest.yaml", f"Optional capability {item.get('name')} has no fallback.")
            )

    markdown_files = [path for path in root.rglob("*.md") if ".git" not in path.parts]
    used: set[str] = set()
    for path in markdown_files:
        for token in INLINE_CODE_RE.findall(path.read_text(encoding="utf-8")):
            token = token.strip()
            if CAPABILITY_NAME_RE.fullmatch(token):
                used.add(token)
    for name in sorted(used - declared):
        findings.append(
            Finding("error", "dependency.undeclared", root / "vibio.manifest.yaml", f"Capability '{name}' is referenced but not declared.")
        )
    return findings


def validate_forbidden_paths(root: Path, manifest: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    forbidden = manifest.get("reference_policy", {}).get("forbidden_paths", [])
    if not isinstance(forbidden, list):
        return [Finding("error", "manifest.forbidden", root / "vibio.manifest.yaml", "forbidden_paths must be a list.")]
    for markdown in root.rglob("*.md"):
        if ".git" in markdown.parts:
            continue
        text = markdown.read_text(encoding="utf-8")
        for token in forbidden:
            if str(token) in text:
                findings.append(Finding("error", "reference.forbidden", markdown, f"Stale reference found: {token}"))
    return findings


def validate_duplicate_references(root: Path, manifest: dict[str, Any], strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    canonical_root = root / str(manifest.get("reference_policy", {}).get("canonical_root", "references"))
    if not canonical_root.is_dir():
        return [Finding("error", "reference.canonical-root", canonical_root, "Canonical reference root is missing.")]

    for copied in root.glob("vibio-*/references/**/*.md"):
        parts = copied.relative_to(root).parts
        if len(parts) < 3 or parts[1] != "references":
            continue
        rel = Path(*parts[2:])
        canonical = canonical_root / rel
        if canonical.exists() and copied.read_bytes() != canonical.read_bytes():
            findings.append(
                Finding(
                    "error" if strict else "warning",
                    "reference.drift",
                    copied,
                    f"Copy differs from canonical reference '{canonical.relative_to(root)}'.",
                )
            )
    return findings


def validate_repository(root: Path = ROOT, strict: bool = False) -> list[Finding]:
    manifest_path = root / "vibio.manifest.yaml"
    schema_path = root / "evals" / "schema" / "evals.schema.json"
    findings: list[Finding] = []

    try:
        manifest = load_yaml(manifest_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [Finding("error", "manifest.invalid", manifest_path, str(exc))]
    try:
        eval_schema = load_json(schema_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [Finding("error", "eval-schema.invalid", schema_path, str(exc))]

    skills = manifest.get("skills")
    if not isinstance(skills, list) or not skills:
        return [Finding("error", "manifest.skills", manifest_path, "Manifest must declare at least one skill.")]

    seen_paths: set[str] = set()
    seen_names: set[str] = set()
    for entry in skills:
        if not isinstance(entry, dict) or not {"path", "name"}.issubset(entry):
            findings.append(Finding("error", "manifest.skill-entry", manifest_path, f"Invalid skill entry: {entry!r}"))
            continue
        path_value = str(entry["path"])
        name_value = str(entry["name"])
        if path_value in seen_paths or name_value in seen_names:
            findings.append(Finding("error", "manifest.skill-duplicate", manifest_path, f"Duplicate skill path or name: {entry!r}"))
        seen_paths.add(path_value)
        seen_names.add(name_value)
        findings.extend(validate_skill(root, entry, eval_schema, strict))

    findings.extend(validate_dependencies(root, manifest))
    findings.extend(validate_forbidden_paths(root, manifest))
    findings.extend(validate_duplicate_references(root, manifest, strict))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--strict", action="store_true", help="Treat migration warnings as errors.")
    args = parser.parse_args()

    findings = validate_repository(args.root.resolve(), strict=args.strict)
    for finding in findings:
        print(finding.render(args.root.resolve()))

    errors = sum(finding.severity == "error" for finding in findings)
    warnings = sum(finding.severity == "warning" for finding in findings)
    print(f"\nValidation summary: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
