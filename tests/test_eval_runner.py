from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.eval_runner import (
    DEFAULT_RESPONSES,
    ROOT,
    classify_route,
    evaluate_assertion,
    load_contract_fixture,
    render_human,
    run_suite,
    strict_failure_reasons,
    validate_contract_output,
)


def write_fixture(tmp_path: Path, mutate) -> Path:
    data = json.loads((ROOT / DEFAULT_RESPONSES).read_text(encoding="utf-8"))
    mutate(data)
    fixture = tmp_path / "responses.json"
    fixture.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return fixture


def indexing_assertion() -> dict:
    return {
        "type": "citation_coverage",
        "target": "output.claims",
        "expected": {
            "claim_ids": ["indexing-api"],
            "official_domains": ["developers.google.com", "support.google.com"],
            "min_ratio": 1.0,
        },
    }


def test_full_suite_is_labeled_as_authored_offline_contract_regression() -> None:
    report = run_suite(ROOT)
    summary = report["summary"]

    assert report["evaluation_kind"] == "offline_contract_regression"
    assert report["scope"] == {
        "executes_skill": False,
        "invokes_model": False,
        "tests_runtime_triggering": False,
        "measures_seo_outcomes": False,
        "note": "手写静态示例的离线合同回归；不是 Skill 效果、触发率或 SEO 结果评测。",
    }
    assert report["fixture"]["fixture_kind"] == "authored_contract_examples"
    assert report["fixture"]["provenance"]["independent"] is False
    assert report["fixture"]["provenance"]["generated_by_skill"] is False
    assert summary["cases"] >= 41
    assert summary["hard_failures"] == 0
    assert summary["contract_weighted_pass_rate"] == 1.0
    assert summary["fixture_response_cases"] == summary["response_required_cases"]
    assert summary["missing_response_cases"] == 0
    assert "routing_macro_accuracy" not in summary
    assert "baseline_comparison" not in report


def test_human_report_does_not_claim_skill_accuracy_or_baseline_gain() -> None:
    text = render_human(run_suite(ROOT))

    assert text.startswith("Vibio SEO 离线合同回归")
    assert "非实际 Skill 触发" in text
    assert "macro accuracy" not in text
    assert "候选输出" not in text
    assert "基线" not in text
    assert "+81.7" not in text


def test_missing_authored_response_is_a_hard_failure(tmp_path: Path) -> None:
    fixture = write_fixture(tmp_path, lambda data: data["responses"].pop("vibio-seo:6"))

    report = run_suite(ROOT, fixture)

    assert report["summary"]["missing_response_cases"] == 1
    failures = [item for item in report["failures"] if item["case_key"] == "vibio-seo:6"]
    assert failures
    assert all(item["hard_gate"] for item in failures)
    assert all("authored contract response fixture is missing" in item["detail"] for item in failures)


def test_empty_authored_response_is_rejected_by_fixture_schema(tmp_path: Path) -> None:
    fixture = write_fixture(tmp_path, lambda data: data["responses"].update({"vibio-seo:1": ""}))

    with pytest.raises(ValueError, match="not valid under any of the given schemas"):
        run_suite(ROOT, fixture)


def test_keyword_stuffed_response_becomes_a_hard_contract_failure(tmp_path: Path) -> None:
    stuffing = "SEO SEO SEO SEO SEO SEO SEO SEO SEO SEO audit ranking backlink"
    fixture = write_fixture(
        tmp_path,
        lambda data: data["responses"].update({"vibio-seo:1": stuffing}),
    )

    report = run_suite(ROOT, fixture)
    failures = [
        item
        for item in report["failures"]
        if item["case_key"] == "vibio-seo:1" and item["assertion_id"] == "fixture-output-sanity"
    ]

    assert len(failures) == 1
    assert failures[0]["hard_gate"] is True
    assert "keyword stuffing" in failures[0]["detail"]


def test_fixture_provenance_cannot_claim_independence(tmp_path: Path) -> None:
    fixture = write_fixture(tmp_path, lambda data: data["provenance"].update({"independent": True}))

    with pytest.raises(ValueError, match="False was expected"):
        load_contract_fixture(ROOT, fixture)


def test_citation_coverage_accepts_saved_claim_specific_official_evidence() -> None:
    fixture = load_contract_fixture(ROOT, None)
    response = fixture.responses["vibio-seo:6"]

    passed, detail, _ = evaluate_assertion(
        indexing_assertion(), {}, ROOT / "vibio", "", response, fixture.sources
    )

    assert passed is True, detail


def test_official_domain_url_alone_does_not_count_as_evidence() -> None:
    response = {
        "claims": [
            {
                "id": "indexing-api",
                "text": "The Indexing API is limited to specific page types.",
                "source_url": "https://developers.google.com/search/apis/indexing-api/v3/using-api",
            }
        ]
    }

    passed, detail, _ = evaluate_assertion(
        indexing_assertion(), {}, ROOT / "vibio", "", response, {}
    )

    assert passed is False
    assert "source_id/source_ids is missing" in detail


