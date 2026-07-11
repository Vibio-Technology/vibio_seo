#!/usr/bin/env python3
"""CSV-first SEO 业务复盘。

只处理指定的聚合 cohort，不读取查询词或用户级数据，不从前后对比推断因果。
本文件只使用 Python 标准库，可独立复制执行。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import urllib.parse
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


TOOL_NAME = "vibio-seo-measurement-review"
TOOL_VERSION = "1.2.0"
SCHEMA_VERSION = "1.2"
DEFAULT_GSC_SOURCE_TIMEZONE = "America/Los_Angeles"
FINALITY_VALUES = {"final", "preliminary", "unknown"}
DATA_QUALITY_VALUES = {"complete", "degraded", "unknown"}
SOURCE_LABELS = {
    "gsc_page": "GSC 页面数据",
    "ga4": "GA4 登陆页数据",
    "crm": "CRM 聚合 cohort",
    "mapping": "口径配置",
}
SOURCE_KINDS = {
    "gsc_page": "gsc_search_analytics",
    "ga4": "ga4_property_report",
    "crm": "crm_aggregate_export",
}
SOURCE_GRAINS = {
    "gsc_page": ("date", "landing_page", "country", "device"),
    "ga4": ("date", "landing_page", "country", "device"),
    "crm": ("date", "landing_page", "country"),
}
REQUIRED_METRICS = {
    "gsc_page": ("clicks", "impressions"),
    "ga4": ("sessions", "conversions"),
}
DEFAULT_METRIC_MAPPING = {
    "gsc_page": {"clicks": "clicks", "impressions": "impressions"},
    "ga4": {"sessions": "sessions", "conversions": "conversions"},
}
SAFE_NON_GRAIN_HEADERS = {
    "gsc_page": {
        "ctr",
        "average ctr",
        "点击率",
        "平均点击率",
        "position",
        "average position",
        "排名",
        "平均排名",
    },
    "ga4": set(),
    "crm": set(),
}
DERIVED_METRICS = {
    "gsc_page": {"ctr": ("clicks", "impressions")},
    "ga4": {"conversion_rate": ("conversions", "sessions")},
    "crm": {"qualified_rate": ("qualified", "leads")},
}
RATE_METRICS = {"ctr", "conversion_rate", "qualified_rate"}
METRIC_LABELS = {
    "clicks": "点击",
    "impressions": "展示",
    "ctr": "CTR",
    "sessions": "会话",
    "conversions": "转化",
    "conversion_rate": "转化率",
    "leads": "线索",
    "qualified": "合格线索",
    "qualified_rate": "合格率",
    "pipeline_value": "商机金额",
    "opportunities": "商机数",
    "won": "成交数",
    "revenue": "收入",
    "customers": "客户数",
}

# 查询词会把搜索意图与下游业务数据过度关联，所有来源都拒绝。
QUERY_HEADERS = {
    "query",
    "queries",
    "search_query",
    "search_queries",
    "search_term",
    "search_terms",
    "keyword",
    "keywords",
    "查询",
    "查询词",
    "搜索词",
    "关键词",
    "热门查询",
}

# 只按表头拦截；脚本不尝试检查或输出原始值。
PII_HEADERS = {
    "id",
    "email",
    "email_address",
    "e_mail",
    "phone",
    "phone_number",
    "mobile",
    "mobile_phone",
    "telephone",
    "lead_id",
    "contact_id",
    "customer_id",
    "user_id",
    "client_id",
    "visitor_id",
    "session_id",
    "account_id",
    "record_id",
    "order_id",
    "opportunity_id",
    "full_name",
    "first_name",
    "last_name",
    "name",
    "address",
    "ip",
    "ip_address",
    "cookie_id",
    "gclid",
    "msclkid",
    "fbclid",
    "邮箱",
    "电子邮箱",
    "手机号",
    "手机号码",
    "电话",
    "电话号码",
    "线索id",
    "联系人id",
    "用户id",
    "客户id",
    "姓名",
    "地址",
    "身份证",
    "身份证号",
}

CRM_RAW_HEADERS = {
    "stage",
    "lead_stage",
    "status",
    "created_at",
    "updated_at",
    "owner",
    "sales_owner",
    "阶段",
    "线索阶段",
    "负责人",
}

REASON_MESSAGES = {
    "no_rows": "该窗口或 cohort 没有行，不用 0 代替缺失。",
    "all_values_blank": "该指标全部为空。",
    "partial_values_blank": "该指标存在空值，为避免低估而不汇总。",
    "zero_denominator": "分母为 0，不返回伪百分比。",
    "baseline_unavailable": "基线窗口值不可用。",
    "current_unavailable": "当前窗口值不可用。",
    "cohort_missing_in_baseline": "基线窗口不存在该 cohort，不补 0。",
    "cohort_missing_in_current": "当前窗口不存在该 cohort，不补 0。",
    "blank_or_invalid_grain": "共享粒度维度为空或 URL 无法规范化。",
    "no_reference_cohorts": "GSC 在该窗口没有可用的参照 cohort。",
    "cross_source_daily_join_forbidden": "来源日界或时间粒度不一致，逐日跨源 join 已被禁止。",
}

JOIN_LIMITATIONS = [
    "仅在 date + normalized landing page + country + device 的允许维度集上比较聚合数据；CRM 没有 device，因此只与 GSC 的 date + landing page + country 聚合键对齐。",
    "GSC 查询词、CRM 原始线索、用户 ID、邮箱、电话等字段被明确拒绝，不进行用户级或线索级拼接。",
    "GSC 点击、GA4 会话与 CRM 线索受时区、同意模式、跨域、归因窗口、阶段回填和数据延迟影响，数值不应被视为同一事件。",
    "URL 映射命中只说明 cohort 键可对齐，不证明流量或商机由 SEO 造成。",
    "纯前后窗口会同时受季节性、品牌需求、广告、产品与网站变更影响；没有合适对照或实验时，只能得出方向性描述。",
    "GSC 常规日数据按 America/Los_Angeles 划日；GA4 按 property 时区，CRM 按其业务系统时区。来源日界不同且只有 date 粒度时，禁止逐日跨源 join，只保留各来源的显式窗口汇总。",
]


class ReviewError(ValueError):
    """可直接向 CLI 用户展示的口径或数据错误。"""


def _report_file_reference(path: Path, fallback: str) -> str:
    """报告只保存文件名，并用已有 SHA-256 绑定原始输入。"""
    return path.name or fallback


class ChineseArgumentParser(argparse.ArgumentParser):
    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法：", 1)

    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace("usage:", "用法：", 1)
            .replace("options:\n", "选项：\n", 1)
            .replace("show this help message and exit", "显示帮助并退出")
            .replace("show program's version number and exit", "显示版本并退出")
        )

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: 参数错误：{message}\n")


@dataclass(frozen=True)
class Window:
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def as_dict(self) -> dict[str, Any]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "days": self.days}


@dataclass(frozen=True)
class ReviewConfig:
    path: Path
    sha256: str
    baseline: Window
    current: Window
    timezone_name: str
    timezone: ZoneInfo
    source_timezones: dict[str, str | None]
    source_metadata: dict[str, dict[str, Any]]
    contract_issues: tuple[dict[str, str], ...]
    property_id: str
    search_type: str
    dimension_mapping: dict[str, dict[str, str]]
    metric_mapping: dict[str, dict[str, str]]
    value_mapping: dict[str, dict[str, str]]
    url_settings: dict[str, Any]
    crm_definition: dict[str, str]


@dataclass(frozen=True)
class URLResult:
    value: str | None
    reason: str | None
    explicitly_mapped: bool


@dataclass(frozen=True)
class DataRow:
    row_number: int
    day: date | None
    landing_page: str | None
    url_reason: str | None
    explicitly_mapped: bool
    country: str | None
    device: str | None
    metrics: dict[str, float | None]
    temporal_grain: str


@dataclass(frozen=True)
class Dataset:
    kind: str
    path: Path
    sha256: str
    headers: tuple[str, ...]
    ignored_headers: tuple[str, ...]
    rows: tuple[DataRow, ...]
    metric_names: tuple[str, ...]
    temporal_grain: str


def _header_key(value: str) -> str:
    normalized = value.strip().lstrip("\ufeff").casefold()
    normalized = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "_", normalized)
    return normalized.strip("_")


def _sensitive_header_kind(value: str) -> str | None:
    key = _header_key(value)
    if key in QUERY_HEADERS:
        return "查询词"
    if key in PII_HEADERS:
        return "用户级或 PII"
    if re.search(r"(?:^|_)(?:id|uuid|guid)(?:_|$)", key):
        return "稳定标识符"
    if re.fullmatch(
        r"(?:account|record|order|opportunity|lead|contact|customer|user|client|visitor|session)(?:id|uuid|guid)",
        key,
    ):
        return "稳定标识符"
    return None


def _clean_number(value: float | int | None) -> float | int | None:
    if value is None:
        return None
    rounded = round(float(value), 10)
    return int(rounded) if rounded.is_integer() else rounded


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise ReviewError(f"找不到{label}：{path}。") from exc
    except IsADirectoryError as exc:
        raise ReviewError(f"{label}路径不是文件：{path}。") from exc
    except OSError as exc:
        raise ReviewError(f"无法读取{label} {path}：{exc}。") from exc


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewError(f"{context}必须是 JSON 对象。")
    return value


def _require_nonempty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewError(f"{context}必须是非空字符串。")
    return value.strip()


def _parse_config_date(value: Any, context: str) -> date:
    raw = _require_nonempty_string(value, context)
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ReviewError(f"{context}必须使用 YYYY-MM-DD，当前为 {raw!r}。") from exc


def _source_mapping(mapping: Mapping[str, Any], kind: str) -> dict[str, Any]:
    value = mapping.get(kind)
    if value is None and kind == "gsc_page":
        value = mapping.get("gsc")
    return _require_object(value, f"dimension_mapping.{kind}")


def _parse_column_mapping(
    raw_mapping: Mapping[str, Any], kind: str, required: Sequence[str]
) -> dict[str, str]:
    source = _source_mapping(raw_mapping, kind)
    allowed = set(SOURCE_GRAINS[kind])
    extras = sorted(set(source) - allowed)
    if extras:
        raise ReviewError(
            f"dimension_mapping.{kind} 包含不允许的共享维度："
            + "、".join(extras)
            + "。"
        )
    result: dict[str, str] = {}
    for canonical in required:
        result[canonical] = _require_nonempty_string(
            source.get(canonical), f"dimension_mapping.{kind}.{canonical}"
        )
    return result


def _parse_metric_mapping(raw: Any, enabled_sources: set[str]) -> dict[str, dict[str, str]]:
    root = {} if raw is None else _require_object(raw, "metric_mapping")
    result: dict[str, dict[str, str]] = {}
    for kind in enabled_sources:
        source_raw = root.get(kind)
        if source_raw is None and kind == "gsc_page":
            source_raw = root.get("gsc")
        if source_raw is None:
            if kind in DEFAULT_METRIC_MAPPING:
                result[kind] = dict(DEFAULT_METRIC_MAPPING[kind])
                continue
            raise ReviewError(
                "提供 --crm 时必须在 metric_mapping.crm 中声明已聚合数值指标。"
            )
        source = _require_object(source_raw, f"metric_mapping.{kind}")
        if not source:
            raise ReviewError(f"metric_mapping.{kind} 不得为空。")
        parsed: dict[str, str] = {}
        for canonical, header in source.items():
            if not isinstance(canonical, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", canonical):
                raise ReviewError(
                    f"metric_mapping.{kind} 的指标名 {canonical!r} 必须是小写 snake_case。"
                )
            key = _header_key(canonical)
            if _sensitive_header_kind(canonical) or key in CRM_RAW_HEADERS:
                raise ReviewError(f"指标名 {canonical!r} 可能是查询、PII 或原始 CRM 字段。")
            configured_header = _require_nonempty_string(
                header, f"metric_mapping.{kind}.{canonical}"
            )
            if _sensitive_header_kind(configured_header):
                raise ReviewError(
                    f"metric_mapping.{kind}.{canonical} 指向查询、PII 或稳定标识符列，"
                    "不能作为聚合数值指标。"
                )
            parsed[canonical] = configured_header
        missing = sorted(set(REQUIRED_METRICS.get(kind, ())) - set(parsed))
        if missing:
            raise ReviewError(
                f"metric_mapping.{kind} 缺少必需指标：" + "、".join(missing) + "。"
            )
        result[kind] = parsed
    return result


def _parse_value_mapping(raw: Any) -> dict[str, dict[str, str]]:
    if raw is None:
        return {"country": {}, "device": {}}
    root = _require_object(raw, "value_mapping")
    extras = sorted(set(root) - {"country", "device"})
    if extras:
        raise ReviewError("value_mapping 只允许 country 和 device。")
    result: dict[str, dict[str, str]] = {"country": {}, "device": {}}
    for dimension in result:
        source = root.get(dimension, {})
        source = _require_object(source, f"value_mapping.{dimension}")
        for before, after in source.items():
            before_text = _require_nonempty_string(before, f"value_mapping.{dimension} 的原值")
            after_text = _require_nonempty_string(after, f"value_mapping.{dimension}.{before}")
            result[dimension][before_text.casefold()] = after_text.casefold()
    return result


def _parse_timezone_name(value: Any, context: str) -> tuple[str, ZoneInfo]:
    timezone_name = _require_nonempty_string(value, context)
    try:
        timezone_value = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ReviewError(f"{context} {timezone_name!r} 不是可用的 IANA 时区。") from exc
    return timezone_name, timezone_value


def _optional_timezone_name(value: Any, context: str) -> str | None:
    if value is None or value == "":
        return None
    return _parse_timezone_name(value, context)[0]


def _normalize_data_as_of(value: Any, context: str) -> str | None:
    if value is None or value == "":
        return None
    raw = _require_nonempty_string(value, context)
    try:
        parsed = datetime.fromisoformat(
            raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
        )
    except ValueError as exc:
        raise ReviewError(f"{context} 必须是带 UTC 偏移的 ISO 8601 时间戳。") from exc
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
        or re.search(r"(?:[Zz]|[+-]\d{2}:\d{2})$", raw) is None
    ):
        raise ReviewError(f"{context} 必须包含 Z 或 +08:00 这类 UTC 偏移。")
    return raw


def _data_as_of_date(value: str, source_timezone: str) -> date:
    parsed = datetime.fromisoformat(
        value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    )
    return parsed.astimezone(ZoneInfo(source_timezone)).date()


def _optional_bool(value: Any, context: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ReviewError(f"{context} 必须是 true、false 或 null。")


def _source_quality_contract(
    kind: str,
    raw: Mapping[str, Any],
    configured_timezone: str | None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    embedded_timezone = _optional_timezone_name(
        raw.get("source_timezone"), f"source_metadata.{kind}.source_timezone"
    )
    if embedded_timezone and configured_timezone and embedded_timezone != configured_timezone:
        issues.append(
            {
                "code": "source_timezone_inconsistent",
                "source": kind,
                "detail": "source_timezones 与 source_metadata.source_timezone 不一致。",
            }
        )
    source_timezone = embedded_timezone or configured_timezone
    if source_timezone is None and kind == "gsc_page":
        source_timezone = DEFAULT_GSC_SOURCE_TIMEZONE

    source_kind = raw.get("source_kind", SOURCE_KINDS[kind])
    if not isinstance(source_kind, str) or not source_kind.strip():
        raise ReviewError(f"source_metadata.{kind}.source_kind 必须是非空字符串。")
    finality = raw.get("finality", "unknown")
    if finality not in FINALITY_VALUES:
        raise ReviewError(
            f"source_metadata.{kind}.finality 只能是 final、preliminary 或 unknown。"
        )
    explicit_preliminary = raw.get("preliminary")
    if explicit_preliminary is not None and not isinstance(explicit_preliminary, bool):
        raise ReviewError(f"source_metadata.{kind}.preliminary 必须是布尔值。")
    preliminary = finality == "preliminary" if explicit_preliminary is None else explicit_preliminary
    row_limit_hit = _optional_bool(
        raw.get("row_limit_hit"), f"source_metadata.{kind}.row_limit_hit"
    )
    pagination_complete = _optional_bool(
        raw.get("pagination_complete"), f"source_metadata.{kind}.pagination_complete"
    )
    thresholding_applied = _optional_bool(
        raw.get("thresholding_applied"),
        f"source_metadata.{kind}.thresholding_applied",
    )
    sampling_rate_raw = raw.get("sampling_rate")
    sampling_rate: float | None = None
    if sampling_rate_raw is not None:
        if isinstance(sampling_rate_raw, bool) or not isinstance(sampling_rate_raw, (int, float)):
            raise ReviewError(f"source_metadata.{kind}.sampling_rate 必须是 0 到 1 的数值或 null。")
        sampling_rate = float(sampling_rate_raw)
        if not math.isfinite(sampling_rate) or not 0 <= sampling_rate <= 1:
            raise ReviewError(f"source_metadata.{kind}.sampling_rate 必须在 0 到 1 之间。")
    attribution_model = raw.get("attribution_model")
    if attribution_model is not None:
        attribution_model = _require_nonempty_string(
            attribution_model, f"source_metadata.{kind}.attribution_model"
        )
    declared_quality = raw.get("data_quality", "unknown")
    if isinstance(declared_quality, Mapping):
        declared_quality = declared_quality.get(
            "declared", declared_quality.get("status", "unknown")
        )
    if declared_quality not in DATA_QUALITY_VALUES:
        raise ReviewError(
            f"source_metadata.{kind}.data_quality 只能是 complete、degraded 或 unknown。"
        )
    data_as_of = _normalize_data_as_of(
        raw.get("data_as_of"), f"source_metadata.{kind}.data_as_of"
    )

    def add(code: str, detail: str) -> None:
        issues.append({"code": code, "source": kind, "detail": detail})

    if source_timezone is None:
        add("source_timezone_missing", "未记录来源系统用于划分日期的 IANA 时区。")
    if kind == "gsc_page" and source_timezone != DEFAULT_GSC_SOURCE_TIMEZONE:
        add(
            "gsc_source_timezone_nonstandard",
            "GSC 常规 Search Analytics 日数据应记录为 America/Los_Angeles。",
        )
    if data_as_of is None:
        add("data_as_of_missing", "未记录数据截止时间。")
    if finality == "unknown":
        add("finality_unknown", "未记录数据是否已经最终化。")
    elif finality == "preliminary" or preliminary:
        add("data_preliminary", "来源仍标记为 preliminary。")
    if explicit_preliminary is not None and explicit_preliminary != (finality == "preliminary"):
        add("finality_preliminary_inconsistent", "finality 与 preliminary 字段不一致。")
    if row_limit_hit is None:
        add("row_limit_status_missing", "未声明是否触及行数上限。")
    elif row_limit_hit:
        add("row_limit_hit", "来源触及行数上限。")
    if pagination_complete is None:
        add("pagination_status_missing", "未声明分页是否完整。")
    elif not pagination_complete:
        add("pagination_incomplete", "来源分页未完成。")
    if kind == "ga4":
        if sampling_rate is None:
            add("sampling_rate_missing", "GA4 来源未记录 sampling_rate。")
        elif sampling_rate < 1:
            add("sampling_applied", "GA4 数据存在采样。")
        if thresholding_applied is None:
            add("thresholding_status_missing", "GA4 来源未记录 thresholding_applied。")
        elif thresholding_applied:
            add("thresholding_applied", "GA4 数据触发了阈值处理。")
    if kind in {"ga4", "crm"} and attribution_model is None:
        add("attribution_model_missing", "未记录该业务来源使用的归因/cohort 模型。")
    if declared_quality == "unknown":
        add("data_quality_unknown", "来源未声明数据质量。")
    elif declared_quality == "degraded":
        add("data_quality_degraded", "来源声明数据质量已降级。")

    status = "complete" if not issues else (
        "unknown"
        if any(item["code"].endswith(("_missing", "_unknown")) for item in issues)
        else "degraded"
    )
    return (
        {
            "source_kind": source_kind.strip(),
            "source_timezone": source_timezone,
            "data_as_of": data_as_of,
            "finality": finality,
            "preliminary": preliminary,
            "row_limit_hit": row_limit_hit,
            "pagination_complete": pagination_complete,
            "sampling_rate": _clean_number(sampling_rate),
            "thresholding_applied": thresholding_applied,
            "data_quality": {
                "declared": declared_quality,
                "status": status,
                "issues": [item["code"] for item in issues],
            },
            "attribution_model": attribution_model,
        },
        issues,
    )


def load_config(path: str | Path, enabled_sources: Iterable[str]) -> ReviewConfig:
    config_path = Path(path)
    raw_bytes = _read_bytes(config_path, "口径配置")
    try:
        raw = json.loads(raw_bytes.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise ReviewError(f"{config_path}：配置不是有效 UTF-8。") from exc
    except json.JSONDecodeError as exc:
        raise ReviewError(f"{config_path}：JSON 无效（第 {exc.lineno} 行）。") from exc
    root = _require_object(raw, "口径配置")

    windows = root.get("windows", root)
    windows = _require_object(windows, "windows")
    parsed_windows: dict[str, Window] = {}
    for name in ("baseline", "current"):
        item = _require_object(windows.get(name), name)
        start = _parse_config_date(item.get("start"), f"{name}.start")
        end = _parse_config_date(item.get("end"), f"{name}.end")
        if start > end:
            raise ReviewError(f"{name}.start 不得晚于 {name}.end。")
        parsed_windows[name] = Window(start, end)
    baseline = parsed_windows["baseline"]
    current = parsed_windows["current"]
    if baseline.end >= current.start:
        raise ReviewError("基线窗口与当前窗口必须不重叠，且基线必须在前。")

    analysis_timezone_raw = root.get("analysis_timezone", root.get("timezone"))
    timezone_name, timezone_value = _parse_timezone_name(
        analysis_timezone_raw, "analysis_timezone"
    )
    contract_issues: list[dict[str, str]] = []
    if (
        root.get("analysis_timezone") is not None
        and root.get("timezone") is not None
        and root.get("analysis_timezone") != root.get("timezone")
    ):
        contract_issues.append(
            {
                "code": "analysis_timezone_inconsistent",
                "source": "mapping",
                "detail": "analysis_timezone 与兼容字段 timezone 不一致。",
            }
        )
    property_id = _require_nonempty_string(root.get("property"), "property")
    search_type = _require_nonempty_string(root.get("search_type"), "search_type")

    enabled = set(enabled_sources)
    raw_source_timezones = root.get("source_timezones", {})
    raw_source_timezones = _require_object(raw_source_timezones, "source_timezones")
    source_timezones: dict[str, str | None] = {}
    for kind in enabled:
        configured = raw_source_timezones.get(kind)
        if configured is None and kind == "gsc_page":
            configured = raw_source_timezones.get("gsc")
        source_timezones[kind] = _optional_timezone_name(
            configured, f"source_timezones.{kind}"
        )
        if source_timezones[kind] is None and kind == "gsc_page":
            source_timezones[kind] = DEFAULT_GSC_SOURCE_TIMEZONE

    raw_source_metadata = root.get("source_metadata", {})
    raw_source_metadata = _require_object(raw_source_metadata, "source_metadata")
    source_metadata: dict[str, dict[str, Any]] = {}
    for kind in enabled:
        source_raw = raw_source_metadata.get(kind)
        if source_raw is None and kind == "gsc_page":
            source_raw = raw_source_metadata.get("gsc")
        source_raw = {} if source_raw is None else _require_object(
            source_raw, f"source_metadata.{kind}"
        )
        normalized, issues = _source_quality_contract(
            kind, source_raw, source_timezones[kind]
        )
        source_metadata[kind] = normalized
        source_timezones[kind] = normalized["source_timezone"]
        contract_issues.extend(issues)
        data_as_of = normalized.get("data_as_of")
        source_timezone = normalized.get("source_timezone")
        if (
            isinstance(data_as_of, str)
            and isinstance(source_timezone, str)
            and _data_as_of_date(data_as_of, source_timezone) < current.end
        ):
            issue = {
                "code": "data_as_of_before_current_window_end",
                "source": kind,
                "detail": "数据截止日期早于当前窗口结束日。",
            }
            contract_issues.append(issue)
            normalized["data_quality"]["issues"].append(issue["code"])
            normalized["data_quality"]["status"] = "degraded"
    raw_dimensions = _require_object(root.get("dimension_mapping"), "dimension_mapping")
    dimensions = {
        kind: _parse_column_mapping(raw_dimensions, kind, SOURCE_GRAINS[kind])
        for kind in enabled
    }
    metrics = _parse_metric_mapping(root.get("metric_mapping"), enabled)
    value_mapping = _parse_value_mapping(root.get("value_mapping"))

    url_settings = _require_object(root.get("url_normalization"), "url_normalization")
    base_url = _require_nonempty_string(url_settings.get("base_url"), "url_normalization.base_url")
    parsed_base = urllib.parse.urlsplit(base_url)
    if parsed_base.scheme.lower() not in {"http", "https"} or not parsed_base.hostname:
        raise ReviewError("url_normalization.base_url 必须是完整的 HTTP(S) URL。")
    trailing = url_settings.get("trailing_slash", "remove")
    if trailing not in {"remove", "add", "preserve"}:
        raise ReviewError("url_normalization.trailing_slash 只能为 remove、add 或 preserve。")
    strip_query = url_settings.get("strip_query", True)
    strip_fragment = url_settings.get("strip_fragment", True)
    lowercase_host = url_settings.get("lowercase_host", True)
    force_https = url_settings.get("force_https", False)
    for key, value in {
        "strip_query": strip_query,
        "strip_fragment": strip_fragment,
        "lowercase_host": lowercase_host,
        "force_https": force_https,
    }.items():
        if not isinstance(value, bool):
            raise ReviewError(f"url_normalization.{key} 必须是 true 或 false。")
    if not strip_query or not strip_fragment:
        raise ReviewError(
            "为避免把跟踪参数或 fragment 当作共享 cohort，"
            "url_normalization.strip_query 和 strip_fragment 必须为 true。"
        )
    mappings = url_settings.get("mappings", url_settings.get("aliases", {}))
    mappings = _require_object(mappings, "url_normalization.mappings")
    normalized_url_settings = {
        "base_url": base_url,
        "force_https": force_https,
        "strip_query": strip_query,
        "strip_fragment": strip_fragment,
        "lowercase_host": lowercase_host,
        "trailing_slash": trailing,
        "mappings": dict(mappings),
    }

    crm_definition_raw = root.get("crm_definition", root.get("crm_definitions"))
    crm_definition_obj = _require_object(crm_definition_raw, "crm_definition")
    crm_definition = {
        "stage": _require_nonempty_string(
            crm_definition_obj.get("stage"), "crm_definition.stage"
        ),
        "qualified": _require_nonempty_string(
            crm_definition_obj.get("qualified"), "crm_definition.qualified"
        ),
    }

    return ReviewConfig(
        path=config_path,
        sha256=_sha256(raw_bytes),
        baseline=baseline,
        current=current,
        timezone_name=timezone_name,
        timezone=timezone_value,
        source_timezones=source_timezones,
        source_metadata=source_metadata,
        contract_issues=tuple(contract_issues),
        property_id=property_id,
        search_type=search_type,
        dimension_mapping=dimensions,
        metric_mapping=metrics,
        value_mapping=value_mapping,
        url_settings=normalized_url_settings,
        crm_definition=crm_definition,
    )


class URLNormalizer:
    def __init__(self, settings: Mapping[str, Any]) -> None:
        self.settings = settings
        self.base_url = str(settings["base_url"])
        mappings = settings.get("mappings", {})
        self.mappings: dict[str, str] = {}
        for raw_before, raw_after in mappings.items():
            before_text = _require_nonempty_string(raw_before, "URL 映射原值")
            after_text = _require_nonempty_string(raw_after, f"URL 映射 {before_text}")
            before = self._normalize(before_text)
            after = self._normalize(after_text)
            if before is None or after is None:
                raise ReviewError(f"URL 映射无效：{before_text!r} -> {after_text!r}。")
            if before in self.mappings and self.mappings[before] != after:
                raise ReviewError(f"URL 映射原值重复且目标不同：{before}。")
            self.mappings[before] = after

    def _normalize(self, raw: str) -> str | None:
        resolved = urllib.parse.urljoin(self.base_url, raw.strip())
        try:
            parsed = urllib.parse.urlsplit(resolved)
            port = parsed.port
        except ValueError:
            return None
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        scheme = "https" if self.settings["force_https"] else parsed.scheme.lower()
        host = parsed.hostname.lower() if self.settings["lowercase_host"] else parsed.hostname
        default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
        netloc = host if port is None or default_port else f"{host}:{port}"
        path = re.sub(r"/{2,}", "/", parsed.path or "/")
        trailing = self.settings["trailing_slash"]
        if path != "/" and trailing == "remove":
            path = path.rstrip("/")
        elif path != "/" and trailing == "add":
            path = path.rstrip("/") + "/"
        query = "" if self.settings["strip_query"] else parsed.query
        fragment = "" if self.settings["strip_fragment"] else parsed.fragment
        return urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))

    def normalize(self, raw: str | None) -> URLResult:
        if raw is None or not raw.strip():
            return URLResult(None, "blank_landing_page", False)
        value = self._normalize(raw)
        if value is None:
            return URLResult(None, "invalid_landing_page", False)
        mapped = self.mappings.get(value)
        if mapped is not None:
            return URLResult(mapped, None, True)
        return URLResult(value, None, False)


def _detect_dialect(text: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(text[:8192], delimiters=",\t;")
    except csv.Error:
        return csv.excel


def _parse_day(
    value: str | None,
    config: ReviewConfig,
    kind: str,
    path: Path,
    row_number: int,
) -> tuple[date | None, str]:
    raw = (value or "").strip()
    if not raw:
        return None, "unknown"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        try:
            return date.fromisoformat(raw), "date"
        except ValueError as exc:
            raise ReviewError(f"{path}：第 {row_number} 行日期 {raw!r} 无效。") from exc
    for date_format in ("%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(raw, date_format).date(), "date"
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw)
    except ValueError as exc:
        raise ReviewError(
            f"{path}：第 {row_number} 行日期 {raw!r} 无法解析；请使用 ISO 8601。"
        ) from exc
    if parsed.tzinfo is None:
        source_timezone_name = config.source_timezones.get(kind)
        source_timezone = (
            ZoneInfo(source_timezone_name) if source_timezone_name else config.timezone
        )
        parsed = parsed.replace(tzinfo=source_timezone)
    parsed = parsed.astimezone(config.timezone)
    return parsed.date(), "timestamp"


def _parse_metric(value: str | None, path: Path, row_number: int, metric: str) -> float | None:
    raw = (value or "").strip().replace("\u00a0", "").replace(" ", "")
    if not raw:
        return None
    raw = raw.replace(",", "")
    try:
        number = float(raw)
    except ValueError as exc:
        raise ReviewError(
            f"{path}：第 {row_number} 行指标 {metric!r} 不是有效数值：{value!r}。"
        ) from exc
    if not math.isfinite(number) or number < 0:
        raise ReviewError(f"{path}：第 {row_number} 行指标 {metric!r} 必须是非负有限数。")
    return number


def _normalize_dimension(value: str | None, dimension: str, config: ReviewConfig) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    key = raw.casefold()
    return config.value_mapping.get(dimension, {}).get(key, key)


def _resolve_headers(
    headers: Sequence[str], configured: Mapping[str, str], path: Path
) -> tuple[dict[str, str], dict[str, str]]:
    actual_by_key: dict[str, str] = {}
    for header in headers:
        key = _header_key(header)
        if not key:
            raise ReviewError(f"{path}：存在空表头。")
        if key in actual_by_key:
            raise ReviewError(f"{path}：表头 {actual_by_key[key]!r} 与 {header!r} 重复。")
        actual_by_key[key] = header
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for canonical, configured_header in configured.items():
        actual = actual_by_key.get(_header_key(configured_header))
        if actual is None:
            missing.append(f"{canonical} -> {configured_header}")
        else:
            resolved[canonical] = actual
    if missing:
        raise ReviewError(f"{path}：缺少配置所需列：" + "、".join(missing) + "。")
    return resolved, actual_by_key


def _reject_sensitive_headers(headers: Sequence[str], path: Path) -> None:
    for header in headers:
        key = _header_key(header)
        kind = _sensitive_header_kind(header)
        if kind == "查询词":
            raise ReviewError(
                f"{path}：检测到禁止的查询词列 {header!r}；请导出无 Query/关键词的页面级 CSV。"
            )
        if kind is not None:
            raise ReviewError(
                f"{path}：检测到禁止的{kind}列 {header!r}；请先在源系统聚合。"
            )


def read_dataset(
    kind: str, path: str | Path, config: ReviewConfig, normalizer: URLNormalizer
) -> Dataset:
    csv_path = Path(path)
    raw_bytes = _read_bytes(csv_path, SOURCE_LABELS[kind])
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ReviewError(f"{csv_path}：不是有效 UTF-8 CSV。") from exc
    if not text.strip():
        raise ReviewError(f"{csv_path}：CSV 为空。")
    reader = csv.DictReader(text.splitlines(), dialect=_detect_dialect(text))
    if not reader.fieldnames:
        raise ReviewError(f"{csv_path}：未找到表头。")
    headers = tuple(reader.fieldnames)
    _reject_sensitive_headers(headers, csv_path)

    dimensions, actual_by_key = _resolve_headers(
        headers, config.dimension_mapping[kind], csv_path
    )
    metrics, _ = _resolve_headers(headers, config.metric_mapping[kind], csv_path)
    used_headers = set(dimensions.values()) | set(metrics.values())
    if len(used_headers) != len(dimensions) + len(metrics):
        raise ReviewError(f"{csv_path}：维度列和指标列的映射发生冲突。")

    if kind == "crm":
        for header in headers:
            key = _header_key(header)
            if key in CRM_RAW_HEADERS:
                raise ReviewError(
                    f"{csv_path}：CRM 只接受 date + landing_page + country cohort 和已聚合数值指标，"
                    f"不接受原始列 {header!r}。"
                )
    safe_ignored = SAFE_NON_GRAIN_HEADERS[kind]
    extras = [
        header
        for header in headers
        if header not in used_headers and _header_key(header) not in safe_ignored
    ]
    if extras:
        raise ReviewError(
            f"{csv_path}：存在未声明列：" + "、".join(extras) + "。"
            "未声明列可能是额外维度并改变聚合粒度；请在口径配置中显式映射或移除。"
        )
    ignored_headers = tuple(header for header in headers if header not in used_headers)

    rows: list[DataRow] = []
    for row_number, raw_row in enumerate(reader, start=2):
        if None in raw_row:
            raise ReviewError(f"{csv_path}：第 {row_number} 行列数多于表头。")
        if not any((value or "").strip() for value in raw_row.values()):
            continue
        day, temporal_grain = _parse_day(
            raw_row.get(dimensions["date"]), config, kind, csv_path, row_number
        )
        url_result = normalizer.normalize(raw_row.get(dimensions["landing_page"]))
        country = _normalize_dimension(raw_row.get(dimensions["country"]), "country", config)
        device = None
        if "device" in dimensions:
            device = _normalize_dimension(raw_row.get(dimensions["device"]), "device", config)
        parsed_metrics = {
            canonical: _parse_metric(raw_row.get(header), csv_path, row_number, canonical)
            for canonical, header in metrics.items()
        }
        rows.append(
            DataRow(
                row_number=row_number,
                day=day,
                landing_page=url_result.value,
                url_reason=url_result.reason,
                explicitly_mapped=url_result.explicitly_mapped,
                country=country,
                device=device,
                metrics=parsed_metrics,
                temporal_grain=temporal_grain,
            )
        )
    if not rows:
        raise ReviewError(f"{csv_path}：没有可读取的数据行。")
    observed_grains = {
        row.temporal_grain for row in rows if row.temporal_grain != "unknown"
    }
    dataset_grain = (
        next(iter(observed_grains)) if len(observed_grains) == 1 else
        "mixed" if observed_grains else "unknown"
    )
    return Dataset(
        kind=kind,
        path=csv_path,
        sha256=_sha256(raw_bytes),
        headers=headers,
        ignored_headers=ignored_headers,
        rows=tuple(rows),
        metric_names=tuple(metrics),
        temporal_grain=dataset_grain,
    )


def _window_name(day: date | None, config: ReviewConfig) -> str:
    if day is None:
        return "blank_date"
    if config.baseline.contains(day):
        return "baseline"
    if config.current.contains(day):
        return "current"
    return "outside"


def _reason(code: str) -> dict[str, str]:
    return {"code": code, "message": REASON_MESSAGES[code]}


def observation(value: float | int | None, reason_code: str | None = None) -> dict[str, Any]:
    return {
        "value": _clean_number(value),
        "reason": _reason(reason_code) if reason_code else None,
    }


def _sum_metric(rows: Sequence[DataRow], metric: str) -> dict[str, Any]:
    if not rows:
        return observation(None, "no_rows")
    values = [row.metrics.get(metric) for row in rows]
    known = [value for value in values if value is not None]
    if not known:
        return observation(None, "all_values_blank")
    if len(known) != len(values):
        return observation(None, "partial_values_blank")
    return observation(sum(known))


def _rate(numerator: dict[str, Any], denominator: dict[str, Any]) -> dict[str, Any]:
    if numerator["value"] is None:
        return {"value": None, "reason": numerator["reason"]}
    if denominator["value"] is None:
        return {"value": None, "reason": denominator["reason"]}
    if denominator["value"] == 0:
        return observation(None, "zero_denominator")
    return observation(float(numerator["value"]) / float(denominator["value"]))


def metric_bundle(dataset: Dataset, rows: Sequence[DataRow]) -> dict[str, Any]:
    metrics = {metric: _sum_metric(rows, metric) for metric in dataset.metric_names}
    for derived, pair in DERIVED_METRICS.get(dataset.kind, {}).items():
        numerator, denominator = pair
        if numerator in metrics and denominator in metrics:
            metrics[derived] = _rate(metrics[numerator], metrics[denominator])
    return {"rows": len(rows), "metrics": metrics}


def _unavailable_delta_reason(
    baseline: dict[str, Any], current: dict[str, Any], baseline_rows: int, current_rows: int
) -> str:
    if baseline_rows == 0:
        return "cohort_missing_in_baseline"
    if current_rows == 0:
        return "cohort_missing_in_current"
    if baseline["value"] is None:
        return "baseline_unavailable"
    return "current_unavailable"


def metric_delta(baseline: dict[str, Any], current: dict[str, Any], *, baseline_rows: int, current_rows: int) -> dict[str, Any]:
    if baseline["value"] is None or current["value"] is None:
        code = _unavailable_delta_reason(baseline, current, baseline_rows, current_rows)
        return {"absolute": observation(None, code), "relative": observation(None, code)}
    absolute = float(current["value"]) - float(baseline["value"])
    if baseline["value"] == 0:
        relative = observation(None, "zero_denominator")
    else:
        relative = observation(absolute / float(baseline["value"]))
    return {"absolute": observation(absolute), "relative": relative}


def bundle_delta(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    names = sorted(set(baseline["metrics"]) | set(current["metrics"]))
    for metric in names:
        before = baseline["metrics"].get(metric, observation(None, "baseline_unavailable"))
        after = current["metrics"].get(metric, observation(None, "current_unavailable"))
        result[metric] = metric_delta(
            before,
            after,
            baseline_rows=baseline["rows"],
            current_rows=current["rows"],
        )
    return result


def _rows_for_window(dataset: Dataset, window: str, config: ReviewConfig) -> list[DataRow]:
    return [row for row in dataset.rows if _window_name(row.day, config) == window]


def _quality(dataset: Dataset, config: ReviewConfig) -> dict[str, Any]:
    window_counts = Counter(_window_name(row.day, config) for row in dataset.rows)
    grain = SOURCE_GRAINS[dataset.kind]
    full_keys: list[tuple[Any, ...]] = []
    for row in dataset.rows:
        values: dict[str, Any] = {
            "date": row.day,
            "landing_page": row.landing_page,
            "country": row.country,
            "device": row.device,
        }
        if all(values[name] is not None for name in grain):
            full_keys.append(tuple(values[name] for name in grain))
    key_counts = Counter(full_keys)
    duplicate_groups = sum(1 for count in key_counts.values() if count > 1)
    duplicate_rows = sum(count for count in key_counts.values() if count > 1)
    return {
        "source_kind": config.source_metadata[dataset.kind]["source_kind"],
        "source_timezone": config.source_timezones[dataset.kind],
        "temporal_grain": dataset.temporal_grain,
        "metadata_status": config.source_metadata[dataset.kind]["data_quality"]["status"],
        "source_rows": len(dataset.rows),
        "window_rows": {
            "baseline": window_counts["baseline"],
            "current": window_counts["current"],
            "outside": window_counts["outside"],
            "blank_date": window_counts["blank_date"],
        },
        "blank_or_invalid_dimensions": {
            "date": sum(row.day is None for row in dataset.rows),
            "landing_page": sum(row.landing_page is None for row in dataset.rows),
            "country": sum(row.country is None for row in dataset.rows),
            "device": (
                sum(row.device is None for row in dataset.rows)
                if "device" in SOURCE_GRAINS[dataset.kind]
                else None
            ),
        },
        "blank_metrics": {
            metric: sum(row.metrics.get(metric) is None for row in dataset.rows)
            for metric in dataset.metric_names
        },
        "full_grain_eligible_rows": len(full_keys),
        "duplicate_grain_groups": duplicate_groups,
        "duplicate_grain_rows": duplicate_rows,
        "ignored_columns": list(dataset.ignored_headers),
    }


def _quality_gate_issues(kind: str, quality: Mapping[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    dimensions = quality["blank_or_invalid_dimensions"]
    for dimension, count in dimensions.items():
        if count:
            issues.append(
                {
                    "code": f"blank_or_invalid_{dimension}",
                    "source": kind,
                    "detail": f"完整聚合粒度中的 {dimension} 有 {count} 行为空或无效。",
                }
            )
    for metric, count in quality["blank_metrics"].items():
        if count:
            issues.append(
                {
                    "code": f"blank_metric_{metric}",
                    "source": kind,
                    "detail": f"指标 {metric} 有 {count} 行为空；未把空值填成 0。",
                }
            )
    if quality["temporal_grain"] in {"mixed", "unknown"}:
        issues.append(
            {
                "code": "temporal_grain_unusable",
                "source": kind,
                "detail": "日期粒度为 mixed/unknown，不能视为完整同口径窗口。",
            }
        )
    for window in ("baseline", "current"):
        if quality["window_rows"][window] == 0:
            issues.append(
                {
                    "code": f"{window}_window_empty",
                    "source": kind,
                    "detail": f"{window} 窗口没有可用数据行。",
                }
            )
    return issues


def _grain_key(row: DataRow, kind: str) -> tuple[Any, ...] | None:
    dimensions = SOURCE_GRAINS[kind]
    values: dict[str, Any] = {
        "date": row.day,
        "landing_page": row.landing_page,
        "country": row.country,
        "device": row.device,
    }
    if any(values[name] is None for name in dimensions):
        return None
    return tuple(values[name] for name in dimensions)


def _cross_source_alignment(
    datasets: Mapping[str, Dataset], config: ReviewConfig
) -> dict[str, Any]:
    grains = {kind: dataset.temporal_grain for kind, dataset in datasets.items()}
    timezones = {kind: config.source_timezones.get(kind) for kind in datasets}
    issues: list[dict[str, str]] = []
    if len(datasets) == 1:
        return {
            "mode": "single_source",
            "daily_join_allowed": False,
            "window_aggregation_allowed": True,
            "analysis_timezone": config.timezone_name,
            "source_timezones": timezones,
            "source_temporal_grains": grains,
            "issues": issues,
        }

    grain_values = set(grains.values())
    if grain_values == {"timestamp"}:
        mode = "timestamp_normalized_daily_join"
        daily_join_allowed = True
    elif grain_values == {"date"}:
        known_timezones = {value for value in timezones.values() if value is not None}
        daily_join_allowed = len(known_timezones) == 1 and all(timezones.values())
        mode = "source_date_daily_join" if daily_join_allowed else "window_aggregate_only"
        if not daily_join_allowed:
            issues.append(
                {
                    "code": "source_day_boundary_mismatch",
                    "source": ",".join(sorted(datasets)),
                    "detail": (
                        "date 粒度来源使用不同或缺失的日界；禁止逐日跨源 join，"
                        "只允许各来源按显式窗口汇总。"
                    ),
                }
            )
    else:
        mode = "window_aggregate_only"
        daily_join_allowed = False
        issues.append(
            {
                "code": "temporal_grain_inconsistent",
                "source": ",".join(sorted(datasets)),
                "detail": "来源混用了 date、timestamp、mixed 或 unknown 粒度，禁止逐日跨源 join。",
            }
        )
    return {
        "mode": mode,
        "daily_join_allowed": daily_join_allowed,
        "window_aggregation_allowed": True,
        "analysis_timezone": config.timezone_name,
        "source_timezones": timezones,
        "source_temporal_grains": grains,
        "issues": issues,
    }


def _mapping_coverage(
    dataset: Dataset,
    gsc: Dataset,
    window: str,
    config: ReviewConfig,
    alignment: Mapping[str, Any],
) -> dict[str, Any]:
    rows = _rows_for_window(dataset, window, config)
    if dataset.kind == "gsc_page":
        eligible = sum(_grain_key(row, "gsc_page") is not None for row in rows)
        return {
            "key_dimensions": list(SOURCE_GRAINS["gsc_page"]),
            "rows": len(rows),
            "eligible_rows": eligible,
            "matched_rows": eligible,
            "unmatched_rows": 0,
            "blank_or_invalid_grain_rows": len(rows) - eligible,
            "explicit_url_mapping_rows": sum(row.explicitly_mapped for row in rows),
            "matched_rate": observation(eligible / len(rows)) if rows else observation(None, "zero_denominator"),
            "unmatched_landing_page_examples": [],
            "join_performed": False,
            "join_reason": "reference_source",
        }
    if not alignment["daily_join_allowed"]:
        eligible = sum(_grain_key(row, dataset.kind) is not None for row in rows)
        return {
            "key_dimensions": list(SOURCE_GRAINS[dataset.kind]),
            "rows": len(rows),
            "eligible_rows": eligible,
            "matched_rows": None,
            "unmatched_rows": None,
            "blank_or_invalid_grain_rows": len(rows) - eligible,
            "explicit_url_mapping_rows": sum(row.explicitly_mapped for row in rows),
            "matched_rate": observation(None, "cross_source_daily_join_forbidden"),
            "unmatched_landing_page_examples": [],
            "join_performed": False,
            "join_reason": alignment["mode"],
        }
    reference_dimensions = SOURCE_GRAINS[dataset.kind]
    gsc_keys: set[tuple[Any, ...]] = set()
    for row in _rows_for_window(gsc, window, config):
        values = {
            "date": row.day,
            "landing_page": row.landing_page,
            "country": row.country,
            "device": row.device,
        }
        if all(values[name] is not None for name in reference_dimensions):
            gsc_keys.add(tuple(values[name] for name in reference_dimensions))
    eligible_rows: list[DataRow] = []
    matched = 0
    unmatched_pages: list[str] = []
    for row in rows:
        key = _grain_key(row, dataset.kind)
        if key is None:
            continue
        eligible_rows.append(row)
        if key in gsc_keys:
            matched += 1
        elif row.landing_page is not None:
            unmatched_pages.append(row.landing_page)
    unmatched = len(eligible_rows) - matched
    if not eligible_rows:
        matched_rate = observation(None, "zero_denominator")
    elif not gsc_keys:
        matched_rate = observation(None, "no_reference_cohorts")
    else:
        matched_rate = observation(matched / len(eligible_rows))
    return {
        "key_dimensions": list(reference_dimensions),
        "rows": len(rows),
        "eligible_rows": len(eligible_rows),
        "matched_rows": matched,
        "unmatched_rows": unmatched,
        "blank_or_invalid_grain_rows": len(rows) - len(eligible_rows),
        "explicit_url_mapping_rows": sum(row.explicitly_mapped for row in rows),
        "matched_rate": matched_rate,
        "unmatched_landing_page_examples": sorted(set(unmatched_pages))[:10],
        "join_performed": True,
        "join_reason": None,
    }


def _landing_page_cohorts(datasets: Mapping[str, Dataset], config: ReviewConfig) -> list[dict[str, Any]]:
    pages = sorted(
        {
            row.landing_page
            for dataset in datasets.values()
            for row in dataset.rows
            if row.landing_page is not None
            and _window_name(row.day, config) in {"baseline", "current"}
        }
    )
    cohorts: list[dict[str, Any]] = []
    for page in pages:
        sources: dict[str, Any] = {}
        for kind, dataset in datasets.items():
            baseline_rows = [
                row
                for row in dataset.rows
                if row.landing_page == page and _window_name(row.day, config) == "baseline"
            ]
            current_rows = [
                row
                for row in dataset.rows
                if row.landing_page == page and _window_name(row.day, config) == "current"
            ]
            baseline = metric_bundle(dataset, baseline_rows)
            current = metric_bundle(dataset, current_rows)
            sources[kind] = {
                "baseline": baseline,
                "current": current,
                "delta": bundle_delta(baseline, current),
            }
        cohorts.append({"landing_page": page, "sources": sources})
    return cohorts


def _source_meta(dataset: Dataset, config: ReviewConfig) -> dict[str, Any]:
    return {
        "label": SOURCE_LABELS[dataset.kind],
        "path": _report_file_reference(dataset.path, f"{dataset.kind}.csv"),
        "sha256": dataset.sha256,
        "rows": len(dataset.rows),
        "headers": list(dataset.headers),
        "temporal_grain": dataset.temporal_grain,
        **config.source_metadata[dataset.kind],
    }


def _verdict(
    datasets: Mapping[str, Dataset],
    totals: Mapping[str, Any],
    coverage: Mapping[str, Any],
    config: ReviewConfig,
    alignment: Mapping[str, Any],
    quality_issues: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    reasons: list[str] = []
    reasons.extend(
        f"数据完整性 {item['source']}:{item['code']}：{item.get('detail', '')}".rstrip("：")
        for item in config.contract_issues
    )
    reasons.extend(
        f"时间契约 {item['source']}:{item['code']}：{item.get('detail', '')}".rstrip("：")
        for item in alignment["issues"]
    )
    reasons.extend(
        f"输入质量 {item['source']}:{item['code']}：{item.get('detail', '')}".rstrip("：")
        for item in quality_issues
    )
    if config.baseline.days != config.current.days:
        reasons.append("两个窗口天数不同。")
    for kind, dataset in datasets.items():
        for window in ("baseline", "current"):
            bundle = totals[window][kind]
            if bundle["rows"] == 0:
                reasons.append(f"{SOURCE_LABELS[kind]}在{'基线' if window == 'baseline' else '当前'}窗口无数据。")
            for metric in dataset.metric_names:
                if bundle["metrics"][metric]["value"] is None:
                    reasons.append(
                        f"{SOURCE_LABELS[kind]}的 {metric} 在{'基线' if window == 'baseline' else '当前'}窗口不完整。"
                    )
        if kind != "gsc_page":
            for window in ("baseline", "current"):
                item = coverage[kind][window]
                if item["join_performed"] is False:
                    reasons.append(
                        f"{SOURCE_LABELS[kind]}在{'基线' if window == 'baseline' else '当前'}窗口未执行逐日跨源 join（{item['join_reason']}）。"
                    )
                elif item["matched_rows"] == 0:
                    reasons.append(
                        f"{SOURCE_LABELS[kind]}在{'基线' if window == 'baseline' else '当前'}窗口没有与 GSC 对齐的聚合 cohort。"
                    )
    directional_eligible = not reasons
    return {
        "recommended_verdict": "directional" if directional_eligible else "inconclusive",
        "maximum_supported_verdict": "directional",
        "directional_eligible": directional_eligible,
        "causal_inference_eligible": False,
        "automatic_causal_or_incrementality_claim_allowed": False,
        "incremental_positive_allowed": False,
        "no_detectable_change_allowed": False,
        "eligibility_reasons": reasons or ["口径和最低数据覆盖可用，但仍只支持方向性描述。"],
        "boundary": "本工具只评估描述性前后变化是否可报告；没有对照或实验设计，不能判定 SEO 造成了增量。",
    }


def build_report(datasets: Mapping[str, Dataset], config: ReviewConfig) -> dict[str, Any]:
    gsc = datasets["gsc_page"]
    quality = {kind: _quality(dataset, config) for kind, dataset in datasets.items()}
    duplicate_sources = {
        kind: item
        for kind, item in quality.items()
        if item["duplicate_grain_groups"] > 0
    }
    if duplicate_sources:
        details = "；".join(
            f"{SOURCE_LABELS[kind]} {item['duplicate_grain_groups']} 组/"
            f"{item['duplicate_grain_rows']} 行"
            for kind, item in sorted(duplicate_sources.items())
        )
        raise ReviewError(
            "发现重复的完整聚合粒度，拒绝加总以免重复计算：" + details
        )
    dataset_quality_issues: list[dict[str, str]] = []
    for kind, item in quality.items():
        source_issues = _quality_gate_issues(kind, item)
        item["gate_status"] = "complete" if not source_issues else "inconclusive"
        item["issues"] = source_issues
        dataset_quality_issues.extend(source_issues)
    alignment = _cross_source_alignment(datasets, config)
    report_quality_issues = [
        *config.contract_issues,
        *alignment["issues"],
        *dataset_quality_issues,
    ]
    totals: dict[str, Any] = {"baseline": {}, "current": {}}
    for window in totals:
        for kind, dataset in datasets.items():
            totals[window][kind] = metric_bundle(dataset, _rows_for_window(dataset, window, config))
    total_deltas = {
        kind: bundle_delta(totals["baseline"][kind], totals["current"][kind])
        for kind in datasets
    }
    mapping_coverage = {
        kind: {
            window: _mapping_coverage(dataset, gsc, window, config, alignment)
            for window in ("baseline", "current")
        }
        for kind, dataset in datasets.items()
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sources": {
            "mapping": {
                "label": SOURCE_LABELS["mapping"],
                "path": _report_file_reference(config.path, "mapping.json"),
                "sha256": config.sha256,
            },
            **{kind: _source_meta(dataset, config) for kind, dataset in datasets.items()},
        },
        "contract": {
            "property": config.property_id,
            "search_type": config.search_type,
            "timezone": config.timezone_name,
            "analysis_timezone": config.timezone_name,
            "source_timezones": {
                kind: config.source_timezones[kind] for kind in datasets
            },
            "source_temporal_grains": {
                kind: datasets[kind].temporal_grain for kind in datasets
            },
            "cross_source_join": alignment,
            "windows": {
                "baseline": config.baseline.as_dict(),
                "current": config.current.as_dict(),
                "inclusive": True,
                "disjoint": True,
            },
            "allowed_shared_dimensions": [
                "date",
                "normalized_landing_page",
                "country",
                "device",
            ],
            "source_grains": {kind: list(SOURCE_GRAINS[kind]) for kind in datasets},
            "dimension_mapping": config.dimension_mapping,
            "metric_mapping": config.metric_mapping,
            "value_mapping": config.value_mapping,
            "url_normalization": config.url_settings,
            "crm_definition": config.crm_definition,
            "query_columns_allowed": False,
            "user_level_or_pii_columns_allowed": False,
            "missing_values_imputed_as_zero": False,
            "contract_complete": not report_quality_issues,
        },
        "quality": quality,
        "data_quality": {
            "status": "complete" if not report_quality_issues else "inconclusive",
            "complete": not report_quality_issues,
            "issues": report_quality_issues,
        },
        "coverage": {"unmapped": mapping_coverage},
        "window_totals": totals,
        "window_deltas": total_deltas,
        "landing_page_cohorts": _landing_page_cohorts(datasets, config),
        "join_limitations": JOIN_LIMITATIONS,
    }
    report["verdict_eligibility"] = _verdict(
        datasets,
        totals,
        mapping_coverage,
        config,
        alignment,
        dataset_quality_issues,
    )
    return report


def _format_observation(item: Mapping[str, Any], *, percent: bool = False) -> str:
    value = item.get("value")
    if value is None:
        reason = item.get("reason") or {}
        return f"不可计算（{reason.get('message', '原因未记录')}）"
    number = float(value)
    if percent:
        return f"{number * 100:.2f}%"
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.4f}".rstrip("0").rstrip(".")


def _metric_order(kind: str, names: Iterable[str]) -> list[str]:
    preferred = {
        "gsc_page": ["clicks", "impressions", "ctr"],
        "ga4": ["sessions", "conversions", "conversion_rate"],
        "crm": ["leads", "qualified", "qualified_rate", "pipeline_value"],
    }[kind]
    names_set = set(names)
    return [name for name in preferred if name in names_set] + sorted(names_set - set(preferred))


def render_markdown(report: Mapping[str, Any]) -> str:
    verdict = report["verdict_eligibility"]
    verdict_zh = "方向性" if verdict["recommended_verdict"] == "directional" else "无法判定"
    lines = [
        "# SEO 业务复盘报告",
        "",
        "## 结论边界",
        "",
        f"- 建议结论：**{verdict_zh}**（`{verdict['recommended_verdict']}`）",
        "- 最高可支持结论：方向性描述，不支持因果或增量声称。",
        f"- {verdict['boundary']}",
        "",
        "## 数据合同",
        "",
        f"- GSC 资产：`{report['contract']['property']}`",
        f"- 搜索类型：`{report['contract']['search_type']}`",
        f"- 分析时区：`{report['contract']['analysis_timezone']}`",
        "- 来源时区：" + "；".join(
            f"{SOURCE_LABELS[kind]}=`{timezone_name or '未记录'}`"
            for kind, timezone_name in report["contract"]["source_timezones"].items()
        ),
        f"- 跨来源时间模式：`{report['contract']['cross_source_join']['mode']}`；"
        f"逐日 join：{'允许' if report['contract']['cross_source_join']['daily_join_allowed'] else '禁止'}。",
        f"- 基线窗口：{report['contract']['windows']['baseline']['start']} 至 {report['contract']['windows']['baseline']['end']}（含边界）",
        f"- 当前窗口：{report['contract']['windows']['current']['start']} 至 {report['contract']['windows']['current']['end']}（含边界）",
        "- 共享粒度上限：`date + normalized landing page + country + device`；CRM 不含 device。",
        "- 缺失值不补 0；任何不可计算值都保留原因。",
        "",
        "## 来源与指纹",
        "",
        "| 来源 | 行数 | SHA-256 |",
        "|---|---:|---|",
    ]
    for kind, source in report["sources"].items():
        rows = source.get("rows", "-")
        lines.append(f"| {source['label']} | {rows} | `{source['sha256']}` |")

    lines.extend(["", "## 质量与窗口覆盖", "", "| 来源 | 总行数 | 基线 | 当前 | 窗口外 | 空日期 | 空/无效 URL | 完整粒度 |", "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for kind, quality in report["quality"].items():
        counts = quality["window_rows"]
        lines.append(
            f"| {SOURCE_LABELS[kind]} | {quality['source_rows']} | {counts['baseline']} | "
            f"{counts['current']} | {counts['outside']} | {counts['blank_date']} | "
            f"{quality['blank_or_invalid_dimensions']['landing_page']} | {quality['full_grain_eligible_rows']} |"
        )

    lines.extend(["", "## 两窗口汇总", ""])
    for kind in report["window_totals"]["baseline"]:
        before = report["window_totals"]["baseline"][kind]
        after = report["window_totals"]["current"][kind]
        delta = report["window_deltas"][kind]
        lines.extend([
            f"### {SOURCE_LABELS[kind]}",
            "",
            "| 指标 | 基线 | 当前 | 绝对变化 | 相对变化 |",
            "|---|---:|---:|---:|---:|",
        ])
        for metric in _metric_order(kind, before["metrics"]):
            is_rate = metric in RATE_METRICS
            lines.append(
                f"| {METRIC_LABELS.get(metric, metric)} | "
                f"{_format_observation(before['metrics'][metric], percent=is_rate)} | "
                f"{_format_observation(after['metrics'][metric], percent=is_rate)} | "
                f"{_format_observation(delta[metric]['absolute'], percent=is_rate)} | "
                f"{_format_observation(delta[metric]['relative'], percent=True)} |"
            )
        lines.append("")

    lines.extend(["## 按登陆页 cohort 的描述性变化", ""])
    if report["landing_page_cohorts"]:
        for cohort in report["landing_page_cohorts"]:
            lines.extend([f"### `{cohort['landing_page']}`", ""])
            for kind, source in cohort["sources"].items():
                pieces: list[str] = []
                for metric in _metric_order(kind, source["baseline"]["metrics"]):
                    item = source["delta"][metric]["relative"]
                    pieces.append(
                        f"{METRIC_LABELS.get(metric, metric)}：{_format_observation(item, percent=True)}"
                    )
                lines.append(f"- {SOURCE_LABELS[kind]}；" + "；".join(pieces))
            lines.append("")
    else:
        lines.extend(["- 没有可用的规范化登陆页 cohort。", ""])

    lines.extend([
        "## 未映射与对齐覆盖",
        "",
        "| 来源 | 窗口 | 键粒度 | 可参与 | 命中 | 未命中 | 空/无效 | 命中率 |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ])
    for kind, windows in report["coverage"]["unmapped"].items():
        for window, item in windows.items():
            matched = "—" if item["matched_rows"] is None else str(item["matched_rows"])
            unmatched = "—" if item["unmatched_rows"] is None else str(item["unmatched_rows"])
            lines.append(
                f"| {SOURCE_LABELS[kind]} | {'基线' if window == 'baseline' else '当前'} | "
                f"{' + '.join(item['key_dimensions'])} | {item['eligible_rows']} | {matched} | "
                f"{unmatched} | {item['blank_or_invalid_grain_rows']} | "
                f"{_format_observation(item['matched_rate'], percent=True)} |"
            )

    lines.extend(["", "## 不可跨越的拼接与归因边界", ""])
    lines.extend(f"- {item}" for item in report["join_limitations"])
    lines.extend(["", "## 结论资格说明", ""])
    lines.extend(f"- {reason}" for reason in verdict["eligibility_reasons"])
    lines.append("")
    return "\n".join(lines)


def make_parser() -> argparse.ArgumentParser:
    parser = ChineseArgumentParser(
        description="用 GSC 页面级、GA4 登陆页级和 CRM 聚合 CSV 做可追溯的 SEO 业务复盘。",
        epilog=(
            "配置必须包含 baseline/current（或 windows.baseline/current）、timezone、property、"
            "search_type、dimension_mapping、url_normalization 与 crm_definition。"
            "本工具禁止 Query、邮箱、电话、lead_id 等列。"
        ),
    )
    parser.add_argument("--gsc-page", required=True, help="GSC 页面级 CSV，必须不含 Query 列")
    parser.add_argument("--ga4", help="可选：GA4 登陆页聚合 CSV")
    parser.add_argument("--crm", help="可选：CRM date + landing_page + country 聚合 CSV")
    parser.add_argument("--mapping", required=True, help="数据口径与 URL 规范化 JSON")
    parser.add_argument("--json-out", required=True, help="JSON 报告输出路径")
    parser.add_argument("--markdown-out", required=True, help="中文 Markdown 报告输出路径")
    parser.add_argument("--version", action="version", version=f"%(prog)s {TOOL_VERSION}")
    return parser


def _write_text(path: str | Path, content: str, label: str) -> None:
    output = Path(path)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ReviewError(f"无法写入{label} {output}：{exc}。") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    if Path(args.json_out).resolve() == Path(args.markdown_out).resolve():
        print("错误：--json-out 和 --markdown-out 不得是同一文件。", file=sys.stderr)
        return 2
    enabled = {"gsc_page"}
    if args.ga4:
        enabled.add("ga4")
    if args.crm:
        enabled.add("crm")
    try:
        config = load_config(args.mapping, enabled)
        normalizer = URLNormalizer(config.url_settings)
        datasets: dict[str, Dataset] = {
            "gsc_page": read_dataset("gsc_page", args.gsc_page, config, normalizer)
        }
        if args.ga4:
            datasets["ga4"] = read_dataset("ga4", args.ga4, config, normalizer)
        if args.crm:
            datasets["crm"] = read_dataset("crm", args.crm, config, normalizer)
        report = build_report(datasets, config)
        markdown = render_markdown(report)
        _write_text(
            args.json_out,
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            "JSON 报告",
        )
        _write_text(args.markdown_out, markdown, "Markdown 报告")
    except ReviewError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
