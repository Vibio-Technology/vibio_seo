from __future__ import annotations

import copy
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from runtime.gsc_ai_compare import (
    AGGREGATION_WARNING,
    CAUSALITY_WARNING,
    INFERENCE_WARNING,
    SOURCE_KIND,
    SOURCE_TIMEZONE,
    SUBSET_WARNING,
    GSCAIError,
    aggregate,
    build_report,
    main,
    read_gsc_ai_csv,
    render_markdown,
    select_window,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime" / "gsc_ai_compare.py"
SCHEMA = ROOT / "schemas" / "gsc_ai_compare.report.schema.json"
DECLARED_WINDOWS = {
    "baseline_start": date(2026, 5, 2),
    "baseline_end": date(2026, 5, 31),
    "current_start": date(2026, 6, 1),
    "current_end": date(2026, 6, 30),
}


def write_csv(tmp_path: Path, name: str, content: str, *, bom: bool = False) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8-sig" if bom else "utf-8")
    return path


def complete_metadata(
    *, data_as_of: str = "2026-07-05T12:00:00Z"
) -> dict[str, dict[str, object]]:
    return {
        period: {
            "data_as_of": data_as_of,
            "finality": "final",
            "completeness": "complete",
            "row_limit_hit": False,
        }
        for period in ("baseline", "current")
    }


def build_declared(
    current: object, baseline: object, **kwargs: object
) -> dict[str, object]:
    return build_report(current, baseline, **DECLARED_WINDOWS, **kwargs)  # type: ignore[arg-type]


def schema_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_reads_utf8_bom_and_only_supported_english_headers(tmp_path: Path) -> None:
    source = write_csv(
        tmp_path,
        "english.csv",
        "Date,Page,Country,Device,Impressions\n"
        '2026-06-01,https://example.com/a,USA,DESKTOP,"1,250"\n',
        bom=True,
    )

    dataset = read_gsc_ai_csv(source)

    assert dataset.fields == {"date", "page", "country", "device", "impressions"}
    assert dataset.rows[0].day == date(2026, 6, 1)
    assert dataset.rows[0].dimensions == {
        "page": "https://example.com/a",
        "country": "USA",
        "device": "DESKTOP",
    }
    assert aggregate(dataset.rows) == {
        "impressions": 1250,
        "rows": 1,
        "zero_impression_rows": 0,
    }
    assert len(dataset.sha256) == 64


def test_reads_chinese_headers_and_normalizes_ui_placeholders(tmp_path: Path) -> None:
    source = write_csv(
        tmp_path,
        "chinese.csv",
        "日期,热门网页,国家/地区,设备,展示次数\n"
        "2026/05/01,https://example.cn/a,中国,移动设备,-\n"
        "2026/06/02,https://example.cn/b,中国,桌面设备,~\n",
    )

    dataset = read_gsc_ai_csv(source)

    assert [row.impressions for row in dataset.rows] == [0, 0]
    assert dataset.normalized_placeholder_rows == 2
    report = build_report(
        dataset,
        dataset,
        baseline_rows=(dataset.rows[0],),
        current_rows=(dataset.rows[1],),
    )
    codes = {item["code"] for item in report["data_quality"]["issues"]}
    assert "ui_placeholders_normalized_to_zero" in codes


@pytest.mark.parametrize(
    "header",
    [
        "Query",
        "Clicks",
        "CTR",
        "Position",
        "Citations",
        "Conversions",
        "查询",
        "点击次数",
        "点击率",
        "引用",
        "转化次数",
    ],
)
def test_rejects_metrics_and_dimensions_the_report_does_not_provide(
    tmp_path: Path, header: str
) -> None:
    source = write_csv(
        tmp_path, "forbidden.csv", f"Page,Impressions,{header}\n/a,10,value\n"
    )

    with pytest.raises(GSCAIError, match="不接收字段"):
        read_gsc_ai_csv(source)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("Page\n/a\n", "缺少必需列"),
        ("Page,Impressions,Unknown\n/a,1,x\n", "不支持的 CSV 列"),
        ("Page,Impressions\n/a,nope\n", "不是有效数值"),
        ("Page,Impressions\n/a,-1\n", "必须是非负有限数"),
        ("Page,Impressions\n/a,nan\n", "必须是非负有限数"),
        ("Date,Impressions\n2026-99-01,1\n", "无法解析"),
        ("Page,Impressions\n/a,\n", "不能为空"),
    ],
)
def test_bad_input_has_actionable_chinese_errors(
    tmp_path: Path, content: str, message: str
) -> None:
    source = write_csv(tmp_path, "bad.csv", content)

    with pytest.raises(GSCAIError, match=message):
        read_gsc_ai_csv(source)