def test_same_domain_404_snapshot_does_not_count_as_evidence() -> None:
    fixture = load_contract_fixture(ROOT, None)
    sources = copy.deepcopy(fixture.sources)
    sources["google-indexing-api"]["snapshot"]["http_status"] = 404
    response = fixture.responses["vibio-seo:6"]

    passed, detail, _ = evaluate_assertion(
        indexing_assertion(), {}, ROOT / "vibio", "", response, sources
    )

    assert passed is False
    assert "successful HTTP status" in detail


def test_snapshot_without_excerpt_does_not_count_as_evidence() -> None:
    fixture = load_contract_fixture(ROOT, None)
    sources = copy.deepcopy(fixture.sources)
    sources["google-indexing-api"]["snapshot"]["excerpt"] = ""
    response = fixture.responses["vibio-seo:6"]

    passed, detail, _ = evaluate_assertion(
        indexing_assertion(), {}, ROOT / "vibio", "", response, sources
    )

    assert passed is False
    assert "snapshot excerpt is missing" in detail


def test_wrong_source_id_does_not_count_as_evidence() -> None:
    fixture = load_contract_fixture(ROOT, None)
    response = copy.deepcopy(fixture.responses["vibio-seo:6"])
    response["claims"][1]["source_id"] = "nonexistent-source"

    passed, detail, _ = evaluate_assertion(
        indexing_assertion(), {}, ROOT / "vibio", "", response, fixture.sources
    )

    assert passed is False
    assert "absent from the evidence registry" in detail


def test_numeric_claims_require_claim_specific_snapshot_support() -> None:
    assertion = {
        "type": "numeric_claims_have_source",
        "target": "output.claims",
        "expected": {"min_numeric_claims": 1},
    }
    fixture = load_contract_fixture(ROOT, None)
    valid_claim = fixture.responses["vibio-content:1"]["claims"][0]

    valid, valid_detail, _ = evaluate_assertion(
        assertion,
        {},
        ROOT / "vibio-content",
        "",
        {"claims": [valid_claim]},
        fixture.sources,
    )
    invalid, invalid_detail, _ = evaluate_assertion(
        assertion,
        {},
        ROOT / "vibio-content",
        "",
        {
            "claims": [
                {
                    "id": "ctr",
                    "text": "CTR is 7.2%.",
                    "numeric": True,
                    "numeric_value": 7.2,
                    "source_id": "fixture-material-datasheet",
                }
            ]
        },
        fixture.sources,
    )

    assert valid is True, valid_detail
    assert invalid is False
    assert "has no support record for claim 'ctr'" in invalid_detail


@pytest.mark.parametrize("empty", [None, "", "   ", {}, []])
def test_empty_outputs_are_rejected(empty) -> None:
    passed, detail = validate_contract_output(empty)

    assert passed is False
    assert "empty" in detail


def test_repeated_keyword_stuffing_is_rejected() -> None:
    passed, detail = validate_contract_output(
        "SEO SEO SEO SEO SEO SEO SEO SEO SEO SEO audit ranking backlink"
    )

    assert passed is False
    assert "keyword stuffing" in detail


def test_normal_concise_output_is_not_rejected_as_keyword_stuffing() -> None:
    passed, detail = validate_contract_output(
        "先验证页面是否可抓取与可索引，再观察目标 SERP 意图；缺失数据保持 unknown。"
    )

    assert passed is True, detail


def test_routing_helper_is_only_a_deterministic_boundary_heuristic() -> None:
    assert classify_route("什么是 SEO？给实习生解释一下。 ")["skill"] == "NONE"
    assert classify_route("帮我给 Google Ads 新建 Campaign，分广告组、定预算和出价。 ")["skill"] == "NONE"
    assert classify_route("把每天整理客服工单的流程做成一个 skill。 ")["skill"] == "skill-creator"
    assert classify_route("把 Google Ads 搜索词报告用于 SEO，验证买家用语。 ")["skill"] == "vibio-keyword"
    assert classify_route("优化 vibio-audit 这个 skill 的触发边界。 ")["skill"] == "vibio-factory"


def test_strict_mode_enforces_soft_contract_threshold_when_soft_assertions_exist() -> None:
    report = {
        "summary": {
            "hard_failures": 0,
            "missing_response_cases": 0,
            "soft_contract_weighted_pass_rate": 0.89,
        }
    }

    assert strict_failure_reasons(report, min_soft_contract_rate=0.90) == [
        "soft contract rate 0.890 is below the minimum 0.900"
    ]
    report["summary"]["soft_contract_weighted_pass_rate"] = None
    assert strict_failure_reasons(report, min_soft_contract_rate=0.90) == []


def test_strict_mode_rejects_invalid_soft_contract_threshold() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        strict_failure_reasons(
            {
                "summary": {
                    "hard_failures": 0,
                    "missing_response_cases": 0,
                    "soft_contract_weighted_pass_rate": None,
                }
            },
            min_soft_contract_rate=1.1,
        )
