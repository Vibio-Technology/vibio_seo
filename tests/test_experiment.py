from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from runtime.experiment import (
    CAUSALITY_BOUNDARY,
    PAID_SEARCH_BOUNDARY,
    ExperimentError,
    _assignments_csv,
    analyze_experiment,
    compute_plan_hash,
    load_and_verify_plan,
    load_spec,
    plan_experiment,
    render_markdown,
    validate_experiment_report,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime" / "experiment.py"


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def spec_value(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "experiment_id": "seo-exp-001",
        "design": "randomized_page_holdout",
        "unit_id_column": "page",
        "primary_metric": "organic_clicks",
        "primary_metric_direction": "increase",
        "guardrails": [
            {
                "metric": "conversion_rate",
                "direction": "non_decrease",
                "threshold": 0.01,
            }
        ],
        "seed": 20260711,
        "treatment_fraction": 0.5,
        "baseline_start": "2026-01-01",
        "baseline_end": "2026-01-31",
        "observation_start": "2026-02-01",
        "observation_end": "2026-02-28",
        "minimum_detectable_effect": {"value": 1.0, "scale": "absolute"},
        "alpha": 0.05,
        "measurement_contract": {
            "analysis_timezone": "UTC",
            "temporal_grain": "date",
            "source_timezones": {"panel": "UTC"},
            "sources": {
                "panel": {
                    "source_kind": "derived_experiment_panel",
                    "metrics": ["organic_clicks", "conversion_rate"],
                    "data_as_of": "2026-07-05",
                    "finality": "final",
                    "row_limit_hit": False,
                    "pagination_complete": True,
                    "data_quality": "complete",
                }
            },
        },
    }
    value.update(overrides)
    return value


def artifact_value(
    plan: dict[str, object], *, passed: bool = True
) -> dict[str, object]:
    return {
        "experiment_id": plan["experiment_id"],
        "plan_hash": plan["plan_hash"],
        "passed": passed,
        "evidence": "seo_inspect before/after artifact gate",
    }


BASELINE = (
    "page,organic_clicks,conversion_rate\n"
    "/a,10,0.20\n"
    "/b,10,0.20\n"
    "/c,10,0.20\n"
    "/d,10,0.20\n"
)


def prepare_plan(tmp_path: Path, **spec_overrides: object) -> tuple[Path, dict[str, object]]:
    spec = write_json(tmp_path / "spec.json", spec_value(**spec_overrides))
    baseline = write_text(tmp_path / "baseline.csv", BASELINE)
    out_dir = tmp_path / "planned"
    plan = plan_experiment(spec, baseline, out_dir)
    return out_dir / "plan.json", plan


def panel_for_plan(
    plan: dict[str, object],
    *,
    treatment_click_change: float = 4,
    control_click_change: float = 1,
    treatment_guardrail_change: float = 0,
    control_guardrail_change: float = 0,
    contaminated_unit: str | None = None,
    omit_current_unit: str | None = None,
) -> str:
    lines = [
        "page,date,group,organic_clicks,conversion_rate,contaminated,treatment_applied"
    ]
    prereg = plan["preregistration"]  # type: ignore[index]
    baseline_window = prereg["baseline_window"]
    observation_window = prereg["observation_window"]

    def days(window: dict[str, str]) -> list[date]:
        start = date.fromisoformat(window["start"])
        end = date.fromisoformat(window["end"])
        return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]

    for assignment in plan["assignments"]:  # type: ignore[index]
        unit_id = assignment["unit_id"]
        group = assignment["group"]
        for day in days(baseline_window):
            lines.append(f"{unit_id},{day.isoformat()},{group},10,0.20,false,false")
        if unit_id == omit_current_unit:
            continue
        if group == "treatment":
            clicks = 10 + treatment_click_change
            conversion = 0.20 + treatment_guardrail_change
            applied = "true"
        else:
            clicks = 10 + control_click_change
            conversion = 0.20 + control_guardrail_change
            applied = "false"
        contaminated = "true" if unit_id == contaminated_unit else "false"
        for day in days(observation_window):
            lines.append(
                f"{unit_id},{day.isoformat()},{group},{clicks},{conversion},{contaminated},{applied}"
            )
    return "\n".join(lines) + "\n"


def prepare_analysis_inputs(
    tmp_path: Path, **panel_options: object
) -> tuple[Path, dict[str, object], Path, Path]:
    plan_path, plan = prepare_plan(tmp_path)
    panel = write_text(
        tmp_path / "panel.csv", panel_for_plan(plan, **panel_options)  # type: ignore[arg-type]
    )
    artifact = write_json(
        tmp_path / "artifact.json",
        artifact_value(plan),
    )
    return plan_path, plan, panel, artifact