def test_duplicate_chinese_and_english_aliases_are_rejected(tmp_path: Path) -> None:
    source = write_csv(
        tmp_path, "duplicate.csv", "Page,网页,Impressions\n/a,/a,1\n"
    )

    with pytest.raises(GSCAIError, match="都被识别为“页面”"):
        read_gsc_ai_csv(source)


@pytest.mark.parametrize(
    ("page", "kind"),
    [
        ("https://example.com/product?email=alice@example.com", "邮箱"),
        ("/product/#phone=13800138000", "电话号码"),
        ("/product/?account_id=acct_92837465", "稳定个人标识"),
        ("/product/?session_token=secret92837465", "稳定个人标识"),
    ],
)
def test_page_url_pii_is_rejected_without_echoing_value(
    tmp_path: Path,
    page: str,
    kind: str,
) -> None:
    source = write_csv(
        tmp_path,
        "private-page.csv",
        f"Page,Impressions\n{page},10\n",
    )

    with pytest.raises(GSCAIError) as captured:
        read_gsc_ai_csv(source)

    message = str(captured.value)
    assert kind in message
    assert page not in message
    assert str(tmp_path) not in message


def test_single_csv_two_windows_and_all_supported_cohorts(tmp_path: Path) -> None:
    dataset = read_gsc_ai_csv(
        write_csv(
            tmp_path,
            "all.csv",
            "Date,Page,Country,Device,Impressions\n"
            "2026-05-02,/a,US,DESKTOP,10\n"
            "2026-05-31,/old,DE,MOBILE,5\n"
            "2026-06-01,/a,US,DESKTOP,20\n"
            "2026-06-30,/new,FR,MOBILE,15\n"
            "2026-07-01,/outside,US,DESKTOP,999\n",
        )
    )
    baseline = select_window(dataset, date(2026, 5, 2), date(2026, 5, 31), "基线")
    current = select_window(dataset, date(2026, 6, 1), date(2026, 6, 30), "当前")

    report = build_report(
        dataset,
        dataset,
        baseline_rows=baseline,
        current_rows=current,
        baseline_start=date(2026, 5, 2),
        baseline_end=date(2026, 5, 31),
        current_start=date(2026, 6, 1),
        current_end=date(2026, 6, 30),
        property_id="sc-domain:example.com",
        filters="none",
        source_metadata=complete_metadata(),
        top=0,
    )

    assert report["overall"]["baseline"]["impressions"] == 15
    assert report["overall"]["current"]["impressions"] == 35
    assert report["overall"]["delta"]["impressions_relative"] == pytest.approx(4 / 3)
    assert report["coverage"]["current"]["excluded_rows"] == 3
    assert report["coverage"]["shared_dimensions"] == ["page", "country", "device"]
    assert all(report["cohorts"][key]["available"] for key in ("page", "country", "device"))
    pages = {item["value"]: item for item in report["cohorts"]["page"]["rows"]}
    assert set(pages) == {"/a", "/old", "/new"}
    assert pages["/old"]["current"]["impressions"] == 0
    assert report["data_quality"]["status"] == "complete"


def test_dual_csv_mode_compares_same_grain(tmp_path: Path) -> None:
    baseline = read_gsc_ai_csv(
        write_csv(tmp_path, "before.csv", "Page,Impressions\n/a,10\n/b,5\n")
    )
    current = read_gsc_ai_csv(
        write_csv(tmp_path, "after.csv", "Page,Impressions\n/a,12\n/c,8\n")
    )

    report = build_declared(current, baseline, filters="country=all")

    assert report["overall"]["baseline"]["impressions"] == 15
    assert report["overall"]["current"]["impressions"] == 20
    assert report["sources"]["baseline"]["sha256"] != report["sources"]["current"]["sha256"]
    assert report["periods"]["baseline"]["calendar_days"] == 30
    assert report["data_quality"]["status"] == "unknown"


