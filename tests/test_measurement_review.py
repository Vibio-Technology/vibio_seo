from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from runtime.measurement_review import ReviewError, main


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime/measurement_review.py"
SCHEMA = ROOT / "schemas/measurement_review.report.schema.json"


def write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def schema_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def config(tmp_path: Path) -> Path:
    value = {
        "windows": {
            "baseline": {"start": "2026-05-01", "end": "2026-05-31"},
            "current": {"start": "2026-06-01", "end": "2026-06-30"},
        },
        "timezone": "Europe/Berlin",
        "source_timezones": {
            "gsc_page": "America/Los_Angeles",
            "ga4": "America/Los_Angeles",
            "crm": "America/Los_Angeles",
        },
        "source_metadata": {
            "gsc_page": {
                "source_kind": "gsc_search_analytics",
                "data_as_of": "2026-07-05T12:00:00Z",
                "finality": "final",
                "row_limit_hit": False,
                "pagination_complete": True,
                "data_quality": "complete",
            },
            "ga4": {
                "source_kind": "ga4_property_report",
                "data_as_of": "2026-07-05T12:00:00Z",
                "finality": "final",
                "row_limit_hit": False,
                "pagination_complete": True,
                "sampling_rate": 1,
                "thresholding_applied": False,
                "data_quality": "complete",
                "attribution_model": "data_driven",
            },
            "crm": {
                "source_kind": "crm_aggregate_export",
                "data_as_of": "2026-07-05T12:00:00Z",
                "finality": "final",
                "row_limit_hit": False,
                "pagination_complete": True,
                "data_quality": "complete",
                "attribution_model": "first_organic_landing_cohort",
            },
        },
        "property": "sc-domain:example.com",
        "search_type": "web",
        "dimension_mapping": {
            "gsc_page": {
                "date": "Date",
                "landing_page": "Page",
                "country": "Country",
                "device": "Device",
            },
            "ga4": {
                "date": "Date",
                "landing_page": "Landing page",
                "country": "Country",
                "device": "Device",
            },
            "crm": {
                "date": "Date",
                "landing_page": "Landing page",
                "country": "Country",
            },
        },
        "metric_mapping": {
            "crm": {
                "leads": "Leads",
                "qualified": "Qualified",
                "pipeline_value": "Pipeline value",
            }
        },
        "value_mapping": {
            "country": {"DEU": "de", "Germany": "de"},
            "device": {"DESKTOP": "desktop", "desktop": "desktop"},
        },
        "url_normalization": {
            "base_url": "https://example.com/",
            "force_https": True,
            "strip_query": True,
            "strip_fragment": True,
            "lowercase_host": True,
            "trailing_slash": "remove",
            "mappings": {"/old-product/": "/product/"},
        },
        "crm_definition": {
            "stage": "sales accepted",
            "qualified": "meets ICP and product need",
        },
    }
    path = tmp_path / "mapping.json"
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def datasets(tmp_path: Path) -> tuple[Path, Path, Path]:
    gsc = write(
        tmp_path / "gsc.csv",
        "Date,Page,Country,Device,Clicks,Impressions\n"
        "2026-05-10,https://example.com/product/?utm_source=x,DEU,DESKTOP,10,100\n"
        "2026-06-10,https://example.com/product/,DEU,DESKTOP,15,150\n",
    )
    ga4 = write(
        tmp_path / "ga4.csv",
        "Date,Landing page,Country,Device,Sessions,Conversions\n"
        "2026-05-10,/old-product/,Germany,desktop,8,1\n"
        "2026-06-10,/product/,Germany,desktop,12,2\n"
        "2026-06-11,/unmapped/,Germany,desktop,3,\n",
    )
    crm = write(
        tmp_path / "crm.csv",
        "Date,Landing page,Country,Leads,Qualified,Pipeline value\n"
        "2026-05-10,/product/,Germany,2,1,1000\n"
        "2026-06-10,/product/,Germany,3,2,2400\n",
    )
    return gsc, ga4, crm