def test_plan_is_seed_reproducible_and_freezes_source_hashes(tmp_path: Path) -> None:
    spec_path = write_json(tmp_path / "spec.json", spec_value())
    baseline_path = write_text(tmp_path / "baseline.csv", BASELINE)

    first = plan_experiment(spec_path, baseline_path, tmp_path / "first")
    second = plan_experiment(spec_path, baseline_path, tmp_path / "second")

    assert first == second
    assert (tmp_path / "first" / "assignments.csv").read_bytes() == (
        tmp_path / "second" / "assignments.csv"
    ).read_bytes()
    assert first["frozen_inputs"]["spec_sha256"] == hashlib.sha256(spec_path.read_bytes()).hexdigest()
    assert first["frozen_inputs"]["baseline_sha256"] == hashlib.sha256(
        baseline_path.read_bytes()
    ).hexdigest()
    assert first["balance"]["unit_counts"] == {"treatment": 2, "control": 2}
    assert len(first["plan_hash"]) == 64
    assert first["boundaries"]["paid_search"] == PAID_SEARCH_BOUNDARY
    assert first["measurement_contract"]["analysis_timezone"] == "UTC"
    assert first["measurement_contract"]["sources"]["panel"]["source_kind"] == (
        "derived_experiment_panel"
    )


def test_plan_refuses_to_overwrite_frozen_files(tmp_path: Path) -> None:
    spec_path = write_json(tmp_path / "spec.json", spec_value())
    baseline_path = write_text(tmp_path / "baseline.csv", BASELINE)
    out_dir = tmp_path / "frozen"
    plan_experiment(spec_path, baseline_path, out_dir)

    with pytest.raises(ExperimentError, match="拒绝覆盖"):
        plan_experiment(spec_path, baseline_path, out_dir)


def test_matched_design_preserves_pair_id_and_splits_each_pair(tmp_path: Path) -> None:
    spec_path = write_json(
        tmp_path / "spec.json", spec_value(design="matched_page_did", seed="stable-seed")
    )
    baseline_path = write_text(
        tmp_path / "baseline.csv",
        "page,pair_id,organic_clicks,conversion_rate\n"
        "/a,p1,10,0.2\n/b,p1,11,0.2\n"
        "/c,p2,20,0.3\n/d,p2,19,0.3\n",
    )

    plan = plan_experiment(spec_path, baseline_path, tmp_path / "matched")

    by_pair: dict[str, set[str]] = {}
    for item in plan["assignments"]:
        by_pair.setdefault(item["pair_id"], set()).add(item["group"])
    assert by_pair == {"p1": {"treatment", "control"}, "p2": {"treatment", "control"}}
    assert "pair_id" in (tmp_path / "matched" / "assignments.csv").read_text(encoding="utf-8")


def test_hash_mismatch_is_rejected_before_analysis(tmp_path: Path) -> None:
    plan_path, plan = prepare_plan(tmp_path)
    plan["preregistration"]["primary_metric"] = "impressions"  # type: ignore[index]
    write_json(plan_path, plan)

    with pytest.raises(ExperimentError, match="plan hash 不匹配"):
        load_and_verify_plan(plan_path)


def test_panel_group_overlap_is_rejected(tmp_path: Path) -> None:
    plan_path, plan = prepare_plan(tmp_path)
    first = plan["assignments"][0]  # type: ignore[index]
    other_group = "control" if first["group"] == "treatment" else "treatment"
    panel = write_text(
        tmp_path / "overlap.csv",
        "page,date,group,organic_clicks,conversion_rate,contaminated\n"
        f"{first['unit_id']},2026-01-15,{first['group']},10,0.2,false\n"
        f"{first['unit_id']},2026-02-15,{other_group},12,0.2,false\n",
    )
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    with pytest.raises(ExperimentError, match="分组重叠"):
        analyze_experiment(plan_path, panel, artifact)


def test_frozen_plan_cannot_assign_one_unit_twice_even_with_recomputed_hash(tmp_path: Path) -> None:
    _, plan = prepare_plan(tmp_path)
    plan["assignments"][1]["unit_id"] = plan["assignments"][0]["unit_id"]  # type: ignore[index]
    plan["plan_hash"] = compute_plan_hash(plan)
    bad_dir = tmp_path / "duplicate-plan"
    bad_dir.mkdir()
    bad_plan = write_json(bad_dir / "plan.json", plan)

    with pytest.raises(ExperimentError, match="实验单位.*重复分配"):
        load_and_verify_plan(bad_plan)


def test_artifact_failure_has_distinct_implementation_failed_eligibility(tmp_path: Path) -> None:
    plan_path, plan, panel, artifact = prepare_analysis_inputs(tmp_path)
    write_json(
        artifact,
        artifact_value(plan, passed=False),
    )

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "implementation-failed"
    assert result["eligibility_details"]["reasons"] == ["artifact_verification_failed"]
    assert result["eligibility_details"]["business_verdict"] is None


def test_artifact_report_must_bind_to_frozen_plan_and_evidence(tmp_path: Path) -> None:
    plan_path, _, panel, _ = prepare_analysis_inputs(tmp_path)
    artifact = write_json(tmp_path / "unbound-artifact.json", {"passed": True})

    with pytest.raises(ExperimentError, match="experiment_id.*plan_hash.*evidence"):
        analyze_experiment(plan_path, panel, artifact)