def test_zero_denominator_is_null_with_machine_readable_reason(tmp_path: Path) -> None:
    baseline = read_gsc_ai_csv(
        write_csv(tmp_path, "before.csv", "Page,Impressions\n/new,0\n")
    )
    current = read_gsc_ai_csv(
        write_csv(tmp_path, "after.csv", "Page,Impressions\n/new,8\n")
    )

    report = build_declared(current, baseline)
    overall_delta = report["overall"]["delta"]
    page_delta = report["cohorts"]["page"]["rows"][0]["delta"]

    assert overall_delta["impressions_relative"] is None
    assert overall_delta["impressions_relative_reason"] == "baseline_impressions_zero"
    assert page_delta["impressions_relative"] is None
    assert page_delta["impressions_relative_reason"] == "baseline_impressions_zero"
    assert "不可计算（基线展示次数为 0）" in render_markdown(report)


def test_missing_cohorts_are_explicit_not_inferred(tmp_path: Path) -> None:
    baseline = read_gsc_ai_csv(
        write_csv(tmp_path, "before.csv", "Country,Impressions\nUS,10\n")
    )
    current = read_gsc_ai_csv(
        write_csv(tmp_path, "after.csv", "Country,Impressions\nUS,12\n")
    )

    report = build_declared(current, baseline)

    assert report["cohorts"]["country"]["available"] is True
    assert report["cohorts"]["page"] == {
        "label": "页面",
        "available": False,
        "unavailable_reason": "dimension_not_present_in_both_periods",
        "groups_total": 0,
        "groups_returned": 0,
        "rows": [],
    }
    assert report["coverage"]["missing_dimensions"] == ["page", "device"]


def test_mismatched_period_grains_are_rejected(tmp_path: Path) -> None:
    baseline = read_gsc_ai_csv(
        write_csv(tmp_path, "before.csv", "Page,Impressions\n/a,10\n")
    )
    current = read_gsc_ai_csv(
        write_csv(tmp_path, "after.csv", "Country,Impressions\nUS,12\n")
    )

    with pytest.raises(GSCAIError, match="两期口径不一致"):
        build_declared(current, baseline)


def test_unequal_window_lengths_are_reported_as_limited(tmp_path: Path) -> None:
    dataset = read_gsc_ai_csv(
        write_csv(
            tmp_path,
            "dates.csv",
            "Date,Impressions\n2026-05-01,10\n2026-06-01,20\n",
        )
    )

    report = build_report(
        dataset,
        dataset,
        baseline_rows=select_window(
            dataset, date(2026, 5, 1), date(2026, 5, 31), "基线"
        ),
        current_rows=select_window(
            dataset, date(2026, 6, 1), date(2026, 6, 30), "当前"
        ),
        baseline_start=date(2026, 5, 1),
        baseline_end=date(2026, 5, 31),
        current_start=date(2026, 6, 1),
        current_end=date(2026, 6, 30),
        property_id="sc-domain:example.com",
        filters="none",
        source_metadata=complete_metadata(),
    )

    assert report["dataset_contract"]["window_lengths_aligned"] is False
    assert report["data_quality"]["status"] == "limited"
    assert "window_length_mismatch" in {
        issue["code"] for issue in report["data_quality"]["issues"]
    }


def test_mismatched_filters_and_properties_are_rejected(tmp_path: Path) -> None:
    baseline = read_gsc_ai_csv(
        write_csv(tmp_path, "before.csv", "Page,Impressions\n/a,10\n")
    )
    current = read_gsc_ai_csv(
        write_csv(tmp_path, "after.csv", "Page,Impressions\n/a,12\n")
    )

    with pytest.raises(GSCAIError, match="过滤条件不同"):
        build_declared(
            current,
            baseline,
            source_metadata={
                "baseline": {"filters": "country=US"},
                "current": {"filters": "country=DE"},
            },
        )

    with pytest.raises(GSCAIError, match="property_id 不同"):
        build_declared(
            current,
            baseline,
            source_metadata={
                "baseline": {"property_id": "sc-domain:a.example"},
                "current": {"property_id": "sc-domain:b.example"},
            },
        )


