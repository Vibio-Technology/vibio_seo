from __future__ import annotations

import copy
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from runtime.gsc_compare import (
    CAUSALITY_WARNING,
    JOIN_WARNING,
    GSCError,
    aggregate,
    build_report,
    main,
    read_gsc_csv,
    render_markdown,
    select_window,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime" / "gsc_compare.py"
SCHEMA = ROOT / "schemas" / "gsc_compare.report.schema.json"
DECLARED_WINDOWS = {
    "baseline_start": date(2026, 5, 1),
    "baseline_end": date(2026, 5, 31),
    "current_start": date(2026, 6, 1),
    "current_end": date(2026, 6, 30),
}


def write_csv(tmp_path: Path, name: str, content: str, *, bom: bool = False) -> Path:
    path = tmp_path / name
    encoding = "utf-8-sig" if bom else "utf-8"
    path.write_text(content, encoding=encoding)
    return path


def schema_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_reads_utf8_bom_and_english_gsc_headers(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "english.csv",
        "Date,Query,Page,Country,Device,Clicks,Impressions,CTR,Position\n"
        "2026-06-01,seo tool,https://example.com/,USA,DESKTOP,10,100,99%,4.5\n",
        bom=True,
    )

    dataset = read_gsc_csv(path)

    assert dataset.fields == {
        "date",
        "query",
        "page",
        "country",
        "device",
        "clicks",
        "impressions",
        "ctr",
        "position",
    }
    assert dataset.rows[0].day.isoformat() == "2026-06-01"
    assert dataset.rows[0].dimensions["query"] == "seo tool"
    # CSV 的 99% CTR 被故意忽略，CTR 由点击/展示重算。
    assert aggregate(dataset.rows)["ctr"] == 0.1


def test_reads_common_chinese_headers_and_thousands_separators(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "chinese.csv",
        "日期,热门查询,热门网页,地区,设备,点击次数,展示次数,CTR,排名\n"
        '2026/06/01,工业传感器,https://example.cn/a,中国,移动设备,"1,200","12,000",10%,3.2\n',
    )

    row = read_gsc_csv(path).rows[0]

    assert row.clicks == 1200
    assert row.impressions == 12000
    assert row.position == 3.2
    assert row.dimensions == {
        "query": "工业传感器",
        "page": "https://example.cn/a",
        "country": "中国",
        "device": "移动设备",
    }


def test_aggregation_recalculates_ctr_and_impression_weighted_position(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "weighted.csv",
        "Query,Device,Clicks,Impressions,CTR,Position\n"
        "alpha,DESKTOP,10,100,90%,2\n"
        "alpha,MOBILE,10,300,1%,6\n"
        "beta,DESKTOP,0,0,100%,1\n",
    )

    metrics = aggregate(read_gsc_csv(path).rows)

    assert metrics["clicks"] == 20
    assert metrics["impressions"] == 400
    assert metrics["ctr"] == 0.05
    assert metrics["weighted_position"] == 5
    assert metrics["position_impressions"] == 400
    assert metrics["position_rows"] == 2


def test_zero_denominators_are_null_not_fake_percentages(tmp_path: Path) -> None:
    current = read_gsc_csv(
        write_csv(tmp_path, "current.csv", "Query,Clicks,Impressions,Position\nnew,5,10,2\n")
    )
    baseline = read_gsc_csv(
        write_csv(tmp_path, "baseline.csv", "Query,Clicks,Impressions,Position\nnew,0,0,2\n")
    )

    report = build_report(
        current, baseline, allow_unaligned_overall=True, **DECLARED_WINDOWS
    )

    assert report["overall"]["baseline"]["ctr"] is None
    assert report["overall"]["baseline"]["weighted_position"] is None
    assert report["overall"]["delta"]["clicks_relative"] is None
    assert report["overall"]["delta"]["impressions_relative"] is None
    assert report["overall"]["delta"]["ctr_percentage_points"] is None
    assert report["cohorts"]["query"]["rows"][0]["delta"]["weighted_position"] is None
    assert "不可计算" in render_markdown(report)


def test_single_file_date_windows_filter_inclusively_and_report_coverage(tmp_path: Path) -> None:
    dataset = read_gsc_csv(
        write_csv(
            tmp_path,
            "dates.csv",
            "日期,查询,点击次数,展示次数,平均排名\n"
            "2026-05-01,a,1,10,10\n"
            "2026-05-31,b,2,20,8\n"
            "2026-06-01,a,3,30,6\n"
            "2026-06-30,b,4,40,4\n"
            "2026-07-01,c,100,100,1\n",
        )
    )
    baseline = select_window(
        dataset,
        start=dataset.rows[0].day,
        end=dataset.rows[1].day,
        label="基线窗口",
    )
    current = select_window(
        dataset,
        start=dataset.rows[2].day,
        end=dataset.rows[3].day,
        label="当前窗口",
    )

    report = build_report(dataset, dataset, current_rows=current, baseline_rows=baseline)

    assert report["overall"]["baseline"]["clicks"] == 3
    assert report["overall"]["current"]["clicks"] == 7
    assert report["overall"]["delta"]["ctr_percentage_points"] == 0
    assert report["coverage"]["current"]["source_rows"] == 5
    assert report["coverage"]["current"]["included_rows"] == 2
    assert report["coverage"]["current"]["excluded_rows"] == 3


def test_cohorts_include_union_and_missing_dimensions_are_explicit(tmp_path: Path) -> None:
    current = read_gsc_csv(
        write_csv(
            tmp_path,
            "current.csv",
            "Query,Country,Clicks,Impressions,Position\na,US,5,50,2\nnew,DE,3,30,4\n",
        )
    )
    baseline = read_gsc_csv(
        write_csv(
            tmp_path,
            "baseline.csv",
            "Query,Country,Clicks,Impressions,Position\na,US,2,20,3\nlost,FR,1,10,8\n",
        )
    )

    report = build_report(current, baseline, top=0, **DECLARED_WINDOWS)

    assert report["coverage"]["shared_dimensions"] == ["query", "country"]
    assert set(report["coverage"]["missing_dimensions"]) == {"page", "device"}
    query_rows = {item["value"]: item for item in report["cohorts"]["query"]["rows"]}
    assert set(query_rows) == {"a", "new", "lost"}
    assert query_rows["new"]["baseline"]["impressions"] == 0
    assert query_rows["lost"]["current"]["impressions"] == 0
    assert report["cohorts"]["page"]["available"] is False


def test_two_files_with_unaligned_dimensions_do_not_fake_cohort_join(tmp_path: Path) -> None:
    current = read_gsc_csv(
        write_csv(tmp_path, "current.csv", "Page,Clicks,Impressions\n/a,2,10\n")
    )
    baseline = read_gsc_csv(
        write_csv(tmp_path, "baseline.csv", "Query,Clicks,Impressions\na,1,5\n")
    )

    report = build_report(
        current, baseline, allow_unaligned_overall=True, **DECLARED_WINDOWS
    )

    assert report["coverage"]["shared_dimensions"] == []
    assert report["cohorts"]["page"]["available"] is False
    assert report["cohorts"]["query"]["available"] is False
    assert "不进行臆测对比" in render_markdown(report)
    assert report["dataset_contract"]["grains_aligned"] is False


def test_unaligned_dimensions_are_rejected_without_explicit_override(tmp_path: Path) -> None:
    current = read_gsc_csv(
        write_csv(tmp_path, "current.csv", "Page,Clicks,Impressions\n/a,2,10\n")
    )
    baseline = read_gsc_csv(
        write_csv(tmp_path, "baseline.csv", "Query,Clicks,Impressions\na,1,5\n")
    )

    with pytest.raises(GSCError, match="维度粒度不同"):
        build_report(current, baseline, **DECLARED_WINDOWS)


def test_report_records_source_hash_and_dataset_contract(tmp_path: Path) -> None:
    current = read_gsc_csv(
        write_csv(tmp_path, "current.csv", "Query,Clicks,Impressions\na,2,10\n")
    )
    baseline = read_gsc_csv(
        write_csv(tmp_path, "baseline.csv", "Query,Clicks,Impressions\na,1,5\n")
    )

    report = build_report(
        current,
        baseline,
        property_id="sc-domain:example.com",
        search_type="web",
        timezone_name="Asia/Shanghai",
        filter_notes="country=DE; device=all",
        **DECLARED_WINDOWS,
    )

    assert len(report["sources"]["current"]["sha256"]) == 64
    assert report["sources"]["current"]["path"] == "current.csv"
    assert report["sources"]["baseline"]["path"] == "baseline.csv"
    assert report["periods"]["current"]["source"] == "current.csv"
    assert report["coverage"]["baseline"]["source"] == "baseline.csv"
    assert str(tmp_path) not in json.dumps(report, ensure_ascii=False)
    assert report["dataset_contract"]["contract_complete"] is True
    assert report["dataset_contract"]["filter_notes"] == "country=DE; device=all"
    assert report["dataset_contract"]["analysis_timezone"] == "Asia/Shanghai"
    assert report["dataset_contract"]["source_timezones"] == {
        "baseline": "America/Los_Angeles",
        "current": "America/Los_Angeles",
    }
    assert report["sources"]["current"]["source_kind"] == "gsc_search_analytics"
    assert "聚合前拒绝高置信邮箱" in render_markdown(report)
    assert report["verdict_eligibility"]["recommended_verdict"] == "inconclusive"


def test_json_and_markdown_preserve_causality_and_join_boundaries(tmp_path: Path) -> None:
    current = read_gsc_csv(
        write_csv(tmp_path, "current.csv", "Query,Clicks,Impressions\na,2,10\n")
    )
    baseline = read_gsc_csv(
        write_csv(tmp_path, "baseline.csv", "Query,Clicks,Impressions\na,1,10\n")
    )

    report = build_report(current, baseline, **DECLARED_WINDOWS)
    markdown = render_markdown(report)
    serialized = json.dumps(report, ensure_ascii=False)

    assert report["methodology"]["causal_inference"] is False
    assert CAUSALITY_WARNING in markdown
    assert JOIN_WARNING in markdown
    assert "不得与 GA4/CRM" in serialized
    assert "因果" in serialized
    assert "SEO 带来" not in markdown


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("Query,Clicks\na,1\n", "缺少必需列：展示次数"),
        ("Query,Clicks,Impressions\na,nope,10\n", "不是有效数值"),
        ("Query,Clicks,Impressions\na,-1,10\n", "必须是非负有限数"),
        ("Date,Clicks,Impressions\n2026-99-01,1,10\n", "无法解析"),
    ],
)
def test_bad_csv_data_has_actionable_errors(
    tmp_path: Path, content: str, message: str
) -> None:
    path = write_csv(tmp_path, "bad.csv", content)

    with pytest.raises(GSCError, match=message):
        read_gsc_csv(path)