def test_missing_period_and_contamination_are_inconclusive(tmp_path: Path) -> None:
    plan_path, plan = prepare_plan(tmp_path)
    omitted = plan["assignments"][0]["unit_id"]  # type: ignore[index]
    contaminated = plan["assignments"][1]["unit_id"]  # type: ignore[index]
    panel = write_text(
        tmp_path / "panel.csv",
        panel_for_plan(plan, omit_current_unit=omitted, contaminated_unit=contaminated),
    )
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    codes = {issue["code"] for issue in result["data_quality"]["issues"]}
    assert "missing_unit_period" in codes
    assert "contamination_detected" in codes


def test_missing_preregistered_metric_column_is_inconclusive(tmp_path: Path) -> None:
    plan_path, plan = prepare_plan(tmp_path)
    lines = ["page,date,group,organic_clicks,contaminated"]
    for assignment in plan["assignments"]:  # type: ignore[index]
        unit = assignment["unit_id"]
        group = assignment["group"]
        lines.append(f"{unit},2026-01-15,{group},10,false")
        lines.append(f"{unit},2026-02-15,{group},12,false")
    panel = write_text(tmp_path / "missing-column.csv", "\n".join(lines) + "\n")
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    assert result["data_quality"]["issues"][0] == {
        "code": "missing_columns",
        "detail": "缺少列：conversion_rate",
    }


def test_numeric_did_ci_guardrail_and_eligibility(tmp_path: Path) -> None:
    plan_path, _, panel, artifact = prepare_analysis_inputs(tmp_path)

    result = analyze_experiment(plan_path, panel, artifact)
    primary = result["primary_metric"]

    assert primary["arms"]["treatment"] == {
        "units": 2,
        "baseline_mean": 10,
        "current_mean": 14,
        "absolute_change": 4,
        "relative_change": 0.4,
    }
    assert primary["arms"]["control"]["absolute_change"] == 1
    assert primary["difference_in_differences"] == 3
    assert primary["relative_difference_in_differences"] == 0.3
    assert primary["standard_error"] == 0
    assert primary["confidence_interval"]["lower"] == 3
    assert primary["confidence_interval"]["upper"] == 3
    assert primary["detectability"]["power"] is None
    assert primary["detectability"]["precision_sufficient_for_mde"] is True
    assert result["guardrails"]["passed"] is True
    assert result["eligibility"] == "eligible_incremental"
    assert result["measurement_contract"]["status"] == "complete"
    assert result["eligibility_details"]["incremental_positive_allowed"] is True
    assert result["eligibility_details"]["primary_metric_direction"] == "increase"
    assert result["eligibility_details"]["point_estimate_supports_direction"] is True
    assert result["eligibility_details"]["confidence_interval_supports_direction"] is True
    assert result["eligibility_details"]["no_detectable_change_allowed"] is False
    assert result["methodology"]["causal_claim_automated"] is False
    assert CAUSALITY_BOUNDARY in render_markdown(result)


def test_precise_negative_effect_is_eligible_but_not_incremental_positive(
    tmp_path: Path,
) -> None:
    plan_path, _, panel, artifact = prepare_analysis_inputs(
        tmp_path,
        treatment_click_change=-4,
        control_click_change=1,
    )

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["primary_metric"]["difference_in_differences"] == -5
    assert result["eligibility"] == "eligible_incremental"
    assert result["eligibility_details"]["point_estimate_supports_direction"] is False
    assert result["eligibility_details"]["confidence_interval_supports_direction"] is False
    assert result["eligibility_details"]["incremental_positive_allowed"] is False


def test_guardrail_breach_prevents_incremental_eligibility(tmp_path: Path) -> None:
    plan_path, _, panel, artifact = prepare_analysis_inputs(
        tmp_path,
        treatment_guardrail_change=-0.04,
        control_guardrail_change=0,
    )

    result = analyze_experiment(plan_path, panel, artifact)

    guardrail = result["guardrails"]["results"][0]
    assert guardrail["difference_in_differences"] == pytest.approx(-0.04)
    assert guardrail["passed"] is False
    assert result["guardrails"]["passed"] is False
    assert result["eligibility"] == "inconclusive"
    assert "guardrail_breached" in result["eligibility_details"]["reasons"]


def test_missing_contamination_observability_is_inconclusive(tmp_path: Path) -> None:
    plan_path, plan = prepare_plan(tmp_path)
    lines = ["page,date,group,organic_clicks,conversion_rate"]
    for assignment in plan["assignments"]:  # type: ignore[index]
        unit = assignment["unit_id"]
        group = assignment["group"]
        lines.append(f"{unit},2026-01-15,{group},10,0.2")
        lines.append(f"{unit},2026-02-15,{group},12,0.2")
    panel = write_text(tmp_path / "panel.csv", "\n".join(lines) + "\n")
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    assert result["data_quality"]["contamination_observable"] is False
    assert "contamination_not_observable" in result["eligibility_details"]["reasons"]


def test_observation_window_must_be_mature(tmp_path: Path) -> None:
    plan_path, plan = prepare_plan(
        tmp_path,
        baseline_start="2999-01-01",
        baseline_end="2999-01-31",
        observation_start="2999-02-01",
        observation_end="2999-02-28",
    )
    lines = [
        "page,date,group,organic_clicks,conversion_rate,contaminated,treatment_applied"
    ]
    for assignment in plan["assignments"]:  # type: ignore[index]
        unit = assignment["unit_id"]
        group = assignment["group"]
        lines.append(f"{unit},2999-01-15,{group},10,0.2,false,false")
        applied = "true" if group == "treatment" else "false"
        lines.append(f"{unit},2999-02-15,{group},12,0.2,false,{applied}")
    panel = write_text(tmp_path / "future-panel.csv", "\n".join(lines) + "\n")
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    assert "observation_not_mature" in result["eligibility_details"]["reasons"]


