#!/usr/bin/env python3
"""Google Search Console CSV 窗口对比工具。

本文件只使用 Python 标准库，可被独立复制到 Skill 的 scripts/ 目录执行。
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
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SCHEMA_VERSION = "1.3.0"
DEFAULT_GSC_SOURCE_TIMEZONE = "America/Los_Angeles"
FINALITY_VALUES = {"final", "preliminary", "unknown"}
DATA_QUALITY_VALUES = {"complete", "degraded", "unknown"}
DIMENSIONS = ("page", "query", "country", "device")
DIMENSION_LABELS = {
    "page": "页面",
    "query": "查询",
    "country": "国家/地区",
    "device": "设备",
}
FIELD_LABELS = {
    "date": "日期",
    "query": "查询",
    "page": "页面",
    "country": "国家/地区",
    "device": "设备",
    "clicks": "点击次数",
    "impressions": "展示次数",
    "ctr": "CTR",
    "position": "平均排名",
}


def _header_key(value: str) -> str:
    return " ".join(value.strip().lstrip("\ufeff").lower().replace("_", " ").split())


HEADER_ALIASES = {
    # Date
    "date": "date",
    "日期": "date",
    # Query
    "query": "query",
    "top queries": "query",
    "热门查询": "query",
    "查询": "query",
    # Page
    "page": "page",
    "top pages": "page",
    "热门网页": "page",
    "网页": "page",
    # Country / region
    "country": "country",
    "countries": "country",
    "top countries": "country",
    "国家": "country",
    "地区": "country",
    "国家/地区": "country",
    # Device
    "device": "device",
    "devices": "device",
    "设备": "device",
    # Metrics
    "clicks": "clicks",
    "点击次数": "clicks",
    "点击": "clicks",
    "impressions": "impressions",
    "展示次数": "impressions",
    "展现次数": "impressions",
    "展示": "impressions",
    "ctr": "ctr",
    "average ctr": "ctr",
    "平均点击率": "ctr",
    "点击率": "ctr",
    "position": "position",
    "average position": "position",
    "排名": "position",
    "平均排名": "position",
}


CAUSALITY_WARNING = (
    "本报告只描述 GSC 聚合数据在两个窗口间的变化，不能把变化归因于 SEO、"
    "广告或任何单一措施；因果结论需要合适的对照或实验设计。"
)
JOIN_WARNING = (
    "GSC 的查询和页面是聚合维度，不得与 GA4/CRM 用户或线索记录做用户级直接拼接；"
    "只能在口径对齐后做聚合层分析。"
)
TIMEZONE_WARNING = (
    "Search Console 常规日数据按 America/Los_Angeles（太平洋时间）划分日期；"
    "analysis_timezone 只描述分析/决策时区，不能把既有日汇总重新切成另一时区的日数据。"
)
QUERY_PRIVACY_WARNING = (
    "查询 cohort 会在聚合前拒绝高置信邮箱、电话号码和稳定个人标识；"
    "错误信息不回显原始查询值。"
)

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
PHONE_CONTEXT_RE = re.compile(
    r"\b(?:(?:phone|mobile|cell)[ _-]*(?:number|no)|telephone|tel|whatsapp|wechat)\b|"
    r"(?:电话|手机号|手机号码|联系电话)",
    re.IGNORECASE,
)
PHONE_AFTER_CONTEXT_RE = re.compile(r"(?:\d[ .()\-]*){7,15}")
STABLE_ID_RE = re.compile(
    r"(?:user|customer|client|contact|lead|account|record|order|opportunity|visitor|session)"
    r"[ _-]*(?:id|uuid|guid|token)|"
    r"gclid|msclkid|fbclid|passport|ssn|social[ -]*security|"
    r"用户(?:编号|id)?|客户(?:编号|id)?|联系人(?:编号|id)?|线索(?:编号|id)?|"
    r"身份证(?:号)?|护照(?:号)?",
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


class GSCError(ValueError):
    """可向 CLI 用户直接展示的数据错误。"""


def _report_file_reference(path: Path) -> str:
    """报告只保存可与 SHA-256 配对的文件名，不暴露本机目录。"""
    return path.name or "input.csv"


def _valid_china_resident_id(value: str) -> bool:
    """校验 18 位身份证格式、出生日期与校验位，避免仅凭长度判断。"""
    if not re.fullmatch(r"\d{17}[0-9Xx]", value):
        return False
    try:
        datetime.strptime(value[6:14], "%Y%m%d")
    except ValueError:
        return False
    weights = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    checks = "10X98765432"
    expected = checks[
        sum(int(digit) * weight for digit, weight in zip(value[:17], weights)) % 11
    ]
    return value[-1].upper() == expected


def _query_pii_kind(value: str) -> str | None:
    """只识别高置信 PII，避免把年份、尺寸、SKU 等普通数字当成电话。"""
    if EMAIL_RE.search(value):
        return "邮箱"
    if (
        CHINA_MOBILE_RE.search(value)
        or INTERNATIONAL_PHONE_RE.search(value)
        or NORTH_AMERICAN_PHONE_RE.search(value)
    ):
        return "电话号码"
    context = PHONE_CONTEXT_RE.search(value)
    if context and PHONE_AFTER_CONTEXT_RE.search(value, context.end()):
        return "电话号码"
    for candidate in re.findall(r"(?<!\d)\d{17}[0-9Xx](?!\w)", value):
        if _valid_china_resident_id(candidate):
            return "身份证号"
    identity_context = STABLE_ID_RE.search(value)
    if identity_context:
        for candidate in ID_VALUE_RE.findall(value[identity_context.end() :]):
            if any(char.isdigit() for char in candidate):
                return "稳定个人标识"
    return None


def _page_pii_kind(value: str) -> str | None:
    parsed = urllib.parse.urlsplit(value)
    decoded_path = urllib.parse.unquote(parsed.path)
    path_kind = _query_pii_kind(decoded_path)
    if path_kind and path_kind != "稳定个人标识":
        return path_kind
    query_fragment = urllib.parse.unquote_plus(
        " ".join(item for item in (parsed.query, parsed.fragment) if item)
    )
    component_kind = _query_pii_kind(query_fragment)
    if component_kind:
        return component_kind
    for raw_component in (parsed.query, parsed.fragment):
        for key, _value in urllib.parse.parse_qsl(
            raw_component, keep_blank_values=True
        ):
            if SENSITIVE_PAGE_PARAMETER_RE.fullmatch(key.strip()):
                return "敏感 URL 参数"
    return None


class ChineseArgumentParser(argparse.ArgumentParser):
    """将 argparse 固定的英文帮助框架转为中文。"""

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


def _optional_bool(value: Any, field: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise GSCError(f"{field} 必须是 true、false 或 null。")


def _timezone_name(value: str | None, field: str, *, default: str | None = None) -> str | None:
    timezone_name = value.strip() if isinstance(value, str) and value.strip() else default
    if timezone_name is None:
        return None
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise GSCError(f"{field} {timezone_name!r} 不是可用的 IANA 时区。") from exc
    return timezone_name


def _normalize_data_as_of(value: Any, field: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise GSCError(f"{field} 必须是 ISO 8601 日期或时间。")
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(
            raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
        )
    except ValueError as exc:
        raise GSCError(
            f"{field} 必须是带 UTC 偏移的 ISO 8601 时间戳，当前为 {raw!r}。"
        ) from exc
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
        or re.search(r"(?:[Zz]|[+-]\d{2}:\d{2})$", raw) is None
    ):
        raise GSCError(
            f"{field} 必须包含 Z 或 +08:00 这类 UTC 偏移，当前为 {raw!r}。"
        )
    return raw


def _data_as_of_date(value: str, source_timezone: str) -> date:
    parsed = datetime.fromisoformat(
        value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    )
    return parsed.astimezone(ZoneInfo(source_timezone)).date()


def _source_contract(
    source_id: str,
    *,
    source_timezone: str | None,
    metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    raw = dict(metadata or {})
    embedded_timezone = _timezone_name(
        raw.get("source_timezone"),
        f"{source_id}.source_timezone",
    )
    timezone_name = _timezone_name(
        embedded_timezone or source_timezone,
        f"{source_id}.source_timezone",
        default=DEFAULT_GSC_SOURCE_TIMEZONE,
    )
    finality = raw.get("finality", "unknown")
    if finality not in FINALITY_VALUES:
        raise GSCError(
            f"{source_id}.finality 只能是 final、preliminary 或 unknown。"
        )
    explicit_preliminary = raw.get("preliminary")
    if explicit_preliminary is not None and not isinstance(explicit_preliminary, bool):
        raise GSCError(f"{source_id}.preliminary 必须是布尔值。")
    preliminary = finality == "preliminary" if explicit_preliminary is None else explicit_preliminary
    declared_quality = raw.get("data_quality", "unknown")
    if isinstance(declared_quality, Mapping):
        declared_quality = declared_quality.get("declared", declared_quality.get("status", "unknown"))
    if declared_quality not in DATA_QUALITY_VALUES:
        raise GSCError(
            f"{source_id}.data_quality 只能是 complete、degraded 或 unknown。"
        )
    row_limit_hit = _optional_bool(raw.get("row_limit_hit"), f"{source_id}.row_limit_hit")
    pagination_complete = _optional_bool(
        raw.get("pagination_complete"), f"{source_id}.pagination_complete"
    )
    data_as_of = _normalize_data_as_of(raw.get("data_as_of"), f"{source_id}.data_as_of")

    issues: list[str] = []
    if embedded_timezone and source_timezone and embedded_timezone != source_timezone:
        issues.append("source_timezone_inconsistent")
    if raw.get("source_kind") not in (None, "gsc_search_analytics"):
        issues.append("source_kind_inconsistent")
    if timezone_name != DEFAULT_GSC_SOURCE_TIMEZONE:
        issues.append("gsc_source_timezone_nonstandard")
    if data_as_of is None:
        issues.append("data_as_of_missing")
    if finality == "unknown":
        issues.append("finality_unknown")
    elif finality == "preliminary" or preliminary:
        issues.append("data_preliminary")
    if explicit_preliminary is not None and explicit_preliminary != (finality == "preliminary"):
        issues.append("finality_preliminary_inconsistent")
    if row_limit_hit is None:
        issues.append("row_limit_status_missing")
    elif row_limit_hit:
        issues.append("row_limit_hit")
    if pagination_complete is None:
        issues.append("pagination_status_missing")
    elif not pagination_complete:
        issues.append("pagination_incomplete")
    if declared_quality == "unknown":
        issues.append("data_quality_unknown")
    elif declared_quality == "degraded":
        issues.append("data_quality_degraded")

    status = "complete" if not issues else (
        "unknown"
        if any(code.endswith("_missing") or code.endswith("_unknown") for code in issues)
        else "degraded"
    )
    return {
        "source_id": source_id,
        "source_kind": "gsc_search_analytics",
        "source_timezone": timezone_name,
        "temporal_grain": "date",
        "data_as_of": data_as_of,
        "finality": finality,
        "preliminary": preliminary,
        "row_limit_hit": row_limit_hit,
        "pagination_complete": pagination_complete,
        "sampling_rate": None,
        "thresholding_applied": None,
        "data_quality": {
            "declared": declared_quality,
            "status": status,
            "issues": issues,
        },
        "attribution_model": None,
    }


@dataclass(frozen=True)
class GSCRow:
    row_number: int
    day: date | None
    dimensions: dict[str, str]
    clicks: float
    impressions: float
    position: float | None


@dataclass(frozen=True)
class GSCDataset:
    path: Path
    rows: tuple[GSCRow, ...]
    fields: frozenset[str]
    original_headers: tuple[str, ...]
    sha256: str


@dataclass
class MetricAccumulator:
    clicks: float = 0.0
    impressions: float = 0.0
    position_weighted_sum: float = 0.0
    position_impressions: float = 0.0
    rows: int = 0
    position_rows: int = 0

    def add(self, row: GSCRow) -> None:
        self.clicks += row.clicks
        self.impressions += row.impressions
        self.rows += 1
        if row.position is not None and row.impressions > 0:
            self.position_weighted_sum += row.position * row.impressions
            self.position_impressions += row.impressions
            self.position_rows += 1

    def as_dict(self) -> dict[str, float | int | None]:
        ctr = self.clicks / self.impressions if self.impressions > 0 else None
        position = (
            self.position_weighted_sum / self.position_impressions
            if self.position_impressions > 0
            else None
        )
        return {
            "clicks": _clean_number(self.clicks),
            "impressions": _clean_number(self.impressions),
            "ctr": _clean_number(ctr),
            "weighted_position": _clean_number(position),
            "rows": self.rows,
            "position_rows": self.position_rows,
            "position_impressions": _clean_number(self.position_impressions),
        }


def _clean_number(value: float | int | None) -> float | int | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    rounded = round(number, 10)
    if rounded.is_integer():
        return int(rounded)
    return rounded


def _parse_number(value: str | None, *, field: str, path: Path, row_number: int) -> float:
    raw = (value or "").strip().replace("\u00a0", "").replace(" ", "")
    if not raw:
        raise GSCError(f"{path}：第 {row_number} 行的“{FIELD_LABELS[field]}”为空。")
    raw = raw.replace(",", "")
    try:
        number = float(raw)
    except ValueError as exc:
        raise GSCError(
            f"{path}：第 {row_number} 行的“{FIELD_LABELS[field]}”不是有效数值：{value!r}。"
        ) from exc
    if not math.isfinite(number) or number < 0:
        raise GSCError(
            f"{path}：第 {row_number} 行的“{FIELD_LABELS[field]}”必须是非负有限数。"
        )
    return number


def _parse_optional_position(value: str | None, *, path: Path, row_number: int) -> float | None:
    if value is None or not value.strip():
        return None
    return _parse_number(value, field="position", path=path, row_number=row_number)


DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%m/%d/%Y", "%Y年%m月%d日")


def parse_date(value: str, *, context: str = "日期") -> date:
    raw = value.strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(raw, date_format).date()
        except ValueError:
            continue
    raise GSCError(
        f"{context}“{value}”无法解析；请使用 YYYY-MM-DD（也支持 YYYY/MM/DD）。"
    )


def _detect_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        return csv.excel


def _canonical_headers(headers: Sequence[str], path: Path) -> tuple[dict[str, str], frozenset[str]]:
    mapping: dict[str, str] = {}
    canonical_seen: dict[str, str] = {}
    unsupported: list[str] = []
    for original in headers:
        if not original.strip():
            raise GSCError(f"{path}：CSV 表头包含空列名。")
        canonical = HEADER_ALIASES.get(_header_key(original))
        if canonical is None:
            unsupported.append(original)
            continue
        if canonical in canonical_seen:
            raise GSCError(
                f"{path}：列“{canonical_seen[canonical]}”和“{original}”都被识别为"
                f"“{FIELD_LABELS[canonical]}”，无法确定使用哪一列。"
            )
        mapping[original] = canonical
        canonical_seen[canonical] = original

    if unsupported:
        raise GSCError(
            f"{path}：存在未识别列：{', '.join(repr(item) for item in unsupported)}。"
            "未知列可能是未声明的 GSC 维度并改变聚合粒度；请只保留已支持列，"
            "或先显式映射后再比较。"
        )
    missing = [field for field in ("clicks", "impressions") if field not in canonical_seen]
    if missing:
        labels = "、".join(FIELD_LABELS[field] for field in missing)
        raise GSCError(f"{path}：缺少必需列：{labels}。")
    return mapping, frozenset(canonical_seen)


def read_gsc_csv(path: str | Path) -> GSCDataset:
    """读取 GSC UI CSV，支持 UTF-8 BOM 和常见中英文列名。"""
    csv_path = Path(path)
    try:
        raw_bytes = csv_path.read_bytes()
        text = raw_bytes.decode("utf-8-sig")
    except FileNotFoundError as exc:
        raise GSCError(f"找不到 CSV 文件：{csv_path}。") from exc
    except IsADirectoryError as exc:
        raise GSCError(f"路径不是 CSV 文件：{csv_path}。") from exc
    except UnicodeDecodeError as exc:
        raise GSCError(f"{csv_path}：不是有效的 UTF-8 CSV。") from exc
    except OSError as exc:
        raise GSCError(f"无法读取 {csv_path}：{exc}。") from exc

    if not text.strip():
        raise GSCError(f"{csv_path}：CSV 为空。")

    reader = csv.DictReader(text.splitlines(), dialect=_detect_dialect(text[:8192]))
    if not reader.fieldnames:
        raise GSCError(f"{csv_path}：未找到表头。")
    original_headers = tuple(reader.fieldnames)
    mapping, fields = _canonical_headers(original_headers, csv_path)
    canonical_to_original = {canonical: original for original, canonical in mapping.items()}

    rows: list[GSCRow] = []
    for row_number, raw_row in enumerate(reader, start=2):
        # DictReader 会用 None 作为多余列的键。
        if None in raw_row:
            raise GSCError(f"{csv_path}：第 {row_number} 行的列数多于表头。")
        if not any((value or "").strip() for value in raw_row.values()):
            continue

        def value(field: str) -> str | None:
            original = canonical_to_original.get(field)
            return raw_row.get(original) if original is not None else None

        parsed_day = None
        if "date" in fields:
            raw_day = (value("date") or "").strip()
            if not raw_day:
                raise GSCError(f"{csv_path}：第 {row_number} 行的“日期”为空。")
            parsed_day = parse_date(raw_day, context=f"{csv_path}：第 {row_number} 行日期")

        dimensions = {
            dimension: (value(dimension) or "").strip()
            for dimension in DIMENSIONS
            if dimension in fields
        }
        query_pii = _query_pii_kind(dimensions.get("query", ""))
        if query_pii:
            raise GSCError(
                f"{_report_file_reference(csv_path)}：第 {row_number} 行的查询维度疑似包含"
                f"{query_pii}；为避免 PII 进入 cohort 报告，已在聚合前拒绝。"
                "请先在来源系统排除或不可逆脱敏该行。"
            )
        page_pii = _page_pii_kind(dimensions.get("page", ""))
        if page_pii:
            raise GSCError(
                f"{_report_file_reference(csv_path)}：第 {row_number} 行的页面维度疑似包含"
                f"{page_pii}；为避免 PII 进入 cohort 报告，已在聚合前拒绝。"
                "请先在来源系统移除敏感 URL 参数或不可逆脱敏该行。"
            )
        clicks = _parse_number(
            value("clicks"), field="clicks", path=csv_path, row_number=row_number
        )
        impressions = _parse_number(
            value("impressions"),
            field="impressions",
            path=csv_path,
            row_number=row_number,
        )
        if clicks > impressions:
            raise GSCError(
                f"{_report_file_reference(csv_path)}：第 {row_number} 行的点击次数大于展示次数；"
                "拒绝生成 CTR 大于 100% 的报告，请重新导出同一口径的 GSC 数据。"
            )
        rows.append(
            GSCRow(
                row_number=row_number,
                day=parsed_day,
                dimensions=dimensions,
                clicks=clicks,
                impressions=impressions,
                position=_parse_optional_position(
                    value("position"), path=csv_path, row_number=row_number
                ),
            )
        )

    if not rows:
        raise GSCError(f"{csv_path}：没有可分析的数据行。")
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
            raise GSCError(
                f"{csv_path}：第 {first_row} 行与第 {row.row_number} 行的完整聚合粒度"
                f"（{grain_label}）重复；拒绝加总以免指标翻倍。"
            )
        seen_grain[key] = row.row_number
    return GSCDataset(
        csv_path,
        tuple(rows),
        fields,
        original_headers,
        hashlib.sha256(raw_bytes).hexdigest(),
    )


def aggregate(rows: Iterable[GSCRow]) -> dict[str, float | int | None]:
    accumulator = MetricAccumulator()
    for row in rows:
        accumulator.add(row)
    return accumulator.as_dict()


def aggregate_dimension(
    rows: Iterable[GSCRow], dimension: str
) -> dict[str, dict[str, float | int | None]]:
    grouped: dict[str, MetricAccumulator] = {}
    for row in rows:
        key = row.dimensions.get(dimension, "").strip()
        if not key:
            continue
        grouped.setdefault(key, MetricAccumulator()).add(row)
    return {key: accumulator.as_dict() for key, accumulator in grouped.items()}


def metric_delta(
    current: dict[str, float | int | None], baseline: dict[str, float | int | None]
) -> dict[str, float | int | None]:
    def difference(field: str) -> float | int | None:
        left = current[field]
        right = baseline[field]
        if left is None or right is None:
            return None
        return _clean_number(float(left) - float(right))

    def relative(field: str) -> float | int | None:
        left = current[field]
        right = baseline[field]
        if left is None or right is None or float(right) == 0:
            return None
        return _clean_number((float(left) - float(right)) / float(right))

    ctr_delta = difference("ctr")

    return {
        "clicks": difference("clicks"),
        "clicks_relative": relative("clicks"),
        "impressions": difference("impressions"),
        "impressions_relative": relative("impressions"),
        "ctr_percentage_points": (
            _clean_number(float(ctr_delta) * 100) if ctr_delta is not None else None
        ),
        "weighted_position": difference("weighted_position"),
    }


def _empty_metrics() -> dict[str, float | int | None]:
    return MetricAccumulator().as_dict()


def _coverage(dataset: GSCDataset, rows: Sequence[GSCRow]) -> dict[str, object]:
    dated = [row.day for row in rows if row.day is not None]
    dimensions: dict[str, dict[str, int | bool]] = {}
    for dimension in DIMENSIONS:
        column_present = dimension in dataset.fields
        populated = sum(bool(row.dimensions.get(dimension, "").strip()) for row in rows)
        dimensions[dimension] = {
            "column_present": column_present,
            "populated_rows": populated,
            "blank_rows": len(rows) - populated if column_present else len(rows),
        }
    position_rows = sum(row.position is not None and row.impressions > 0 for row in rows)
    position_impressions = sum(
        row.impressions for row in rows if row.position is not None and row.impressions > 0
    )
    total_impressions = sum(row.impressions for row in rows)
    return {
        "source": _report_file_reference(dataset.path),
        "source_rows": len(dataset.rows),
        "included_rows": len(rows),
        "excluded_rows": len(dataset.rows) - len(rows),
        "date_column_present": "date" in dataset.fields,
        "observed_date_start": min(dated).isoformat() if dated else None,
        "observed_date_end": max(dated).isoformat() if dated else None,
        "zero_impression_rows": sum(row.impressions == 0 for row in rows),
        "position_rows": position_rows,
        "position_impressions": _clean_number(position_impressions),
        "position_impression_coverage": (
            _clean_number(position_impressions / total_impressions)
            if total_impressions > 0
            else None
        ),
        "dimensions": dimensions,
    }


def _period(
    label: str,
    dataset: GSCDataset,
    rows: Sequence[GSCRow],
    requested_start: date | None,
    requested_end: date | None,
) -> dict[str, object]:
    dated = [row.day for row in rows if row.day is not None]
    effective_start = requested_start or (min(dated) if dated else None)
    effective_end = requested_end or (max(dated) if dated else None)
    return {
        "label": label,
        "requested_start": requested_start.isoformat() if requested_start else None,
        "requested_end": requested_end.isoformat() if requested_end else None,
        "observed_start": min(dated).isoformat() if dated else None,
        "observed_end": max(dated).isoformat() if dated else None,
        "effective_start": effective_start.isoformat() if effective_start else None,
        "effective_end": effective_end.isoformat() if effective_end else None,
        "boundary_source": "declared" if requested_start is not None else "observed",
        "source": _report_file_reference(dataset.path),
    }


def _window_bounds(
    rows: Sequence[GSCRow],
    requested_start: date | None,
    requested_end: date | None,
    label: str,
) -> tuple[date, date]:
    if (requested_start is None) != (requested_end is None):
        raise GSCError(f"{label}必须同时声明开始日期和结束日期。")
    observed = [row.day for row in rows if row.day is not None]
    if requested_start is None:
        if not observed:
            raise GSCError(
                f"{label}没有 Date/日期列，必须显式声明该窗口的开始和结束日期。"
            )
        return min(observed), max(observed)
    assert requested_end is not None
    if requested_start > requested_end:
        raise GSCError(f"{label}的开始日期不能晚于结束日期。")
    outside = [
        row.row_number
        for row in rows
        if row.day is not None and not requested_start <= row.day <= requested_end
    ]
    if outside:
        examples = "、".join(str(item) for item in outside[:5])
        raise GSCError(
            f"{label}存在落在声明边界之外的数据行（例如第 {examples} 行）；"
            "拒绝把部分覆盖误当成完整窗口。"
        )
    return requested_start, requested_end


def _comparison_window_bounds(
    current_rows: Sequence[GSCRow],
    baseline_rows: Sequence[GSCRow],
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
        raise GSCError("基线窗口与当前窗口必须不重叠，且基线必须严格在当前窗口之前。")
    return {"baseline": baseline, "current": current}


def _cohort_report(
    current_rows: Sequence[GSCRow],
    baseline_rows: Sequence[GSCRow],
    dimension: str,
    *,
    available: bool,
    top: int,
) -> dict[str, object]:
    if not available:
        return {
            "label": DIMENSION_LABELS[dimension],
            "available": False,
            "groups_total": 0,
            "groups_returned": 0,
            "rows": [],
        }
    current_groups = aggregate_dimension(current_rows, dimension)
    baseline_groups = aggregate_dimension(baseline_rows, dimension)
    keys = set(current_groups) | set(baseline_groups)
    entries = []
    for key in keys:
        current = current_groups.get(key, _empty_metrics())
        baseline = baseline_groups.get(key, _empty_metrics())
        entries.append(
            {
                "value": key,
                "baseline": baseline,
                "current": current,
                "delta": metric_delta(current, baseline),
            }
        )
    entries.sort(
        key=lambda item: (
            -float(item["current"]["impressions"] or 0),
            -float(item["baseline"]["impressions"] or 0),
            str(item["value"]),
        )
    )
    returned = entries if top == 0 else entries[:top]
    return {
        "label": DIMENSION_LABELS[dimension],
        "available": True,
        "groups_total": len(entries),
        "groups_returned": len(returned),
        "rows": returned,
    }


def build_report(
    current_dataset: GSCDataset,
    baseline_dataset: GSCDataset,
    *,
    current_rows: Sequence[GSCRow] | None = None,
    baseline_rows: Sequence[GSCRow] | None = None,
    current_start: date | None = None,
    current_end: date | None = None,
    baseline_start: date | None = None,
    baseline_end: date | None = None,
    top: int = 20,
    property_id: str | None = None,
    search_type: str | None = None,
    timezone_name: str | None = None,
    analysis_timezone: str | None = None,
    source_timezones: Mapping[str, str] | None = None,
    source_metadata: Mapping[str, Mapping[str, Any]] | None = None,
    filter_notes: str | None = None,
    allow_unaligned_overall: bool = False,
) -> dict[str, object]:
    if top < 0:
        raise GSCError("--top 不能小于 0。")
    selected_current = tuple(current_rows if current_rows is not None else current_dataset.rows)
    selected_baseline = tuple(baseline_rows if baseline_rows is not None else baseline_dataset.rows)
    if not selected_current:
        raise GSCError("当前窗口没有数据行。")
    if not selected_baseline:
        raise GSCError("基线窗口没有数据行。")

    window_bounds = _comparison_window_bounds(
        selected_current,
        selected_baseline,
        current_start=current_start,
        current_end=current_end,
        baseline_start=baseline_start,
        baseline_end=baseline_end,
    )

    current_metrics = aggregate(selected_current)
    baseline_metrics = aggregate(selected_baseline)
    current_dimensions = set(current_dataset.fields) & set(DIMENSIONS)
    baseline_dimensions = set(baseline_dataset.fields) & set(DIMENSIONS)
    shared_dimensions = current_dimensions & baseline_dimensions
    missing_dimensions = {
        dimension: {
            "current_missing": dimension not in current_dimensions,
            "baseline_missing": dimension not in baseline_dimensions,
        }
        for dimension in DIMENSIONS
        if dimension not in shared_dimensions
    }
    current_grain = [dimension for dimension in DIMENSIONS if dimension in current_dimensions]
    baseline_grain = [dimension for dimension in DIMENSIONS if dimension in baseline_dimensions]
    grains_aligned = current_grain == baseline_grain
    if not grains_aligned and not allow_unaligned_overall:
        raise GSCError(
            "当前与基线导出的维度粒度不同，直接比较总体值可能重复计数或改变口径。"
            "请导出相同维度，或在确认两份文件都是互斥、同口径总体后使用 --allow-unaligned-overall。"
        )

    analysis_timezone_name = _timezone_name(
        analysis_timezone or timezone_name,
        "analysis_timezone",
    )
    timezone_overrides = dict(source_timezones or {})
    metadata_overrides = dict(source_metadata or {})
    source_contracts = {
        source_id: _source_contract(
            source_id,
            source_timezone=timezone_overrides.get(source_id),
            metadata=metadata_overrides.get(source_id),
        )
        for source_id in ("baseline", "current")
    }
    quality_issues: list[dict[str, str]] = []
    for source_id, contract in source_contracts.items():
        for code in contract["data_quality"]["issues"]:
            quality_issues.append({"code": code, "source": source_id})
        required_end = window_bounds[source_id][1]
        if contract["data_as_of"]:
            if _data_as_of_date(
                contract["data_as_of"], contract["source_timezone"]
            ) < required_end:
                quality_issues.append(
                    {
                        "code": "data_as_of_before_window_end",
                        "source": source_id,
                        "detail": "数据截止日期早于该窗口结束日。",
                    }
                )
    if source_contracts["baseline"]["source_timezone"] != source_contracts["current"]["source_timezone"]:
        quality_issues.append(
            {
                "code": "source_timezone_mismatch",
                "source": "baseline,current",
                "detail": "两期 GSC 日数据的来源日界不同，不能当作完全同口径窗口。",
            }
        )
    if analysis_timezone_name is None:
        quality_issues.append(
            {
                "code": "analysis_timezone_missing",
                "source": "analysis",
                "detail": "未记录分析/决策时区。",
            }
        )
    if not property_id:
        quality_issues.append(
            {
                "code": "property_id_missing",
                "source": "analysis",
                "detail": "未记录 GSC property。",
            }
        )
    if not search_type:
        quality_issues.append(
            {
                "code": "search_type_missing",
                "source": "analysis",
                "detail": "未记录 GSC search type。",
            }
        )
    if not grains_aligned:
        quality_issues.append(
            {
                "code": "grain_alignment_overridden",
                "source": "baseline,current",
                "detail": "两期维度粒度不同，仅允许探索性总体描述。",
            }
        )
    quality_status = "complete" if not quality_issues else "inconclusive"
    quality_reasons = [
        f"{item['source']}:{item['code']}" for item in quality_issues
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "analysis_kind": "descriptive_gsc_window_comparison",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "methodology": {
            "causal_inference": False,
            "warnings": [
                CAUSALITY_WARNING,
                JOIN_WARNING,
                TIMEZONE_WARNING,
                QUERY_PRIVACY_WARNING,
            ],
            "ctr": "CTR 始终用点击次数 / 展示次数重算，不求和 CSV 中的 CTR 列。",
            "position": (
                "平均排名仅对有排名且展示次数大于 0 的行按展示次数加权；"
                "负的排名 delta 代表数值变小，不代表已证明为优化所致。"
            ),
            "zero_denominator": "展示次数或基线值为 0 时，相应比率返回 null，不伪造百分比。",
            "grain_alignment": (
                "两期维度一致。" if grains_aligned else
                "两期维度不一致；用户通过 --allow-unaligned-overall 明确接受仅总体描述性比较。"
            ),
        },
        "dataset_contract": {
            "property_id": property_id,
            "search_type": search_type,
            "timezone": analysis_timezone_name,
            "analysis_timezone": analysis_timezone_name,
            "source_timezones": {
                source_id: source_contracts[source_id]["source_timezone"]
                for source_id in ("baseline", "current")
            },
            "temporal_grain": "date",
            "filter_notes": filter_notes,
            "current_grain": current_grain,
            "baseline_grain": baseline_grain,
            "grains_aligned": grains_aligned,
            "allow_unaligned_overall": allow_unaligned_overall,
            "windows_disjoint": True,
            "baseline_precedes_current": True,
            "contract_complete": all([property_id, search_type, analysis_timezone_name]),
            "measurement_integrity_complete": quality_status == "complete",
            "warning": None if all([property_id, search_type, analysis_timezone_name]) else (
                "property、搜索类型或时区未完整记录；报告可用于探索，但不能证明两个导出口径完全一致。"
            ),
        },
        "periods": {
            "baseline": _period(
                "基线窗口",
                baseline_dataset,
                selected_baseline,
                baseline_start,
                baseline_end,
            ),
            "current": _period(
                "当前窗口", current_dataset, selected_current, current_start, current_end
            ),
        },
        "coverage": {
            "baseline": _coverage(baseline_dataset, selected_baseline),
            "current": _coverage(current_dataset, selected_current),
            "shared_dimensions": [
                dimension for dimension in DIMENSIONS if dimension in shared_dimensions
            ],
            "missing_dimensions": missing_dimensions,
        },
        "sources": {
            "baseline": {
                "path": _report_file_reference(baseline_dataset.path),
                "sha256": baseline_dataset.sha256,
                **source_contracts["baseline"],
            },
            "current": {
                "path": _report_file_reference(current_dataset.path),
                "sha256": current_dataset.sha256,
                **source_contracts["current"],
            },
        },
        "data_quality": {
            "status": quality_status,
            "complete": quality_status == "complete",
            "issues": quality_issues,
        },
        "verdict_eligibility": {
            "recommended_verdict": "descriptive" if quality_status == "complete" else "inconclusive",
            "maximum_supported_verdict": "descriptive",
            "incremental_positive_allowed": False,
            "no_detectable_change_allowed": False,
            "reasons": quality_reasons or [
                "数据完整性契约已记录；该工具仍只支持描述性窗口变化。"
            ],
        },
        "overall": {
            "baseline": baseline_metrics,
            "current": current_metrics,
            "delta": metric_delta(current_metrics, baseline_metrics),
        },
        "cohorts": {
            dimension: _cohort_report(
                selected_current,
                selected_baseline,
                dimension,
                available=dimension in shared_dimensions,
                top=top,
            )
            for dimension in DIMENSIONS
        },
    }


def select_window(dataset: GSCDataset, start: date, end: date, label: str) -> tuple[GSCRow, ...]:
    if start > end:
        raise GSCError(f"{label}的开始日期不能晚于结束日期。")
    if "date" not in dataset.fields:
        raise GSCError(f"{dataset.path}：单文件窗口模式需要“Date/日期”列。")
    rows = tuple(row for row in dataset.rows if row.day is not None and start <= row.day <= end)
    if not rows:
        raise GSCError(
            f"{label} {start.isoformat()} 至 {end.isoformat()} 没有匹配的数据行。"
        )
    return rows


def _fmt_number(value: float | int | None) -> str:
    if value is None:
        return "不可计算"
    return f"{float(value):,.2f}".rstrip("0").rstrip(".")


def _fmt_percent(value: float | int | None) -> str:
    if value is None:
        return "不可计算"
    return f"{float(value) * 100:.2f}%"


def _fmt_delta(value: float | int | None, *, percentage_points: bool = False) -> str:
    if value is None:
        return "不可计算"
    number = float(value)
    suffix = " 个百分点" if percentage_points else ""
    return f"{number:+,.2f}".rstrip("0").rstrip(".") + suffix


def _escape_table(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, object]) -> str:
    periods = report["periods"]
    coverage = report["coverage"]
    overall = report["overall"]
    methodology = report["methodology"]
    contract = report["dataset_contract"]
    quality = report["data_quality"]
    eligibility = report["verdict_eligibility"]

    def period_text(period: dict[str, object]) -> str:
        requested_start = period["requested_start"]
        requested_end = period["requested_end"]
        observed_start = period["observed_start"]
        observed_end = period["observed_end"]
        if requested_start and requested_end:
            return f"{requested_start} 至 {requested_end}"
        if observed_start and observed_end:
            return f"{observed_start} 至 {observed_end}"
        return "独立导出未提供日期列"

    lines = [
        "# GSC 前后窗口描述性对比",
        "",
        f"> 结论边界：{methodology['warnings'][0]}",
        "",
        "## 方法与边界",
        "",
        f"- {methodology['ctr']}",
        f"- {methodology['position']}",
        f"- {methodology['zero_denominator']}",
        f"- {methodology['grain_alignment']}",
        *[f"- {warning}" for warning in methodology["warnings"][1:]],
        f"- 分析时区：`{contract['analysis_timezone'] or '未记录'}`；GSC 来源时区："
        f"`{contract['source_timezones']['baseline']}` / `{contract['source_timezones']['current']}`。",
        f"- 数据完整性：`{quality['status']}`；建议结论：`{eligibility['recommended_verdict']}`。",
        "",
        "## 窗口与数据覆盖",
        "",
        "| 窗口 | 日期 | 数据行 | 零展示行 | 排名展示覆盖 | 来源 |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    if contract["warning"]:
        method_end = lines.index("## 窗口与数据覆盖") - 1
        lines.insert(method_end, f"- 数据契约提醒：{contract['warning']}")
    if quality["issues"]:
        method_end = lines.index("## 窗口与数据覆盖") - 1
        issue_codes = "、".join(
            f"{item['source']}:{item['code']}" for item in quality["issues"]
        )
        lines.insert(method_end, f"- 完整性门禁：{issue_codes}。这些问题未解决前结论降级为 `inconclusive`。")
    for key, label in (("baseline", "基线"), ("current", "当前")):
        period = periods[key]
        item = coverage[key]
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    period_text(period),
                    str(item["included_rows"]),
                    str(item["zero_impression_rows"]),
                    _fmt_percent(item["position_impression_coverage"]),
                    _escape_table(item["source"]),
                ]
            )
            + " |"
        )

    shared_labels = [DIMENSION_LABELS[item] for item in coverage["shared_dimensions"]]
    missing_labels = [
        DIMENSION_LABELS[item] for item in coverage["missing_dimensions"]
    ]
    lines.extend(
        [
            "",
            f"- 可对比 cohort：{'、'.join(shared_labels) if shared_labels else '无'}",
            f"- 缺失或无法两期对齐的维度：{'、'.join(missing_labels) if missing_labels else '无'}",
            "",
            "## 总体指标",
            "",
            "| 指标 | 基线 | 当前 | 绝对变化 | 相对变化 |",
            "| --- | ---: | ---: | ---: | ---: |",
            (
                f"| 点击次数 | {_fmt_number(overall['baseline']['clicks'])} | "
                f"{_fmt_number(overall['current']['clicks'])} | "
                f"{_fmt_delta(overall['delta']['clicks'])} | "
                f"{_fmt_percent(overall['delta']['clicks_relative'])} |"
            ),
            (
                f"| 展示次数 | {_fmt_number(overall['baseline']['impressions'])} | "
                f"{_fmt_number(overall['current']['impressions'])} | "
                f"{_fmt_delta(overall['delta']['impressions'])} | "
                f"{_fmt_percent(overall['delta']['impressions_relative'])} |"
            ),
            (
                f"| CTR（重算） | {_fmt_percent(overall['baseline']['ctr'])} | "
                f"{_fmt_percent(overall['current']['ctr'])} | "
                f"{_fmt_delta(overall['delta']['ctr_percentage_points'], percentage_points=True)} | — |"
            ),
            (
                f"| 展示加权排名 | {_fmt_number(overall['baseline']['weighted_position'])} | "
                f"{_fmt_number(overall['current']['weighted_position'])} | "
                f"{_fmt_delta(overall['delta']['weighted_position'])} | — |"
            ),
        ]
    )

    for dimension in DIMENSIONS:
        cohort = report["cohorts"][dimension]
        lines.extend(["", f"## {DIMENSION_LABELS[dimension]} cohort", ""])
        if not cohort["available"]:
            lines.append("当前与基线导出未同时包含该维度，不进行臆测对比。")
            continue
        if not cohort["rows"]:
            lines.append("该维度没有非空值。")
            continue
        lines.extend(
            [
                f"显示 {cohort['groups_returned']} / {cohort['groups_total']} 个 cohort，按当前展示次数降序。",
                "",
                "| cohort | 基线点击 | 当前点击 | 点击 delta | 基线展示 | 当前展示 | 展示 delta | CTR delta | 排名 delta |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for item in cohort["rows"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _escape_table(item["value"]),
                        _fmt_number(item["baseline"]["clicks"]),
                        _fmt_number(item["current"]["clicks"]),
                        _fmt_delta(item["delta"]["clicks"]),
                        _fmt_number(item["baseline"]["impressions"]),
                        _fmt_number(item["current"]["impressions"]),
                        _fmt_delta(item["delta"]["impressions"]),
                        _fmt_delta(
                            item["delta"]["ctr_percentage_points"], percentage_points=True
                        ),
                        _fmt_delta(item["delta"]["weighted_position"]),
                    ]
                )
                + " |"
            )

    lines.extend(
        [
            "",
            "## 解读约束",
            "",
            f"- {CAUSALITY_WARNING}",
            f"- {JOIN_WARNING}",
            "- 变化值是后续调查线索，不是排名、流量或收入效果的因果证明。",
            "",
        ]
    )
    return "\n".join(lines)


def _write_text(path: Path, content: str, label: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise GSCError(f"无法写入{label} {path}：{exc}。") from exc


def create_parser() -> argparse.ArgumentParser:
    parser = ChineseArgumentParser(
        description=(
            "比较 Google Search Console UI 导出的 CSV，按页面、查询、国家/地区和设备聚合。"
            "输出只是描述性变化，不做因果归因。"
        ),
        epilog=(
            "双文件示例：python gsc_compare.py --current current.csv --baseline baseline.csv\n"
            "单文件示例：python gsc_compare.py --input export.csv "
            "--baseline-start 2026-05-01 --baseline-end 2026-05-31 "
            "--current-start 2026-06-01 --current-end 2026-06-30"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    parser.add_argument("-h", "--help", action="help", help="显示帮助并退出")
    parser.add_argument("--current", type=Path, help="当前窗口的独立 CSV 导出")
    parser.add_argument("--baseline", type=Path, help="基线窗口的独立 CSV 导出")
    parser.add_argument("--input", type=Path, help="包含 Date/日期列的单个 CSV")
    parser.add_argument("--current-start", help="当前窗口开始日期；无 Date 的双文件模式必须提供")
    parser.add_argument("--current-end", help="当前窗口结束日期；无 Date 的双文件模式必须提供")
    parser.add_argument("--baseline-start", help="基线窗口开始日期；无 Date 的双文件模式必须提供")
    parser.add_argument("--baseline-end", help="基线窗口结束日期；无 Date 的双文件模式必须提供")
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="每个维度输出的 cohort 数量（默认 20，0 表示全部）",
    )
    parser.add_argument("--property-id", help="GSC property（建议记录，例如 sc-domain:example.com）")
    parser.add_argument("--search-type", help="搜索类型（例如 web、image、video、news）")
    parser.add_argument(
        "--analysis-timezone",
        "--timezone",
        dest="analysis_timezone",
        help="分析/决策使用的 IANA 时区；--timezone 为兼容别名",
    )
    parser.add_argument(
        "--source-timezone",
        default=DEFAULT_GSC_SOURCE_TIMEZONE,
        help="两份 GSC 日数据的来源时区（默认 America/Los_Angeles）",
    )
    parser.add_argument("--baseline-source-timezone", help="覆盖基线来源时区")
    parser.add_argument("--current-source-timezone", help="覆盖当前来源时区")
    parser.add_argument("--data-as-of", help="两份数据共同的带 UTC 偏移 ISO 8601 截止时间")
    parser.add_argument("--baseline-data-as-of", help="覆盖基线数据截止日期/时间")
    parser.add_argument("--current-data-as-of", help="覆盖当前数据截止日期/时间")
    parser.add_argument(
        "--finality",
        choices=sorted(FINALITY_VALUES),
        default="unknown",
        help="两份数据共同的成熟状态（final/preliminary/unknown）",
    )
    parser.add_argument("--baseline-finality", choices=sorted(FINALITY_VALUES))
    parser.add_argument("--current-finality", choices=sorted(FINALITY_VALUES))
    parser.add_argument(
        "--row-limit-hit",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="是否触及导出/API 行数上限；可用 --no-row-limit-hit 明确未触限",
    )
    parser.add_argument(
        "--baseline-row-limit-hit",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="覆盖基线是否触及行数上限",
    )
    parser.add_argument(
        "--current-row-limit-hit",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="覆盖当前窗口是否触及行数上限",
    )
    parser.add_argument(
        "--pagination-complete",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="分页是否完整；可用 --no-pagination-complete 标记未完成",
    )
    parser.add_argument(
        "--baseline-pagination-complete",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="覆盖基线分页完整性",
    )
    parser.add_argument(
        "--current-pagination-complete",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="覆盖当前窗口分页完整性",
    )
    parser.add_argument(
        "--data-quality",
        choices=sorted(DATA_QUALITY_VALUES),
        default="unknown",
        help="来源声明的数据质量（complete/degraded/unknown）",
    )
    parser.add_argument("--baseline-data-quality", choices=sorted(DATA_QUALITY_VALUES))
    parser.add_argument("--current-data-quality", choices=sorted(DATA_QUALITY_VALUES))
    parser.add_argument("--filter-notes", help="国家、设备、品牌词等过滤条件的文字记录")
    parser.add_argument(
        "--allow-unaligned-overall",
        action="store_true",
        help="明确接受不同维度文件只做总体描述性比较；默认拒绝以防口径错配",
    )
    parser.add_argument("--json-out", type=Path, help="写入完整 JSON 报告")
    parser.add_argument(
        "--markdown-out",
        type=Path,
        help="写入中文 Markdown 报告；未指定时输出到标准输出",
    )
    return parser


def _resolve_inputs(args: argparse.Namespace) -> tuple[
    GSCDataset,
    GSCDataset,
    tuple[GSCRow, ...],
    tuple[GSCRow, ...],
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
            raise GSCError("--input 不能与 --current/--baseline 同时使用。")
        if not all(window_values):
            raise GSCError(
                "单文件模式必须同时提供 --baseline-start、--baseline-end、"
                "--current-start 和 --current-end。"
            )
        baseline_start = parse_date(args.baseline_start, context="--baseline-start ")
        baseline_end = parse_date(args.baseline_end, context="--baseline-end ")
        current_start = parse_date(args.current_start, context="--current-start ")
        current_end = parse_date(args.current_end, context="--current-end ")
        if baseline_end >= current_start:
            raise GSCError("基线窗口与当前窗口必须不重叠，且基线必须严格在前。")
        dataset = read_gsc_csv(args.input)
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
        raise GSCError("请使用 --current 和 --baseline 提供两份 CSV，或使用 --input 单文件模式。")
    if any(window_values) and not all(window_values):
        raise GSCError("双文件模式声明日期边界时，必须同时提供四个窗口日期参数。")
    current_dataset = read_gsc_csv(args.current)
    baseline_dataset = read_gsc_csv(args.baseline)
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
    source_timezones = {
        "baseline": args.baseline_source_timezone or args.source_timezone,
        "current": args.current_source_timezone or args.source_timezone,
    }
    source_metadata = {
        source_id: {
            "data_as_of": getattr(args, f"{source_id}_data_as_of") or args.data_as_of,
            "finality": getattr(args, f"{source_id}_finality") or args.finality,
            "row_limit_hit": (
                getattr(args, f"{source_id}_row_limit_hit")
                if getattr(args, f"{source_id}_row_limit_hit") is not None
                else args.row_limit_hit
            ),
            "pagination_complete": (
                getattr(args, f"{source_id}_pagination_complete")
                if getattr(args, f"{source_id}_pagination_complete") is not None
                else args.pagination_complete
            ),
            "data_quality": (
                getattr(args, f"{source_id}_data_quality") or args.data_quality
            ),
        }
        for source_id in ("baseline", "current")
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
        top=args.top,
        property_id=args.property_id,
        search_type=args.search_type,
        analysis_timezone=args.analysis_timezone,
        source_timezones=source_timezones,
        source_metadata=source_metadata,
        filter_notes=args.filter_notes,
        allow_unaligned_overall=args.allow_unaligned_overall,
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
    except GSCError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
