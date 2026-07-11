from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import runtime.state_manager as state_manager
from runtime.experiment import analyze_experiment, plan_experiment

from runtime.state_manager import (
    GENESIS_HASH,
    StateError,
    append_change,
    append_review,
    create_detectability_evidence,
    initialize_project,
    main,
    render_markdown,
    validate_state,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime" / "state_manager.py"


def initialize(root: Path) -> dict:
    return initialize_project(
        root,
        project_id="vibio-demo",
        site_url="https://example.com/",
        market="DE",
        language="de-DE",
    )


def advance_to_outcome_pending(
    root: Path,
    change_id: str = "change-001",
    experiment_binding: dict[str, Any] | None = None,
) -> None:
    planned: dict[str, object] = {
        "change_id": change_id,
        "status": "planned",
        "summary": "修复 canonical",
    }
    if experiment_binding is not None:
        plan_relative = experiment_binding["experiment_plan"]
        plan_path = root / plan_relative
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        planned["experiment_registration"] = {
            "experiment_id": plan["experiment_id"],
            "plan": plan_relative,
            "plan_file_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            "plan_hash": plan["plan_hash"],
        }
    append_change(root, planned)
    append_change(root, {"change_id": change_id, "status": "implemented"})
    append_change(
        root,
        {
            "change_id": change_id,
            "status": "artifact_verified",
            "artifact_verification": {"passed": True, "evidence": "渲染 HTML 与 HTTP 响应已复测"},
        },
    )
    append_change(root, {"change_id": change_id, "status": "outcome_pending"})


def write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def canonical_sha256(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def write_experiment_result(
    root: Path,
    experiment_id: str,
    *,
    incremental_positive_allowed: bool,
    with_guardrail: bool = False,
    heterogeneous: bool = False,
    mde_value: float = 1,
    mde_scale: str = "absolute",
) -> dict[str, Any]:
    plan_relative = f".vibio/experiments/{experiment_id}/plan.json"
    relative = f".vibio/experiments/{experiment_id}/result.json"
    experiment_dir = root / ".vibio" / "experiments" / experiment_id
    spec = {
        "experiment_id": experiment_id,
        "design": "randomized_page_holdout",
        "unit_id_column": "page",
        "primary_metric": "organic_clicks",
        "primary_metric_direction": "increase",
        "guardrails": (
            [
                {
                    "metric": "conversion_rate",
                    "direction": "non_decrease",
                    "threshold": 0.01,
                }
            ]
            if with_guardrail
            else []
        ),
        "seed": 20260711,
        "treatment_fraction": 0.5,
        "baseline_start": "2025-01-01",
        "baseline_end": "2025-01-01",
        "observation_start": "2025-02-01",
        "observation_end": "2025-02-01",
        "minimum_detectable_effect": {"value": mde_value, "scale": mde_scale},
        "alpha": 0.05,
        "measurement_contract": {
            "analysis_timezone": "UTC",
            "temporal_grain": "date",
            "source_timezones": {"panel": "UTC"},
            "sources": {
                "panel": {
                    "source_kind": "derived_experiment_panel",
                    "metrics": [
                        "organic_clicks",
                        *(["conversion_rate"] if with_guardrail else []),
                    ],
                    "data_as_of": "2025-02-02",
                    "finality": "final",
                    "row_limit_hit": False,
                    "pagination_complete": True,
                    "data_quality": "complete",
                }
            },
        },
    }
    spec_path = write_json(experiment_dir / "spec.json", spec)
    baseline_header = "page,organic_clicks"
    baseline_suffix = "" if not with_guardrail else ",conversion_rate"
    baseline_rows = [
        f"{unit},10{'' if not with_guardrail else ',0.20'}"
        for unit in ("/a", "/b", "/c", "/d")
    ]
    baseline_path = experiment_dir / "baseline.csv"
    baseline_path.write_text(
        baseline_header + baseline_suffix + "\n" + "\n".join(baseline_rows) + "\n",
        encoding="utf-8",
    )
    plan = plan_experiment(spec_path, baseline_path, experiment_dir)
    plan_path = root / plan_relative

    metrics = "organic_clicks" + (",conversion_rate" if with_guardrail else "")
    panel_lines = [f"page,date,group,{metrics},contaminated,treatment_applied"]
    group_positions = {"treatment": 0, "control": 0}
    for assignment in plan["assignments"]:
        unit = assignment["unit_id"]
        group = assignment["group"]
        baseline_values = "10" + (",0.20" if with_guardrail else "")
        panel_lines.append(
            f"{unit},2025-01-01,{group},{baseline_values},false,false"
        )
        if heterogeneous:
            current_clicks = 10 + 2 * group_positions[group]
            group_positions[group] += 1
        elif incremental_positive_allowed:
            current_clicks = 14 if group == "treatment" else 11
        else:
            current_clicks = 11
        current_values = str(current_clicks) + (",0.20" if with_guardrail else "")
        applied = "true" if group == "treatment" else "false"
        panel_lines.append(
            f"{unit},2025-02-01,{group},{current_values},false,{applied}"
        )
    panel_path = experiment_dir / "panel.csv"
    panel_path.write_text("\n".join(panel_lines) + "\n", encoding="utf-8")
    artifact_path = write_json(
        experiment_dir / "artifact.json",
        {
            "experiment_id": experiment_id,
            "plan_hash": plan["plan_hash"],
            "passed": True,
            "evidence": "seo_inspect before/after",
        },
    )
    result = analyze_experiment(plan_path, panel_path, artifact_path)
    result_path = write_json(root / relative, result)
    return {
        "experiment_result": relative,
        "experiment_result_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
        "experiment_plan": plan_relative,
        "experiment_inputs": {
            "panel": {
                "path": panel_path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(panel_path.read_bytes()).hexdigest(),
            },
            "artifact_report": {
                "path": artifact_path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            },
        },
    }


def test_init_creates_structured_sources_and_refuses_overwrite(tmp_path: Path) -> None:
    project = initialize(tmp_path)
    state = tmp_path / ".vibio" / "state"

    assert project["project_id"] == "vibio-demo"
    assert json.loads((state / "project.json").read_text(encoding="utf-8"))["site_url"] == "https://example.com/"
    assert (state / "changes.jsonl").read_text(encoding="utf-8") == ""
    assert (state / "reviews.jsonl").read_text(encoding="utf-8") == ""
    integrity = validate_state(tmp_path)["integrity"]
    assert len(integrity.pop("project_sha256")) == 64
    assert integrity == {
        "changes_records": 0,
        "reviews_records": 0,
        "changes_head": GENESIS_HASH,
        "reviews_head": GENESIS_HASH,
    }
    with pytest.raises(StateError, match="拒绝覆盖"):
        initialize(tmp_path)


def test_append_change_and_review_form_hash_chains_and_render(tmp_path: Path) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "experiment-001", incremental_positive_allowed=True
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    review = append_review(
        tmp_path,
        {
            "review_id": "review-001",
            "change_id": "change-001",
            "verdict": "incremental-positive",
            "experiment_id": "experiment-001",
            **binding,
            "counterfactual_method": "匹配页面 treatment/control 差异中的差异",
            "measurement_integrity": {
                "status": "complete",
                "issues": [],
                "evidence": binding["experiment_result"],
            },
        },
    )
    report = validate_state(tmp_path)

    assert report["change_states"]["change-001"] == "reviewed"
    assert report["changes"][0]["previous_hash"] == GENESIS_HASH
    assert report["changes"][1]["previous_hash"] == report["changes"][0]["record_hash"]
    assert review["previous_hash"] == GENESIS_HASH
    assert report["integrity"]["changes_records"] == 4
    markdown = render_markdown(tmp_path)
    assert "结构化真源派生" in markdown
    assert "`reviewed`" in markdown
    assert "incremental-positive" in markdown


def test_hash_tamper_is_detected_instead_of_silently_accepted(tmp_path: Path) -> None:
    initialize(tmp_path)
    append_change(tmp_path, {"change_id": "change-001", "status": "planned", "summary": "原始值"})
    path = tmp_path / ".vibio" / "state" / "changes.jsonl"
    path.write_text(path.read_text(encoding="utf-8").replace("原始值", "篡改值"), encoding="utf-8")

    with pytest.raises(StateError, match="record_hash 不匹配"):
        validate_state(tmp_path)


def test_project_identity_is_bound_to_anchor_and_every_chain_record(tmp_path: Path) -> None:
    initialize(tmp_path)
    append_change(tmp_path, {"change_id": "c-1", "status": "planned"})
    state = tmp_path / ".vibio" / "state"
    project_path = state / "project.json"
    project = json.loads(project_path.read_text(encoding="utf-8"))
    project["site_url"] = "https://other.example/"
    project_path.write_text(
        json.dumps(project, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (state / "project.sha256").write_text(canonical_sha256(project) + "\n", encoding="ascii")

    with pytest.raises(StateError, match="未绑定当前 project.json"):
        validate_state(tmp_path)


def test_concurrent_cli_appends_are_serialized_without_duplicate_sequence(tmp_path: Path) -> None:
    project = tmp_path / "site"
    project.mkdir()
    initialize(project)
    inputs = [
        write_json(tmp_path / f"change-{index}.json", {"change_id": f"c-{index}", "status": "planned"})
        for index in (1, 2)
    ]
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                str(SCRIPT),
                "append-change",
                "--project-root",
                str(project),
                "--input",
                str(path),
            ],
            cwd="/tmp",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for path in inputs
    ]
    completed = [process.communicate(timeout=15) + (process.returncode,) for process in processes]

    assert all(returncode == 0 for _, _, returncode in completed), completed
    report = validate_state(project)
    assert [record["sequence"] for record in report["changes"]] == [1, 2]
    assert report["changes"][1]["previous_hash"] == report["changes"][0]["record_hash"]


@pytest.mark.parametrize(
    "events",
    [
        [{"change_id": "c-1", "status": "implemented"}],
        [
            {"change_id": "c-1", "status": "planned"},
            {
                "change_id": "c-1",
                "status": "artifact_verified",
                "artifact_verification": {"passed": True, "evidence": "HTML 通过"},
            },
        ],
        [
            {"change_id": "c-1", "status": "planned"},
            {"change_id": "c-1", "status": "implemented"},
            {"change_id": "c-1", "status": "outcome_pending"},
        ],
    ],
)
def test_illegal_state_transitions_are_rejected(tmp_path: Path, events: list[dict]) -> None:
    initialize(tmp_path)
    with pytest.raises(StateError, match="首条状态必须|illegal|非法状态转移"):
        for event in events:
            append_change(tmp_path, event)


def test_artifact_statuses_have_semantic_gates(tmp_path: Path) -> None:
    initialize(tmp_path)
    append_change(tmp_path, {"change_id": "c-1", "status": "planned"})
    append_change(tmp_path, {"change_id": "c-1", "status": "implemented"})

    with pytest.raises(StateError, match="artifact_verified"):
        append_change(tmp_path, {"change_id": "c-1", "status": "artifact_verified"})
    with pytest.raises(StateError, match="passed=false"):
        append_change(
            tmp_path,
            {
                "change_id": "c-1",
                "status": "implementation_failed",
                "artifact_verification": {"passed": True, "evidence": "已通过"},
            },
        )
    failed = append_change(
        tmp_path,
        {
            "change_id": "c-1",
            "status": "implementation_failed",
            "artifact_verification": {"passed": False, "evidence": "生产 HTML 仍为 noindex"},
        },
    )
    assert failed["status"] == "implementation_failed"


def test_review_must_reference_existing_change(tmp_path: Path) -> None:
    initialize(tmp_path)
    with pytest.raises(StateError, match="不存在的 change"):
        append_review(
            tmp_path,
            {"review_id": "r-1", "change_id": "missing", "verdict": "inconclusive"},
        )


def test_incremental_positive_requires_experiment_and_counterfactual(tmp_path: Path) -> None:
    initialize(tmp_path)
    advance_to_outcome_pending(tmp_path)
    with pytest.raises(StateError, match="experiment_id"):
        append_review(
            tmp_path,
            {
                "review_id": "r-1",
                "change_id": "change-001",
                "verdict": "incremental-positive",
                "counterfactual_method": "matched control",
            },
        )
    with pytest.raises(StateError, match="counterfactual_method"):
        append_review(
            tmp_path,
            {
                "review_id": "r-1",
                "change_id": "change-001",
                "verdict": "incremental-positive",
                "experiment_id": "exp-1",
            },
        )


@pytest.mark.parametrize(
    "measurement_integrity",
    [
        None,
        {"status": "inconclusive", "issues": ["row_limit_hit"], "evidence": "result.json"},
        {"status": "complete", "issues": ["pagination_incomplete"], "evidence": "result.json"},
        {"status": "complete", "issues": [], "evidence": ""},
    ],
)
def test_strong_verdicts_require_complete_measurement_integrity(
    tmp_path: Path, measurement_integrity: object
) -> None:
    initialize(tmp_path)
    advance_to_outcome_pending(tmp_path)
    payload = {
        "review_id": "r-integrity",
        "change_id": "change-001",
        "verdict": "incremental-positive",
        "experiment_id": "exp-integrity",
        "counterfactual_method": "randomized holdout",
    }
    if measurement_integrity is not None:
        payload["measurement_integrity"] = measurement_integrity

    with pytest.raises(StateError, match="measurement_integrity"):
        append_review(tmp_path, payload)


def test_incremental_positive_requires_bound_favorable_experiment_result(
    tmp_path: Path,
) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "exp-negative", incremental_positive_allowed=False
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    payload = {
        "review_id": "r-negative",
        "change_id": "change-001",
        "verdict": "incremental-positive",
        "experiment_id": "exp-negative",
        **binding,
        "counterfactual_method": "randomized page holdout",
        "measurement_integrity": {
            "status": "complete",
            "issues": [],
            "evidence": binding["experiment_result"],
        },
    }

    with pytest.raises(StateError, match="效果方向或区间"):
        append_review(tmp_path, payload)

    payload["experiment_result"] = ".vibio/experiments/missing/result.json"
    payload["measurement_integrity"]["evidence"] = payload["experiment_result"]
    with pytest.raises(StateError, match="文件不存在"):
        append_review(tmp_path, payload)


def test_strong_verdict_requires_plan_registration_in_planned_event(tmp_path: Path) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "exp-unregistered", incremental_positive_allowed=True
    )
    advance_to_outcome_pending(tmp_path)

    with pytest.raises(StateError, match="planned.*experiment_registration"):
        append_review(
            tmp_path,
            {
                "review_id": "r-unregistered",
                "change_id": "change-001",
                "verdict": "incremental-positive",
                "experiment_id": "exp-unregistered",
                **binding,
                "counterfactual_method": "randomized page holdout",
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )


def test_registered_plan_mutation_breaks_state_validation(tmp_path: Path) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "exp-plan-bound", incremental_positive_allowed=True
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    plan_path = tmp_path / binding["experiment_plan"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["experiment_id"] = "changed-after-registration"
    write_json(plan_path, plan)

    with pytest.raises(StateError, match="plan 文件已变化"):
        validate_state(tmp_path)


def test_strong_verdict_guardrails_must_match_registered_plan(tmp_path: Path) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path,
        "exp-guardrail",
        incremental_positive_allowed=True,
        with_guardrail=True,
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    result_path = tmp_path / binding["experiment_result"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["guardrails"] = {"passed": True, "results": []}
    write_json(result_path, result)
    binding["experiment_result_sha256"] = hashlib.sha256(
        result_path.read_bytes()
    ).hexdigest()

    with pytest.raises(StateError, match="guardrails 未完整绑定"):
        append_review(
            tmp_path,
            {
                "review_id": "r-guardrail",
                "change_id": "change-001",
                "verdict": "incremental-positive",
                "experiment_id": "exp-guardrail",
                **binding,
                "counterfactual_method": "randomized page holdout",
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )


def test_strong_verdict_rejects_guardrail_did_tampering(tmp_path: Path) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path,
        "exp-guardrail-did",
        incremental_positive_allowed=True,
        with_guardrail=True,
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    result_path = tmp_path / binding["experiment_result"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["metrics"]["conversion_rate"]["difference_in_differences"] = -0.5
    result["guardrails"]["results"][0]["difference_in_differences"] = -0.5
    result["guardrails"]["results"][0]["passed"] = True
    write_json(result_path, result)
    binding["experiment_result_sha256"] = hashlib.sha256(
        result_path.read_bytes()
    ).hexdigest()

    with pytest.raises(StateError, match="DID.*arms|guardrail.passed.*DID"):
        append_review(
            tmp_path,
            {
                "review_id": "r-guardrail-did",
                "change_id": "change-001",
                "verdict": "incremental-positive",
                "experiment_id": "exp-guardrail-did",
                **binding,
                "counterfactual_method": "randomized page holdout",
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )


def test_strong_verdict_requires_bound_raw_experiment_inputs(tmp_path: Path) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "exp-raw-inputs", incremental_positive_allowed=True
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    binding.pop("experiment_inputs")

    with pytest.raises(StateError, match="experiment_inputs"):
        append_review(
            tmp_path,
            {
                "review_id": "r-raw-inputs",
                "change_id": "change-001",
                "verdict": "incremental-positive",
                "experiment_id": "exp-raw-inputs",
                **binding,
                "counterfactual_method": "randomized page holdout",
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )


def test_strong_verdict_rejects_changed_bound_panel(tmp_path: Path) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "exp-panel-hash", incremental_positive_allowed=True
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    panel_path = tmp_path / binding["experiment_inputs"]["panel"]["path"]
    panel_path.write_text(
        panel_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )

    with pytest.raises(StateError, match=r"experiment_inputs\.panel.*摘要不匹配"):
        append_review(
            tmp_path,
            {
                "review_id": "r-panel-hash",
                "change_id": "change-001",
                "verdict": "incremental-positive",
                "experiment_id": "exp-panel-hash",
                **binding,
                "counterfactual_method": "randomized page holdout",
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )


def test_strong_verdict_replays_inputs_against_self_consistent_result(
    tmp_path: Path,
) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "exp-replay", incremental_positive_allowed=True
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    panel_path = tmp_path / binding["experiment_inputs"]["panel"]["path"]
    forged_lines: list[str] = []
    for line in panel_path.read_text(encoding="utf-8").splitlines():
        values = line.split(",")
        if len(values) > 3 and values[1] == "2025-02-01" and values[2] == "treatment":
            values[3] = "999"
        forged_lines.append(",".join(values))
    forged_panel = panel_path.with_name("forged-panel.csv")
    forged_panel.write_text("\n".join(forged_lines) + "\n", encoding="utf-8")
    plan_path = tmp_path / binding["experiment_plan"]
    artifact_path = tmp_path / binding["experiment_inputs"]["artifact_report"]["path"]
    forged_result = analyze_experiment(plan_path, forged_panel, artifact_path)
    result_path = tmp_path / binding["experiment_result"]
    write_json(result_path, forged_result)
    binding["experiment_result_sha256"] = hashlib.sha256(
        result_path.read_bytes()
    ).hexdigest()

    with pytest.raises(StateError, match="实验重放结果与提交报告不匹配"):
        append_review(
            tmp_path,
            {
                "review_id": "r-replay",
                "change_id": "change-001",
                "verdict": "incremental-positive",
                "experiment_id": "exp-replay",
                **binding,
                "counterfactual_method": "randomized page holdout",
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )


@pytest.mark.parametrize(
    ("section", "field", "replacement"),
    [
        ("methodology", "power_calculated", 0),
        ("artifact_verification", "passed", 1),
    ],
)
def test_experiment_replay_distinguishes_json_booleans_from_numbers(
    tmp_path: Path,
    section: str,
    field: str,
    replacement: int,
) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "json-type-replay", incremental_positive_allowed=True
    )
    result_path = tmp_path / binding["experiment_result"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    original = result[section][field]
    assert isinstance(original, bool)
    assert original == replacement
    assert type(original) is not type(replacement)
    result[section][field] = replacement

    with pytest.raises(
        StateError,
        match=rf"实验重放结果与提交报告不匹配：.*{section}",
    ):
        state_manager._replay_experiment_result(tmp_path, binding, result)


def test_no_detectable_change_requires_preregistered_mde_and_detectability(tmp_path: Path) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "no-change", incremental_positive_allowed=False
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    with pytest.raises(StateError, match="结构化 preregistered_mde"):
        append_review(
            tmp_path,
            {
                "review_id": "r-1",
                "change_id": "change-001",
                "verdict": "no-detectable-change",
                "preregistered_mde": "10% qualified clicks",
                "detectability_evidence": "power=0.8",
            },
        )
    with pytest.raises(StateError, match="detectability_evidence"):
        append_review(
            tmp_path,
            {
                "review_id": "r-1",
                "change_id": "change-001",
                "verdict": "no-detectable-change",
                "preregistered_mde": {"value": 1, "scale": "absolute"},
            },
        )
    detectability_relative = ".vibio/experiments/no-change/detectability.json"
    _, detectability_path = create_detectability_evidence(
        tmp_path,
        experiment_plan=binding["experiment_plan"],
        experiment_result=binding["experiment_result"],
        out=detectability_relative,
    )
    with pytest.raises(StateError, match="preregistered_mde.*严格一致"):
        append_review(
            tmp_path,
            {
                "review_id": "r-mde-mismatch",
                "change_id": "change-001",
                "verdict": "no-detectable-change",
                "experiment_id": "no-change",
                **binding,
                "preregistered_mde": {"value": 2, "scale": "absolute"},
                "detectability_evidence": detectability_relative,
                "detectability_evidence_sha256": hashlib.sha256(
                    detectability_path.read_bytes()
                ).hexdigest(),
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )
    record = append_review(
        tmp_path,
        {
            "review_id": "r-1",
            "change_id": "change-001",
            "verdict": "no-detectable-change",
            "experiment_id": "no-change",
            **binding,
            "preregistered_mde": {"value": 1, "scale": "absolute"},
            "detectability_evidence": detectability_relative,
            "detectability_evidence_sha256": hashlib.sha256(detectability_path.read_bytes()).hexdigest(),
            "measurement_integrity": {
                "status": "complete",
                "issues": [],
                "evidence": binding["experiment_result"],
            },
        },
    )
    assert record["verdict"] == "no-detectable-change"


def test_detectability_nonzero_standard_error_and_low_power_are_enforced(
    tmp_path: Path,
) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path,
        "low-power",
        incremental_positive_allowed=False,
        heterogeneous=True,
        mde_value=2.8,
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    evidence_relative = ".vibio/experiments/low-power/detectability.json"
    evidence, evidence_path = create_detectability_evidence(
        tmp_path,
        experiment_plan=binding["experiment_plan"],
        experiment_result=binding["experiment_result"],
        out=evidence_relative,
    )

    assert evidence["standard_error"] == pytest.approx(2**0.5)
    assert evidence["power"] == pytest.approx(0.507993152829)
    assert evidence["confidence_interval"]["lower"] < 0
    assert evidence["confidence_interval"]["upper"] > 0
    assert evidence["no_detectable_change_supported"] is False

    with pytest.raises(StateError, match="power>=0.8"):
        append_review(
            tmp_path,
            {
                "review_id": "r-low-power",
                "change_id": "change-001",
                "verdict": "no-detectable-change",
                "experiment_id": "low-power",
                **binding,
                "preregistered_mde": {"value": 2.8, "scale": "absolute"},
                "detectability_evidence": evidence_relative,
                "detectability_evidence_sha256": hashlib.sha256(
                    evidence_path.read_bytes()
                ).hexdigest(),
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )


def test_detectability_relative_mde_is_converted_to_metric_units(tmp_path: Path) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path,
        "relative-mde",
        incremental_positive_allowed=False,
        mde_value=0.1,
        mde_scale="relative_to_control_baseline",
    )
    evidence, _ = create_detectability_evidence(
        tmp_path,
        experiment_plan=binding["experiment_plan"],
        experiment_result=binding["experiment_result"],
        out=".vibio/experiments/relative-mde/detectability.json",
    )

    assert evidence["minimum_detectable_effect"] == {
        "value": 0.1,
        "scale": "relative_to_control_baseline",
    }
    assert evidence["mde_in_metric_units"] == pytest.approx(1)
    assert evidence["power"] == 1


def test_no_detectable_change_rejects_confidence_interval_excluding_zero(
    tmp_path: Path,
) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "directional-result", incremental_positive_allowed=True
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    evidence_relative = ".vibio/experiments/directional-result/detectability.json"
    evidence, evidence_path = create_detectability_evidence(
        tmp_path,
        experiment_plan=binding["experiment_plan"],
        experiment_result=binding["experiment_result"],
        out=evidence_relative,
    )

    assert evidence["power"] == 1
    assert evidence["confidence_interval"]["lower"] > 0
    assert evidence["no_detectable_change_supported"] is False

    with pytest.raises(StateError, match="未支持 no-detectable-change"):
        append_review(
            tmp_path,
            {
                "review_id": "r-ci-excludes-zero",
                "change_id": "change-001",
                "verdict": "no-detectable-change",
                "experiment_id": "directional-result",
                **binding,
                "preregistered_mde": {"value": 1, "scale": "absolute"},
                "detectability_evidence": evidence_relative,
                "detectability_evidence_sha256": hashlib.sha256(
                    evidence_path.read_bytes()
                ).hexdigest(),
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )


def test_detectability_power_threshold_is_bracketed_at_point_eight() -> None:
    below = state_manager._detectability_power(2.801, 1, 0.05)
    above = state_manager._detectability_power(2.802, 1, 0.05)

    assert below < 0.8
    assert above >= 0.8


def test_legacy_self_reported_detectability_evidence_is_rejected(
    tmp_path: Path,
) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "legacy-power", incremental_positive_allowed=False
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    evidence_relative = ".vibio/experiments/legacy-power/detectability.json"
    result = json.loads(
        (tmp_path / binding["experiment_result"]).read_text(encoding="utf-8")
    )
    evidence_path = write_json(
        tmp_path / evidence_relative,
        {
            "experiment_id": "legacy-power",
            "plan_hash": result["plan_hash"],
            "power_calculated": True,
            "power": 0.99,
            "minimum_detectable_effect": {"value": 1, "scale": "absolute"},
            "no_detectable_change_supported": True,
        },
    )

    with pytest.raises(StateError, match="确定性重算不匹配"):
        append_review(
            tmp_path,
            {
                "review_id": "r-legacy-power",
                "change_id": "change-001",
                "verdict": "no-detectable-change",
                "experiment_id": "legacy-power",
                **binding,
                "preregistered_mde": {"value": 1, "scale": "absolute"},
                "detectability_evidence": evidence_relative,
                "detectability_evidence_sha256": hashlib.sha256(
                    evidence_path.read_bytes()
                ).hexdigest(),
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tool", "untrusted-power-tool"),
        ("version", "999.0.0"),
        ("power", 0.99),
        ("input_hashes.panel_sha256", "0" * 64),
    ],
)
def test_detectability_evidence_tampering_is_rejected(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "power-tamper", incremental_positive_allowed=False
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    evidence_relative = ".vibio/experiments/power-tamper/detectability.json"
    evidence, evidence_path = create_detectability_evidence(
        tmp_path,
        experiment_plan=binding["experiment_plan"],
        experiment_result=binding["experiment_result"],
        out=evidence_relative,
    )
    if "." in field:
        parent, child = field.split(".", 1)
        evidence[parent][child] = value
    else:
        evidence[field] = value
    write_json(evidence_path, evidence)

    with pytest.raises(StateError, match="确定性重算不匹配"):
        append_review(
            tmp_path,
            {
                "review_id": f"r-{field.replace('.', '-')}",
                "change_id": "change-001",
                "verdict": "no-detectable-change",
                "experiment_id": "power-tamper",
                **binding,
                "preregistered_mde": {"value": 1, "scale": "absolute"},
                "detectability_evidence": evidence_relative,
                "detectability_evidence_sha256": hashlib.sha256(
                    evidence_path.read_bytes()
                ).hexdigest(),
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )


def test_strong_verdict_rejects_extra_experiment_report_claim(
    tmp_path: Path,
) -> None:
    initialize(tmp_path)
    binding = write_experiment_result(
        tmp_path, "extra-claim", incremental_positive_allowed=True
    )
    advance_to_outcome_pending(tmp_path, experiment_binding=binding)
    result_path = tmp_path / binding["experiment_result"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["causal_business_claim"] = "This SEO change caused pipeline growth."
    write_json(result_path, result)
    binding["experiment_result_sha256"] = hashlib.sha256(
        result_path.read_bytes()
    ).hexdigest()

    with pytest.raises(
        StateError,
        match="实验报告包含额外字段|额外正式报告字段|重放结果",
    ):
        append_review(
            tmp_path,
            {
                "review_id": "r-extra-claim",
                "change_id": "change-001",
                "verdict": "incremental-positive",
                "experiment_id": "extra-claim",
                **binding,
                "counterfactual_method": "randomized page holdout",
                "measurement_integrity": {
                    "status": "complete",
                    "issues": [],
                    "evidence": binding["experiment_result"],
                },
            },
        )


def test_implementation_failed_review_requires_failed_artifact_check(tmp_path: Path) -> None:
    initialize(tmp_path)
    append_change(tmp_path, {"change_id": "c-1", "status": "planned"})
    append_change(tmp_path, {"change_id": "c-1", "status": "implemented"})
    with pytest.raises(StateError, match="passed=false"):
        append_review(
            tmp_path,
            {
                "review_id": "r-1",
                "change_id": "c-1",
                "verdict": "implementation-failed",
                "artifact_verification": {"passed": True, "evidence": "通过"},
            },
        )
    record = append_review(
        tmp_path,
        {
            "review_id": "r-1",
            "change_id": "c-1",
            "verdict": "implementation-failed",
            "artifact_verification": {"passed": False, "evidence": "部署产物未包含变更"},
        },
    )
    assert record["verdict"] == "implementation-failed"
    assert validate_state(tmp_path)["change_states"]["c-1"] == "implementation_failed"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"change_id": "c-1", "status": "planned", "owner": "seo@example.com"}, "电子邮箱"),
        ({"change_id": "c-1", "status": "planned", "phone": "+86 13800138000"}, "手机号码"),
        ({"change_id": "c-1", "status": "planned", "api_key": "placeholder"}, "凭据字段"),
        ({"change_id": "c-1", "status": "planned", "note": "sk-1234567890abcdefghijkl"}, "API token"),
    ],
)
def test_pii_and_credentials_are_refused_before_disk_write(
    tmp_path: Path, payload: dict, message: str
) -> None:
    initialize(tmp_path)
    with pytest.raises(StateError, match=message):
        append_change(tmp_path, payload)
    assert (tmp_path / ".vibio" / "state" / "changes.jsonl").read_text(encoding="utf-8") == ""


def test_integrity_hash_digits_are_not_misclassified_as_phone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initialize(tmp_path)
    digest_with_phone_digits = "13800138000" + "a" * 53
    monkeypatch.setattr(state_manager, "_record_digest", lambda _record: digest_with_phone_digits)

    append_change(
        tmp_path,
        {"change_id": "c-1", "status": "planned", "summary": "修复 canonical"},
    )

    assert validate_state(tmp_path)["changes"][0]["record_hash"] == digest_with_phone_digits
    state_manager._scan_sensitive({"changes_head": digest_with_phone_digits})
    state_manager._scan_sensitive({"reviews_head": digest_with_phone_digits})
    with pytest.raises(StateError, match="手机号码"):
        state_manager._scan_sensitive({"untrusted_head": digest_with_phone_digits})


def test_input_and_render_paths_are_guarded(tmp_path: Path) -> None:
    initialize(tmp_path)
    state_dir = tmp_path / ".vibio" / "state"
    outside = tmp_path.parent / "outside-state-render.md"
    with pytest.raises(StateError, match="项目根目录内"):
        main_result_path = str(outside)
        from runtime.state_manager import _write_rendered

        _write_rendered(tmp_path, main_result_path, "x")
    with pytest.raises(StateError, match="结构化真源"):
        from runtime.state_manager import _write_rendered

        _write_rendered(tmp_path, state_dir / "project.json", "x")
    missing = tmp_path / "missing.json"
    assert main(["append-change", "--project-root", str(tmp_path), "--input", str(missing)]) == 2


def test_cli_end_to_end_and_direct_execution_outside_repository(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd="/tmp",
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "结构化状态" in result.stdout
    assert "append-change" in result.stdout
    assert "位置参数" in result.stdout
    assert "选项" in result.stdout
    assert "show this help" not in result.stdout

    project = tmp_path / "site"
    project.mkdir()
    initialized = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "init",
            "--project-root",
            str(project),
            "--project-id",
            "cli-demo",
            "--site-url",
            "https://example.com/",
            "--market",
            "CN",
            "--language",
            "zh-CN",
        ],
        cwd="/tmp",
        check=False,
        capture_output=True,
        text=True,
    )
    assert initialized.returncode == 0, initialized.stderr
    change = write_json(tmp_path / "change.json", {"change_id": "c-1", "status": "planned"})
    appended = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "append-change",
            "--project-root",
            str(project),
            "--input",
            str(change),
        ],
        cwd="/tmp",
        check=False,
        capture_output=True,
        text=True,
    )
    assert appended.returncode == 0, appended.stderr
    rendered = subprocess.run(
        [sys.executable, str(SCRIPT), "render", "--project-root", str(project)],
        cwd="/tmp",
        check=False,
        capture_output=True,
        text=True,
    )
    assert rendered.returncode == 0, rendered.stderr
    assert "# cli-demo" in rendered.stdout
    assert "`planned`" in rendered.stdout

    render_file = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "render",
            "--project-root",
            str(project),
            "--out",
            "reports/state.md",
        ],
        cwd="/tmp",
        check=False,
        capture_output=True,
        text=True,
    )
    assert render_file.returncode == 0, render_file.stderr
    assert (project / "reports" / "state.md").read_text(encoding="utf-8").startswith("# cli-demo")


def test_cli_missing_arguments_are_reported_in_chinese(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["init"])

    assert exc.value.code == 2
    stderr = capsys.readouterr().err
    assert "缺少必需参数" in stderr
    assert "the following arguments" not in stderr


def test_cli_unknown_command_is_reported_in_chinese(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["unknown-command"])

    assert exc.value.code == 2
    stderr = capsys.readouterr().err
    assert "取值无效" in stderr
    assert "invalid choice" not in stderr
    assert "argument " not in stderr