def test_measurement_review_keeps_shared_grain_and_directional_boundary(tmp_path: Path) -> None:
    gsc, ga4, crm = datasets(tmp_path)
    output = tmp_path / "report.json"

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--ga4",
            str(ga4),
            "--crm",
            str(crm),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "report.md"),
        ]
    )

    assert result == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["contract"]["query_columns_allowed"] is False
    assert report["contract"]["user_level_or_pii_columns_allowed"] is False
    assert report["contract"]["missing_values_imputed_as_zero"] is False
    assert report["verdict_eligibility"]["maximum_supported_verdict"] == "directional"
    assert report["verdict_eligibility"]["causal_inference_eligible"] is False
    assert report["sources"]["gsc_page"]["sha256"]
    assert report["window_totals"]["current"]["gsc_page"]["metrics"]["ctr"]["value"] == 0.1
    assert report["window_totals"]["current"]["ga4"]["metrics"]["conversions"]["value"] is None
    assert (
        report["window_totals"]["current"]["ga4"]["metrics"]["conversions"]["reason"]["code"]
        == "partial_values_blank"
    )
    assert report["coverage"]["unmapped"]["ga4"]["current"]["unmatched_rows"] == 1
    assert report["contract"]["analysis_timezone"] == "Europe/Berlin"
    assert report["contract"]["source_timezones"]["gsc_page"] == "America/Los_Angeles"
    assert report["contract"]["cross_source_join"]["daily_join_allowed"] is True
    assert report["sources"]["ga4"]["sampling_rate"] == 1
    assert report["sources"]["ga4"]["attribution_model"] == "data_driven"
    validator = schema_validator()
    assert list(validator.iter_errors(report)) == []

    contradictory_quality = copy.deepcopy(report)
    contradictory_quality["data_quality"]["status"] = "complete"
    assert list(validator.iter_errors(contradictory_quality))

    contradictory_contract = copy.deepcopy(report)
    contradictory_contract["contract"]["contract_complete"] = True
    assert list(validator.iter_errors(contradictory_contract))

    contradictory_verdict = copy.deepcopy(report)
    contradictory_verdict["verdict_eligibility"]["directional_eligible"] = True
    assert list(validator.iter_errors(contradictory_verdict))


@pytest.mark.parametrize(
    "header", ["Query", "Email", "lead_id", "account_id", "record_id", "accountId"]
)
def test_sensitive_or_query_columns_are_rejected(tmp_path: Path, header: str) -> None:
    gsc, _, _ = datasets(tmp_path)
    content = gsc.read_text(encoding="utf-8")
    first, *rest = content.splitlines()
    bad = write(tmp_path / "bad.csv", first + f",{header}\n" + "\n".join(line + ",x" for line in rest) + "\n")

    result = main(
        [
            "--gsc-page",
            str(bad),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(tmp_path / "bad.json"),
            "--markdown-out",
            str(tmp_path / "bad.md"),
        ]
    )

    assert result == 2


@pytest.mark.parametrize("header", ["account_id", "record_id", "accountId"])
def test_metric_mapping_cannot_relabel_stable_identifier_as_metric(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    header: str,
) -> None:
    gsc, _, _ = datasets(tmp_path)
    mapping_path = config(tmp_path)
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping["metric_mapping"]["crm"] = {"account_count": header}
    mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
    crm = write(
        tmp_path / "stable-id.csv",
        f"Date,Landing page,Country,{header}\n"
        "2026-05-10,/product/,Germany,92837465\n"
        "2026-06-10,/product/,Germany,83746592\n",
    )
    json_out = tmp_path / "must-not-exist.json"

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--crm",
            str(crm),
            "--mapping",
            str(mapping_path),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(tmp_path / "must-not-exist.md"),
        ]
    )

    assert result == 2
    assert not json_out.exists()
    assert "92837465" not in capsys.readouterr().err


def test_duplicate_full_grain_is_rejected_before_metrics_are_summed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    duplicate = write(
        tmp_path / "duplicate-gsc.csv",
        "Date,Page,Country,Device,Clicks,Impressions\n"
        "2026-05-10,https://example.com/product/,DEU,DESKTOP,10,100\n"
        "2026-05-10,https://example.com/product/,DEU,DESKTOP,10,100\n"
        "2026-06-10,https://example.com/product/,DEU,DESKTOP,15,150\n",
    )

    result = main(
        [
            "--gsc-page",
            str(duplicate),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(tmp_path / "should-not-exist.json"),
            "--markdown-out",
            str(tmp_path / "should-not-exist.md"),
        ]
    )

    assert result == 2
    assert "重复的完整聚合粒度" in capsys.readouterr().err
    assert not (tmp_path / "should-not-exist.json").exists()


def test_cli_runs_directly_outside_repository() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd="/tmp",
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "GSC 页面级" in result.stdout
    assert "CRM 聚合" in result.stdout


