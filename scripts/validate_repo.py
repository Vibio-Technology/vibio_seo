#!/usr/bin/env python3
"""Validate the Vibio SEO skill pack without executing any skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[1]
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REFERENCE_RE = re.compile(r"(?<![\w./-])(references/[A-Za-z0-9_./<>-]+)")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
CAPABILITY_NAME_RE = re.compile(r"^(?:seo|b2b)-[a-z0-9-]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GENERATOR = "scripts/build_skills.py"


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


def safe_relative_path(raw: object, label: str, *, filename_only: bool = False) -> Path:
    value = str(raw)
    if not value or "\x00" in value or "\\" in value or ":" in value:
        raise ValueError(f"Invalid {label}: {raw!r}")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    raw_parts = value.split("/")
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or any(part in {"", ".", ".."} for part in raw_parts)
        or (filename_only and len(raw_parts) != 1)
    ):
        raise ValueError(f"Invalid {label}: {raw!r}")
    return Path(*posix.parts)


def first_symlink(root: Path, target: Path) -> Path | None:
    try:
        relative = target.relative_to(root)
    except ValueError:
        return target
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return current
    return None


def marker_canonical_root(canonical: Path, output_root: Path) -> str:
    return os.path.relpath(canonical, output_root).replace(os.sep, "/")


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
    try:
        skill_relative = safe_relative_path(entry["path"], "skill path")
    except ValueError as exc:
        return [Finding("error", "manifest.skill-path", root / "vibio.manifest.yaml", str(exc))]
    skill_dir = root / skill_relative
    skill_md = skill_dir / "SKILL.md"
    expected_name = str(entry["name"])

    linked = first_symlink(root, skill_md)
    if linked is not None:
        return [
            Finding(
                "error",
                "skill.symlink",
                linked,
                "Skill paths and SKILL.md must not traverse symbolic links.",
            )
        ]

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
        try:
            target.resolve().relative_to(skill_dir.resolve())
        except ValueError:
            findings.append(
                Finding("error", "reference.boundary", skill_md, f"Reference escapes skill directory: {raw}")
            )
            continue
        linked = first_symlink(root, target)
        if linked is not None:
            findings.append(
                Finding("error", "reference.symlink", linked, f"Reference uses a symbolic link: {raw}")
            )
        elif not target.exists():
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


def reference_names_from_text(text: str) -> Iterable[str]:
    seen: set[str] = set()
    for raw in REFERENCE_RE.findall(text):
        value = normalize_reference(raw)
        if value in seen or "<" in value or ">" in value or "/xxx." in value:
            continue
        seen.add(value)
        yield value.removeprefix("references/")


def validate_legacy_duplicate_references(
    root: Path, manifest: dict[str, Any], strict: bool
) -> list[Finding]:
    findings: list[Finding] = []
    canonical_root = root / str(manifest.get("reference_policy", {}).get("canonical_root", "references"))
    if not canonical_root.is_dir():
        return [Finding("error", "reference.canonical-root", canonical_root, "Canonical reference root is missing.")]

    for entry in manifest.get("skills", []):
        if not isinstance(entry, dict) or not entry.get("path"):
            continue
        try:
            skill_relative = safe_relative_path(entry["path"], "skill path")
        except ValueError:
            continue
        output_root = root / skill_relative / "references"
        for copied in output_root.rglob("*.md") if output_root.is_dir() else []:
            rel = copied.relative_to(output_root)
            canonical = canonical_root / rel
            if canonical.exists() and copied.read_bytes() != canonical.read_bytes():
                findings.append(
                    Finding(
                        "error" if strict else "warning",
                        "references.drift",
                        copied,
                        f"Copy differs from canonical reference '{canonical.relative_to(root)}'.",
                    )
                )
    return findings


def expected_reference_files(
    root: Path,
    canonical_root: Path,
    skill_md: Path,
    mode: object,
) -> tuple[dict[str, str], list[Finding]]:
    findings: list[Finding] = []
    sources: set[Path] = set()
    if mode == "all":
        sources = {
            path
            for path in canonical_root.rglob("*.md")
            if path.is_file() and not path.is_symlink()
        }
    elif mode == "closure":
        try:
            queue = list(reference_names_from_text(skill_md.read_text(encoding="utf-8")))
        except OSError as exc:
            return {}, [Finding("error", "references.skill-read", skill_md, str(exc))]
        selected: set[str] = set()
        while queue:
            raw_relative = queue.pop(0).rstrip("/")
            if raw_relative in selected:
                continue
            selected.add(raw_relative)
            try:
                relative = safe_relative_path(raw_relative, "reference bundle path")
            except ValueError as exc:
                findings.append(
                    Finding("error", "references.path-boundary", skill_md, str(exc))
                )
                continue
            target = canonical_root / relative
            linked = first_symlink(root, target)
            if linked is not None:
                findings.append(
                    Finding(
                        "error",
                        "references.symlink",
                        linked,
                        "Canonical reference source must not traverse a symbolic link.",
                    )
                )
                continue
            if target.is_dir():
                expanded = sorted(
                    path for path in target.rglob("*.md") if path.is_file()
                )
            elif target.is_file():
                expanded = [target]
            else:
                findings.append(
                    Finding(
                        "error",
                        "references.canonical-missing",
                        target,
                        "Canonical reference required by the bundle is missing.",
                    )
                )
                continue
            for source in expanded:
                source_link = first_symlink(root, source)
                if source_link is not None:
                    findings.append(
                        Finding(
                            "error",
                            "references.symlink",
                            source_link,
                            "Canonical reference source must not traverse a symbolic link.",
                        )
                    )
                    continue
                sources.add(source)
                if source.suffix == ".md":
                    try:
                        nested = reference_names_from_text(
                            source.read_text(encoding="utf-8")
                        )
                        queue.extend(item for item in nested if item not in selected)
                    except OSError as exc:
                        findings.append(
                            Finding("error", "references.canonical-read", source, str(exc))
                        )
    else:
        findings.append(
            Finding(
                "error",
                "references.bundle-mode",
                skill_md,
                f"Reference bundle mode must be 'all' or 'closure', found {mode!r}.",
            )
        )

    expected = {
        source.relative_to(canonical_root).as_posix(): hash_file(source)
        for source in sorted(sources)
    }
    return expected, findings


def validate_reference_bundles(
    root: Path, manifest: dict[str, Any], strict: bool
) -> list[Finding]:
    findings: list[Finding] = []
    policy = manifest.get("reference_policy", {})
    bundles = policy.get("bundles")
    if bundles is None:
        return validate_legacy_duplicate_references(root, manifest, strict)
    manifest_path = root / "vibio.manifest.yaml"
    if not isinstance(bundles, dict):
        return [
            Finding(
                "error",
                "references.bundles",
                manifest_path,
                "reference_policy.bundles must be a mapping.",
            )
        ]
    try:
        canonical_relative = safe_relative_path(
            policy.get("canonical_root", "references"), "reference canonical root"
        )
        marker_relative = safe_relative_path(
            policy.get("generated_marker", ".vibio-generated.json"),
            "reference marker path",
            filename_only=True,
        )
    except ValueError as exc:
        return [Finding("error", "references.policy-path", manifest_path, str(exc))]

    canonical_root = root / canonical_relative
    canonical_link = first_symlink(root, canonical_root)
    if canonical_link is not None:
        return [
            Finding(
                "error",
                "references.symlink",
                canonical_link,
                "Canonical reference root must not traverse a symbolic link.",
            )
        ]
    if not canonical_root.is_dir():
        return [
            Finding(
                "error",
                "references.canonical-root",
                canonical_root,
                "Canonical reference root is missing.",
            )
        ]
    for path in canonical_root.rglob("*"):
        if path.is_symlink():
            findings.append(
                Finding(
                    "error",
                    "references.symlink",
                    path,
                    "Canonical reference tree must not contain symbolic links.",
                )
            )

    declared: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("skills", []):
        if not isinstance(entry, dict) or not entry.get("path") or not entry.get("name"):
            continue
        try:
            safe_relative_path(entry["path"], "skill path")
        except ValueError:
            continue
        declared[str(entry["path"])] = entry
    for raw_skill_path in bundles:
        if str(raw_skill_path) not in declared:
            findings.append(
                Finding(
                    "error",
                    "references.unknown-skill",
                    manifest_path,
                    f"Reference bundle targets undeclared skill: {raw_skill_path}",
                )
            )

    consumed: set[str] = set()
    for skill_path, entry in declared.items():
        skill_relative = safe_relative_path(skill_path, "skill path")
        skill_md = root / skill_relative / "SKILL.md"
        output_root = root / skill_relative / "references"
        output_link = first_symlink(root, output_root)
        if output_link is not None:
            findings.append(
                Finding(
                    "error",
                    "references.symlink",
                    output_link,
                    "Generated reference directory must not traverse a symbolic link.",
                )
            )
            continue
        expected, expected_findings = expected_reference_files(
            root,
            canonical_root,
            skill_md,
            bundles.get(skill_path, "closure"),
        )
        findings.extend(expected_findings)
        consumed.update(expected)
        for relative_posix in sorted(expected):
            relative = Path(*PurePosixPath(relative_posix).parts)
            canonical = canonical_root / relative
            copied = output_root / relative
            copied_link = first_symlink(root, copied)
            if copied_link is not None:
                findings.append(
                    Finding(
                        "error",
                        "references.symlink",
                        copied_link,
                        "Generated reference must not traverse a symbolic link.",
                    )
                )
            elif not copied.is_file():
                findings.append(
                    Finding(
                        "error",
                        "references.copy-missing",
                        copied,
                        "Generated Skill reference is missing; run scripts/build_skills.py --clean.",
                    )
                )
            elif copied.read_bytes() != canonical.read_bytes():
                findings.append(
                    Finding(
                        "error",
                        "references.drift",
                        copied,
                        f"Generated reference differs from '{canonical.relative_to(root)}'.",
                    )
                )

        canonical_relatives = {
            path.relative_to(canonical_root).as_posix()
            for path in canonical_root.rglob("*.md")
            if path.is_file() and not path.is_symlink()
        }
        if output_root.is_dir():
            for copied in sorted(output_root.rglob("*.md")):
                relative_posix = copied.relative_to(output_root).as_posix()
                if relative_posix in canonical_relatives and relative_posix not in expected:
                    findings.append(
                        Finding(
                            "error",
                            "references.unexpected-copy",
                            copied,
                            "Generated reference exists outside the recomputed Skill closure; "
                            "run scripts/build_skills.py --clean or remove the stale copy.",
                        )
                    )

        marker = output_root / marker_relative
        if not marker.is_file():
            findings.append(
                Finding(
                    "error",
                    "references.marker-missing",
                    marker,
                    "Generated reference marker is missing.",
                )
            )
            continue
        findings.extend(
            validate_marker(
                root,
                marker,
                prefix="references",
                item_label="reference",
                skill_name=str(entry["name"]),
                canonical_root=marker_canonical_root(canonical_root, output_root),
                expected=expected,
            )
        )

    orphan_severity = "error" if strict else "warning"
    for canonical in sorted(canonical_root.rglob("*.md")):
        relative = canonical.relative_to(canonical_root).as_posix()
        if not canonical.is_symlink() and relative not in consumed:
            findings.append(
                Finding(
                    orphan_severity,
                    "references.orphan",
                    canonical,
                    "Canonical reference is not consumed by any Skill bundle.",
                )
            )
    return findings


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_files(canonical_root: Path) -> list[Path]:
    return sorted(
        path
        for path in canonical_root.rglob("*")
        if (
            not path.is_symlink()
            and path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        )
    )


def validate_marker(
    root: Path,
    marker: Path,
    *,
    prefix: str,
    item_label: str,
    skill_name: str,
    canonical_root: str,
    expected: dict[str, str],
) -> list[Finding]:
    findings: list[Finding] = []
    linked = first_symlink(root, marker)
    if linked is not None:
        return [
            Finding(
                "error",
                f"{prefix}.symlink",
                linked,
                f"Generated {item_label} marker must not traverse a symbolic link.",
            )
        ]
    try:
        data = load_json(marker)
    except (OSError, json.JSONDecodeError) as exc:
        return [Finding("error", f"{prefix}.marker-invalid", marker, str(exc))]
    if not isinstance(data, dict):
        return [
            Finding("error", f"{prefix}.marker-invalid", marker, "Marker must contain an object.")
        ]

    if (
        data.get("generated_by") != GENERATOR
        or data.get("skill") != skill_name
        or data.get("canonical_root") != canonical_root
    ):
        findings.append(
            Finding(
                "error",
                f"{prefix}.marker-identity",
                marker,
                "Marker generator, skill, or canonical root does not match this bundle.",
            )
        )
    files = data.get("files")
    marker_files: dict[str, str] = {}
    if not isinstance(files, dict):
        findings.append(
            Finding("error", f"{prefix}.marker-invalid", marker, "Marker files must be an object.")
        )
    else:
        for raw_relative, raw_digest in files.items():
            try:
                relative = safe_relative_path(raw_relative, "marker-owned file path")
            except ValueError as exc:
                findings.append(
                    Finding("error", f"{prefix}.marker-path", marker, str(exc))
                )
                continue
            digest = str(raw_digest)
            if not SHA256_RE.fullmatch(digest):
                findings.append(
                    Finding(
                        "error",
                        f"{prefix}.marker-invalid",
                        marker,
                        f"Invalid SHA-256 for marker file: {raw_relative!r}",
                    )
                )
                continue
            marker_files[relative.as_posix()] = digest
    if marker_files != expected:
        findings.append(
            Finding(
                "error",
                f"{prefix}.marker-drift",
                marker,
                f"{item_label.title()} marker hashes do not match the manifest bundle.",
            )
        )
    return findings


def validate_generated_bundles(
    root: Path,
    manifest: dict[str, Any],
    strict: bool,
    *,
    policy_name: str,
    prefix: str,
    item_label: str,
    default_canonical_root: str,
    default_generated_directory: str,
    default_marker: str,
    validate_schemas: bool = False,
) -> list[Finding]:
    findings: list[Finding] = []
    policy = manifest.get(policy_name, {})
    if not policy:
        return findings
    manifest_path = root / "vibio.manifest.yaml"
    try:
        canonical_relative = safe_relative_path(
            policy.get("canonical_root", default_canonical_root), f"{item_label} canonical root"
        )
        generated_relative = safe_relative_path(
            policy.get("generated_directory", default_generated_directory),
            f"{item_label} generated directory",
        )
        marker_relative = safe_relative_path(
            policy.get("generated_marker", default_marker),
            f"{item_label} marker path",
            filename_only=True,
        )
    except ValueError as exc:
        return [Finding("error", f"{prefix}.policy-path", manifest_path, str(exc))]

    canonical_root = root / canonical_relative
    linked = first_symlink(root, canonical_root)
    if linked is not None:
        return [
            Finding(
                "error",
                f"{prefix}.symlink",
                linked,
                f"Canonical {item_label} root must not traverse a symbolic link.",
            )
        ]
    if not canonical_root.is_dir():
        return [
            Finding(
                "error",
                f"{prefix}.canonical-root",
                canonical_root,
                f"Canonical {item_label} root is missing.",
            )
        ]

    bundles = policy.get("bundles", {})
    if not isinstance(bundles, dict):
        return [
            Finding(
                "error",
                f"{prefix}.bundles",
                manifest_path,
                f"{policy_name}.bundles must be a mapping.",
            )
        ]

    all_canonical = canonical_files(canonical_root)
    canonical_by_relative = {
        path.relative_to(canonical_root).as_posix(): path for path in all_canonical
    }
    for path in canonical_root.rglob("*"):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            findings.append(
                Finding(
                    "error",
                    f"{prefix}.symlink",
                    path,
                    f"Canonical {item_label} tree must not contain symbolic links.",
                )
            )

    if validate_schemas:
        for canonical in all_canonical:
            if canonical.suffix != ".json":
                continue
            try:
                schema = load_json(canonical)
                Draft202012Validator.check_schema(schema)
            except (OSError, json.JSONDecodeError, SchemaError, TypeError, ValueError) as exc:
                findings.append(
                    Finding("error", "schemas.canonical-invalid", canonical, str(exc))
                )

    declared_skills: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("skills", []):
        if not isinstance(entry, dict) or not entry.get("path") or not entry.get("name"):
            continue
        try:
            safe_relative_path(entry["path"], "skill path")
        except ValueError:
            continue
        declared_skills[str(entry["path"])] = entry
    for raw_skill_path in bundles:
        if str(raw_skill_path) not in declared_skills:
            findings.append(
                Finding(
                    "error",
                    f"{prefix}.unknown-skill",
                    manifest_path,
                    f"{item_label.title()} bundle targets undeclared skill: {raw_skill_path}",
                )
            )

    consumed: set[str] = set()
    for skill_path, entry in declared_skills.items():
        requested = bundles.get(skill_path, [])
        if not isinstance(requested, list):
            findings.append(
                Finding(
                    "error",
                    f"{prefix}.bundle-type",
                    manifest_path,
                    f"{item_label.title()} bundle for {skill_path} must be a list.",
                )
            )
            continue
        if len([str(item) for item in requested]) != len(set(str(item) for item in requested)):
            findings.append(
                Finding(
                    "error",
                    f"{prefix}.bundle-duplicate",
                    manifest_path,
                    f"{item_label.title()} bundle for {skill_path} contains duplicate paths.",
                )
            )

        skill_relative = safe_relative_path(skill_path, "skill path")
        output_root = root / skill_relative / generated_relative
        output_link = first_symlink(root, output_root)
        if output_link is not None:
            findings.append(
                Finding(
                    "error",
                    f"{prefix}.symlink",
                    output_link,
                    f"Generated {item_label} directory must not traverse a symbolic link.",
                )
            )
            continue

        expected: dict[str, str] = {}
        for raw_relative in requested:
            try:
                relative = safe_relative_path(raw_relative, f"{item_label} bundle path")
            except ValueError as exc:
                findings.append(
                    Finding("error", f"{prefix}.path-boundary", manifest_path, str(exc))
                )
                continue
            relative_posix = relative.as_posix()
            consumed.add(relative_posix)
            canonical = canonical_root / relative
            linked = first_symlink(root, canonical)
            if linked is not None:
                findings.append(
                    Finding(
                        "error",
                        f"{prefix}.symlink",
                        linked,
                        f"Canonical {item_label} source must not traverse a symbolic link.",
                    )
                )
                continue
            if not canonical.is_file():
                findings.append(
                    Finding(
                        "error",
                        f"{prefix}.canonical-missing",
                        canonical,
                        f"Canonical {item_label} is missing.",
                    )
                )
                continue

            expected[relative_posix] = hash_file(canonical)
            copied = output_root / relative
            copied_link = first_symlink(root, copied)
            if copied_link is not None:
                findings.append(
                    Finding(
                        "error",
                        f"{prefix}.symlink",
                        copied_link,
                        f"Generated {item_label} must not traverse a symbolic link.",
                    )
                )
            elif not copied.is_file():
                findings.append(
                    Finding(
                        "error",
                        f"{prefix}.copy-missing",
                        copied,
                        f"Generated Skill {item_label} is missing; run scripts/build_skills.py --clean.",
                    )
                )
            elif copied.read_bytes() != canonical.read_bytes():
                findings.append(
                    Finding(
                        "error",
                        f"{prefix}.drift",
                        copied,
                        f"Generated {item_label} differs from '{canonical.relative_to(root)}'.",
                    )
                )

        if output_root.is_dir():
            for copied in canonical_files(output_root):
                relative_posix = copied.relative_to(output_root).as_posix()
                if relative_posix in canonical_by_relative and relative_posix not in expected:
                    findings.append(
                        Finding(
                            "error",
                            f"{prefix}.unexpected-copy",
                            copied,
                            f"Generated {item_label} exists outside the manifest bundle; "
                            "run scripts/build_skills.py --clean or remove the stale copy.",
                        )
                    )

        marker = output_root / marker_relative
        marker_link = first_symlink(root, marker)
        if marker_link is not None:
            findings.append(
                Finding(
                    "error",
                    f"{prefix}.symlink",
                    marker_link,
                    f"Generated {item_label} marker must not traverse a symbolic link.",
                )
            )
            continue
        if requested and not marker.is_file():
            findings.append(
                Finding(
                    "error",
                    f"{prefix}.marker-missing",
                    marker,
                    f"Generated {item_label} marker is missing.",
                )
            )
            continue
        if not requested and marker.exists():
            findings.append(
                Finding(
                    "error",
                    f"{prefix}.marker-unexpected",
                    marker,
                    f"Empty {item_label} bundles must not keep a generated marker.",
                )
            )
        if marker.is_file():
            findings.extend(
                validate_marker(
                    root,
                    marker,
                    prefix=prefix,
                    item_label=item_label,
                    skill_name=str(entry["name"]),
                    canonical_root=marker_canonical_root(canonical_root, output_root),
                    expected=expected,
                )
            )

    orphan_severity = "error" if strict else "warning"
    for relative, canonical in canonical_by_relative.items():
        if relative not in consumed:
            findings.append(
                Finding(
                    orphan_severity,
                    f"{prefix}.orphan",
                    canonical,
                    f"Canonical {item_label} is not consumed by any Skill bundle.",
                )
            )
    return findings


def validate_tool_bundles(
    root: Path, manifest: dict[str, Any], strict: bool = False
) -> list[Finding]:
    return validate_generated_bundles(
        root,
        manifest,
        strict,
        policy_name="tool_policy",
        prefix="tools",
        item_label="tool",
        default_canonical_root="runtime",
        default_generated_directory="scripts",
        default_marker=".vibio-tools.json",
    )


def validate_schema_bundles(
    root: Path, manifest: dict[str, Any], strict: bool = False
) -> list[Finding]:
    return validate_generated_bundles(
        root,
        manifest,
        strict,
        policy_name="schema_policy",
        prefix="schemas",
        item_label="schema",
        default_canonical_root="schemas",
        default_generated_directory="schemas",
        default_marker=".vibio-schemas.json",
        validate_schemas=True,
    )


def validate_repository(root: Path = ROOT, strict: bool = False) -> list[Finding]:
    root = root.resolve()
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
    findings.extend(validate_reference_bundles(root, manifest, strict))
    findings.extend(validate_tool_bundles(root, manifest, strict))
    findings.extend(validate_schema_bundles(root, manifest, strict))
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