def test_pure_before_after_design_is_rejected(tmp_path: Path) -> None:
    spec_path = write_json(tmp_path / "spec.json", spec_value(design="before_after"))

    with pytest.raises(ExperimentError, match="不接受纯前后对比"):
        load_spec(spec_path)


def test_script_can_run_plan_and_analyze_directly(tmp_path: Path) -> None:
    spec_path = write_json(tmp_path / "spec.json", spec_value())
    baseline_path = write_text(tmp_path / "baseline.csv", BASELINE)
    out_dir = tmp_path / "cli-plan"
    planned = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "plan",
            "--spec",
            str(spec_path),
            "--baseline",
            str(baseline_path),
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert planned.returncode == 0, planned.stderr
    assert "已冻结实验计划" in planned.stdout

    plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))
    result_path = tmp_path / "result.json"
    analyzed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "analyze",
            "--plan",
            str(out_dir / "plan.json"),
            "--panel",
            str(panel),
            "--artifact-report",
            str(artifact),
            "--out",
            str(result_path),
            "--markdown-out",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert analyzed.returncode == 0, analyzed.stderr
    assert "资格状态：eligible_incremental" in analyzed.stdout
    assert json.loads(result_path.read_text(encoding="utf-8"))["eligibility"] == "eligible_incremental"
    assert result_path.with_suffix(".md").exists()


def test_help_and_cli_errors_are_chinese(tmp_path: Path) -> None:
    help_result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert help_result.returncode == 0
    assert "用法：" in help_result.stdout
    assert "子命令" in help_result.stdout

    error_result = subprocess.run(
        [sys.executable, str(SCRIPT), "plan"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert error_result.returncode == 2
    assert "错误：缺少必需参数" in error_result.stderr


def test_missing_measurement_metadata_blocks_incremental_eligibility(tmp_path: Path) -> None:
    plan_path, plan = prepare_plan(tmp_path, measurement_contract={})
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    assert result["measurement_contract"]["status"] == "inconclusive"
    reasons = set(result["eligibility_details"]["reasons"])
    assert "analysis_timezone_missing" in reasons
    assert "source_metadata_missing" in reasons
    assert result["eligibility_details"]["incremental_positive_allowed"] is False
    assert result["eligibility_details"]["no_detectable_change_allowed"] is False


def test_row_limit_sampling_thresholding_and_preliminary_block_eligibility(
    tmp_path: Path,
) -> None:
    contract = {
        "analysis_timezone": "UTC",
        "temporal_grain": "date",
        "source_timezones": {"ga4": "UTC"},
        "sources": {
            "ga4": {
                "source_kind": "ga4_property_report",
                "metrics": ["organic_clicks", "conversion_rate"],
                "data_as_of": "2026-07-05",
                "finality": "preliminary",
                "row_limit_hit": True,
                "pagination_complete": False,
                "sampling_rate": 0.75,
                "thresholding_applied": True,
                "data_quality": "degraded",
                "attribution_model": "data_driven",
            }
        },
    }
    plan_path, plan = prepare_plan(tmp_path, measurement_contract=contract)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    reasons = set(result["eligibility_details"]["reasons"])
    assert {
        "data_preliminary",
        "row_limit_hit",
        "pagination_incomplete",
        "sampling_applied",
        "thresholding_applied",
        "data_quality_degraded",
    } <= reasons


def test_date_grain_source_timezone_mismatch_blocks_incremental_eligibility(
    tmp_path: Path,
) -> None:
    complete = {
        "data_as_of": "2026-07-05",
        "finality": "final",
        "row_limit_hit": False,
        "pagination_complete": True,
        "data_quality": "complete",
    }
    contract = {
        "analysis_timezone": "UTC",
        "temporal_grain": "date",
        "source_timezones": {
            "gsc": "America/Los_Angeles",
            "crm": "Europe/Berlin",
        },
        "sources": {
            "gsc": {
                **complete,
                "source_kind": "gsc_search_analytics",
                "metrics": ["organic_clicks"],
            },
            "crm": {
                **complete,
                "source_kind": "crm_aggregate_export",
                "metrics": ["conversion_rate"],
                "attribution_model": "first_organic_landing_cohort",
            },
        },
    }
    plan_path, plan = prepare_plan(tmp_path, measurement_contract=contract)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    assert result["measurement_contract"]["daily_cross_source_join_allowed"] is False
    assert "source_day_boundary_mismatch" in result["eligibility_details"]["reasons"]


def test_analysis_metadata_can_complete_preregistered_source_contract(
    tmp_path: Path,
) -> None:
    preregistered = {
        "analysis_timezone": "UTC",
        "temporal_grain": "date",
        "source_timezones": {"panel": "UTC"},
        "sources": {
            "panel": {
                "source_kind": "derived_experiment_panel",
                "metrics": ["organic_clicks", "conversion_rate"],
            }
        },
    }
    plan_path, plan = prepare_plan(tmp_path, measurement_contract=preregistered)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))
    metadata = write_json(
        tmp_path / "measurement-metadata.json",
        {
            "sources": {
                "panel": {
                    "data_as_of": "2026-07-05",
                    "finality": "final",
                    "row_limit_hit": False,
                    "pagination_complete": True,
                    "data_quality": "complete",
                }
            }
        },
    )

    result = analyze_experiment(plan_path, panel, artifact, metadata)

    assert result["eligibility"] == "eligible_incremental"
    assert result["measurement_contract"]["complete"] is True
    assert result["measurement_contract"]["metadata_file_sha256"] == hashlib.sha256(
        metadata.read_bytes()
    ).hexdigest()
    validate_experiment_report(result, plan)


