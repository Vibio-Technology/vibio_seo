from __future__ import annotations

import copy
import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from runtime.experiment import analyze_experiment, plan_experiment
from runtime.gsc_compare import build_report, read_gsc_csv
from runtime.gsc_ai_compare import build_report as build_gsc_ai_report, read_gsc_ai_csv
from runtime.measurement_review import URLNormalizer, build_report as build_measurement_report
from runtime.measurement_review import load_config, read_dataset
from runtime.seo_inspect import BrowserProvenance, analyze, parse_page


ROOT = Path(__file__).resolve().parents[1]


def load_validator(name: str) -> Draft202012Validator:
    schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "schema_name",
    [
        "seo_inspect.report.schema.json",
        "gsc_compare.report.schema.json",
        "gsc_ai_compare.report.schema.json",
        "measurement_review.report.schema.json",
    ],
)
@pytest.mark.parametrize(
    "bad_reference",
    [
        "/private/report.csv",
        r"C:\private\report.csv",
        r"\private\report.csv",
        "C:/private/report.csv",
        "C:relative-report.csv",
        "file:///private/report.csv",
        "https://example.com/report.csv",
        "../private/report.csv",
        "evidence/../private/report.csv",
    ],
)
def test_data_report_file_references_reject_non_project_paths(
    schema_name: str, bad_reference: str
) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema["$defs"]["fileReference"])

    assert list(validator.iter_errors(bad_reference))
    assert list(validator.iter_errors("evidence/report.csv")) == []


def test_real_site_inspection_output_matches_shipped_schema() -> None:
    page = parse_page(
        html=(
            b'<html lang="en"><head><title>Product</title>'
            b'<link rel="canonical" href="https://example.com/product/">'
            b'</head><body><main><a href="/">Home</a></main></body></html>'
        ),
        url="https://example.com/product/",
        source="fixture",
    )
    report = analyze(
        {page.url: page},
        base_url="https://example.com/",
        assets=set(),
        fetches={},
        sitemap_urls={page.url},
        sitemap_duplicates=[],
        sitemap_errors=[],
        robots=None,
        robots_source=None,
        production=False,
        scope_mode="local",
        crawl_notes=[],
    )

    validator = load_validator("seo_inspect.report.schema.json")
    errors = list(validator.iter_errors(report))
    assert errors == []

    absolute_source = copy.deepcopy(report)
    absolute_source["pages"][0]["source"] = "/Users/example/private/index.html"
    assert list(validator.iter_errors(absolute_source))


def test_browser_dom_comparison_matches_schema_and_mode_contract() -> None:
    source = parse_page(
        html=b'<html><head><meta name="robots" content="noindex"></head><body></body></html>',
        url="https://example.com/product/",
        source="source.html",
        evidence_mode="static_build",
        status=None,
    )
    rendered = parse_page(
        html=(
            b'<html><head><title>Product</title></head>'
            b'<body><main><a href="/">Home</a></main></body></html>'
        ),
        url="https://example.com/product/",
        source="rendered.html",
        evidence_mode="browser_dom",
        status=None,
    )
    report = analyze(
        {rendered.url: rendered},
        base_url="https://example.com/",
        assets=set(),
        fetches={},
        sitemap_urls=set(),
        sitemap_duplicates=[],
        sitemap_errors=[],
        robots=None,
        robots_source=None,
        production=False,
        scope_mode="local",
        crawl_notes=[],
        evidence_mode="browser_dom",
        source_pages={source.url: source},
        source_input="source.html",
        browser_provenance=BrowserProvenance(
            source="browser-provenance.json",
            schema_version="1.0",
            capture_method="Playwright page.content()",
            browser="Chromium 140",
            captured_at="2026-07-11T10:00:00+08:00",
            javascript_enabled=True,
            documents_verified=1,
            provenance_sha256="a" * 64,
        ),
    )

    validator = load_validator("seo_inspect.report.schema.json")
    assert list(validator.iter_errors(report)) == []

    absolute_provenance = copy.deepcopy(report)
    absolute_provenance["scope"]["browser_provenance"]["source"] = (
        r"C:\Users\example\browser-provenance.json"
    )
    assert list(validator.iter_errors(absolute_provenance))

    report["scope"]["javascript_rendered"] = False
    assert list(validator.iter_errors(report))


