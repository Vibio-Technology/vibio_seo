#!/usr/bin/env python3
"""Google Search Console 生成式 AI 展示数据窗口比较器。

本工具只处理生成式 AI 效果报告中的展示次数，不接收或推断查询、点击、
CTR、引用、排名和转化。它只依赖 Python 标准库，可独立复制执行。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo


SCHEMA_VERSION = "1.2"
SOURCE_KIND = "gsc_generative_ai_performance_csv"
SOURCE_TIMEZONE = "America/Los_Angeles"
SOURCE_TIMEZONE_LABEL = "PT"
SEARCH_TYPE = "web"
UI_ROW_LIMIT = 1000
DIMENSIONS = ("page", "country", "device")
ALL_FIELDS = ("date", *DIMENSIONS, "impressions")
FINALITY_VALUES = {"final", "preliminary", "unknown"}
COMPLETENESS_VALUES = {"complete", "incomplete", "unknown"}

OFFICIAL_REPORT_URL = "https://support.google.com/webmasters/answer/16984139"
OFFICIAL_CONTROL_URL = "https://support.google.com/webmasters/answer/16908024"
OFFICIAL_GUIDE_URL = (
    "https://developers.google.com/search/docs/fundamentals/ai-optimization-guide"
)

FIELD_LABELS = {
    "date": "日期",
    "page": "页面",
    "country": "国家/地区",
    "device": "设备",
    "impressions": "展示次数",
}
DIMENSION_LABELS = {
    "page": "页面",
    "country": "国家/地区",
    "device": "设备",
}


def _header_key(value: str) -> str:
    return " ".join(value.strip().lstrip("\ufeff").lower().replace("_", " ").split())


HEADER_ALIASES = {
    "date": "date",
    "日期": "date",
    "page": "page",
    "pages": "page",
    "top pages": "page",
    "页面": "page",
    "网页": "page",
    "热门网页": "page",
    "country": "country",
    "countries": "country",
    "top countries": "country",
    "国家": "country",
    "地区": "country",
    "国家/地区": "country",
    "热门国家/地区": "country",
    "device": "device",
    "devices": "device",
    "top devices": "device",
    "设备": "device",
    "impressions": "impressions",
    "impression": "impressions",
    "展示次数": "impressions",
    "展现次数": "impressions",
    "展示": "impressions",
    "展现": "impressions",
}

FORBIDDEN_ALIASES = {
    "query": "查询",
    "queries": "查询",
    "top queries": "查询",
    "查询": "查询",
    "热门查询": "查询",
    "click": "点击",
    "clicks": "点击",
    "点击": "点击",
    "点击次数": "点击",
    "ctr": "CTR",
    "average ctr": "CTR",
    "点击率": "CTR",
    "平均点击率": "CTR",
    "position": "排名",
    "average position": "排名",
    "排名": "排名",
    "平均排名": "排名",
    "citation": "引用",
    "citations": "引用",
    "引用": "引用",
    "conversion": "转化",
    "conversions": "转化",
    "转化": "转化",
    "转化次数": "转化",
    "revenue": "收入",
    "收入": "收入",
}

EMAIL_RE = re.compile(
    r"(?<![A-Z0-9.!#$%&'*+/=?^_`{|}~-])[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}(?![A-Z0-9.-])",
    re.IGNORECASE,
)
CHINA_MOBILE_RE = re.compile(r"(?<!\d)(?:\+?86[ -]?)?1[3-9]\d{9}(?!\d)")
INTERNATIONAL_PHONE_RE = re.compile(r"(?<!\w)\+\d(?:[ .()\-]*\d){7,14}(?!\d)")
NORTH_AMERICAN_PHONE_RE = re.compile(
    r"(?<!\d)(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?!\d)"
)
STABLE_ID_RE = re.compile(
    r"(?:user|customer|client|contact|lead|account|record|order|opportunity|visitor|session)"
    r"[ _-]*(?:id|uuid|guid|token)|gclid|dclid|msclkid|fbclid|yclid|_gl",
    re.IGNORECASE,
)
ID_VALUE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{5,127}")
SENSITIVE_PAGE_PARAMETER_RE = re.compile(
    r"^(?:email|e_mail|phone|mobile|telephone|address|ip|cookie|token|auth|"
    r"gclid|dclid|msclkid|fbclid|yclid|_gl|"
    r"(?:user|customer|client|contact|lead|account|record|order|opportunity|visitor|session)"
    r"[_-]?(?:id|uuid|guid|token))$",
    re.IGNORECASE,
)

SUBSET_WARNING = (
    "生成式 AI 效果报告的数据来自普通 Web Performance（搜索结果）报告的子集；"
    "两者不能相加，否则会重复计算。"
)
INFERENCE_WARNING = (
    "本报告只有展示次数，不能据此推断查询、点击、CTR、引用/被引用、排名、"
    "会话、转化或收入。"
)
CAUSALITY_WARNING = (
    "窗口变化是描述性信号，不证明 SEO、内容、广告或生成式 AI 控制设置造成了变化。"
)
AGGREGATION_WARNING = (
    "页面表按页面聚合，国家、设备和日期表按 property 聚合；表格行之和可能与图表总数不同，"
    "不同维度导出不得相加。"
)


class GSCAIError(ValueError):
    """可直接展示给 CLI 用户的数据或契约错误。"""


def _page_pii_kind(value: str) -> str | None:
    parsed = urllib.parse.urlsplit(value)
    decoded = urllib.parse.unquote_plus(
        " ".join(item for item in (parsed.path, parsed.query, parsed.fragment) if item)
    )
    if EMAIL_RE.search(decoded):
        return "邮箱"
    if (
        CHINA_MOBILE_RE.search(decoded)
        or INTERNATIONAL_PHONE_RE.search(decoded)
        or NORTH_AMERICAN_PHONE_RE.search(decoded)
    ):
        return "电话号码"
    query_fragment = urllib.parse.unquote_plus(
        " ".join(item for item in (parsed.query, parsed.fragment) if item)
    )
    identity_context = STABLE_ID_RE.search(query_fragment)
    if identity_context:
        for candidate in ID_VALUE_RE.findall(query_fragment[identity_context.end() :]):
            if any(char.isdigit() for char in candidate):
                return "稳定个人标识"
    for raw_component in (parsed.query, parsed.fragment):
        for key, _value in urllib.parse.parse_qsl(
            raw_component, keep_blank_values=True
        ):
            if SENSITIVE_PAGE_PARAMETER_RE.fullmatch(key.strip()):
                return "敏感 URL 参数"
    return None


def _report_file_reference(path: Path) -> str:
    """机器报告只保存文件名；内容指纹负责精确复验。"""
    return path.name or "input.csv"


class ChineseArgumentParser(argparse.ArgumentParser):
    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法：", 1)

    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace("usage:", "用法：", 1)
            .replace("options:\n", "选项：\n", 1)
        )

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: 参数错误：{message}\n")


@dataclass(frozen=True)
class AIRow:
    row_number: int
    day: date | None
    dimensions: dict[str, str]
    impressions: float


@dataclass(frozen=True)
class AIDataset:
    path: Path
    rows: tuple[AIRow, ...]
    fields: frozenset[str]
    original_headers: tuple[str, ...]
    sha256: str
    normalized_placeholder_rows: int


def _clean_number(value: float) -> int | float:
    if value.is_integer():
        return int(value)
    return round(value, 12)


def parse_date(value: str, *, context: str = "") -> date:
    raw = value.strip()
    for pattern in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, pattern).date()
        except ValueError:
            pass
    raise GSCAIError(f"{context}日期 {value!r} 无法解析；请使用 YYYY-MM-DD。")


def _parse_impressions(value: str, *, path: Path, row_number: int) -> tuple[float, bool]:
    raw = value.strip()
    if raw in {"~", "-"}:
        # 官方说明：界面中的 ~ 或 - 在导出数据中会成为 0。兼容手工保存的界面值，
        # 同时在来源质量中记录发生过规范化。
        return 0.0, True
    if not raw:
        raise GSCAIError(f"{path} 第 {row_number} 行：展示次数不能为空。")
    normalized = raw.replace(",", "").replace("\u00a0", "").replace(" ", "")
    try:
        number = float(normalized)
    except ValueError as exc:
        raise GSCAIError(
            f"{path} 第 {row_number} 行：展示次数 {value!r} 不是有效数值。"
        ) from exc
    if not math.isfinite(number) or number < 0:
        raise GSCAIError(
            f"{path} 第 {row_number} 行：展示次数必须是非负有限数。"
        )
    return number, False


def _map_headers(path: Path, headers: Sequence[str | None]) -> tuple[dict[str, str], frozenset[str]]:
    if not headers or any(header is None or not header.strip() for header in headers):
        raise GSCAIError(f"{path}：CSV 表头为空或包含空列名。")

    mapping: dict[str, str] = {}
    canonical_to_original: dict[str, str] = {}
    unsupported: list[str] = []
    forbidden: list[str] = []
    for original in headers:
        assert original is not None
        key = _header_key(original)
        canonical = HEADER_ALIASES.get(key)
        if canonical is None:
            if key in FORBIDDEN_ALIASES:
                forbidden.append(f"{original}（{FORBIDDEN_ALIASES[key]}）")
            else:
                unsupported.append(original)
            continue
        if canonical in canonical_to_original:
            raise GSCAIError(
                f"{path}：列 {canonical_to_original[canonical]!r} 和 {original!r} "
                f"都被识别为“{FIELD_LABELS[canonical]}”。"
            )
        mapping[original] = canonical
        canonical_to_original[canonical] = original

    if forbidden:
        raise GSCAIError(
            f"{path}：生成式 AI 展示比较器不接收字段：{', '.join(forbidden)}；"
            "请只保留日期、页面、国家/地区、设备和展示次数。"
        )
    if unsupported:
        raise GSCAIError(
            f"{path}：不支持的 CSV 列：{', '.join(repr(item) for item in unsupported)}；"
            "允许的字段只有日期、页面、国家/地区、设备和展示次数。"
        )
    fields = frozenset(mapping.values())
    if "impressions" not in fields:
        raise GSCAIError(f"{path}：缺少必需列“展示次数/Impressions”。")
    return mapping, fields


def read_gsc_ai_csv(path: Path | str) -> AIDataset:
    csv_path = Path(path)
    try:
        raw_bytes = csv_path.read_bytes()
    except OSError as exc:
        raise GSCAIError(f"无法读取 CSV {csv_path}：{exc}。") from exc
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise GSCAIError(f"{csv_path} 不是 UTF-8 CSV。") from exc

    reader = csv.DictReader(io.StringIO(text, newline=""))
    mapping, fields = _map_headers(csv_path, reader.fieldnames or ())
    rows: list[AIRow] = []
    placeholder_rows = 0
    for row_number, raw_row in enumerate(reader, start=2):
        if None in raw_row:
            raise GSCAIError(f"{csv_path} 第 {row_number} 行的字段数多于表头。")
        if all((value or "").strip() == "" for value in raw_row.values()):
            continue
        canonical_row = {
            mapping[original]: (value or "").strip()
            for original, value in raw_row.items()
            if original in mapping
        }
        day = None
        if "date" in fields:
            if not canonical_row.get("date"):
                raise GSCAIError(f"{csv_path} 第 {row_number} 行：日期不能为空。")
            day = parse_date(canonical_row["date"], context=f"{csv_path} 第 {row_number} 行：")
        impressions, normalized_placeholder = _parse_impressions(
            canonical_row["impressions"], path=csv_path, row_number=row_number
        )
        placeholder_rows += int(normalized_placeholder)
        page_pii = _page_pii_kind(canonical_row.get("page", ""))
        if page_pii:
            raise GSCAIError(
                f"{_report_file_reference(csv_path)}：第 {row_number} 行的页面维度疑似包含"
                f"{page_pii}；为避免 PII 进入 cohort 报告，已在聚合前拒绝。"
                "请先在来源系统移除敏感 URL 参数或不可逆脱敏该行。"
            )
        rows.append(
            AIRow(
                row_number=row_number,
                day=day,
                dimensions={
                    dimension: canonical_row.get(dimension, "")
                    for dimension in DIMENSIONS
                    if dimension in fields
                },
                impressions=impressions,
            )
        )
    if not rows:
        raise GSCAIError(f"{csv_path}：CSV 没有可用数据行。")
    grain_fields = [field for field in ("date", *DIMENSIONS) if field in fields]
    seen_grain: dict[tuple[object, ...], int] = {}
    for row in rows:
        key = tuple(
            row.day if field == "date" else row.dimensions.get(field, "").strip()
            for field in grain_fields
        )
        first_row = seen_grain.get(key)
        if first_row is not None:
            grain_label = " + ".join(FIELD_LABELS[field] for field in grain_fields) or "overall"
            raise GSCAIError(
                f"{csv_path}：第 {first_row} 行与第 {row.row_number} 行的完整聚合粒度"
                f"（{grain_label}）重复；拒绝加总以免展示次数翻倍。"
            )
        seen_grain[key] = row.row_number
    return AIDataset(
        path=csv_path,
        rows=tuple(rows),
        fields=fields,
        original_headers=tuple(reader.fieldnames or ()),
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        normalized_placeholder_rows=placeholder_rows,
    )


def select_window(
    dataset: AIDataset, start: date, end: date, label: str
) -> tuple[AIRow, ...]:
    if start > end:
        raise GSCAIError(f"{label}的开始日期不能晚于结束日期。")
    if "date" not in dataset.fields:
        raise GSCAIError(f"{dataset.path}：单文件窗口模式需要“Date/日期”列。")
    selected = tuple(
        row for row in dataset.rows if row.day is not None and start <= row.day <= end
    )
    if not selected:
        raise GSCAIError(
            f"{label} {start.isoformat()} 至 {end.isoformat()} 没有匹配的数据行。"
        )
    return selected


def aggregate(rows: Sequence[AIRow]) -> dict[str, int | float]:
    impressions = sum(row.impressions for row in rows)
    return {
        "impressions": _clean_number(impressions),
        "rows": len(rows),
        "zero_impression_rows": sum(row.impressions == 0 for row in rows),
    }


def metric_delta(
    current: Mapping[str, int | float], baseline: Mapping[str, int | float]
) -> dict[str, int | float | str | None]:
    current_value = float(current["impressions"])
    baseline_value = float(baseline["impressions"])
    relative = None
    reason = "baseline_impressions_zero"
    if baseline_value > 0:
        relative = _clean_number((current_value - baseline_value) / baseline_value)
        reason = None
    return {
        "impressions_absolute": _clean_number(current_value - baseline_value),
        "impressions_relative": relative,
        "impressions_relative_reason": reason,
    }


def _empty_metrics() -> dict[str, int]:
    return {"impressions": 0, "rows": 0, "zero_impression_rows": 0}


def _aggregate_dimension(
    rows: Sequence[AIRow], dimension: str
) -> dict[str, dict[str, int | float]]:
    grouped_rows: dict[str, list[AIRow]] = {}
    for row in rows:
        value = row.dimensions.get(dimension, "").strip()
        if value:
            grouped_rows.setdefault(value, []).append(row)
    return {key: aggregate(value) for key, value in grouped_rows.items()}


def _cohort_report(
    current_rows: Sequence[AIRow],
    baseline_rows: Sequence[AIRow],
    dimension: str,
    *,
    available: bool,
    top: int,
) -> dict[str, object]:
    if not available:
        return {
            "label": DIMENSION_LABELS[dimension],
            "available": False,
            "unavailable_reason": "dimension_not_present_in_both_periods",
            "groups_total": 0,
            "groups_returned": 0,
            "rows": [],
        }
    current_groups = _aggregate_dimension(current_rows, dimension)
    baseline_groups = _aggregate_dimension(baseline_rows, dimension)
    entries: list[dict[str, object]] = []
    for value in set(current_groups) | set(baseline_groups):
        current = current_groups.get(value, _empty_metrics())
        baseline = baseline_groups.get(value, _empty_metrics())
        entries.append(
            {
                "value": value,
                "baseline": baseline,
                "current": current,
                "delta": metric_delta(current, baseline),
            }
        )
    entries.sort(
        key=lambda item: (
            -float(item["current"]["impressions"]),  # type: ignore[index]
            -float(item["baseline"]["impressions"]),  # type: ignore[index]
            str(item["value"]),
        )
    )
    returned = entries if top == 0 else entries[:top]
    return {
        "label": DIMENSION_LABELS[dimension],
        "available": True,
        "unavailable_reason": None,
        "groups_total": len(entries),
        "groups_returned": len(returned),
        "rows": returned,
    }


def _normalize_optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise GSCAIError(f"{field} 必须是字符串或 null。")
    normalized = value.strip()
    return normalized or None


def _normalize_data_as_of(value: Any, field: str) -> str | None:
    normalized = _normalize_optional_text(value, field)
    if normalized is None:
        return None
    try:
        parsed = datetime.fromisoformat(
            normalized[:-1] + "+00:00"
            if normalized.endswith(("Z", "z"))
            else normalized
        )
    except ValueError as exc:
        raise GSCAIError(f"{field} 必须是带 UTC 偏移的 ISO 8601 时间戳。") from exc
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
        or re.search(r"(?:[Zz]|[+-]\d{2}:\d{2})$", normalized) is None
    ):
        raise GSCAIError(f"{field} 必须包含 Z 或 +08:00 这类 UTC 偏移。")
    return normalized


def _as_of_date(value: str) -> date:
    parsed = datetime.fromisoformat(
        value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    )
    return parsed.astimezone(ZoneInfo(SOURCE_TIMEZONE)).date()


def _optional_bool(value: Any, field: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise GSCAIError(f"{field} 必须是 true、false 或 null。")


def _period(
    label: str,
    dataset: AIDataset,
    rows: Sequence[AIRow],
    requested_start: date | None,
    requested_end: date | None,
) -> dict[str, str | int | None]:
    days = [row.day for row in rows if row.day is not None]
    observed_start = min(days) if days else None
    observed_end = max(days) if days else None
    effective_start = requested_start or observed_start
    effective_end = requested_end or observed_end
    period_days = None
    if requested_start is not None and requested_end is not None:
        period_days = (requested_end - requested_start).days + 1
    elif observed_start is not None and observed_end is not None:
        period_days = (observed_end - observed_start).days + 1
    return {
        "label": label,
        "requested_start": requested_start.isoformat() if requested_start else None,
        "requested_end": requested_end.isoformat() if requested_end else None,
        "observed_start": observed_start.isoformat() if observed_start else None,
        "observed_end": observed_end.isoformat() if observed_end else None,
        "effective_start": effective_start.isoformat() if effective_start else None,
        "effective_end": effective_end.isoformat() if effective_end else None,
        "boundary_source": "declared" if requested_start is not None else "observed",
        "calendar_days": period_days,
        "source": _report_file_reference(dataset.path),
    }


def _window_bounds(
    rows: Sequence[AIRow],
    requested_start: date | None,
    requested_end: date | None,
    label: str,
) -> tuple[date, date]:
    if (requested_start is None) != (requested_end is None):
        raise GSCAIError(f"{label}必须同时声明开始日期和结束日期。")
    observed = [row.day for row in rows if row.day is not None]
    if requested_start is None:
        if not observed:
            raise GSCAIError(
                f"{label}没有 Date/日期列，必须显式声明该窗口的开始和结束日期。"
            )
        return min(observed), max(observed)
    assert requested_end is not None
    if requested_start > requested_end:
        raise GSCAIError(f"{label}的开始日期不能晚于结束日期。")
    outside = [
        row.row_number
        for row in rows
        if row.day is not None and not requested_start <= row.day <= requested_end
    ]
    if outside:
        examples = "、".join(str(item) for item in outside[:5])
        raise GSCAIError(
            f"{label}存在落在声明边界之外的数据行（例如第 {examples} 行）；"
            "拒绝把部分覆盖误当成完整窗口。"
        )
    return requested_start, requested_end


def _comparison_window_bounds(
    current_rows: Sequence[AIRow],
    baseline_rows: Sequence[AIRow],
    *,
    current_start: date | None,
    current_end: date | None,
    baseline_start: date | None,
    baseline_end: date | None,
) -> dict[str, tuple[date, date]]:
    baseline = _window_bounds(
        baseline_rows, baseline_start, baseline_end, "基线窗口"
    )
    current = _window_bounds(current_rows, current_start, current_end, "当前窗口")
    if baseline[1] >= current[0]:
        raise GSCAIError("基线窗口与当前窗口必须不重叠，且基线必须严格在当前窗口之前。")
    return {"baseline": baseline, "current": current}


def _coverage(dataset: AIDataset, rows: Sequence[AIRow]) -> dict[str, object]:
    selected_ids = {id(row) for row in rows}
    dimensions: dict[str, dict[str, int | bool]] = {}
    for dimension in DIMENSIONS:
        present = dimension in dataset.fields
        populated = sum(bool(row.dimensions.get(dimension, "").strip()) for row in rows)
        dimensions[dimension] = {
            "column_present": present,
            "populated_rows": populated if present else 0,
            "blank_rows": len(rows) - populated if present else 0,
        }
    days = [row.day for row in rows if row.day is not None]
    return {
        "source_rows": len(dataset.rows),
        "included_rows": len(rows),
        "excluded_rows": sum(id(row) not in selected_ids for row in dataset.rows),
        "date_column_present": "date" in dataset.fields,
        "observed_date_start": min(days).isoformat() if days else None,
        "observed_date_end": max(days).isoformat() if days else None,
        "zero_impression_rows": sum(row.impressions == 0 for row in rows),
        "normalized_placeholder_rows_in_source": dataset.normalized_placeholder_rows,
        "dimensions": dimensions,
    }


def _source_contract(
    source_id: str,
    dataset: AIDataset,
    rows: Sequence[AIRow],
    *,
    property_id: str | None,
    filters: str | None,
    metadata: Mapping[str, Any] | None,
    required_end: date | None,
) -> dict[str, object]:
    raw = dict(metadata or {})
    unknown_keys = set(raw) - {
        "source_kind",
        "property_id",
        "source_timezone",
        "source_timezone_label",
        "data_as_of",
        "finality",
        "preliminary",
        "completeness",
        "row_limit_hit",
        "filters",
    }
    if unknown_keys:
        raise GSCAIError(
            f"{source_id} 来源元数据包含未知字段：{', '.join(sorted(unknown_keys))}。"
        )

    source_kind = raw.get("source_kind", SOURCE_KIND)
    if source_kind != SOURCE_KIND:
        raise GSCAIError(
            f"{source_id}.source_kind 必须是 {SOURCE_KIND!r}，不能把普通 Performance CSV 当成本报告。"
        )
    timezone_name = raw.get("source_timezone", SOURCE_TIMEZONE)
    timezone_label = raw.get("source_timezone_label", SOURCE_TIMEZONE_LABEL)
    if timezone_name != SOURCE_TIMEZONE or timezone_label != SOURCE_TIMEZONE_LABEL:
        raise GSCAIError(
            f"{source_id} 的日期口径必须记录为 {SOURCE_TIMEZONE}（{SOURCE_TIMEZONE_LABEL}）。"
        )
    source_property = _normalize_optional_text(
        raw.get("property_id", property_id), f"{source_id}.property_id"
    )
    source_filters = _normalize_optional_text(
        raw.get("filters", filters), f"{source_id}.filters"
    )
    data_as_of = _normalize_data_as_of(raw.get("data_as_of"), f"{source_id}.data_as_of")

    finality = raw.get("finality", "unknown")
    if finality not in FINALITY_VALUES:
        raise GSCAIError(
            f"{source_id}.finality 只能是 final、preliminary 或 unknown。"
        )
    explicit_preliminary = _optional_bool(
        raw.get("preliminary"), f"{source_id}.preliminary"
    )
    preliminary = finality == "preliminary" if explicit_preliminary is None else explicit_preliminary
    if explicit_preliminary is not None and explicit_preliminary != (finality == "preliminary"):
        raise GSCAIError(
            f"{source_id}.preliminary 与 finality={finality!r} 不一致。"
        )

    completeness = raw.get("completeness", "unknown")
    if completeness not in COMPLETENESS_VALUES:
        raise GSCAIError(
            f"{source_id}.completeness 只能是 complete、incomplete 或 unknown。"
        )
    row_limit_hit = _optional_bool(raw.get("row_limit_hit"), f"{source_id}.row_limit_hit")
    at_or_above_limit = len(dataset.rows) >= UI_ROW_LIMIT

    issues: list[dict[str, str]] = []
    if source_property is None:
        issues.append({"code": "property_missing", "severity": "unknown"})
    if source_filters is None:
        issues.append({"code": "filters_missing", "severity": "unknown"})
    if data_as_of is None:
        issues.append({"code": "data_as_of_missing", "severity": "unknown"})
    elif required_end is not None and _as_of_date(data_as_of) < required_end:
        issues.append({"code": "data_as_of_before_window_end", "severity": "limited"})
    if finality == "unknown":
        issues.append({"code": "finality_unknown", "severity": "unknown"})
    elif preliminary:
        issues.append({"code": "data_preliminary", "severity": "limited"})
    if completeness == "unknown":
        issues.append({"code": "completeness_unknown", "severity": "unknown"})
    elif completeness == "incomplete":
        issues.append({"code": "completeness_incomplete", "severity": "limited"})
    if row_limit_hit is None:
        issues.append({"code": "row_limit_status_unknown", "severity": "unknown"})
    elif row_limit_hit:
        issues.append({"code": "ui_row_limit_hit", "severity": "limited"})
    if at_or_above_limit:
        issues.append({"code": "source_rows_at_or_above_ui_limit", "severity": "limited"})
    if dataset.normalized_placeholder_rows:
        issues.append({"code": "ui_placeholders_normalized_to_zero", "severity": "unknown"})

    if any(item["severity"] == "limited" for item in issues):
        status = "limited"
    elif issues:
        status = "unknown"
    else:
        status = "complete"

    return {
        "source_id": source_id,
        "path": _report_file_reference(dataset.path),
        "sha256": dataset.sha256,
        "source_kind": SOURCE_KIND,
        "property_id": source_property,
        "search_type": SEARCH_TYPE,
        "web_performance_relationship": "subset_non_additive",
        "source_timezone": SOURCE_TIMEZONE,
        "source_timezone_label": SOURCE_TIMEZONE_LABEL,
        "data_as_of": data_as_of,
        "finality": finality,
        "preliminary": preliminary,
        "completeness": completeness,
        "ui_row_limit": UI_ROW_LIMIT,
        "row_limit_hit": row_limit_hit,
        "source_rows_at_or_above_ui_limit": at_or_above_limit,
        "filters": source_filters,
        "source_rows": len(dataset.rows),
        "included_rows": len(rows),
        "quality": {"status": status, "issues": issues},
    }


def build_report(
    current_dataset: AIDataset,
    baseline_dataset: AIDataset,
    *,
    current_rows: Sequence[AIRow] | None = None,
    baseline_rows: Sequence[AIRow] | None = None,
    current_start: date | None = None,
    current_end: date | None = None,
    baseline_start: date | None = None,
    baseline_end: date | None = None,
    property_id: str | None = None,
    filters: str | None = None,
    source_metadata: Mapping[str, Mapping[str, Any]] | None = None,
    top: int = 20,
) -> dict[str, object]:
    if top < 0:
        raise GSCAIError("--top 不能小于 0。")
    current = tuple(current_rows if current_rows is not None else current_dataset.rows)
    baseline = tuple(baseline_rows if baseline_rows is not None else baseline_dataset.rows)
    if not current:
        raise GSCAIError("当前窗口没有数据行。")
    if not baseline:
        raise GSCAIError("基线窗口没有数据行。")

    window_bounds = _comparison_window_bounds(
        current,
        baseline,
        current_start=current_start,
        current_end=current_end,
        baseline_start=baseline_start,
        baseline_end=baseline_end,
    )

    current_grain = [field for field in ("date", *DIMENSIONS) if field in current_dataset.fields]
    baseline_grain = [field for field in ("date", *DIMENSIONS) if field in baseline_dataset.fields]
    if current_grain != baseline_grain:
        raise GSCAIError(
            "两期口径不一致：CSV 的日期/页面/国家/地区/设备维度必须完全相同；"
            f"当前为 {current_grain or ['overall']}，基线为 {baseline_grain or ['overall']}。"
        )

    metadata = dict(source_metadata or {})
    unknown_periods = set(metadata) - {"baseline", "current"}
    if unknown_periods:
        raise GSCAIError(
            f"source_metadata 只允许 baseline/current，当前包含：{', '.join(sorted(unknown_periods))}。"
        )

    current_required_end = window_bounds["current"][1]
    baseline_required_end = window_bounds["baseline"][1]
    sources = {
        "baseline": _source_contract(
            "baseline",
            baseline_dataset,
            baseline,
            property_id=property_id,
            filters=filters,
            metadata=metadata.get("baseline"),
            required_end=baseline_required_end,
        ),
        "current": _source_contract(
            "current",
            current_dataset,
            current,
            property_id=property_id,
            filters=filters,
            metadata=metadata.get("current"),
            required_end=current_required_end,
        ),
    }
    if sources["baseline"]["property_id"] != sources["current"]["property_id"]:
        raise GSCAIError("两期口径不一致：property_id 不同，不能直接比较。")
    if sources["baseline"]["filters"] != sources["current"]["filters"]:
        raise GSCAIError("两期口径不一致：过滤条件不同，不能直接比较。")

    dimensions = [dimension for dimension in DIMENSIONS if dimension in current_dataset.fields]
    periods = {
        "baseline": _period(
            "基线窗口", baseline_dataset, baseline, baseline_start, baseline_end
        ),
        "current": _period("当前窗口", current_dataset, current, current_start, current_end),
    }
    report_issues: list[dict[str, str]] = []
    for source_id in ("baseline", "current"):
        source_quality = sources[source_id]["quality"]
        assert isinstance(source_quality, Mapping)
        for issue in source_quality["issues"]:  # type: ignore[index]
            report_issues.append({"source": source_id, **issue})

    baseline_days_count = periods["baseline"]["calendar_days"]
    current_days_count = periods["current"]["calendar_days"]
    windows_aligned = (
        baseline_days_count is not None
        and current_days_count is not None
        and baseline_days_count == current_days_count
    )
    if baseline_days_count is None or current_days_count is None:
        report_issues.append(
            {
                "source": "comparison",
                "code": "window_length_unknown",
                "severity": "unknown",
            }
        )
    elif not windows_aligned:
        report_issues.append(
            {
                "source": "comparison",
                "code": "window_length_mismatch",
                "severity": "limited",
            }
        )

    if any(issue["severity"] == "limited" for issue in report_issues):
        quality_status = "limited"
    elif report_issues:
        quality_status = "unknown"
    else:
        quality_status = "complete"

    current_metrics = aggregate(current)
    baseline_metrics = aggregate(baseline)
    missing_dimensions = [dimension for dimension in DIMENSIONS if dimension not in dimensions]
    contract_complete = all(
        [
            sources["baseline"]["property_id"],
            sources["baseline"]["filters"],
            sources["baseline"]["data_as_of"],
            sources["current"]["data_as_of"],
            sources["baseline"]["finality"] != "unknown",
            sources["current"]["finality"] != "unknown",
            sources["baseline"]["completeness"] != "unknown",
            sources["current"]["completeness"] != "unknown",
            sources["baseline"]["row_limit_hit"] is not None,
            sources["current"]["row_limit_hit"] is not None,
        ]
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "analysis_kind": "descriptive_gsc_generative_ai_window_comparison",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "methodology": {
            "metric": "impressions_only",
            "causal_inference": False,
            "aggregation": "sum_of_rows_within_each_same-grain_export",
            "zero_denominator": (
                "基线展示次数为 0 时，相对变化返回 null，并记录 "
                "impressions_relative_reason=baseline_impressions_zero。"
            ),
            "warnings": [
                SUBSET_WARNING,
                INFERENCE_WARNING,
                CAUSALITY_WARNING,
                AGGREGATION_WARNING,
            ],
            "official_sources": [
                OFFICIAL_REPORT_URL,
                OFFICIAL_CONTROL_URL,
                OFFICIAL_GUIDE_URL,
            ],
        },
        "limitations": {
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
        },
        "dataset_contract": {
            "source_kind": SOURCE_KIND,
            "property_id": sources["baseline"]["property_id"],
            "search_type": SEARCH_TYPE,
            "web_performance_relationship": "subset_non_additive",
            "source_timezone": SOURCE_TIMEZONE,
            "source_timezone_label": SOURCE_TIMEZONE_LABEL,
            "temporal_grain": "date",
            "ui_row_limit": UI_ROW_LIMIT,
            "current_grain": current_grain,
            "baseline_grain": baseline_grain,
            "grains_aligned": True,
            "filters": {
                "baseline": sources["baseline"]["filters"],
                "current": sources["current"]["filters"],
            },
            "filters_aligned": True,
            "windows_disjoint": True,
            "baseline_precedes_current": True,
            "window_lengths_aligned": windows_aligned,
            "contract_complete": contract_complete,
        },
        "periods": periods,
        "coverage": {
            "baseline": _coverage(baseline_dataset, baseline),
            "current": _coverage(current_dataset, current),
            "shared_dimensions": dimensions,
            "missing_dimensions": missing_dimensions,
        },
        "sources": sources,
        "data_quality": {
            "status": quality_status,
            "complete": quality_status == "complete",
            "issues": report_issues,
        },
        "verdict_eligibility": {
            "recommended_verdict": (
                "descriptive" if quality_status == "complete" else "inconclusive"
            ),
            "maximum_supported_verdict": "descriptive",
            "causal_or_incremental_claim_allowed": False,
            "reasons": [
                f"{issue['source']}:{issue['code']}" for issue in report_issues
            ]
            or ["完整性元数据已记录；工具仍只支持描述性比较。"],
        },
        "overall": {
            "label": "同维度 CSV 行展示次数之和（不保证等于图表 property 总数）",
            "baseline": baseline_metrics,
            "current": current_metrics,
            "delta": metric_delta(current_metrics, baseline_metrics),
        },
        "cohorts": {
            dimension: _cohort_report(
                current,
                baseline,
                dimension,
                available=dimension in dimensions,
                top=top,
            )
            for dimension in DIMENSIONS
        },
    }


def _fmt_number(value: int | float | None) -> str:
    if value is None:
        return "不可计算"
    if isinstance(value, int) or float(value).is_integer():
        return f"{int(value):,}"
    return f"{float(value):,.4f}".rstrip("0").rstrip(".")


def _fmt_relative(value: int | float | None, reason: str | None) -> str:
    if value is None:
        labels = {"baseline_impressions_zero": "不可计算（基线展示次数为 0）"}
        return labels.get(reason or "", "不可计算")
    return f"{float(value):+.2%}"


def render_markdown(report: Mapping[str, Any]) -> str:
    overall = report["overall"]
    delta = overall["delta"]
    lines = [
        "# GSC 生成式 AI 展示次数窗口比较",
        "",
        f"- 数据质量：`{report['data_quality']['status']}`",
        f"- GSC property：`{report['dataset_contract']['property_id'] or '未记录'}`",
        f"- 日期口径：`{SOURCE_TIMEZONE}`（{SOURCE_TIMEZONE_LABEL}）",
        f"- 来源类型：`{SOURCE_KIND}`",
        "",
        "## 总体（同维度 CSV 行之和）",
        "",
        "| 指标 | 基线 | 当前 | 绝对变化 | 相对变化 |",
        "|---|---:|---:|---:|---:|",
        "| 展示次数 | {} | {} | {:+,} | {} |".format(
            _fmt_number(overall["baseline"]["impressions"]),
            _fmt_number(overall["current"]["impressions"]),
            delta["impressions_absolute"],
            _fmt_relative(
                delta["impressions_relative"], delta["impressions_relative_reason"]
            ),
        ),
        "",
        f"> {overall['label']}",
        "",
    ]
    for dimension in DIMENSIONS:
        cohort = report["cohorts"][dimension]
        lines.extend([f"## {cohort['label']} cohort", ""])
        if not cohort["available"]:
            lines.extend(["该维度未同时出现在两期 CSV 中，未进行比较。", ""])
            continue
        lines.extend(
            [
                "| 值 | 基线展示 | 当前展示 | 绝对变化 | 相对变化 |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for item in cohort["rows"]:
            item_delta = item["delta"]
            lines.append(
                "| {} | {} | {} | {:+,} | {} |".format(
                    str(item["value"]).replace("|", "\\|"),
                    _fmt_number(item["baseline"]["impressions"]),
                    _fmt_number(item["current"]["impressions"]),
                    item_delta["impressions_absolute"],
                    _fmt_relative(
                        item_delta["impressions_relative"],
                        item_delta["impressions_relative_reason"],
                    ),
                )
            )
        lines.append("")

    lines.extend(["## 数据完整性", ""])
    for source_id, label in (("baseline", "基线"), ("current", "当前")):
        source = report["sources"][source_id]
        lines.append(
            f"- {label}：finality=`{source['finality']}`，"
            f"completeness=`{source['completeness']}`，"
            f"row_limit_hit=`{source['row_limit_hit']}`，"
            f"data_as_of=`{source['data_as_of'] or '未记录'}`，SHA-256=`{source['sha256']}`"
        )
    lines.extend(["", "## 解读边界", ""])
    for warning in report["methodology"]["warnings"]:
        lines.append(f"- {warning}")
    lines.extend(
        [
            "- 本工具不输出点击、CTR、查询、引用、转化或收入估算。",
            "",
            "## 官方依据",
            "",
        ]
    )
    for url in report["methodology"]["official_sources"]:
        lines.append(f"- {url}")
    lines.append("")
    return "\n".join(lines)


def _write_text(path: Path, content: str, label: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise GSCAIError(f"无法写入{label} {path}：{exc}。") from exc


def create_parser() -> argparse.ArgumentParser:
    parser = ChineseArgumentParser(
        description=(
            "比较 Google Search Console 生成式 AI 效果报告 CSV 的展示次数。"
            "只接收日期、页面、国家/地区、设备和展示次数，不推断点击、CTR、查询、引用或转化。"
        ),
        epilog=(
            "双文件示例：python gsc_ai_compare.py --baseline before.csv --current after.csv "
            "--property-id sc-domain:example.com --filters none\n"
            "单文件示例：python gsc_ai_compare.py --input export.csv "
            "--baseline-start 2026-05-01 --baseline-end 2026-05-31 "
            "--current-start 2026-06-01 --current-end 2026-06-30"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    parser.add_argument("-h", "--help", action="help", help="显示帮助并退出")
    parser.add_argument("--current", type=Path, help="当前窗口的独立 CSV")
    parser.add_argument("--baseline", type=Path, help="基线窗口的独立 CSV")
    parser.add_argument("--input", type=Path, help="含 Date/日期列的单个 CSV")
    parser.add_argument("--current-start", help="当前窗口开始日期；无 Date 的双文件模式必须提供")
    parser.add_argument("--current-end", help="当前窗口结束日期；无 Date 的双文件模式必须提供")
    parser.add_argument("--baseline-start", help="基线窗口开始日期；无 Date 的双文件模式必须提供")
    parser.add_argument("--baseline-end", help="基线窗口结束日期；无 Date 的双文件模式必须提供")
    parser.add_argument("--property-id", "--property", dest="property_id", help="GSC property")
    parser.add_argument(
        "--filters",
        help="两期共同过滤条件；无过滤时建议明确写 none，不要留空",
    )
    parser.add_argument("--baseline-filters", help="覆盖基线过滤条件")
    parser.add_argument("--current-filters", help="覆盖当前过滤条件")
    parser.add_argument("--data-as-of", help="两期共同的带 UTC 偏移 ISO 8601 截止时间")
    parser.add_argument("--baseline-data-as-of", help="覆盖基线数据截止日期/时间")
    parser.add_argument("--current-data-as-of", help="覆盖当前数据截止日期/时间")
    parser.add_argument(
        "--finality",
        choices=sorted(FINALITY_VALUES),
        default="unknown",
        help="两期共同成熟状态（final/preliminary/unknown）",
    )
    parser.add_argument("--baseline-finality", choices=sorted(FINALITY_VALUES))
    parser.add_argument("--current-finality", choices=sorted(FINALITY_VALUES))
    parser.add_argument(
        "--completeness",
        choices=sorted(COMPLETENESS_VALUES),
        default="unknown",
        help="两期共同完整性（complete/incomplete/unknown）",
    )
    parser.add_argument("--baseline-completeness", choices=sorted(COMPLETENESS_VALUES))
    parser.add_argument("--current-completeness", choices=sorted(COMPLETENESS_VALUES))
    parser.add_argument(
        "--row-limit-hit",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="是否触及 UI 1000 行限制；未知时不要猜测",
    )
    parser.add_argument(
        "--baseline-row-limit-hit",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="覆盖基线是否触及 UI 1000 行限制",
    )
    parser.add_argument(
        "--current-row-limit-hit",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="覆盖当前是否触及 UI 1000 行限制",
    )
    parser.add_argument(
        "--top", type=int, default=20, help="每个 cohort 输出数量（默认 20，0 表示全部）"
    )
    parser.add_argument("--json-out", type=Path, help="写入机器可读 JSON 报告")
    parser.add_argument("--markdown-out", type=Path, help="写入中文 Markdown 报告")
    return parser


def _resolve_inputs(args: argparse.Namespace) -> tuple[
    AIDataset,
    AIDataset,
    tuple[AIRow, ...],
    tuple[AIRow, ...],
    date | None,
    date | None,
    date | None,
    date | None,
]:
    window_values = (
        args.current_start,
        args.current_end,
        args.baseline_start,
        args.baseline_end,
    )
    if args.input:
        if args.current or args.baseline:
            raise GSCAIError("--input 不能与 --current/--baseline 同时使用。")
        if not all(window_values):
            raise GSCAIError(
                "单文件模式必须同时提供 --baseline-start、--baseline-end、"
                "--current-start 和 --current-end。"
            )
        baseline_start = parse_date(args.baseline_start, context="--baseline-start ")
        baseline_end = parse_date(args.baseline_end, context="--baseline-end ")
        current_start = parse_date(args.current_start, context="--current-start ")
        current_end = parse_date(args.current_end, context="--current-end ")
        if baseline_end >= current_start:
            raise GSCAIError("基线窗口与当前窗口必须不重叠，且基线必须严格在前。")
        dataset = read_gsc_ai_csv(args.input)
        baseline_rows = select_window(dataset, baseline_start, baseline_end, "基线窗口")
        current_rows = select_window(dataset, current_start, current_end, "当前窗口")
        return (
            dataset,
            dataset,
            current_rows,
            baseline_rows,
            current_start,
            current_end,
            baseline_start,
            baseline_end,
        )
    if not args.current or not args.baseline:
        raise GSCAIError("请使用 --current 和 --baseline，或使用 --input 单文件模式。")
    if any(window_values) and not all(window_values):
        raise GSCAIError("双文件模式声明日期边界时，必须同时提供四个窗口日期参数。")
    current_dataset = read_gsc_ai_csv(args.current)
    baseline_dataset = read_gsc_ai_csv(args.baseline)
    if all(window_values):
        baseline_start = parse_date(args.baseline_start, context="--baseline-start ")
        baseline_end = parse_date(args.baseline_end, context="--baseline-end ")
        current_start = parse_date(args.current_start, context="--current-start ")
        current_end = parse_date(args.current_end, context="--current-end ")
    else:
        current_start = current_end = baseline_start = baseline_end = None
    return (
        current_dataset,
        baseline_dataset,
        current_dataset.rows,
        baseline_dataset.rows,
        current_start,
        current_end,
        baseline_start,
        baseline_end,
    )


def run(args: argparse.Namespace) -> dict[str, object]:
    (
        current_dataset,
        baseline_dataset,
        current_rows,
        baseline_rows,
        current_start,
        current_end,
        baseline_start,
        baseline_end,
    ) = _resolve_inputs(args)
    source_metadata: dict[str, dict[str, object]] = {}
    for source_id in ("baseline", "current"):
        row_limit_override = getattr(args, f"{source_id}_row_limit_hit")
        source_metadata[source_id] = {
            "data_as_of": getattr(args, f"{source_id}_data_as_of") or args.data_as_of,
            "finality": getattr(args, f"{source_id}_finality") or args.finality,
            "completeness": (
                getattr(args, f"{source_id}_completeness") or args.completeness
            ),
            "row_limit_hit": (
                row_limit_override if row_limit_override is not None else args.row_limit_hit
            ),
            "filters": getattr(args, f"{source_id}_filters") or args.filters,
        }
    return build_report(
        current_dataset,
        baseline_dataset,
        current_rows=current_rows,
        baseline_rows=baseline_rows,
        current_start=current_start,
        current_end=current_end,
        baseline_start=baseline_start,
        baseline_end=baseline_end,
        property_id=args.property_id,
        filters=args.filters,
        source_metadata=source_metadata,
        top=args.top,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    try:
        report = run(args)
        markdown = render_markdown(report)
        if args.json_out:
            _write_text(
                args.json_out,
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                "JSON 报告",
            )
        if args.markdown_out:
            _write_text(args.markdown_out, markdown, "Markdown 报告")
        else:
            print(markdown)
        return 0
    except GSCAIError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