def test_analysis_metadata_cannot_complete_missing_preregistered_contract(
    tmp_path: Path,
) -> None:
    plan_path, plan = prepare_plan(tmp_path, measurement_contract={})
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))
    metadata = write_json(
        tmp_path / "measurement-metadata.json",
        {"measurement_contract": spec_value()["measurement_contract"]},
    )

    result = analyze_experiment(plan_path, panel, artifact, metadata)

    assert result["eligibility"] == "inconclusive"
    assert result["measurement_contract"]["analysis_timezone"] is None
    assert result["measurement_contract"]["sources"] == {}
    assert {
        "analysis_timezone_missing",
        "source_metadata_missing",
        "analysis_timezone_changed_after_preregistration",
        "source_added_after_preregistration",
    } <= set(result["eligibility_details"]["reasons"])


def test_analysis_metadata_cannot_change_frozen_attribution_model(
    tmp_path: Path,
) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    contract["sources"]["panel"]["source_kind"] = "crm_aggregate_export"  # type: ignore[index]
    contract["sources"]["panel"]["attribution_model"] = "first_touch"  # type: ignore[index]
    plan_path, plan = prepare_plan(tmp_path, measurement_contract=contract)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))
    metadata = write_json(
        tmp_path / "measurement-metadata.json",
        {"sources": {"panel": {"attribution_model": "last_touch"}}},
    )

    result = analyze_experiment(plan_path, panel, artifact, metadata)

    assert result["eligibility"] == "inconclusive"
    assert result["measurement_contract"]["sources"]["panel"]["attribution_model"] == (
        "first_touch"
    )
    assert "source_attribution_model_changed_after_preregistration" in (
        result["eligibility_details"]["reasons"]
    )


def test_sampling_and_thresholding_block_custom_source_kind(tmp_path: Path) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    contract["sources"]["panel"]["source_kind"] = "custom_export"  # type: ignore[index]
    contract["sources"]["panel"]["sampling_rate"] = 0.25  # type: ignore[index]
    contract["sources"]["panel"]["thresholding_applied"] = True  # type: ignore[index]
    plan_path, plan = prepare_plan(tmp_path, measurement_contract=contract)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    assert {"sampling_applied", "thresholding_applied"} <= set(
        result["eligibility_details"]["reasons"]
    )


def test_plan_rejects_source_ids_that_collide_after_trimming(tmp_path: Path) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    source = contract["sources"]["panel"]  # type: ignore[index]
    contract["sources"] = {
        "panel": {
            **source,
            "source_kind": "custom_export",
            "sampling_rate": 0.25,
            "thresholding_applied": True,
        },
        " panel ": {
            **source,
            "source_kind": "custom_export",
            "sampling_rate": 1,
            "thresholding_applied": False,
        },
    }

    with pytest.raises(ExperimentError, match="source_id 规范化后重复.*panel"):
        prepare_plan(tmp_path, measurement_contract=contract)


def test_plan_rejects_sources_and_source_metadata_together(tmp_path: Path) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    contract["source_metadata"] = contract["sources"]

    with pytest.raises(
        ExperimentError,
        match="measurement_contract.*不得同时声明 sources 与 source_metadata",
    ):
        prepare_plan(tmp_path, measurement_contract=contract)


@pytest.mark.parametrize("root_field", ["source_metadata", "sources"])
def test_spec_rejects_measurement_contract_with_root_source_metadata(
    tmp_path: Path, root_field: str
) -> None:
    legacy_source = {
        "panel": {
            "source_kind": "shadow_export",
            "metrics": ["organic_clicks", "conversion_rate"],
        }
    }

    with pytest.raises(
        ExperimentError,
        match=rf"measurement_contract.*根级来源/legacy.*{root_field}",
    ):
        prepare_plan(tmp_path, **{root_field: legacy_source})


def test_analysis_metadata_rejects_source_id_collision_before_quality_gate(
    tmp_path: Path,
) -> None:
    plan_path, plan = prepare_plan(tmp_path)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))
    common = {
        "data_as_of": "2026-07-05",
        "finality": "final",
        "row_limit_hit": False,
        "pagination_complete": True,
        "data_quality": "complete",
    }
    metadata = write_json(
        tmp_path / "measurement-metadata.json",
        {
            "sources": {
                "panel": {
                    **common,
                    "sampling_rate": 0.25,
                    "thresholding_applied": True,
                },
                " panel ": {
                    **common,
                    "sampling_rate": 1,
                    "thresholding_applied": False,
                },
            }
        },
    )

    with pytest.raises(ExperimentError, match="source_id 规范化后重复.*panel"):
        analyze_experiment(plan_path, panel, artifact, metadata)