def test_wrong_source_kind_or_timezone_cannot_masquerade_as_ai_report(
    tmp_path: Path,
) -> None:
    dataset = read_gsc_ai_csv(
        write_csv(tmp_path, "source.csv", "Page,Impressions\n/a,10\n")
    )

    with pytest.raises(GSCAIError, match="普通 Performance CSV"):
        build_declared(
            dataset,
            dataset,
            source_metadata={"current": {"source_kind": "gsc_search_analytics"}},
        )
    with pytest.raises(GSCAIError, match="America/Los_Angeles"):
        build_declared(
            dataset,
            dataset,
            source_metadata={"current": {"source_timezone": "UTC"}},
        )


def test_complete_metadata_is_recorded_but_only_descriptive(tmp_path: Path) -> None:
    dataset = read_gsc_ai_csv(
        write_csv(
            tmp_path,
            "source.csv",
            "Date,Page,Impressions\n"
            "2026-05-01,/a,10\n"
            "2026-06-01,/a,20\n",
        )
    )
    baseline = select_window(dataset, date(2026, 5, 1), date(2026, 5, 1), "基线")
    current = select_window(dataset, date(2026, 6, 1), date(2026, 6, 1), "当前")

    report = build_report(
        dataset,
        dataset,
        current_rows=current,
        baseline_rows=baseline,
        property_id="sc-domain:example.com",
        filters="none",
        source_metadata=complete_metadata(),
    )

    source = report["sources"]["current"]
    assert source["source_kind"] == SOURCE_KIND
    assert source["property_id"] == "sc-domain:example.com"
    assert source["search_type"] == "web"
    assert source["source_timezone"] == SOURCE_TIMEZONE
    assert source["source_timezone_label"] == "PT"
    assert source["data_as_of"] == "2026-07-05T12:00:00Z"
    assert source["finality"] == "final"
    assert source["preliminary"] is False
    assert source["completeness"] == "complete"
    assert source["ui_row_limit"] == 1000
    assert source["row_limit_hit"] is False
    assert report["data_quality"]["status"] == "complete"
    assert report["verdict_eligibility"]["maximum_supported_verdict"] == "descriptive"
    assert report["verdict_eligibility"]["causal_or_incremental_claim_allowed"] is False


def test_unknown_completeness_stays_unknown_instead_of_assuming_complete(
    tmp_path: Path,
) -> None:
    dataset = read_gsc_ai_csv(
        write_csv(tmp_path, "source.csv", "Page,Impressions\n/a,10\n")
    )

    report = build_declared(dataset, dataset)

    assert report["sources"]["current"]["completeness"] == "unknown"
    assert report["sources"]["current"]["row_limit_hit"] is None
    assert report["data_quality"]["complete"] is False
    assert report["data_quality"]["status"] == "unknown"
    codes = {item["code"] for item in report["data_quality"]["issues"]}
    assert {"completeness_unknown", "row_limit_status_unknown"} <= codes
    assert report["verdict_eligibility"]["recommended_verdict"] == "inconclusive"


def test_preliminary_or_row_limited_data_is_limited(tmp_path: Path) -> None:
    dataset = read_gsc_ai_csv(
        write_csv(tmp_path, "source.csv", "Page,Impressions\n/a,10\n")
    )
    metadata = complete_metadata()
    metadata["current"] = {
        **metadata["current"],
        "finality": "preliminary",
        "row_limit_hit": True,
    }

    report = build_declared(
        dataset,
        dataset,
        property_id="sc-domain:example.com",
        filters="none",
        source_metadata=metadata,
    )

    codes = {item["code"] for item in report["data_quality"]["issues"]}
    assert {"data_preliminary", "ui_row_limit_hit"} <= codes
    assert report["sources"]["current"]["preliminary"] is True
    assert report["data_quality"]["status"] == "limited"


def test_exactly_1000_rows_is_flagged_even_when_limit_status_is_unknown(
    tmp_path: Path,
) -> None:
    rows = "".join(f"/p-{index},{index + 1}\n" for index in range(1000))
    dataset = read_gsc_ai_csv(
        write_csv(tmp_path, "thousand.csv", "Page,Impressions\n" + rows)
    )

    report = build_declared(dataset, dataset)

    source = report["sources"]["current"]
    assert source["source_rows_at_or_above_ui_limit"] is True
    assert source["row_limit_hit"] is None
    assert source["ui_row_limit"] == 1000
    assert "source_rows_at_or_above_ui_limit" in {
        issue["code"] for issue in source["quality"]["issues"]
    }
    assert report["data_quality"]["status"] == "limited"