def test_real_gsc_output_matches_shipped_schema(tmp_path: Path) -> None:
    current_path = tmp_path / "current.csv"
    baseline_path = tmp_path / "baseline.csv"
    current_path.write_text("Query,Clicks,Impressions,Position\nsensor,2,20,4\n", encoding="utf-8")
    baseline_path.write_text("Query,Clicks,Impressions,Position\nsensor,1,10,5\n", encoding="utf-8")
    report = build_report(
        read_gsc_csv(current_path),
        read_gsc_csv(baseline_path),
        property_id="sc-domain:example.com",
        search_type="web",
        timezone_name="Asia/Shanghai",
        baseline_start=date(2026, 5, 1),
        baseline_end=date(2026, 5, 31),
        current_start=date(2026, 6, 1),
        current_end=date(2026, 6, 30),
    )

    validator = load_validator("gsc_compare.report.schema.json")
    errors = list(validator.iter_errors(report))
    assert errors == []

    absolute_source = copy.deepcopy(report)
    absolute_source["sources"]["current"]["path"] = "/tmp/private/current.csv"
    assert list(validator.iter_errors(absolute_source))
    traversal_source = copy.deepcopy(report)
    traversal_source["sources"]["current"]["path"] = "../private/current.csv"
    assert list(validator.iter_errors(traversal_source))


def test_real_gsc_ai_output_matches_shipped_schema(tmp_path: Path) -> None:
    baseline_path = tmp_path / "ai-baseline.csv"
    current_path = tmp_path / "ai-current.csv"
    baseline_path.write_text("Page,Impressions\n/a,10\n", encoding="utf-8")
    current_path.write_text("Page,Impressions\n/a,20\n", encoding="utf-8")
    report = build_gsc_ai_report(
        read_gsc_ai_csv(current_path),
        read_gsc_ai_csv(baseline_path),
        baseline_start=date(2026, 5, 2),
        baseline_end=date(2026, 5, 31),
        current_start=date(2026, 6, 1),
        current_end=date(2026, 6, 30),
    )

    validator = load_validator("gsc_ai_compare.report.schema.json")
    assert list(validator.iter_errors(report)) == []

    absolute_source = copy.deepcopy(report)
    absolute_source["sources"]["current"]["path"] = r"C:\private\current.csv"
    assert list(validator.iter_errors(absolute_source))
    traversal_source = copy.deepcopy(report)
    traversal_source["sources"]["current"]["path"] = "../private/current.csv"
    assert list(validator.iter_errors(traversal_source))


def test_real_measurement_review_output_matches_shipped_schema(tmp_path: Path) -> None:
    mapping = write_json(
        tmp_path / "measurement.json",
        {
            "windows": {
                "baseline": {"start": "2026-05-01", "end": "2026-05-31"},
                "current": {"start": "2026-06-01", "end": "2026-06-30"},
            },
            "analysis_timezone": "UTC",
            "property": "sc-domain:example.com",
            "search_type": "web",
            "source_timezones": {"gsc_page": "America/Los_Angeles"},
            "source_metadata": {
                "gsc_page": {
                    "source_kind": "gsc_search_analytics",
                    "data_as_of": "2026-07-05T12:00:00Z",
                    "finality": "final",
                    "row_limit_hit": False,
                    "pagination_complete": True,
                    "data_quality": "complete",
                }
            },
            "dimension_mapping": {
                "gsc_page": {
                    "date": "Date",
                    "landing_page": "Page",
                    "country": "Country",
                    "device": "Device",
                }
            },
            "url_normalization": {
                "base_url": "https://example.com/",
                "strip_query": True,
                "strip_fragment": True,
                "trailing_slash": "remove",
            },
            "crm_definition": {
                "stage": "sales accepted",
                "qualified": "meets ICP and product need",
            },
        },
    )
    gsc_path = tmp_path / "gsc.csv"
    gsc_path.write_text(
        "Date,Page,Country,Device,Clicks,Impressions\n"
        "2026-05-10,/product/,DE,DESKTOP,10,100\n"
        "2026-06-10,/product/,DE,DESKTOP,12,120\n",
        encoding="utf-8",
    )
    config = load_config(mapping, {"gsc_page"})
    normalizer = URLNormalizer(config.url_settings)
    report = build_measurement_report(
        {"gsc_page": read_dataset("gsc_page", gsc_path, config, normalizer)},
        config,
    )

    validator = load_validator("measurement_review.report.schema.json")
    errors = list(validator.iter_errors(report))
    assert errors == []

    absolute_source = copy.deepcopy(report)
    absolute_source["sources"]["mapping"]["path"] = "/private/measurement.json"
    assert list(validator.iter_errors(absolute_source))
    traversal_source = copy.deepcopy(report)
    traversal_source["sources"]["mapping"]["path"] = "../private/measurement.json"
    assert list(validator.iter_errors(traversal_source))