def test_analysis_metadata_rejects_sources_and_source_metadata_together(
    tmp_path: Path,
) -> None:
    plan_path, plan, panel, artifact = prepare_analysis_inputs(tmp_path)
    metadata = write_json(
        tmp_path / "measurement-metadata.json",
        {
            "sources": {
                "panel": {"sampling_rate": 1, "thresholding_applied": False}
            },
            "source_metadata": {
                "panel": {"sampling_rate": 0.25, "thresholding_applied": True}
            },
        },
    )

    with pytest.raises(
        ExperimentError,
        match="measurement metadata.*不得同时声明 sources 与 source_metadata",
    ):
        analyze_experiment(plan_path, panel, artifact, metadata)


def test_analysis_metadata_wrapper_rejects_sibling_source_declaration(
    tmp_path: Path,
) -> None:
    plan_path, plan, panel, artifact = prepare_analysis_inputs(tmp_path)
    metadata = write_json(
        tmp_path / "measurement-metadata.json",
        {
            "measurement_contract": {
                "sources": {
                    "panel": {"sampling_rate": 1, "thresholding_applied": False}
                }
            },
            "sources": {
                "panel": {"sampling_rate": 0.25, "thresholding_applied": True}
            },
        },
    )

    with pytest.raises(
        ExperimentError,
        match="measurement_contract 包装.*同级字段.*sources",
    ):
        analyze_experiment(plan_path, panel, artifact, metadata)


def test_analysis_metric_must_map_to_exactly_one_source(tmp_path: Path) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    panel_source = contract["sources"]["panel"]  # type: ignore[index]
    contract["sources"]["secondary"] = {  # type: ignore[index]
        **panel_source,
        "source_kind": "secondary_aggregate_export",
        "metrics": ["organic_clicks"],
    }
    contract["source_timezones"]["secondary"] = "UTC"  # type: ignore[index]
    plan_path, plan = prepare_plan(tmp_path, measurement_contract=contract)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    assert "metric_source_mapping_ambiguous" in result["eligibility_details"]["reasons"]


def test_single_day_per_window_cannot_pass_daily_coverage_gate(tmp_path: Path) -> None:
    plan_path, plan = prepare_plan(tmp_path)
    lines = [
        "page,date,group,organic_clicks,conversion_rate,contaminated,treatment_applied"
    ]
    for assignment in plan["assignments"]:  # type: ignore[index]
        unit = assignment["unit_id"]
        group = assignment["group"]
        lines.append(f"{unit},2026-01-15,{group},10,0.20,false,false")
        applied = "true" if group == "treatment" else "false"
        lines.append(f"{unit},2026-02-15,{group},12,0.20,false,{applied}")
    panel = write_text(tmp_path / "sparse-panel.csv", "\n".join(lines) + "\n")
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    assert result["data_quality"]["coverage"]["complete"] is False
    assert "missing_unit_dates" in result["eligibility_details"]["reasons"]


def test_panel_baseline_must_match_frozen_per_unit_summary(tmp_path: Path) -> None:
    plan_path, plan, panel, artifact = prepare_analysis_inputs(tmp_path)
    panel.write_text(
        panel.read_text(encoding="utf-8").replace(
            "/a,2026-01-01,", "/a,2026-01-01,", 1
        ).replace(
            ",10,0.20,false,false", ",999,0.20,false,false", 1
        ),
        encoding="utf-8",
    )

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    assert result["data_quality"]["coverage"]["frozen_baseline_bound"] is False
    assert "frozen_baseline_mismatch" in result["eligibility_details"]["reasons"]


def test_aggregate_baseline_rejects_duplicate_unit_grain(tmp_path: Path) -> None:
    spec_path = write_json(tmp_path / "spec.json", spec_value())
    baseline = write_text(
        tmp_path / "baseline.csv",
        BASELINE + "/a,10,0.20\n",
    )

    with pytest.raises(ExperimentError, match="每个实验单位只能有一行"):
        plan_experiment(spec_path, baseline, tmp_path / "planned")


def test_data_as_of_datetime_requires_offset(tmp_path: Path) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    contract["sources"]["panel"]["data_as_of"] = "2026-03-01T00:00:00"  # type: ignore[index]

    with pytest.raises(ExperimentError, match="UTC offset"):
        prepare_plan(tmp_path, measurement_contract=contract)


def test_data_as_of_is_compared_after_source_timezone_conversion(tmp_path: Path) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    contract["source_timezones"] = {"panel": "America/Los_Angeles"}
    contract["sources"]["panel"]["data_as_of"] = "2026-02-28T00:30:00+14:00"  # type: ignore[index]
    plan_path, plan = prepare_plan(tmp_path, measurement_contract=contract)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert "data_as_of_before_observation_end" in result["eligibility_details"]["reasons"]