@pytest.mark.parametrize("header", ["SEARCH TERM", "关键词", "Phone Number", "手机号"])
def test_sensitive_header_synonyms_are_rejected(tmp_path: Path, header: str) -> None:
    gsc, _, _ = datasets(tmp_path)
    first, *rest = gsc.read_text(encoding="utf-8").splitlines()
    bad = write(
        tmp_path / "synonym.csv",
        first + f",{header}\n" + "\n".join(line + ",private" for line in rest) + "\n",
    )

    result = main(
        [
            "--gsc-page",
            str(bad),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(tmp_path / "synonym.json"),
            "--markdown-out",
            str(tmp_path / "synonym.md"),
        ]
    )

    assert result == 2


def test_timezone_conversion_assigns_iso_timestamps_to_inclusive_windows(tmp_path: Path) -> None:
    gsc = write(
        tmp_path / "timezone.csv",
        "Date,Page,Country,Device,Clicks,Impressions\n"
        # Europe/Berlin 当地时间为 5 月 1 日 00:30，归入基线。
        "2026-04-30T22:30:00Z,/product/,DEU,DESKTOP,3,30\n"
        # Europe/Berlin 当地时间为 6 月 1 日 00:30，归入当前。
        "2026-05-31T22:30:00Z,/product/,DEU,DESKTOP,7,70\n",
    )
    output = tmp_path / "timezone.json"

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "timezone.md"),
        ]
    )

    assert result == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["contract"]["timezone"] == "Europe/Berlin"
    assert report["contract"]["windows"]["inclusive"] is True
    assert report["window_totals"]["baseline"]["gsc_page"]["metrics"]["clicks"]["value"] == 3
    assert report["window_totals"]["current"]["gsc_page"]["metrics"]["clicks"]["value"] == 7


def test_overlapping_windows_are_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mapping = json.loads(config(tmp_path).read_text(encoding="utf-8"))
    mapping["windows"]["current"]["start"] = "2026-05-31"
    mapping_path = write(tmp_path / "overlap.json", json.dumps(mapping, ensure_ascii=False))
    gsc, _, _ = datasets(tmp_path)

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(mapping_path),
            "--json-out",
            str(tmp_path / "overlap-report.json"),
            "--markdown-out",
            str(tmp_path / "overlap-report.md"),
        ]
    )

    assert result == 2
    assert "不重叠" in capsys.readouterr().err


def test_unequal_windows_downgrade_verdict_to_inconclusive(tmp_path: Path) -> None:
    mapping = json.loads(config(tmp_path).read_text(encoding="utf-8"))
    mapping["windows"]["current"]["end"] = "2026-06-29"
    mapping_path = write(tmp_path / "unequal.json", json.dumps(mapping, ensure_ascii=False))
    gsc, _, _ = datasets(tmp_path)
    output = tmp_path / "unequal-report.json"

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(mapping_path),
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "unequal-report.md"),
        ]
    )

    assert result == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["verdict_eligibility"]["recommended_verdict"] == "inconclusive"
    assert any("天数不同" in reason for reason in report["verdict_eligibility"]["eligibility_reasons"])


def test_zero_denominator_and_missing_cohort_are_null_with_reasons(tmp_path: Path) -> None:
    gsc = write(
        tmp_path / "zero.csv",
        "Date,Page,Country,Device,Clicks,Impressions\n"
        "2026-05-10,/product/,DEU,DESKTOP,0,0\n"
        "2026-06-10,/product/,DEU,DESKTOP,5,10\n"
        "2026-06-11,/new/,DEU,DESKTOP,1,2\n",
    )
    output = tmp_path / "zero-report.json"

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "zero-report.md"),
        ]
    )

    assert result == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    baseline_ctr = report["window_totals"]["baseline"]["gsc_page"]["metrics"]["ctr"]
    assert baseline_ctr["value"] is None
    assert baseline_ctr["reason"]["code"] == "zero_denominator"
    relative_clicks = report["window_deltas"]["gsc_page"]["clicks"]["relative"]
    assert relative_clicks["value"] is None
    assert relative_clicks["reason"]["code"] == "zero_denominator"
    new_cohort = next(
        row for row in report["landing_page_cohorts"] if row["landing_page"].endswith("/new")
    )
    baseline_clicks = new_cohort["sources"]["gsc_page"]["baseline"]["metrics"]["clicks"]
    assert baseline_clicks["value"] is None
    assert baseline_clicks["reason"]["code"] == "no_rows"
    delta = new_cohort["sources"]["gsc_page"]["delta"]["clicks"]["absolute"]
    assert delta["value"] is None
    assert delta["reason"]["code"] == "cohort_missing_in_baseline"