def test_data_as_of_before_period_end_is_limited(tmp_path: Path) -> None:
    dataset = read_gsc_ai_csv(
        write_csv(tmp_path, "source.csv", "Impressions\n10\n")
    )
    metadata = complete_metadata(data_as_of="2026-06-01T12:00:00Z")

    report = build_declared(
        dataset,
        dataset,
        property_id="sc-domain:example.com",
        filters="none",
        source_metadata=metadata,
    )

    assert "data_as_of_before_window_end" in {
        issue["code"] for issue in report["data_quality"]["issues"]
    }
    assert report["data_quality"]["status"] == "limited"


def test_official_scope_boundaries_are_machine_readable_and_visible(
    tmp_path: Path,
) -> None:
    dataset = read_gsc_ai_csv(
        write_csv(tmp_path, "source.csv", "Page,Impressions\n/a,10\n")
    )

    report = build_declared(dataset, dataset)
    markdown = render_markdown(report)

    assert report["limitations"] == {
        "web_performance_subset": True,
        "additive_with_web_performance": False,
        "query_available_or_inferred": False,
        "clicks_available_or_inferred": False,
        "ctr_available_or_inferred": False,
        "citations_available_or_inferred": False,
        "conversions_available_or_inferred": False,
        "ranking_or_causality_supported": False,
        "included_features_documented": ["AI Overviews", "AI Mode"],
        "search_labs_experiments_included": False,
    }
    for warning in (
        SUBSET_WARNING,
        INFERENCE_WARNING,
        CAUSALITY_WARNING,
        AGGREGATION_WARNING,
    ):
        assert warning in markdown
    assert "不能相加" in markdown
    assert "不输出点击、CTR、查询、引用、转化或收入估算" in markdown


def test_real_report_matches_strict_schema_and_extra_fields_are_rejected(
    tmp_path: Path,
) -> None:
    dataset = read_gsc_ai_csv(
        write_csv(
            tmp_path,
            "source.csv",
            "Date,Page,Country,Device,Impressions\n"
            "2026-05-01,/a,US,DESKTOP,10\n"
            "2026-06-01,/a,US,DESKTOP,20\n",
        )
    )
    baseline = select_window(dataset, date(2026, 5, 1), date(2026, 5, 1), "基线")
    current = select_window(dataset, date(2026, 6, 1), date(2026, 6, 1), "当前")
    report = build_report(
        dataset,
        dataset,
        current_rows=current,
        baseline_rows=baseline,
        property_id="sc-domain:example.com",
        filters="none",
        source_metadata=complete_metadata(),
    )
    validator = schema_validator()

    assert list(validator.iter_errors(report)) == []

    unexpected_top = copy.deepcopy(report)
    unexpected_top["unexpected"] = True
    assert list(validator.iter_errors(unexpected_top))

    unexpected_nested = copy.deepcopy(report)
    unexpected_nested["sources"]["current"]["clicks"] = 99
    assert list(validator.iter_errors(unexpected_nested))

    contradictory_quality = copy.deepcopy(report)
    contradictory_quality["data_quality"]["complete"] = False
    assert list(validator.iter_errors(contradictory_quality))

    contradictory_source = copy.deepcopy(report)
    contradictory_source["sources"]["current"]["quality"]["issues"] = [
        {"code": "fabricated_issue", "severity": "unknown"}
    ]
    assert list(validator.iter_errors(contradictory_source))


