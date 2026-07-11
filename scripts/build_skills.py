#!/usr/bin/env python3
"""生成每个 Vibio Skill 的自包含 reference、运行工具与 Schema 包。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_RE = re.compile(r"(?<![\w./-])(references/[A-Za-z0-9_./<>-]+)")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GENERATOR = "scripts/build_skills.py"


def normalize(raw: str) -> str:
    return raw.rstrip("`'\".,:;)]}")


def refs_from_text(text: str) -> Iterable[str]:
    seen: set[str] = set()
    for raw in REFERENCE_RE.findall(text):
        value = normalize(raw)
        if "<" in value or ">" in value or "/xxx." in value:
            continue
        if value not in seen:
            seen.add(value)
            yield value.removeprefix("references/")


def safe_relative_path(raw: object, label: str, *, filename_only: bool = False) -> Path:
    """Return a portable repo-relative path or reject it before filesystem access."""
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


def assert_no_symlink(root: Path, target: Path, label: str) -> None:
    """Reject symlinks in a path, including a final symlink to an external file."""
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes repository root: {target}") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{label} must not traverse a symbolic link: {current}")


def assert_tree_has_no_symlinks(root: Path, tree: Path, label: str) -> None:
    assert_no_symlink(root, tree, label)
    if not tree.exists():
        return
    for path in tree.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"{label} must not contain symbolic links: {path}")


def marker_canonical_root(canonical: Path, output_root: Path) -> str:
    return os.path.relpath(canonical, output_root).replace(os.sep, "/")


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_owned_files(
    root: Path,
    marker: Path,
    *,
    skill_name: str,
    canonical_root: str,
) -> dict[str, str]:
    """Load only a marker created for this exact bundle; invalid markers own nothing."""
    assert_no_symlink(root, marker, "Generated marker")
    if not marker.exists():
        return {}
    if not marker.is_file():
        raise ValueError(f"Generated marker is not a regular file: {marker}")
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid generated marker {marker}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid generated marker {marker}: expected an object")
    if (
        data.get("generated_by") != GENERATOR
        or data.get("skill") != skill_name
        or data.get("canonical_root") != canonical_root
    ):
        raise ValueError(f"Generated marker identity does not match this bundle: {marker}")
    files = data.get("files")
    if not isinstance(files, dict):
        raise ValueError(f"Invalid generated marker {marker}: files must be an object")
    owned: dict[str, str] = {}
    for raw_relative, raw_digest in files.items():
        relative = safe_relative_path(raw_relative, "marker-owned file path")
        digest = str(raw_digest)
        if not SHA256_RE.fullmatch(digest):
            raise ValueError(f"Invalid SHA-256 in generated marker {marker}: {raw_relative!r}")
        owned[relative.as_posix()] = digest
    return owned


def preflight_destination(root: Path, output_root: Path, relative: Path, label: str) -> Path:
    destination = output_root / relative
    assert_no_symlink(root, destination, label)
    if destination.exists() and not destination.is_file():
        raise ValueError(f"{label} is not a regular file: {destination}")
    return destination


def assert_destination_can_update(
    destination: Path,
    relative_posix: str,
    source_hash: str,
    old_owned: dict[str, str],
) -> None:
    """Allow generated updates only when the destination has not been edited by a user."""
    if not destination.exists():
        return
    current_hash = hash_file(destination)
    previous_hash = old_owned.get(relative_posix)
    if previous_hash is None:
        if current_hash != source_hash:
            raise ValueError(f"Refusing to overwrite unowned file: {destination}")
        return
    if current_hash not in {previous_hash, source_hash}:
        raise ValueError(f"Refusing to overwrite modified generated file: {destination}")


def remove_stale_owned_files(
    root: Path,
    output_root: Path,
    old_owned: dict[str, str],
    desired: dict[str, str],
) -> None:
    stale = sorted(set(old_owned) - set(desired), reverse=True)
    candidates: list[tuple[Path, str]] = []
    for raw_relative in stale:
        relative = safe_relative_path(raw_relative, "marker-owned file path")
        target = preflight_destination(root, output_root, relative, "Marker-owned file")
        if not target.exists():
            continue
        if hash_file(target) != old_owned[raw_relative]:
            raise ValueError(f"Refusing to delete modified generated file: {target}")
        candidates.append((target, raw_relative))

    for target, _ in candidates:
        target.unlink()
        parent = target.parent
        while parent != output_root and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent


def write_marker(
    marker: Path,
    *,
    skill_name: str,
    canonical_root: str,
    files: dict[str, str],
) -> None:
    marker.write_text(
        json.dumps(
            {
                "generated_by": GENERATOR,
                "canonical_root": canonical_root,
                "skill": skill_name,
                "files": files,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def expand_paths(root: Path, canonical: Path, requested: Iterable[str]) -> set[Path]:
    files: set[Path] = set()
    for raw_relative in requested:
        normalized = str(raw_relative).rstrip("/")
        relative = safe_relative_path(normalized, "reference path")
        target = canonical / relative
        assert_no_symlink(root, target, "Reference source")
        if target.is_dir():
            assert_tree_has_no_symlinks(root, target, "Reference directory")
            files.update(path for path in target.rglob("*.md") if path.is_file())
        elif target.is_file():
            files.add(target)
        else:
            raise FileNotFoundError(f"Reference does not exist: {raw_relative}")
    return files


def build_bundle(root: Path, skill: dict, clean: bool) -> dict:
    root = root.resolve()
    manifest = yaml.safe_load((root / "vibio.manifest.yaml").read_text(encoding="utf-8"))
    policy = manifest["reference_policy"]
    canonical_relative = safe_relative_path(
        policy.get("canonical_root", "references"), "reference canonical root"
    )
    skill_relative = safe_relative_path(skill["path"], "skill path")
    marker_relative = safe_relative_path(
        policy.get("generated_marker", ".vibio-generated.json"),
        "reference marker path",
        filename_only=True,
    )
    canonical = root / canonical_relative
    skill_dir = root / skill_relative
    skill_md = skill_dir / "SKILL.md"
    output_root = skill_dir / "references"
    marker = output_root / marker_relative
    assert_tree_has_no_symlinks(root, canonical, "Canonical reference root")
    assert_no_symlink(root, skill_md, "Skill file")
    assert_no_symlink(root, output_root, "Generated reference directory")
    if not skill_md.is_file():
        raise FileNotFoundError(f"Missing skill file: {skill_md}")

    canonical_marker_root = marker_canonical_root(canonical, output_root)
    old_owned = load_owned_files(
        root,
        marker,
        skill_name=str(skill["name"]),
        canonical_root=canonical_marker_root,
    )
    bundle_mode = policy.get("bundles", {}).get(skill["path"], "closure")
    if bundle_mode == "all":
        files = set(canonical.rglob("*.md"))
    elif bundle_mode == "closure":
        queue = list(refs_from_text(skill_md.read_text(encoding="utf-8")))
        selected: set[str] = set()
        files: set[Path] = set()
        while queue:
            relative = queue.pop(0)
            if relative in selected:
                continue
            selected.add(relative)
            expanded = expand_paths(root, canonical, [relative])
            files.update(expanded)
            for file in expanded:
                for nested in refs_from_text(file.read_text(encoding="utf-8")):
                    if nested not in selected:
                        queue.append(nested)
    else:
        raise ValueError(f"Invalid reference bundle mode for {skill['path']}: {bundle_mode!r}")

    desired: dict[str, str] = {}
    destinations: list[tuple[Path, Path]] = []
    for source in sorted(files):
        assert_no_symlink(root, source, "Reference source")
        relative = source.relative_to(canonical)
        destination = preflight_destination(
            root, output_root, relative, "Generated reference destination"
        )
        relative_posix = relative.as_posix()
        source_hash = hash_file(source)
        assert_destination_can_update(
            destination,
            relative_posix,
            source_hash,
            old_owned,
        )
        desired[relative_posix] = source_hash
        destinations.append((source, destination))

    if clean:
        remove_stale_owned_files(root, output_root, old_owned, desired)
    for source, destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    output_root.mkdir(parents=True, exist_ok=True)
    marker_files = desired if clean else {**old_owned, **desired}
    write_marker(
        marker,
        skill_name=str(skill["name"]),
        canonical_root=canonical_marker_root,
        files=marker_files,
    )
    return {"skill": skill["name"], "files": len(desired), "marker": str(marker.relative_to(root))}


def build_declared_files(
    root: Path,
    skill: dict,
    clean: bool,
    *,
    policy_name: str,
    default_canonical_root: str,
    default_generated_directory: str,
    default_marker: str,
    item_label: str,
) -> dict:
    root = root.resolve()
    manifest = yaml.safe_load((root / "vibio.manifest.yaml").read_text(encoding="utf-8"))
    policy = manifest.get(policy_name, {})
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
    skill_relative = safe_relative_path(skill["path"], "skill path")
    canonical = root / canonical_relative
    output_root = root / skill_relative / generated_relative
    marker = output_root / marker_relative
    assert_tree_has_no_symlinks(root, canonical, f"Canonical {item_label} root")
    assert_no_symlink(root, output_root, f"Generated {item_label} directory")
    bundles = policy.get("bundles", {})
    if not isinstance(bundles, dict):
        raise ValueError(f"{policy_name}.bundles must be a mapping")
    requested = bundles.get(skill["path"], [])
    if not isinstance(requested, list):
        raise ValueError(f"{item_label.title()} bundle for {skill['path']} must be a list")
    if len([str(item) for item in requested]) != len(set(str(item) for item in requested)):
        raise ValueError(f"{item_label.title()} bundle for {skill['path']} contains duplicates")

    canonical_marker_root = marker_canonical_root(canonical, output_root)
    old_owned = load_owned_files(
        root,
        marker,
        skill_name=str(skill["name"]),
        canonical_root=canonical_marker_root,
    )
    desired: dict[str, str] = {}
    destinations: list[tuple[Path, Path]] = []
    for raw_relative in requested:
        relative = safe_relative_path(raw_relative, f"{item_label} bundle path")
        source = canonical / relative
        assert_no_symlink(root, source, f"Canonical {item_label} source")
        if not source.is_file():
            raise FileNotFoundError(f"{item_label.title()} does not exist: {source}")
        destination = preflight_destination(
            root, output_root, relative, f"Generated {item_label} destination"
        )
        relative_posix = relative.as_posix()
        source_hash = hash_file(source)
        assert_destination_can_update(
            destination,
            relative_posix,
            source_hash,
            old_owned,
        )
        desired[relative_posix] = source_hash
        destinations.append((source, destination))

    if clean:
        remove_stale_owned_files(root, output_root, old_owned, desired)
    for source, destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    marker_files = desired if clean else {**old_owned, **desired}
    if marker_files:
        output_root.mkdir(parents=True, exist_ok=True)
        write_marker(
            marker,
            skill_name=str(skill["name"]),
            canonical_root=canonical_marker_root,
            files=marker_files,
        )
    elif clean and marker.exists():
        marker.unlink()
    if output_root.is_dir() and not any(output_root.iterdir()):
        output_root.rmdir()
    return {
        "skill": skill["name"],
        "files": len(desired),
        "marker": str(marker.relative_to(root)) if marker_files else None,
    }


def build_tools(root: Path, skill: dict, clean: bool) -> dict:
    return build_declared_files(
        root,
        skill,
        clean,
        policy_name="tool_policy",
        default_canonical_root="runtime",
        default_generated_directory="scripts",
        default_marker=".vibio-tools.json",
        item_label="tool",
    )


def build_schemas(root: Path, skill: dict, clean: bool) -> dict:
    return build_declared_files(
        root,
        skill,
        clean,
        policy_name="schema_policy",
        default_canonical_root="schemas",
        default_generated_directory="schemas",
        default_marker=".vibio-schemas.json",
        item_label="schema",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove only stale files explicitly owned by a valid generated marker.",
    )
    parser.add_argument("--skill", action="append", help="Build only this skill path; repeatable.")
    args = parser.parse_args()

    root = args.root.resolve()
    manifest = yaml.safe_load((root / "vibio.manifest.yaml").read_text(encoding="utf-8"))
    skills = manifest["skills"]
    selected = set(args.skill or [])
    if selected:
        skills = [skill for skill in skills if skill["path"] in selected]
        missing = selected - {str(skill["path"]) for skill in skills}
        if missing:
            raise ValueError(f"Unknown skill path(s): {', '.join(sorted(missing))}")
    for skill in skills:
        result = build_bundle(root, skill, args.clean)
        tools = build_tools(root, skill, args.clean)
        schemas = build_schemas(root, skill, args.clean)
        tool_status = f"{tools['files']} tools -> {tools['marker']}" if tools["files"] else "0 tools"
        schema_status = (
            f"{schemas['files']} schemas -> {schemas['marker']}"
            if schemas["files"]
            else "0 schemas"
        )
        print(
            f"{result['skill']}: {result['files']} references -> {result['marker']}; "
            f"{tool_status}; {schema_status}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