def test_missing_required_field_is_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    gsc = write(
        tmp_path / "missing-device.csv",
        "Date,Page,Country,Clicks,Impressions\n2026-05-10,/product/,DEU,1,10\n",
    )

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(tmp_path / "missing.json"),
            "--markdown-out",
            str(tmp_path / "missing.md"),
        ]
    )

    assert result == 2
    assert "device -> Device" in capsys.readouterr().err


def test_source_and_config_hashes_cover_exact_input_bytes(tmp_path: Path) -> None:
    gsc, _, _ = datasets(tmp_path)
    mapping_path = config(tmp_path)
    output = tmp_path / "hash-report.json"

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(mapping_path),
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "hash-report.md"),
        ]
    )

    assert result == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["sources"]["gsc_page"]["sha256"] == hashlib.sha256(gsc.read_bytes()).hexdigest()
    assert report["sources"]["mapping"]["sha256"] == hashlib.sha256(mapping_path.read_bytes()).hexdigest()
    assert report["sources"]["gsc_page"]["path"] == gsc.name
    assert report["sources"]["mapping"]["path"] == mapping_path.name
    assert str(tmp_path) not in json.dumps(report, ensure_ascii=False)


def test_crm_raw_stage_column_is_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    gsc, _, _ = datasets(tmp_path)
    crm = write(
        tmp_path / "raw-crm.csv",
        "Date,Landing page,Country,Leads,Qualified,Pipeline value,Stage\n"
        "2026-05-10,/product/,Germany,1,1,1000,MQL\n",
    )

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--crm",
            str(crm),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(tmp_path / "raw-crm.json"),
            "--markdown-out",
            str(tmp_path / "raw-crm.md"),
        ]
    )

    assert result == 2
    assert "不接受原始列 'Stage'" in capsys.readouterr().err


def test_url_mapping_coverage_and_causal_boundary_are_explicit(tmp_path: Path) -> None:
    gsc, ga4, crm = datasets(tmp_path)
    output = tmp_path / "boundary.json"
    markdown = tmp_path / "boundary.md"

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--ga4",
            str(ga4),
            "--crm",
            str(crm),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(output),
            "--markdown-out",
            str(markdown),
        ]
    )

    assert result == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    baseline = report["coverage"]["unmapped"]["ga4"]["baseline"]
    assert baseline["explicit_url_mapping_rows"] == 1
    assert baseline["matched_rows"] == 1
    verdict = report["verdict_eligibility"]
    assert verdict["recommended_verdict"] in {"directional", "inconclusive"}
    assert verdict["maximum_supported_verdict"] == "directional"
    assert verdict["automatic_causal_or_incrementality_claim_allowed"] is False
    serialized = json.dumps(report, ensure_ascii=False) + markdown.read_text(encoding="utf-8")
    assert "incremental-positive" not in serialized
    assert "不能判定 SEO 造成了增量" in serialized


def test_date_grain_with_different_source_day_boundaries_forbids_daily_join(
    tmp_path: Path,
) -> None:
    mapping = json.loads(config(tmp_path).read_text(encoding="utf-8"))
    mapping["source_timezones"]["ga4"] = "Europe/Berlin"
    mapping["source_metadata"]["ga4"]["source_timezone"] = "Europe/Berlin"
    mapping_path = write(
        tmp_path / "timezone-mismatch.json", json.dumps(mapping, ensure_ascii=False)
    )
    gsc, ga4, _ = datasets(tmp_path)
    output = tmp_path / "timezone-mismatch-report.json"

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--ga4",
            str(ga4),
            "--mapping",
            str(mapping_path),
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "timezone-mismatch.md"),
        ]
    )

    assert result == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    alignment = report["contract"]["cross_source_join"]
    assert alignment["mode"] == "window_aggregate_only"
    assert alignment["daily_join_allowed"] is False
    assert report["coverage"]["unmapped"]["ga4"]["current"]["join_performed"] is False
    assert report["coverage"]["unmapped"]["ga4"]["current"]["matched_rows"] is None
    assert report["verdict_eligibility"]["recommended_verdict"] == "inconclusive"
    assert report["verdict_eligibility"]["incremental_positive_allowed"] is False
    assert any(
        item["code"] == "source_day_boundary_mismatch"
        for item in report["data_quality"]["issues"]
    )


