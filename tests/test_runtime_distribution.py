from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_manifest_consumes_every_canonical_runtime_and_schema() -> None:
    manifest = yaml.safe_load((ROOT / "vibio.manifest.yaml").read_text(encoding="utf-8"))
    tool_bundles = manifest["tool_policy"]["bundles"]
    schema_bundles = manifest["schema_policy"]["bundles"]
    consumed_tools = {item for bundle in tool_bundles.values() for item in bundle}
    consumed_schemas = {item for bundle in schema_bundles.values() for item in bundle}
    canonical_tools = {
        path.relative_to(ROOT / "runtime").as_posix()
        for path in (ROOT / "runtime").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    canonical_schemas = {
        path.relative_to(ROOT / "schemas").as_posix()
        for path in (ROOT / "schemas").rglob("*")
        if path.is_file()
    }

    assert canonical_tools == consumed_tools
    assert canonical_schemas == consumed_schemas
    assert "gsc_ai_compare.py" in tool_bundles["vibio-review"]
    assert "gsc_ai_compare.report.schema.json" in schema_bundles["vibio-review"]


def test_new_official_reference_modules_are_reachable_from_skills() -> None:
    skill_texts = [
        path.read_text(encoding="utf-8")
        for path in ROOT.glob("vibio*/SKILL.md")
        if path.is_file()
    ]
    for reference in (
        "javascript-rendering.md",
        "core-web-vitals.md",
        "faceted-navigation.md",
        "bing-webmaster-docs.md",
    ):
        assert any(f"references/{reference}" in text for text in skill_texts)


def test_audit_skill_tool_runs_after_standalone_copy(tmp_path: Path) -> None:
    skill = tmp_path / "vibio-audit"
    shutil.copytree(ROOT / "vibio-audit", skill)
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(
        '<html><head><title>Test</title><link rel="canonical" href="https://example.com/">'
        '</head><body><main><h1>Test</h1></main></body></html>',
        encoding="utf-8",
    )
    output = tmp_path / "inspection.json"

    result = subprocess.run(
        [
            sys.executable,
            str(skill / "scripts/seo_inspect.py"),
            "--site-dir",
            str(site),
            "--base-url",
            "https://example.com/",
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "inspection.md"),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["scope"]["pages_parsed"] == 1


def test_review_skill_gsc_tool_runs_after_standalone_copy(tmp_path: Path) -> None:
    skill = tmp_path / "vibio-review"
    shutil.copytree(ROOT / "vibio-review", skill)
    source = tmp_path / "gsc.csv"
    source.write_text(
        "Date,Query,Clicks,Impressions,Position\n"
        "2026-05-01,sensor,1,10,5\n"
        "2026-06-01,sensor,2,20,4\n",
        encoding="utf-8",
    )
    output = tmp_path / "gsc.json"

    result = subprocess.run(
        [
            sys.executable,
            str(skill / "scripts/gsc_compare.py"),
            "--input",
            str(source),
            "--baseline-start",
            "2026-05-01",
            "--baseline-end",
            "2026-05-31",
            "--current-start",
            "2026-06-01",
            "--current-end",
            "2026-06-30",
            "--property-id",
            "sc-domain:example.com",
            "--search-type",
            "web",
            "--timezone",
            "Asia/Shanghai",
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "gsc.md"),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["dataset_contract"]["contract_complete"] is True
    assert report["overall"]["current"]["clicks"] == 2


def test_memory_state_tool_runs_after_standalone_copy(tmp_path: Path) -> None:
    skill = tmp_path / "vibio-memory"
    shutil.copytree(ROOT / "vibio-memory", skill)
    project = tmp_path / "project"
    project.mkdir()

    initialized = subprocess.run(
        [
            sys.executable,
            str(skill / "scripts/state_manager.py"),
            "init",
            "--project-root",
            str(project),
            "--project-id",
            "standalone-demo",
            "--site-url",
            "https://example.com/",
            "--market",
            "DE",
            "--language",
            "de-DE",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    validated = subprocess.run(
        [
            sys.executable,
            str(skill / "scripts/state_manager.py"),
            "validate",
            "--project-root",
            str(project),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert initialized.returncode == 0, initialized.stderr
    assert validated.returncode == 0, validated.stderr
    assert "验证通过" in validated.stdout
    assert json.loads(
        (project / ".vibio/state/project.json").read_text(encoding="utf-8")
    )["project_id"] == "standalone-demo"


def test_review_measurement_tool_runs_after_standalone_copy(tmp_path: Path) -> None:
    skill = tmp_path / "vibio-review"
    shutil.copytree(ROOT / "vibio-review", skill)

    result = subprocess.run(
        [sys.executable, str(skill / "scripts/measurement_review.py"), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "GSC 页面级" in result.stdout
    assert "CRM 聚合" in result.stdout
    assert (skill / "schemas/measurement_review.report.schema.json").is_file()


def test_review_gsc_ai_tool_runs_after_standalone_copy(tmp_path: Path) -> None:
    skill = tmp_path / "vibio-review"
    shutil.copytree(ROOT / "vibio-review", skill)

    result = subprocess.run(
        [sys.executable, str(skill / "scripts/gsc_ai_compare.py"), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "生成式 AI 效果报告" in result.stdout
    assert (skill / "schemas/gsc_ai_compare.report.schema.json").is_file()


def test_experiment_workflow_runs_from_standalone_skill_copies(tmp_path: Path) -> None:
    copied: dict[str, Path] = {}
    for skill_name in ("vibio", "vibio-plan", "vibio-review", "vibio-memory"):
        skill = tmp_path / skill_name
        shutil.copytree(ROOT / skill_name, skill)
        copied[skill_name] = skill
        for schema_name in (
            "experiment.plan.schema.json",
            "experiment.report.schema.json",
        ):
            assert (skill / "schemas" / schema_name).is_file()
        help_result = subprocess.run(
            [sys.executable, str(skill / "scripts/experiment.py"), "--help"],
            cwd=tmp_path,
            check=False,
            capture_output=True,
            text=True,
        )
        assert help_result.returncode == 0, help_result.stderr
        assert "冻结 SEO 页面对照实验" in help_result.stdout

    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "experiment_id": "standalone-exp-001",
                "design": "randomized_page_holdout",
                "unit_id_column": "page",
                "primary_metric": "organic_clicks",
                "primary_metric_direction": "increase",
                "guardrails": [
                    {
                        "metric": "qualified_lead_rate",
                        "direction": "non_decrease",
                        "threshold": 0.01,
                    }
                ],
                "seed": 20260711,
                "treatment_fraction": 0.5,
                "baseline_start": "2025-01-01",
                "baseline_end": "2025-01-31",
                "observation_start": "2025-02-01",
                "observation_end": "2025-02-28",
                "minimum_detectable_effect": {"value": 1, "scale": "absolute"},
                "alpha": 0.05,
                "measurement_contract": {
                    "analysis_timezone": "UTC",
                    "temporal_grain": "date",
                    "source_timezones": {"panel": "UTC"},
                    "sources": {
                        "panel": {
                            "source_kind": "derived_experiment_panel",
                            "metrics": ["organic_clicks", "qualified_lead_rate"],
                            "data_as_of": "2025-03-15",
                            "finality": "final",
                            "row_limit_hit": False,
                            "pagination_complete": True,
                            "data_quality": "complete",
                        }
                    },
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "baseline.csv"
    baseline.write_text(
        "page,organic_clicks,qualified_lead_rate\n"
        "/a,10,0.20\n/b,10,0.20\n/c,10,0.20\n/d,10,0.20\n",
        encoding="utf-8",
    )
    frozen = tmp_path / "frozen"
    planned = subprocess.run(
        [
            sys.executable,
            str(copied["vibio-plan"] / "scripts/experiment.py"),
            "plan",
            "--spec",
            str(spec),
            "--baseline",
            str(baseline),
            "--out-dir",
            str(frozen),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert planned.returncode == 0, planned.stderr

    plan = json.loads((frozen / "plan.json").read_text(encoding="utf-8"))
    panel_lines = [
        "page,date,group,organic_clicks,qualified_lead_rate,contaminated,treatment_applied"
    ]
    for assignment in plan["assignments"]:
        unit_id = assignment["unit_id"]
        group = assignment["group"]
        for day in range(1, 32):
            panel_lines.append(
                f"{unit_id},2025-01-{day:02d},{group},10,0.20,false,false"
            )
        clicks = 14 if group == "treatment" else 11
        applied = "true" if group == "treatment" else "false"
        for day in range(1, 29):
            panel_lines.append(
                f"{unit_id},2025-02-{day:02d},{group},{clicks},0.20,false,{applied}"
            )
    panel = tmp_path / "panel.csv"
    panel.write_text("\n".join(panel_lines) + "\n", encoding="utf-8")
    artifact = tmp_path / "artifact.json"
    artifact.write_text(
        json.dumps(
            {
                "experiment_id": plan["experiment_id"],
                "plan_hash": plan["plan_hash"],
                "passed": True,
                "evidence": "独立 Skill 产物复验通过",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    result_path = tmp_path / "experiment-result.json"
    analyzed = subprocess.run(
        [
            sys.executable,
            str(copied["vibio-review"] / "scripts/experiment.py"),
            "analyze",
            "--plan",
            str(frozen / "plan.json"),
            "--panel",
            str(panel),
            "--artifact-report",
            str(artifact),
            "--out",
            str(result_path),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert analyzed.returncode == 0, analyzed.stderr
    assert json.loads(result_path.read_text(encoding="utf-8"))["eligibility"] == (
        "eligible_incremental"
    )
