#!/usr/bin/env python3
"""Generate self-contained reference bundles for each Vibio skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_RE = re.compile(r"(?<![\w./-])(references/[A-Za-z0-9_./<>-]+)")


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


def expand_paths(canonical: Path, requested: Iterable[str]) -> set[Path]:
    files: set[Path] = set()
    for relative in requested:
        target = canonical / relative
        if target.is_dir():
            files.update(path for path in target.rglob("*.md") if path.is_file())
        elif target.is_file():
            files.add(target)
        else:
            raise FileNotFoundError(f"Reference does not exist: {relative}")
    return files


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_bundle(root: Path, skill: dict, clean: bool) -> dict:
    canonical = root / "references"
    skill_dir = root / skill["path"]
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise FileNotFoundError(f"Missing skill file: {skill_md}")

    policy = yaml.safe_load((root / "vibio.manifest.yaml").read_text(encoding="utf-8"))["reference_policy"]
    bundle_mode = policy.get("bundles", {}).get(skill["path"], "closure")
    if bundle_mode == "all":
        files = set(canonical.rglob("*.md"))
    else:
        queue = list(refs_from_text(skill_md.read_text(encoding="utf-8")))
        selected: set[str] = set()
        files: set[Path] = set()
        while queue:
            relative = queue.pop(0)
            if relative in selected:
                continue
            selected.add(relative)
            expanded = expand_paths(canonical, [relative])
            files.update(expanded)
            for file in expanded:
                for nested in refs_from_text(file.read_text(encoding="utf-8")):
                    if nested not in selected:
                        queue.append(nested)

    output_root = skill_dir / "references"
    output_root.mkdir(parents=True, exist_ok=True)
    desired: dict[str, str] = {}
    for source in sorted(files):
        relative = source.relative_to(canonical)
        destination = output_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        desired[str(relative)] = hash_file(source)

    if clean:
        for existing in sorted(output_root.rglob("*.md")):
            relative = str(existing.relative_to(output_root))
            if relative not in desired:
                existing.unlink()
        for directory in sorted(output_root.rglob("*"), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()

    marker_name = str(policy.get("generated_marker", ".vibio-generated.json"))
    marker = output_root / marker_name
    marker.write_text(
        json.dumps(
            {
                "generated_by": "scripts/build_skills.py",
                "canonical_root": "../../references",
                "skill": skill["name"],
                "files": desired,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"skill": skill["name"], "files": len(desired), "marker": str(marker.relative_to(root))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--clean", action="store_true", help="Remove reference files not in the generated closure.")
    parser.add_argument("--skill", action="append", help="Build only this skill path; repeatable.")
    args = parser.parse_args()

    root = args.root.resolve()
    manifest = yaml.safe_load((root / "vibio.manifest.yaml").read_text(encoding="utf-8"))
    skills = manifest["skills"]
    selected = set(args.skill or [])
    if selected:
        skills = [skill for skill in skills if skill["path"] in selected]
    for skill in skills:
        result = build_bundle(root, skill, args.clean)
        print(f"{result['skill']}: {result['files']} references -> {result['marker']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
