from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def test_shipped_audit_fixture_produces_expected_evidence(tmp_path: Path) -> None:
    fixture = ROOT / "vibio-audit/evals/fixtures/industrial-site"
    output = tmp_path / "audit.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "vibio-audit/scripts/seo_inspect.py"),
            "--site-dir",
            str(fixture),
            "--base-url",
            "https://example-industrial.test/",
            "--sitemap",
            str(fixture / "sitemap.xml"),
            "--robots",
            str(fixture / "robots.txt"),
            "--production",
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "audit.md"),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "vibio-audit/schemas/seo_inspect.report.schema.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(schema).iter_errors(report)) == []
    codes = {item["code"] for item in report["findings"]}
    assert {
        "robots.noindex",
        "signals.noindex-cross-canonical",
        "sitemap.noindex-url",
        "sitemap.noncanonical-url",
        "links.broken-internal",
        "links.parameter-url-observed",
        "structured-data.invalid-json",
        "hreflang.return-link-missing",
        "robots.unsupported-noindex",
    } <= codes
    assert report["scope"]["evidence_mode"] == "static_build"
    assert report["scope"]["javascript_rendered"] is False
    assert report["scope"]["http_response_verified"] is False


def test_shipped_review_fixture_recalculates_metrics_and_preserves_causal_boundary(
    tmp_path: Path,
) -> None:
    source = ROOT / "vibio-review/evals/fixtures/gsc-page-daily.csv"
    output = tmp_path / "gsc.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "vibio-review/scripts/gsc_compare.py"),
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
            "sc-domain:example-industrial.test",
            "--search-type",
            "web",
            "--timezone",
            "Europe/Berlin",
            "--filter-notes",
            "country=DE",
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
    schema = json.loads(
        (ROOT / "vibio-review/schemas/gsc_compare.report.schema.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(schema).iter_errors(report)) == []
    assert report["dataset_contract"]["contract_complete"] is True
    assert report["overall"]["baseline"]["clicks"] == 14
    assert report["overall"]["current"]["clicks"] == 19
    assert report["overall"]["baseline"]["ctr"] == 0.0933333333
    assert report["overall"]["current"]["ctr"] == 0.0863636364
    assert report["overall"]["delta"]["ctr_percentage_points"] == -0.69696969
    assert report["methodology"]["causal_inference"] is False
    pages = {item["value"]: item for item in report["cohorts"]["page"]["rows"]}
    assert pages["https://example-industrial.test/products/"]["delta"]["clicks"] == 6
    assert pages["https://example-industrial.test/de/"]["delta"]["clicks"] == -1