@pytest.mark.parametrize(
    ("query", "kind"),
    [
        ("contact alice@example.com", "邮箱"),
        ("call +49 30 12345678", "电话号码"),
        ("phone (415) 555-2671", "电话号码"),
        ("手机号 13800138000", "电话号码"),
        ("身份证 11010519491231002X", "身份证号"),
        ("customer_id=acct_92837465", "稳定个人标识"),
    ],
)
def test_query_pii_is_rejected_without_echoing_value(
    tmp_path: Path,
    query: str,
    kind: str,
) -> None:
    source = write_csv(
        tmp_path,
        "private-query.csv",
        f"Query,Clicks,Impressions\n{query},1,10\n",
    )

    with pytest.raises(GSCError) as captured:
        read_gsc_csv(source)

    message = str(captured.value)
    assert kind in message
    assert query not in message
    assert str(tmp_path) not in message


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
        f"Page,Clicks,Impressions\n{page},1,10\n",
    )

    with pytest.raises(GSCError) as captured:
        read_gsc_csv(source)

    message = str(captured.value)
    assert kind in message
    assert page not in message
    assert str(tmp_path) not in message


def test_clicks_cannot_exceed_impressions(tmp_path: Path) -> None:
    source = write_csv(
        tmp_path,
        "impossible-ctr.csv",
        "Query,Clicks,Impressions\nseo,11,10\n",
    )

    with pytest.raises(GSCError, match="点击次数大于展示次数"):
        read_gsc_csv(source)