def test_missing_or_degraded_source_metadata_blocks_directional_verdict(
    tmp_path: Path,
) -> None:
    mapping = json.loads(config(tmp_path).read_text(encoding="utf-8"))
    mapping["source_metadata"]["gsc_page"].pop("data_as_of")
    mapping["source_metadata"]["gsc_page"]["row_limit_hit"] = True
    mapping_path = write(
        tmp_path / "degraded.json", json.dumps(mapping, ensure_ascii=False)
    )
    gsc, _, _ = datasets(tmp_path)
    output = tmp_path / "degraded-report.json"

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(mapping_path),
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "degraded-report.md"),
        ]
    )

    assert result == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["verdict_eligibility"]["recommended_verdict"] == "inconclusive"
    codes = {item["code"] for item in report["data_quality"]["issues"]}
    assert {"data_as_of_missing", "row_limit_hit"} <= codes
    assert report["verdict_eligibility"]["no_detectable_change_allowed"] is False


def test_blank_date_and_dimensions_enter_report_quality_gate(tmp_path: Path) -> None:
    gsc = write(
        tmp_path / "blank-grain.csv",
        "Date,Page,Country,Device,Clicks,Impressions\n"
        "2026-05-10,/product/,DEU,DESKTOP,10,100\n"
        "2026-06-10,/product/,,DESKTOP,15,150\n"
        ",/product/,DEU,DESKTOP,2,20\n",
    )
    output = tmp_path / "blank-grain-report.json"

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "blank-grain.md"),
        ]
    )

    assert result == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    codes = {item["code"] for item in report["data_quality"]["issues"]}
    assert {"blank_or_invalid_date", "blank_or_invalid_country"} <= codes
    assert report["quality"]["gsc_page"]["gate_status"] == "inconclusive"
    assert report["data_quality"]["complete"] is False
    assert report["contract"]["contract_complete"] is False
    assert report["verdict_eligibility"]["recommended_verdict"] == "inconclusive"


def test_unmapped_column_cannot_silently_change_measurement_grain(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gsc = write(
        tmp_path / "hidden-grain.csv",
        "Date,Page,Country,Device,Search Appearance,Clicks,Impressions\n"
        "2026-05-10,/product/,DEU,DESKTOP,AI overview,10,100\n"
        "2026-06-10,/product/,DEU,DESKTOP,AI overview,15,150\n",
    )

    result = main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(tmp_path / "hidden-grain.json"),
            "--markdown-out",
            str(tmp_path / "hidden-grain.md"),
        ]
    )

    assert result == 2
    error = capsys.readouterr().err
    assert "未声明列" in error
    assert "改变聚合粒度" in error


def test_known_gsc_derived_metrics_are_recorded_without_changing_grain(
    tmp_path: Path,
) -> None:
    gsc = write(
        tmp_path / "derived-metrics.csv",
        "Date,Page,Country,Device,Clicks,Impressions,CTR,Position\n"
        "2026-05-10,/product/,DEU,DESKTOP,10,100,10%,4.2\n"
        "2026-06-10,/product/,DEU,DESKTOP,15,150,10%,3.8\n",
    )
    output = tmp_path / "derived-metrics-report.json"

    assert main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(config(tmp_path)),
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "derived-metrics.md"),
        ]
    ) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["quality"]["gsc_page"]["ignored_columns"] == ["CTR", "Position"]
    assert report["quality"]["gsc_page"]["gate_status"] == "complete"
    assert report["data_quality"]["complete"] is True


def test_measurement_data_as_of_requires_offset_and_uses_source_timezone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gsc, _, _ = datasets(tmp_path)
    mapping = json.loads(config(tmp_path).read_text(encoding="utf-8"))
    mapping["source_metadata"]["gsc_page"]["data_as_of"] = "2026-07-01T00:00:00"
    naive = write(tmp_path / "naive.json", json.dumps(mapping, ensure_ascii=False))

    assert main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(naive),
            "--json-out",
            str(tmp_path / "naive-report.json"),
            "--markdown-out",
            str(tmp_path / "naive.md"),
        ]
    ) == 2
    assert "必须包含 Z" in capsys.readouterr().err

    mapping["source_metadata"]["gsc_page"]["data_as_of"] = "2026-06-30T01:00:00Z"
    localized = write(
        tmp_path / "localized.json", json.dumps(mapping, ensure_ascii=False)
    )
    output = tmp_path / "localized-report.json"
    assert main(
        [
            "--gsc-page",
            str(gsc),
            "--mapping",
            str(localized),
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "localized.md"),
        ]
    ) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert "data_as_of_before_current_window_end" in {
        item["code"] for item in report["data_quality"]["issues"]
    }