def test_real_experiment_outputs_match_shipped_schemas(tmp_path: Path) -> None:
    spec = write_json(
        tmp_path / "spec.json",
        {
            "experiment_id": "schema-exp-001",
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
    )
    baseline = tmp_path / "baseline.csv"
    baseline.write_text(
        "page,organic_clicks,qualified_lead_rate\n"
        "/a,10,0.20\n/b,10,0.20\n/c,10,0.20\n/d,10,0.20\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "frozen"
    plan = plan_experiment(spec, baseline, out_dir)

    panel_lines = [
        "page,date,group,organic_clicks,qualified_lead_rate,contaminated,treatment_applied"
    ]
    for assignment in plan["assignments"]:
        unit_id = assignment["unit_id"]
        group = assignment["group"]
        for offset in range(31):
            day = date(2025, 1, 1) + timedelta(days=offset)
            panel_lines.append(f"{unit_id},{day.isoformat()},{group},10,0.20,false,false")
        clicks = 14 if group == "treatment" else 11
        applied = "true" if group == "treatment" else "false"
        for offset in range(28):
            day = date(2025, 2, 1) + timedelta(days=offset)
            panel_lines.append(
                f"{unit_id},{day.isoformat()},{group},{clicks},0.20,false,{applied}"
            )
    panel = tmp_path / "panel.csv"
    panel.write_text("\n".join(panel_lines) + "\n", encoding="utf-8")
    artifact = write_json(
        tmp_path / "artifact.json",
        {
            "experiment_id": plan["experiment_id"],
            "plan_hash": plan["plan_hash"],
            "passed": True,
            "evidence": "schema test artifact verification",
        },
    )
    result = analyze_experiment(out_dir / "plan.json", panel, artifact)

    plan_errors = list(load_validator("experiment.plan.schema.json").iter_errors(plan))
    report_errors = list(
        load_validator("experiment.report.schema.json").iter_errors(result)
    )
    assert plan_errors == []
    assert report_errors == []

    validator = load_validator("experiment.report.schema.json")
    nested_claim = copy.deepcopy(result)
    nested_claim["methodology"]["causal_business_claim"] = "SEO change caused revenue"
    assert list(validator.iter_errors(nested_claim))

    nested_metric_claim = copy.deepcopy(result)
    nested_metric_claim["primary_metric"]["ranking_increase_proven"] = True
    assert list(validator.iter_errors(nested_metric_claim))

    contradictory_artifact = copy.deepcopy(result)
    contradictory_artifact["artifact_verification"]["passed"] = False
    assert list(validator.iter_errors(contradictory_artifact))

    contradictory_eligibility = copy.deepcopy(result)
    contradictory_eligibility["eligibility"] = "inconclusive"
    contradictory_eligibility["eligibility_details"]["eligible_incremental"] = True
    assert list(validator.iter_errors(contradictory_eligibility))

    contradictory_contract = copy.deepcopy(result)
    contradictory_contract["measurement_contract"]["complete"] = False
    assert list(validator.iter_errors(contradictory_contract))

    contradictory_quality = copy.deepcopy(result)
    contradictory_quality["data_quality"]["passed"] = False
    contradictory_quality["data_quality"]["issues"] = []
    assert list(validator.iter_errors(contradictory_quality))

    contradictory_coverage = copy.deepcopy(result)
    contradictory_coverage["data_quality"]["coverage"]["complete"] = True
    contradictory_coverage["data_quality"]["coverage"]["periods"]["baseline"][
        "complete"
    ] = False
    assert list(validator.iter_errors(contradictory_coverage))

    contradictory_guardrail = copy.deepcopy(result)
    contradictory_guardrail["guardrails"]["passed"] = False
    assert list(validator.iter_errors(contradictory_guardrail))

    contradictory_source = copy.deepcopy(result)
    source = next(iter(contradictory_source["measurement_contract"]["sources"].values()))
    source["data_quality"]["status"] = "complete"
    source["data_quality"]["issues"] = ["contradiction"]
    assert list(validator.iter_errors(contradictory_source))

    contradictory_direction_gate = copy.deepcopy(result)
    contradictory_direction_gate["eligibility_details"][
        "incremental_positive_allowed"
    ] = False
    assert list(validator.iter_errors(contradictory_direction_gate))


@pytest.mark.parametrize(
    ("schema_name", "report"),
    [
        (
            "seo_inspect.report.schema.json",
            {
                "schema_version": "1.3",
                "analysis_kind": "bounded_seo_artifact_inspection",
            },
        ),
        (
            "gsc_compare.report.schema.json",
            {
                "schema_version": "1.3.0",
                "analysis_kind": "descriptive_gsc_window_comparison",
            },
        ),
        (
            "measurement_review.report.schema.json",
            {
                "schema_version": "1.2",
                "tool": {
                    "name": "vibio-seo-measurement-review",
                    "version": "1.2.0",
                },
            },
        ),
        (
            "gsc_ai_compare.report.schema.json",
            {
                "schema_version": "1.2",
                "analysis_kind": "descriptive_gsc_generative_ai_window_comparison",
            },
        ),
        (
            "experiment.plan.schema.json",
            {
                "schema_version": "1.1",
                "tool": "vibio-seo-experiment",
            },
        ),
        (
            "experiment.report.schema.json",
            {
                "schema_version": "1.1",
                "tool": "vibio-seo-experiment",
            },
        ),
    ],
)
def test_incomplete_runtime_reports_are_rejected(schema_name: str, report: dict) -> None:
    assert list(load_validator(schema_name).iter_errors(report))