def test_timestamp_panel_contract_is_rejected_until_supported(tmp_path: Path) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    contract["temporal_grain"] = "timestamp"

    with pytest.raises(ExperimentError, match="只支持 date"):
        prepare_plan(tmp_path, measurement_contract=contract)


def test_duplicate_measurement_metric_mapping_is_rejected(tmp_path: Path) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    contract["sources"]["panel"]["metrics"] = ["organic_clicks", "organic_clicks"]  # type: ignore[index]

    with pytest.raises(ExperimentError, match="不得重复"):
        prepare_plan(tmp_path, measurement_contract=contract)


def test_explicit_null_artifact_cannot_be_promoted_by_nested_summary(tmp_path: Path) -> None:
    plan_path, plan = prepare_plan(tmp_path)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = artifact_value(plan)
    artifact["passed"] = None
    artifact["summary"] = {"passed": True}

    with pytest.raises(ExperimentError, match="passed 必须是布尔值"):
        analyze_experiment(plan_path, panel, write_json(tmp_path / "artifact.json", artifact))


def test_matched_plan_loader_rejects_more_than_two_members_per_pair(tmp_path: Path) -> None:
    spec_path = write_json(
        tmp_path / "spec.json", spec_value(design="matched_page_did", seed="pair-check")
    )
    baseline = write_text(
        tmp_path / "baseline.csv",
        "page,pair_id,organic_clicks,conversion_rate\n"
        "/a,p1,10,0.2\n/b,p1,10,0.2\n/c,p2,10,0.2\n/d,p2,10,0.2\n",
    )
    out = tmp_path / "matched"
    plan_experiment(spec_path, baseline, out)
    plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
    first = plan["assignments"][0]
    plan["assignments"].append(
        {
            "unit_id": "/extra",
            "group": first["group"],
            "pair_id": first["pair_id"],
        }
    )
    plan["plan_hash"] = compute_plan_hash(plan)
    write_json(out / "plan.json", plan)

    with pytest.raises(ExperimentError, match="恰好包含一条实验组和一条对照组"):
        load_and_verify_plan(out / "plan.json")


def test_observation_end_date_itself_is_not_yet_mature(tmp_path: Path) -> None:
    today = date.today()
    baseline_day = today - timedelta(days=2)
    plan_path, plan = prepare_plan(
        tmp_path,
        baseline_start=baseline_day.isoformat(),
        baseline_end=baseline_day.isoformat(),
        observation_start=today.isoformat(),
        observation_end=today.isoformat(),
    )
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert "observation_not_mature" in result["eligibility_details"]["reasons"]


def test_future_data_cutoff_cannot_satisfy_measurement_contract(tmp_path: Path) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    contract["sources"]["panel"]["data_as_of"] = "2999-01-01"  # type: ignore[index]
    plan_path, plan = prepare_plan(tmp_path, measurement_contract=contract)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert "data_as_of_in_future" in result["eligibility_details"]["reasons"]


def test_missing_source_timezone_remains_structured_inconclusive(tmp_path: Path) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    contract["source_timezones"] = {}
    plan_path, plan = prepare_plan(tmp_path, measurement_contract=contract)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))

    result = analyze_experiment(plan_path, panel, artifact)

    assert result["eligibility"] == "inconclusive"
    assert "source_timezone_missing" in result["eligibility_details"]["reasons"]


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("alpha", 1.5, "alpha.*0 和 1"),
        ("treatment_fraction", 0, "treatment_fraction.*0 和 1"),
        (
            "minimum_detectable_effect",
            {"value": -1, "scale": "absolute"},
            "minimum_detectable_effect.*大于 0",
        ),
        ("seed", True, "seed.*整数或非空字符串"),
    ],
)
def test_plan_loader_revalidates_preregistered_numeric_fields(
    tmp_path: Path, field: str, value: object, match: str
) -> None:
    plan_path, plan = prepare_plan(tmp_path)
    plan["preregistration"][field] = value  # type: ignore[index]
    plan["plan_hash"] = compute_plan_hash(plan)
    write_json(plan_path, plan)

    with pytest.raises(ExperimentError, match=match):
        load_and_verify_plan(plan_path)


def test_plan_loader_revalidates_guardrail_semantics_and_baseline_row_count(
    tmp_path: Path,
) -> None:
    plan_path, plan = prepare_plan(tmp_path)
    plan["preregistration"]["guardrails"][0]["direction"] = "sideways"  # type: ignore[index]
    plan["plan_hash"] = compute_plan_hash(plan)
    write_json(plan_path, plan)
    with pytest.raises(ExperimentError, match="direction.*non_decrease"):
        load_and_verify_plan(plan_path)

    rows_root = tmp_path / "rows"
    rows_root.mkdir()
    plan_path, plan = prepare_plan(rows_root)
    plan["frozen_inputs"]["baseline_source_rows"] += 1  # type: ignore[index,operator]
    plan["plan_hash"] = compute_plan_hash(plan)
    write_json(plan_path, plan)
    with pytest.raises(ExperimentError, match="baseline_source_rows.*总和"):
        load_and_verify_plan(plan_path)