def test_cli_single_csv_writes_json_and_chinese_markdown(tmp_path: Path) -> None:
    source = write_csv(
        tmp_path,
        "all.csv",
        "日期,网页,展示次数\n"
        "2026-05-01,/a,10\n"
        "2026-06-01,/a,15\n",
    )
    json_out = tmp_path / "report.json"
    markdown_out = tmp_path / "report.md"

    exit_code = main(
        [
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
            "--filters",
            "none",
            "--data-as-of",
            "2026-07-05T12:00:00Z",
            "--finality",
            "final",
            "--completeness",
            "complete",
            "--no-row-limit-hit",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    assert exit_code == 0
    report = json.loads(json_out.read_text(encoding="utf-8"))
    assert report["sources"]["current"]["path"] == "all.csv"
    assert report["sources"]["baseline"]["path"] == "all.csv"
    assert report["periods"]["current"]["source"] == "all.csv"
    assert str(tmp_path) not in json.dumps(report, ensure_ascii=False)
    assert report["overall"]["current"]["impressions"] == 15
    assert list(schema_validator().iter_errors(report)) == []
    markdown = markdown_out.read_text(encoding="utf-8")
    assert markdown.startswith("# GSC 生成式 AI 展示次数窗口比较")
    assert "不能相加" in markdown


def test_cli_help_is_chinese_and_script_is_standalone() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd="/tmp",
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "生成式 AI 效果报告" in result.stdout
    assert "用法：" in result.stdout
    assert "选项：" in result.stdout
    assert "usage:" not in result.stdout
    assert "不推断点击、CTR、查询、引用或转化" in result.stdout


def test_cli_errors_are_chinese_and_overlapping_windows_are_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--current", "only.csv"]) == 2
    assert "错误：" in capsys.readouterr().err

    source = write_csv(
        tmp_path,
        "source.csv",
        "Date,Impressions\n2026-05-15,10\n2026-06-01,20\n",
    )
    exit_code = main(
        [
            "--input",
            str(source),
            "--baseline-start",
            "2026-05-01",
            "--baseline-end",
            "2026-05-31",
            "--current-start",
            "2026-05-15",
            "--current-end",
            "2026-06-15",
        ]
    )

    assert exit_code == 2
    assert "不重叠" in capsys.readouterr().err


def test_inconsistent_finality_and_preliminary_are_rejected(tmp_path: Path) -> None:
    dataset = read_gsc_ai_csv(
        write_csv(tmp_path, "source.csv", "Page,Impressions\n/a,10\n")
    )

    with pytest.raises(GSCAIError, match="与 finality=.*不一致"):
        build_declared(
            dataset,
            dataset,
            source_metadata={
                "current": {"finality": "final", "preliminary": True}
            },
        )


def test_duplicate_complete_grain_is_rejected_before_impressions_are_summed(
    tmp_path: Path,
) -> None:
    source = write_csv(
        tmp_path,
        "duplicate.csv",
        "Date,Page,Device,Impressions\n"
        "2026-06-01,/a,DESKTOP,10\n"
        "2026-06-01,/a,DESKTOP,20\n",
    )

    with pytest.raises(GSCAIError, match="完整聚合粒度.*重复.*拒绝加总"):
        read_gsc_ai_csv(source)


def test_dual_csv_without_date_requires_explicit_disjoint_boundaries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline = write_csv(tmp_path, "baseline.csv", "Page,Impressions\n/a,10\n")
    current = write_csv(tmp_path, "current.csv", "Page,Impressions\n/a,20\n")

    assert main(["--baseline", str(baseline), "--current", str(current)]) == 2
    assert "必须显式声明" in capsys.readouterr().err

    assert main(
        [
            "--baseline",
            str(baseline),
            "--current",
            str(current),
            "--baseline-start",
            "2026-05-01",
            "--baseline-end",
            "2026-05-31",
            "--current-start",
            "2026-06-01",
            "--current-end",
            "2026-06-30",
        ]
    ) == 0


def test_observed_dual_csv_windows_cannot_be_identical(tmp_path: Path) -> None:
    baseline = read_gsc_ai_csv(
        write_csv(
            tmp_path,
            "baseline-date.csv",
            "Date,Page,Impressions\n2026-06-01,/a,10\n",
        )
    )
    current = read_gsc_ai_csv(
        write_csv(
            tmp_path,
            "current-date.csv",
            "Date,Page,Impressions\n2026-06-01,/a,20\n",
        )
    )

    with pytest.raises(GSCAIError, match="不重叠.*严格在"):
        build_report(current, baseline)


def test_data_as_of_requires_offset_and_compares_in_pt(tmp_path: Path) -> None:
    dataset = read_gsc_ai_csv(
        write_csv(tmp_path, "source.csv", "Page,Impressions\n/a,10\n")
    )

    with pytest.raises(GSCAIError, match="必须包含 Z"):
        build_declared(
            dataset,
            dataset,
            source_metadata=complete_metadata(data_as_of="2026-07-01T00:00:00"),
        )

    report = build_declared(
        dataset,
        dataset,
        property_id="sc-domain:example.com",
        filters="none",
        source_metadata=complete_metadata(data_as_of="2026-06-30T01:00:00Z"),
    )
    assert "data_as_of_before_window_end" in {
        issue["code"] for issue in report["data_quality"]["issues"]
    }