@pytest.mark.parametrize(
    "query",
    [
        "iphone 15 pro max 256gb",
        "iso 9001:2015 requirements",
        "bearing 6204-2rs dimensions",
        "2026 seo trends",
        "best phone 2026 2027 comparison",
        "how to find customer id",
    ],
)
def test_query_privacy_gate_keeps_common_non_pii_queries(
    tmp_path: Path,
    query: str,
) -> None:
    dataset = read_gsc_csv(
        write_csv(
            tmp_path,
            "ordinary-query.csv",
            f"Query,Clicks,Impressions\n{query},1,10\n",
        )
    )

    assert dataset.rows[0].dimensions["query"] == query


def test_cli_single_file_writes_json_and_markdown(tmp_path: Path) -> None:
    source = write_csv(
        tmp_path,
        "all.csv",
        "Date,Query,Clicks,Impressions,Position\n"
        "2026-05-01,a,1,10,4\n"
        "2026-06-01,a,2,10,3\n",
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
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    assert exit_code == 0
    assert json.loads(json_out.read_text(encoding="utf-8"))["overall"]["current"]["clicks"] == 2
    assert markdown_out.read_text(encoding="utf-8").startswith("# GSC 前后窗口")


def test_cli_reports_invalid_mode_in_chinese(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--current", "only.csv"])
    stderr = capsys.readouterr().err

    assert exit_code == 2
    assert "错误：" in stderr
    assert "--current 和 --baseline" in stderr


def test_cli_rejects_overlapping_single_file_windows(tmp_path: Path, capsys) -> None:
    source = write_csv(
        tmp_path,
        "all.csv",
        "Date,Clicks,Impressions\n2026-05-15,1,10\n2026-06-01,2,20\n",
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


def test_duplicate_alias_columns_are_rejected(tmp_path: Path) -> None:
    source = write_csv(
        tmp_path,
        "duplicate.csv",
        "Query,查询,Clicks,Impressions\na,a,1,10\n",
    )

    with pytest.raises(GSCError, match="都被识别为“查询”"):
        read_gsc_csv(source)


def test_single_file_mode_requires_date_column(tmp_path: Path) -> None:
    dataset = read_gsc_csv(
        write_csv(tmp_path, "no-date.csv", "Query,Clicks,Impressions\na,1,10\n")
    )

    with pytest.raises(GSCError, match="需要“Date/日期”列"):
        select_window(dataset, start=date(2026, 5, 1), end=date(2026, 5, 31), label="基线")


def test_script_is_directly_executable_without_repository_imports() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd="/tmp",
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Google Search Console" in result.stdout
    assert "不做因果归因" in result.stdout
    assert "用法：" in result.stdout
    assert "选项：" in result.stdout
    assert "显示帮助并退出" in result.stdout
    assert "usage:" not in result.stdout


def test_complete_source_metadata_passes_integrity_but_remains_descriptive(
    tmp_path: Path,
) -> None:
    current = read_gsc_csv(
        write_csv(tmp_path, "current.csv", "Query,Clicks,Impressions\na,2,10\n")
    )
    baseline = read_gsc_csv(
        write_csv(tmp_path, "baseline.csv", "Query,Clicks,Impressions\na,1,5\n")
    )
    metadata = {
        period: {
                "data_as_of": "2026-07-05T12:00:00Z",
            "finality": "final",
            "row_limit_hit": False,
            "pagination_complete": True,
            "data_quality": "complete",
        }
        for period in ("baseline", "current")
    }

    report = build_report(
        current,
        baseline,
        property_id="sc-domain:example.com",
        search_type="web",
        analysis_timezone="Asia/Shanghai",
        source_metadata=metadata,
        **DECLARED_WINDOWS,
    )

    assert report["data_quality"] == {
        "status": "complete",
        "complete": True,
        "issues": [],
    }
    assert report["schema_version"] == "1.3.0"
    assert report["verdict_eligibility"]["recommended_verdict"] == "descriptive"
    assert report["verdict_eligibility"]["incremental_positive_allowed"] is False
    assert report["verdict_eligibility"]["no_detectable_change_allowed"] is False
    validator = schema_validator()
    assert list(validator.iter_errors(report)) == []

    contradictory = copy.deepcopy(report)
    contradictory["data_quality"]["complete"] = False
    assert list(validator.iter_errors(contradictory))

    contradictory_source = copy.deepcopy(report)
    contradictory_source["sources"]["current"]["data_quality"]["issues"] = [
        "fabricated_issue"
    ]
    assert list(validator.iter_errors(contradictory_source))


def test_row_limit_preliminary_and_timezone_mismatch_are_inconclusive(
    tmp_path: Path,
) -> None:
    current = read_gsc_csv(
        write_csv(tmp_path, "current.csv", "Query,Clicks,Impressions\na,2,10\n")
    )
    baseline = read_gsc_csv(
        write_csv(tmp_path, "baseline.csv", "Query,Clicks,Impressions\na,1,5\n")
    )
    common = {
        "data_as_of": "2026-07-05T12:00:00Z",
        "finality": "final",
        "row_limit_hit": False,
        "pagination_complete": True,
        "data_quality": "complete",
    }
    report = build_report(
        current,
        baseline,
        analysis_timezone="UTC",
        source_timezones={
            "baseline": "America/Los_Angeles",
            "current": "UTC",
        },
        source_metadata={
            "baseline": common,
            "current": {
                **common,
                "finality": "preliminary",
                "row_limit_hit": True,
            },
        },
        **DECLARED_WINDOWS,
    )

    codes = {item["code"] for item in report["data_quality"]["issues"]}
    assert {"data_preliminary", "row_limit_hit", "source_timezone_mismatch"} <= codes
    assert report["verdict_eligibility"]["recommended_verdict"] == "inconclusive"


def test_unknown_column_cannot_hide_an_additional_gsc_grain(tmp_path: Path) -> None:
    source = write_csv(
        tmp_path,
        "search-appearance.csv",
        "Date,Page,Search Appearance,Clicks,Impressions\n"
        "2026-06-01,/a,AI overview,1,10\n",
    )

    with pytest.raises(GSCError, match="未识别列.*Search Appearance.*改变聚合粒度"):
        read_gsc_csv(source)


def test_duplicate_complete_grain_is_rejected_before_aggregation(tmp_path: Path) -> None:
    source = write_csv(
        tmp_path,
        "duplicate-grain.csv",
        "Date,Query,Device,Clicks,Impressions\n"
        "2026-06-01,seo,DESKTOP,1,10\n"
        "2026-06-01,seo,DESKTOP,2,20\n",
    )

    with pytest.raises(GSCError, match="完整聚合粒度.*重复.*拒绝加总"):
        read_gsc_csv(source)


def test_dual_csv_without_date_requires_declared_disjoint_windows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline = write_csv(
        tmp_path, "baseline-no-date.csv", "Query,Clicks,Impressions\na,1,10\n"
    )
    current = write_csv(
        tmp_path, "current-no-date.csv", "Query,Clicks,Impressions\na,2,20\n"
    )

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


def test_dual_csv_observed_windows_cannot_overlap_or_be_identical(tmp_path: Path) -> None:
    baseline = read_gsc_csv(
        write_csv(
            tmp_path,
            "baseline-date.csv",
            "Date,Query,Clicks,Impressions\n2026-06-01,a,1,10\n",
        )
    )
    current = read_gsc_csv(
        write_csv(
            tmp_path,
            "current-date.csv",
            "Date,Query,Clicks,Impressions\n2026-06-01,a,2,20\n",
        )
    )

    with pytest.raises(GSCError, match="不重叠.*严格在"):
        build_report(current, baseline)


def test_data_as_of_requires_offset_and_uses_source_local_date(tmp_path: Path) -> None:
    current = read_gsc_csv(
        write_csv(tmp_path, "current.csv", "Query,Clicks,Impressions\na,2,20\n")
    )
    baseline = read_gsc_csv(
        write_csv(tmp_path, "baseline.csv", "Query,Clicks,Impressions\na,1,10\n")
    )
    complete = {
        "finality": "final",
        "row_limit_hit": False,
        "pagination_complete": True,
        "data_quality": "complete",
    }

    with pytest.raises(GSCError, match="必须包含 Z"):
        build_report(
            current,
            baseline,
            source_metadata={
                period: {**complete, "data_as_of": "2026-07-01T00:00:00"}
                for period in ("baseline", "current")
            },
            **DECLARED_WINDOWS,
        )

    report = build_report(
        current,
        baseline,
        source_metadata={
            period: {**complete, "data_as_of": "2026-06-30T01:00:00Z"}
            for period in ("baseline", "current")
        },
        **DECLARED_WINDOWS,
    )
    assert "data_as_of_before_window_end" in {
        item["code"] for item in report["data_quality"]["issues"]
    }