def test_plan_loader_replays_seeded_assignments_and_balance(tmp_path: Path) -> None:
    plan_path, plan = prepare_plan(tmp_path)
    assignments = plan["assignments"]
    treatment = next(item for item in assignments if item["group"] == "treatment")
    control = next(item for item in assignments if item["group"] == "control")
    treatment["group"], control["group"] = control["group"], treatment["group"]
    assignment_bytes = _assignments_csv(assignments, plan["unit_id_column"], False)
    plan["assignments_sha256"] = hashlib.sha256(assignment_bytes).hexdigest()
    plan["plan_hash"] = compute_plan_hash(plan)
    write_json(plan_path, plan)

    with pytest.raises(ExperimentError, match="seed/design/treatment_fraction.*不一致"):
        load_and_verify_plan(plan_path)


def test_report_validator_rejects_unrecognized_top_level_claims(tmp_path: Path) -> None:
    plan_path, plan, panel, artifact = prepare_analysis_inputs(tmp_path)
    result = analyze_experiment(plan_path, panel, artifact)
    result["causal_business_claim"] = {
        "ranking_increase_proven": True,
        "revenue_caused": 999999,
    }

    with pytest.raises(ExperimentError, match="额外字段.*causal_business_claim"):
        validate_experiment_report(result, plan)


def test_report_validator_rejects_nested_causal_business_claim(tmp_path: Path) -> None:
    plan_path, plan, panel, artifact = prepare_analysis_inputs(tmp_path)
    result = analyze_experiment(plan_path, panel, artifact)
    result["methodology"]["causal_business_claim"] = "SEO caused pipeline growth."

    with pytest.raises(
        ExperimentError,
        match="methodology.*额外字段.*causal_business_claim",
    ):
        validate_experiment_report(result, plan)


def test_report_validator_recomputes_eligibility_from_measurement_issues(
    tmp_path: Path,
) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    contract["sources"]["panel"]["source_kind"] = "custom_export"  # type: ignore[index]
    contract["sources"]["panel"]["sampling_rate"] = 0.25  # type: ignore[index]
    contract["sources"]["panel"]["thresholding_applied"] = True  # type: ignore[index]
    plan_path, plan = prepare_plan(tmp_path, measurement_contract=contract)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))
    result = analyze_experiment(plan_path, panel, artifact)
    assert result["measurement_contract"]["complete"] is False
    assert {"sampling_applied", "thresholding_applied"} <= {
        item["code"] for item in result["data_quality"]["issues"]
    }
    validate_experiment_report(result, plan)

    result["eligibility"] = "eligible_incremental"
    result["eligibility_details"]["eligible_incremental"] = True
    result["eligibility_details"]["reasons"] = []
    result["eligibility_details"]["incremental_positive_allowed"] = True

    with pytest.raises(ExperimentError, match="eligibility.*重算结果矛盾"):
        validate_experiment_report(result, plan)


@pytest.mark.parametrize(
    ("field", "value"),
    [("row_limit_hit", 0), ("sampling_rate", True)],
)
def test_report_validator_rejects_measurement_source_status_type_confusion(
    tmp_path: Path, field: str, value: object
) -> None:
    plan_path, plan, panel, artifact = prepare_analysis_inputs(tmp_path)
    result = analyze_experiment(plan_path, panel, artifact)
    result["measurement_contract"]["sources"]["panel"][field] = value

    with pytest.raises(ExperimentError, match="measurement_contract.*必须|状态或类型"):
        validate_experiment_report(result, plan)


def test_report_validator_binds_measurement_metadata_hash(tmp_path: Path) -> None:
    plan_path, plan, panel, artifact = prepare_analysis_inputs(tmp_path)
    result = analyze_experiment(plan_path, panel, artifact)
    result["measurement_contract"]["metadata_file_sha256"] = "0" * 64

    with pytest.raises(ExperimentError, match="metadata 哈希.*source_hashes"):
        validate_experiment_report(result, plan)


def test_report_validator_requires_measurement_issues_in_data_quality(
    tmp_path: Path,
) -> None:
    contract = spec_value()["measurement_contract"]
    assert isinstance(contract, dict)
    contract["sources"]["panel"]["source_kind"] = "custom_export"  # type: ignore[index]
    contract["sources"]["panel"]["sampling_rate"] = 0.25  # type: ignore[index]
    plan_path, plan = prepare_plan(tmp_path, measurement_contract=contract)
    panel = write_text(tmp_path / "panel.csv", panel_for_plan(plan))
    artifact = write_json(tmp_path / "artifact.json", artifact_value(plan))
    result = analyze_experiment(plan_path, panel, artifact)
    validate_experiment_report(result, plan)
    result["data_quality"]["issues"] = []
    result["data_quality"]["passed"] = True

    with pytest.raises(ExperimentError, match=r"measurement_contract\.issues.*data_quality"):
        validate_experiment_report(result, plan)


def test_report_validator_requires_exact_methodology_boundaries(tmp_path: Path) -> None:
    plan_path, plan, panel, artifact = prepare_analysis_inputs(tmp_path)
    result = analyze_experiment(plan_path, panel, artifact)
    result["methodology"]["causality_boundary"] = "Claims are allowed."

    with pytest.raises(ExperimentError, match="methodology 边界无效"):
        validate_experiment_report(result, plan)
