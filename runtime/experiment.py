#!/usr/bin/env python3
"""SEO 实验计划与增量资格检查器。

只使用 Python 标准库。工具锁定预注册计划与输入哈希，按实验单位计算
difference-in-differences（DiD）及近似正态置信区间。输出的是“是否具备
增量解读资格”，不是 SEO 排名、流量或商业因果结论。
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import random
import re
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SCHEMA_VERSION = "1.1"
TOOL_NAME = "vibio-seo-experiment"
DEFAULT_GSC_SOURCE_TIMEZONE = "America/Los_Angeles"
FINALITY_VALUES = {"final", "preliminary", "unknown"}
DATA_QUALITY_VALUES = {"complete", "degraded", "unknown"}
SUPPORTED_DESIGNS = {"randomized_page_holdout", "matched_page_did"}
PRIMARY_METRIC_DIRECTIONS = {"increase", "decrease"}
GROUPS = ("treatment", "control")
MEASUREMENT_CONTRACT_IMMUTABLE_FIELDS = (
    "analysis_timezone",
    "temporal_grain",
    "source_timezones",
)
MEASUREMENT_SOURCE_IMMUTABLE_FIELDS = (
    "source_kind",
    "source_timezone",
    "metrics",
    "attribution_model",
)
MEASUREMENT_COLLECTION_STATUS_FIELDS = frozenset(
    (
        "data_as_of",
        "finality",
        "preliminary",
        "row_limit_hit",
        "pagination_complete",
        "sampling_rate",
        "thresholding_applied",
        "data_quality",
    )
)
GROUP_ALIASES = {
    "treatment": "treatment",
    "treated": "treatment",
    "test": "treatment",
    "实验组": "treatment",
    "处理组": "treatment",
    "control": "control",
    "holdout": "control",
    "对照组": "control",
    "保留组": "control",
}
TRUE_VALUES = {"1", "true", "yes", "y", "是"}
FALSE_VALUES = {"0", "false", "no", "n", "否"}

CAUSALITY_BOUNDARY = (
    "该结果只判定预注册对照设计是否具备增量解读资格；脚本不自动宣称 "
    "SEO 对排名、自然流量或商业结果的因果。"
)
PAID_SEARCH_BOUNDARY = (
    "付费广告只能用于语言/搜索词研究或落地页实验处理；CPC、广告竞争度和"
    "投放本身都不是自然排名因素。"
)
POWER_BOUNDARY = (
    "本工具不估算统计功效（power）。它只报告样本内标准误、置信区间和"
    "置信区间半宽是否不大于预注册 MDE；这不等同于功效计算。"
)


class ExperimentError(ValueError):
    """可直接展示给 CLI 用户的输入或完整性错误。"""


class ChineseArgumentParser(argparse.ArgumentParser):
    """将 argparse 的主要固定文案转为中文。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._positionals.title = "位置参数"
        self._optionals.title = "选项"
        for action in self._actions:
            if isinstance(action, argparse._HelpAction):
                action.help = "显示帮助并退出"

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法：", 1)

    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace("usage:", "用法：", 1)
            .replace("positional arguments:\n", "位置参数：\n", 1)
            .replace("options:\n", "选项：\n", 1)
        )

    def error(self, message: str) -> None:
        required = "the following arguments are required: "
        unrecognized = "unrecognized arguments: "
        if message.startswith(required):
            message = "缺少必需参数：" + message[len(required) :]
        elif message.startswith(unrecognized):
            message = "无法识别的参数：" + message[len(unrecognized) :]
        self.print_usage(sys.stderr)
        self.exit(2, f"错误：{message}\n")


@dataclass(frozen=True)
class Window:
    start: date
    end: date

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def as_dict(self) -> dict[str, str]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}


@dataclass(frozen=True)
class Guardrail:
    metric: str
    direction: str
    threshold: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "direction": self.direction,
            "threshold": _clean_number(self.threshold),
            "scale": "absolute_did",
        }


@dataclass(frozen=True)
class ParsedSpec:
    raw: dict[str, Any]
    sha256: str
    experiment_id: str
    design: str
    unit_id_column: str
    primary_metric: str
    primary_metric_direction: str
    guardrails: tuple[Guardrail, ...]
    seed: int | str
    treatment_fraction: float
    baseline: Window
    observation: Window
    mde_value: float
    mde_scale: str
    alpha: float
    measurement_contract: dict[str, Any]


@dataclass(frozen=True)
class BaselineUnit:
    unit_id: str
    pair_id: str | None
    metrics: dict[str, float]
    source_rows: int
    dates: tuple[str, ...]


@dataclass(frozen=True)
class PanelRow:
    row_number: int
    unit_id: str
    day: date
    group: str
    metrics: dict[str, float | None]
    contaminated: bool | None
    treatment_applied: bool | None


def _clean_number(value: float | int | None) -> float | int | None:
    if value is None or not math.isfinite(float(value)):
        return None
    rounded = round(float(value), 12)
    return int(rounded) if rounded.is_integer() else rounded


def _canonical_json(value: Mapping[str, Any]) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ExperimentError(f"数据无法序列化为标准 JSON：{exc}") from exc


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _reject_constant(value: str) -> None:
    raise ExperimentError(f"JSON 包含非标准数值 {value}")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExperimentError(f"JSON 包含重复字段：{key}")
        result[key] = value
    return result


def _read_json(path: str | Path, *, label: str) -> tuple[Any, bytes]:
    json_path = Path(path)
    try:
        raw = json_path.read_bytes()
        text = raw.decode("utf-8-sig")
        value = json.loads(
            text,
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except FileNotFoundError as exc:
        raise ExperimentError(f"找不到{label}：{json_path}") from exc
    except UnicodeDecodeError as exc:
        raise ExperimentError(f"{label}不是有效 UTF-8：{json_path}") from exc
    except json.JSONDecodeError as exc:
        raise ExperimentError(f"{label}不是有效 JSON：{exc}") from exc
    except OSError as exc:
        raise ExperimentError(f"无法读取{label} {json_path}：{exc}") from exc
    return value, raw


def _read_csv(path: str | Path, *, label: str) -> tuple[list[dict[str, str]], tuple[str, ...], bytes]:
    csv_path = Path(path)
    try:
        raw = csv_path.read_bytes()
        text = raw.decode("utf-8-sig")
    except FileNotFoundError as exc:
        raise ExperimentError(f"找不到{label}：{csv_path}") from exc
    except UnicodeDecodeError as exc:
        raise ExperimentError(f"{label}不是有效 UTF-8 CSV：{csv_path}") from exc
    except OSError as exc:
        raise ExperimentError(f"无法读取{label} {csv_path}：{exc}") from exc
    if not text.strip():
        raise ExperimentError(f"{label}为空：{csv_path}")
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ExperimentError(f"{label}缺少表头：{csv_path}")
    headers = tuple(header.strip().lstrip("\ufeff") for header in reader.fieldnames)
    if len(set(headers)) != len(headers):
        raise ExperimentError(f"{label}包含重复表头")
    rows: list[dict[str, str]] = []
    for raw_row in reader:
        if None in raw_row:
            raise ExperimentError(f"{label}第 {reader.line_num} 行的列数超过表头")
        normalized = {
            header: (raw_row.get(original) or "").strip()
            for original, header in zip(reader.fieldnames, headers)
        }
        if any(normalized.values()):
            rows.append(normalized)
    if not rows:
        raise ExperimentError(f"{label}没有数据行：{csv_path}")
    return rows, headers, raw


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExperimentError(f"字段 {field} 必须是非空字符串")
    return value.strip()


def _number(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExperimentError(f"字段 {field} 必须是数值")
    number = float(value)
    if not math.isfinite(number):
        raise ExperimentError(f"字段 {field} 必须是有限数")
    if positive and number <= 0:
        raise ExperimentError(f"字段 {field} 必须大于 0")
    return number


def _parse_date(value: Any, field: str) -> date:
    text = _text(value, field)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ExperimentError(f"字段 {field} 必须使用 YYYY-MM-DD") from exc


def _parse_guardrails(value: Any, primary_metric: str) -> tuple[Guardrail, ...]:
    if not isinstance(value, (list, dict)):
        raise ExperimentError("字段 guardrails 必须是数组或按指标命名的对象")
    entries: list[Any]
    if isinstance(value, list):
        entries = value
    else:
        entries = []
        for metric, settings in value.items():
            if isinstance(settings, dict):
                entries.append({"metric": metric, **settings})
            elif isinstance(settings, (int, float)) and not isinstance(settings, bool):
                entries.append({"metric": metric, "threshold": settings})
            else:
                raise ExperimentError(f"guardrails.{metric} 必须是对象或数值")

    guardrails: list[Guardrail] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        field = f"guardrails[{index}]"
        if isinstance(entry, str):
            metric = _text(entry, field)
            direction = "non_decrease"
            threshold = 0.0
        elif isinstance(entry, dict):
            metric = _text(entry.get("metric"), f"{field}.metric")
            direction = entry.get("direction", "non_decrease")
            if direction not in {"non_decrease", "non_increase"}:
                raise ExperimentError(
                    f"{field}.direction 只能是 non_decrease 或 non_increase"
                )
            threshold = _number(entry.get("threshold", 0), f"{field}.threshold")
            if threshold < 0:
                raise ExperimentError(f"{field}.threshold 必须大于或等于 0")
            scale = entry.get("scale", "absolute_did")
            if scale != "absolute_did":
                raise ExperimentError(f"{field}.scale 目前只支持 absolute_did")
        else:
            raise ExperimentError(f"{field} 必须是指标名或配置对象")
        if metric == primary_metric:
            raise ExperimentError(f"护栏指标 {metric} 不能与 primary_metric 重复")
        if metric in seen:
            raise ExperimentError(f"护栏指标重复：{metric}")
        seen.add(metric)
        guardrails.append(Guardrail(metric, direction, threshold))
    return tuple(guardrails)


def _parse_mde(value: Any, primary_metric: str) -> tuple[float, str]:
    if isinstance(value, dict):
        # 同时支持 {"value": ...} 和 {"metric_name": ...} 两种预注册写法。
        candidate: Any
        if "value" in value:
            candidate = value["value"]
            scale = value.get("scale", "absolute")
        elif primary_metric in value:
            candidate = value[primary_metric]
            scale = "absolute"
        else:
            raise ExperimentError(
                "minimum_detectable_effect 对象缺少 value 或 primary_metric 对应值"
            )
        if isinstance(candidate, dict):
            scale = candidate.get("scale", scale)
            candidate = candidate.get("value")
    else:
        candidate = value
        scale = "absolute"
    if scale not in {"absolute", "relative_to_control_baseline"}:
        raise ExperimentError(
            "minimum_detectable_effect.scale 只能是 absolute 或 relative_to_control_baseline"
        )
    return _number(candidate, "minimum_detectable_effect", positive=True), scale


def _optional_timezone(value: Any, field: str) -> str | None:
    if value is None or value == "":
        return None
    timezone_name = _text(value, field)
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ExperimentError(f"字段 {field} 不是可用的 IANA 时区：{timezone_name}") from exc
    return timezone_name


def _optional_bool(value: Any, field: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ExperimentError(f"字段 {field} 必须是 true、false 或 null")


def _optional_data_as_of(value: Any, field: str) -> str | None:
    if value is None or value == "":
        return None
    raw = _text(value, field)
    try:
        if "T" in raw or " " in raw:
            parsed = datetime.fromisoformat(
                raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
            )
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ExperimentError(
                    f"字段 {field} 的时间必须包含 UTC offset 或 Z"
                )
        else:
            date.fromisoformat(raw)
    except ExperimentError:
        raise
    except ValueError as exc:
        raise ExperimentError(f"字段 {field} 必须是 ISO 8601 日期或时间") from exc
    return raw


def _source_mapping(value: Any, field: str) -> dict[str, dict[str, Any]]:
    if value is None:
        return {}
    if isinstance(value, list):
        result: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise ExperimentError(f"字段 {field}[{index}] 必须是对象")
            source_id = _text(item.get("source_id"), f"{field}[{index}].source_id")
            if source_id in result:
                raise ExperimentError(f"字段 {field} 的 source_id 重复：{source_id}")
            result[source_id] = dict(item)
        return result
    if not isinstance(value, dict):
        raise ExperimentError(f"字段 {field} 必须是对象或数组")
    result = {}
    for source_id, item in value.items():
        if not isinstance(source_id, str) or not source_id.strip():
            raise ExperimentError(f"字段 {field} 包含空 source_id")
        if not isinstance(item, dict):
            raise ExperimentError(f"字段 {field}.{source_id} 必须是对象")
        normalized_source_id = source_id.strip()
        if normalized_source_id in result:
            raise ExperimentError(
                f"字段 {field} 的 source_id 规范化后重复：{normalized_source_id}"
            )
        result[normalized_source_id] = dict(item)
    return result


def _source_declaration(
    value: Mapping[str, Any], field: str, *, fallback: Any = None
) -> Any:
    if "sources" in value and "source_metadata" in value:
        raise ExperimentError(
            f"字段 {field} 不得同时声明 sources 与 source_metadata"
        )
    if "sources" in value:
        return value["sources"]
    if "source_metadata" in value:
        return value["source_metadata"]
    return fallback


def _normalize_measurement_source(
    source_id: str,
    raw: Mapping[str, Any],
    timezone_override: str | None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []

    def add(code: str, detail: str) -> None:
        issues.append({"code": code, "source": source_id, "detail": detail})

    source_kind_raw = raw.get("source_kind")
    source_kind = (
        source_kind_raw.strip()
        if isinstance(source_kind_raw, str) and source_kind_raw.strip()
        else "unknown"
    )
    if source_kind == "unknown":
        add("source_kind_missing", "未记录 source_kind。")
    embedded_timezone = _optional_timezone(
        raw.get("source_timezone"), f"measurement_contract.sources.{source_id}.source_timezone"
    )
    if embedded_timezone and timezone_override and embedded_timezone != timezone_override:
        add("source_timezone_inconsistent", "source_timezones 与来源内 source_timezone 不一致。")
    source_timezone = embedded_timezone or timezone_override
    if source_timezone is None and "gsc" in source_kind.casefold():
        source_timezone = DEFAULT_GSC_SOURCE_TIMEZONE
    if source_timezone is None:
        add("source_timezone_missing", "未记录来源日界时区。")
    if "gsc" in source_kind.casefold() and source_timezone != DEFAULT_GSC_SOURCE_TIMEZONE:
        add(
            "gsc_source_timezone_nonstandard",
            "GSC 常规 Search Analytics 日数据应记录为 America/Los_Angeles。",
        )

    finality = raw.get("finality", "unknown")
    if finality not in FINALITY_VALUES:
        raise ExperimentError(
            f"measurement_contract.sources.{source_id}.finality 只能是 final、preliminary 或 unknown"
        )
    explicit_preliminary = raw.get("preliminary")
    if explicit_preliminary is not None and not isinstance(explicit_preliminary, bool):
        raise ExperimentError(
            f"measurement_contract.sources.{source_id}.preliminary 必须是布尔值"
        )
    preliminary = finality == "preliminary" if explicit_preliminary is None else explicit_preliminary
    row_limit_hit = _optional_bool(
        raw.get("row_limit_hit"), f"measurement_contract.sources.{source_id}.row_limit_hit"
    )
    pagination_complete = _optional_bool(
        raw.get("pagination_complete"),
        f"measurement_contract.sources.{source_id}.pagination_complete",
    )
    thresholding_applied = _optional_bool(
        raw.get("thresholding_applied"),
        f"measurement_contract.sources.{source_id}.thresholding_applied",
    )
    sampling_raw = raw.get("sampling_rate")
    sampling_rate: float | None = None
    if sampling_raw is not None:
        if isinstance(sampling_raw, bool) or not isinstance(sampling_raw, (int, float)):
            raise ExperimentError(
                f"measurement_contract.sources.{source_id}.sampling_rate 必须是 0 到 1 的数值"
            )
        sampling_rate = float(sampling_raw)
        if not math.isfinite(sampling_rate) or not 0 <= sampling_rate <= 1:
            raise ExperimentError(
                f"measurement_contract.sources.{source_id}.sampling_rate 必须在 0 到 1 之间"
            )
    attribution_model = raw.get("attribution_model")
    if attribution_model is not None:
        attribution_model = _text(
            attribution_model,
            f"measurement_contract.sources.{source_id}.attribution_model",
        )
    data_as_of = _optional_data_as_of(
        raw.get("data_as_of"), f"measurement_contract.sources.{source_id}.data_as_of"
    )
    declared_quality = raw.get("data_quality", "unknown")
    if isinstance(declared_quality, dict):
        declared_quality = declared_quality.get(
            "declared", declared_quality.get("status", "unknown")
        )
    if declared_quality not in DATA_QUALITY_VALUES:
        raise ExperimentError(
            f"measurement_contract.sources.{source_id}.data_quality 只能是 complete、degraded 或 unknown"
        )

    if data_as_of is None:
        add("data_as_of_missing", "未记录数据截止时间。")
    if finality == "unknown":
        add("finality_unknown", "未记录数据是否已经最终化。")
    elif finality == "preliminary" or preliminary:
        add("data_preliminary", "来源仍处于 preliminary 状态。")
    if explicit_preliminary is not None and explicit_preliminary != (finality == "preliminary"):
        add("finality_preliminary_inconsistent", "finality 与 preliminary 不一致。")
    if row_limit_hit is None:
        add("row_limit_status_missing", "未声明是否触及行数上限。")
    elif row_limit_hit:
        add("row_limit_hit", "来源触及行数上限。")
    if pagination_complete is None:
        add("pagination_status_missing", "未声明分页是否完整。")
    elif not pagination_complete:
        add("pagination_incomplete", "来源分页不完整。")
    source_kind_folded = source_kind.casefold()
    analytics_source = "ga4" in source_kind_folded or "analytics" in source_kind_folded
    if sampling_rate is None:
        if analytics_source:
            add("sampling_rate_missing", "分析平台来源未记录 sampling_rate。")
    elif sampling_rate < 1:
        add("sampling_applied", "来源存在采样。")
    if thresholding_applied is None:
        if analytics_source:
            add("thresholding_status_missing", "分析平台来源未记录 thresholding_applied。")
    elif thresholding_applied:
        add("thresholding_applied", "来源触发阈值处理。")
    if any(token in source_kind_folded for token in ("ga4", "analytics", "crm")):
        if attribution_model is None:
            add("attribution_model_missing", "未记录归因或 cohort 模型。")
    if declared_quality == "unknown":
        add("data_quality_unknown", "来源未声明数据质量。")
    elif declared_quality == "degraded":
        add("data_quality_degraded", "来源声明数据质量已降级。")

    status = "complete" if not issues else (
        "unknown"
        if any(item["code"].endswith(("_missing", "_unknown")) for item in issues)
        else "degraded"
    )
    metrics = raw.get("metrics", [])
    if not isinstance(metrics, list) or any(
        not isinstance(item, str) or not item.strip() for item in metrics
    ):
        raise ExperimentError(
            f"measurement_contract.sources.{source_id}.metrics 必须是字符串数组"
        )
    cleaned_metrics = [item.strip() for item in metrics]
    if len(cleaned_metrics) != len(set(cleaned_metrics)):
        raise ExperimentError(
            f"measurement_contract.sources.{source_id}.metrics 不得重复"
        )
    return (
        {
            "source_id": source_id,
            "source_kind": source_kind,
            "source_timezone": source_timezone,
            "metrics": cleaned_metrics,
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


def _normalize_measurement_contract(root: Mapping[str, Any]) -> dict[str, Any]:
    if "measurement_contract" in root:
        legacy_fields = sorted(
            field
            for field in (
                "analysis_timezone",
                "temporal_grain",
                "source_timezones",
                "sources",
                "source_metadata",
            )
            if field in root
        )
        if legacy_fields:
            raise ExperimentError(
                "measurement_contract 不得与根级来源/legacy 字段同时声明："
                + "、".join(legacy_fields)
            )
    raw_contract = root.get("measurement_contract", {})
    if raw_contract is None:
        raw_contract = {}
    if not isinstance(raw_contract, dict):
        raise ExperimentError("字段 measurement_contract 必须是对象")
    analysis_timezone = _optional_timezone(
        raw_contract.get("analysis_timezone", root.get("analysis_timezone")),
        "measurement_contract.analysis_timezone",
    )
    temporal_grain = raw_contract.get("temporal_grain", root.get("temporal_grain", "date"))
    if temporal_grain != "date":
        raise ExperimentError(
            "experiment panel 目前只支持 date 粒度；timestamp 必须先按统一来源日界生成完整日面板"
        )
    raw_timezones = raw_contract.get("source_timezones", root.get("source_timezones", {}))
    if raw_timezones is None:
        raw_timezones = {}
    if not isinstance(raw_timezones, dict):
        raise ExperimentError("measurement_contract.source_timezones 必须是对象")
    timezone_overrides = {
        str(source_id): _optional_timezone(
            timezone_name, f"measurement_contract.source_timezones.{source_id}"
        )
        for source_id, timezone_name in raw_timezones.items()
    }
    sources_raw = _source_mapping(
        _source_declaration(
            raw_contract,
            "measurement_contract",
            fallback=root.get("source_metadata"),
        ),
        "measurement_contract.sources",
    )
    issues: list[dict[str, str]] = []
    if analysis_timezone is None:
        issues.append(
            {
                "code": "analysis_timezone_missing",
                "source": "measurement_contract",
                "detail": "未记录分析时区。",
            }
        )
    if not sources_raw:
        issues.append(
            {
                "code": "source_metadata_missing",
                "source": "measurement_contract",
                "detail": "未记录实验指标的数据来源元数据。",
            }
        )
    sources: dict[str, dict[str, Any]] = {}
    for source_id, raw in sources_raw.items():
        normalized, source_issues = _normalize_measurement_source(
            source_id, raw, timezone_overrides.get(source_id)
        )
        sources[source_id] = normalized
        issues.extend(source_issues)
    source_timezones = {
        source_id: item["source_timezone"] for source_id, item in sources.items()
    }
    if temporal_grain == "date" and len(sources) > 1:
        known = {value for value in source_timezones.values() if value is not None}
        if len(known) != 1 or not all(source_timezones.values()):
            issues.append(
                {
                    "code": "source_day_boundary_mismatch",
                    "source": ",".join(sorted(sources)),
                    "detail": (
                        "date 粒度来源使用不同或缺失日界；逐日跨源 join 不具备资格，"
                        "应先在各来源内按显式窗口汇总，再构造统一日面板。"
                    ),
                }
            )
    return {
        "analysis_timezone": analysis_timezone,
        "temporal_grain": temporal_grain,
        "source_timezones": source_timezones,
        "daily_cross_source_join_allowed": (
            len(sources) > 1
            and (
                temporal_grain == "timestamp"
                or (
                    len(
                        {
                            value
                            for value in source_timezones.values()
                            if value is not None
                        }
                    )
                    == 1
                    and all(source_timezones.values())
                )
            )
        ),
        "window_aggregation_allowed": True,
        "sources": sources,
        "issues": issues,
    }


def load_spec(path: str | Path) -> ParsedSpec:
    value, raw_bytes = _read_json(path, label="实验 spec")
    if not isinstance(value, dict):
        raise ExperimentError("实验 spec 的顶层必须是 JSON 对象")
    required = (
        "experiment_id",
        "design",
        "unit_id_column",
        "primary_metric",
        "primary_metric_direction",
        "guardrails",
        "seed",
        "treatment_fraction",
        "baseline_start",
        "baseline_end",
        "observation_start",
        "observation_end",
        "minimum_detectable_effect",
        "alpha",
    )
    missing = [field for field in required if field not in value]
    if missing:
        raise ExperimentError("实验 spec 缺少必需字段：" + "、".join(missing))

    experiment_id = _text(value["experiment_id"], "experiment_id")
    design = _text(value["design"], "design")
    if design not in SUPPORTED_DESIGNS:
        raise ExperimentError(
            "design 只能是 randomized_page_holdout 或 matched_page_did；"
            "不接受纯前后对比设计"
        )
    unit_id_column = _text(value["unit_id_column"], "unit_id_column")
    primary_metric = _text(value["primary_metric"], "primary_metric")
    primary_metric_direction = _text(
        value["primary_metric_direction"], "primary_metric_direction"
    )
    if primary_metric_direction not in PRIMARY_METRIC_DIRECTIONS:
        raise ExperimentError(
            "primary_metric_direction 只能是 increase 或 decrease"
        )
    guardrails = _parse_guardrails(value["guardrails"], primary_metric)

    seed = value["seed"]
    if isinstance(seed, bool) or not isinstance(seed, (int, str)) or (
        isinstance(seed, str) and not seed.strip()
    ):
        raise ExperimentError("字段 seed 必须是整数或非空字符串")
    treatment_fraction = _number(value["treatment_fraction"], "treatment_fraction")
    if not 0 < treatment_fraction < 1:
        raise ExperimentError("字段 treatment_fraction 必须在 0 和 1 之间")
    if design == "matched_page_did" and not math.isclose(treatment_fraction, 0.5):
        raise ExperimentError("matched_page_did 要求 treatment_fraction 为 0.5")

    baseline = Window(
        _parse_date(value["baseline_start"], "baseline_start"),
        _parse_date(value["baseline_end"], "baseline_end"),
    )
    observation = Window(
        _parse_date(value["observation_start"], "observation_start"),
        _parse_date(value["observation_end"], "observation_end"),
    )
    if baseline.start > baseline.end:
        raise ExperimentError("baseline_start 不能晚于 baseline_end")
    if observation.start > observation.end:
        raise ExperimentError("observation_start 不能晚于 observation_end")
    if baseline.end >= observation.start:
        raise ExperimentError("基线窗口与观察窗口不得重叠")
    mde_value, mde_scale = _parse_mde(value["minimum_detectable_effect"], primary_metric)
    alpha = _number(value["alpha"], "alpha")
    if not 0 < alpha < 1:
        raise ExperimentError("字段 alpha 必须在 0 和 1 之间")

    # 如果 spec 显式声明广告角色，把边界变成可执行校验。
    paid_role = value.get("paid_ads_role")
    if paid_role is not None:
        allowed_roles = {
            "language_research",
            "search_term_research",
            "landing_page_experiment",
            "none",
        }
        if paid_role not in allowed_roles:
            raise ExperimentError(
                "paid_ads_role 只能是语言/搜索词研究或落地页实验，不能把广告当作排名因素"
            )

    measurement_contract = _normalize_measurement_contract(value)

    return ParsedSpec(
        raw=value,
        sha256=_sha256_bytes(raw_bytes),
        experiment_id=experiment_id,
        design=design,
        unit_id_column=unit_id_column,
        primary_metric=primary_metric,
        primary_metric_direction=primary_metric_direction,
        guardrails=guardrails,
        seed=seed.strip() if isinstance(seed, str) else seed,
        treatment_fraction=treatment_fraction,
        baseline=baseline,
        observation=observation,
        mde_value=mde_value,
        mde_scale=mde_scale,
        alpha=alpha,
        measurement_contract=measurement_contract,
    )


def _csv_number(raw: str, *, label: str) -> float:
    if not raw.strip():
        raise ExperimentError(f"{label}为空")
    try:
        value = float(raw.replace(",", ""))
    except ValueError as exc:
        raise ExperimentError(f"{label}不是有效数值：{raw!r}") from exc
    if not math.isfinite(value):
        raise ExperimentError(f"{label}必须是有限数")
    return value


def load_baseline(path: str | Path, spec: ParsedSpec) -> tuple[list[BaselineUnit], str, int]:
    rows, headers, raw_bytes = _read_csv(path, label="基线 CSV")
    metrics = [spec.primary_metric, *(guardrail.metric for guardrail in spec.guardrails)]
    required = [spec.unit_id_column, *metrics]
    if spec.design == "matched_page_did":
        required.append("pair_id")
    missing_headers = [field for field in required if field not in headers]
    if missing_headers:
        raise ExperimentError("基线 CSV 缺少必需列：" + "、".join(missing_headers))

    values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    pair_by_unit: dict[str, str] = {}
    row_counts: dict[str, int] = defaultdict(int)
    dates_by_unit: dict[str, set[str]] = defaultdict(set)
    seen_unit_dates: set[tuple[str, str]] = set()
    seen_aggregate_units: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        unit_id = row[spec.unit_id_column].strip()
        if not unit_id:
            raise ExperimentError(f"基线 CSV 第 {row_number} 行的 {spec.unit_id_column} 为空")
        if "date" in headers:
            day = _parse_date(row["date"], f"基线 CSV 第 {row_number} 行 date")
            if not spec.baseline.contains(day):
                raise ExperimentError(
                    f"基线 CSV 第 {row_number} 行日期 {day.isoformat()} 不在预注册基线窗口"
                )
            key = (unit_id, day.isoformat())
            if key in seen_unit_dates:
                raise ExperimentError(f"基线 CSV 存在重复的实验单位+日期：{unit_id}, {day}")
            seen_unit_dates.add(key)
            dates_by_unit[unit_id].add(day.isoformat())
        else:
            if unit_id in seen_aggregate_units:
                raise ExperimentError(
                    f"无 date 列的基线 CSV 每个实验单位只能有一行：{unit_id}"
                )
            seen_aggregate_units.add(unit_id)
        row_counts[unit_id] += 1
        for metric in metrics:
            values[unit_id][metric].append(
                _csv_number(row[metric], label=f"基线 CSV 第 {row_number} 行 {metric}")
            )
        if spec.design == "matched_page_did":
            pair_id = row["pair_id"].strip()
            if not pair_id:
                raise ExperimentError(f"基线 CSV 第 {row_number} 行 pair_id 为空")
            previous = pair_by_unit.setdefault(unit_id, pair_id)
            if previous != pair_id:
                raise ExperimentError(f"实验单位 {unit_id} 出现在多个 pair_id 中")

    units = [
        BaselineUnit(
            unit_id=unit_id,
            pair_id=pair_by_unit.get(unit_id),
            metrics={metric: statistics.fmean(metric_values) for metric, metric_values in data.items()},
            source_rows=row_counts[unit_id],
            dates=tuple(sorted(dates_by_unit.get(unit_id, set()))),
        )
        for unit_id, data in sorted(values.items())
    ]
    if len(units) < 2:
        raise ExperimentError("基线 CSV 至少需要 2 个唯一实验单位")
    if "date" in headers:
        expected_dates = {
            (spec.baseline.start + timedelta(days=offset)).isoformat()
            for offset in range((spec.baseline.end - spec.baseline.start).days + 1)
        }
        for unit in units:
            missing_dates = sorted(expected_dates - set(unit.dates))
            if missing_dates:
                raise ExperimentError(
                    f"基线 CSV 的实验单位 {unit.unit_id} 缺少 {len(missing_dates)} 个预注册日期"
                )
    if spec.design == "matched_page_did":
        pair_members: dict[str, list[str]] = defaultdict(list)
        for unit in units:
            assert unit.pair_id is not None
            pair_members[unit.pair_id].append(unit.unit_id)
        invalid = {pair: members for pair, members in pair_members.items() if len(members) != 2}
        if invalid:
            details = "；".join(f"{pair}={len(members)} 页" for pair, members in sorted(invalid.items()))
            raise ExperimentError(f"matched_page_did 要求每个 pair_id 恰好 2 个页面：{details}")
        if len(pair_members) < 2:
            raise ExperimentError("matched_page_did 至少需要 2 对页面才能估计标准误")
    return units, _sha256_bytes(raw_bytes), len(rows)


def _stable_random(seed: int | str) -> random.Random:
    # random.Random 对 str 的算法在同一 Python 主版本稳定；显式加前缀避免 7 与 "7" 混淆。
    return random.Random(f"vibio-seo-experiment-v1:{type(seed).__name__}:{seed}")


def assign_units(units: Sequence[BaselineUnit], spec: ParsedSpec) -> list[dict[str, str]]:
    rng = _stable_random(spec.seed)
    assignments: list[dict[str, str]] = []
    if spec.design == "randomized_page_holdout":
        unit_ids = sorted(unit.unit_id for unit in units)
        rng.shuffle(unit_ids)
        treatment_count = round(len(unit_ids) * spec.treatment_fraction)
        treatment_count = min(max(1, treatment_count), len(unit_ids) - 1)
        treatment = set(unit_ids[:treatment_count])
        for unit_id in sorted(unit_ids):
            assignments.append(
                {"unit_id": unit_id, "group": "treatment" if unit_id in treatment else "control"}
            )
    else:
        by_pair: dict[str, list[str]] = defaultdict(list)
        for unit in units:
            assert unit.pair_id is not None
            by_pair[unit.pair_id].append(unit.unit_id)
        for pair_id, members in sorted(by_pair.items()):
            ordered = sorted(members)
            treatment_id = ordered[rng.randrange(2)]
            for unit_id in ordered:
                assignments.append(
                    {
                        "unit_id": unit_id,
                        "group": "treatment" if unit_id == treatment_id else "control",
                        "pair_id": pair_id,
                    }
                )
    return sorted(assignments, key=lambda item: item["unit_id"])


def _mean(values: Iterable[float]) -> float | None:
    materialized = list(values)
    return statistics.fmean(materialized) if materialized else None


def _sample_variance(values: Sequence[float]) -> float | None:
    return statistics.variance(values) if len(values) >= 2 else None


def _balance_summary(
    units: Sequence[BaselineUnit], assignments: Sequence[Mapping[str, str]], metrics: Sequence[str]
) -> dict[str, Any]:
    group_by_unit = {row["unit_id"]: row["group"] for row in assignments}
    counts = {group: sum(group_by_unit[u.unit_id] == group for u in units) for group in GROUPS}
    metric_rows: dict[str, Any] = {}
    for metric in metrics:
        treatment = [u.metrics[metric] for u in units if group_by_unit[u.unit_id] == "treatment"]
        control = [u.metrics[metric] for u in units if group_by_unit[u.unit_id] == "control"]
        treatment_mean = statistics.fmean(treatment)
        control_mean = statistics.fmean(control)
        variances = [_sample_variance(treatment), _sample_variance(control)]
        available_variances = [value for value in variances if value is not None]
        pooled_sd = math.sqrt(statistics.fmean(available_variances)) if available_variances else None
        absolute = treatment_mean - control_mean
        metric_rows[metric] = {
            "treatment_mean": _clean_number(treatment_mean),
            "control_mean": _clean_number(control_mean),
            "absolute_difference": _clean_number(absolute),
            "standardized_difference": _clean_number(absolute / pooled_sd)
            if pooled_sd and pooled_sd > 0
            else None,
            "note": "仅描述基线平衡，不进行事后显著性筛选。",
        }
    return {"unit_counts": counts, "metrics": metric_rows}


def _assignments_csv(assignments: Sequence[Mapping[str, str]], unit_column: str, matched: bool) -> bytes:
    buffer = io.StringIO(newline="")
    fieldnames = [unit_column, "group", *( ["pair_id"] if matched else [])]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for item in assignments:
        row = {unit_column: item["unit_id"], "group": item["group"]}
        if matched:
            row["pair_id"] = item["pair_id"]
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def compute_plan_hash(plan: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(plan))
    payload.pop("plan_hash", None)
    return _sha256_bytes(_canonical_json(payload).encode("utf-8"))


def build_plan(spec: ParsedSpec, units: Sequence[BaselineUnit], baseline_sha256: str, row_count: int) -> tuple[dict[str, Any], bytes]:
    assignments = assign_units(units, spec)
    assignments_bytes = _assignments_csv(
        assignments, spec.unit_id_column, spec.design == "matched_page_did"
    )
    metrics = [spec.primary_metric, *(guardrail.metric for guardrail in spec.guardrails)]
    baseline_units = [
        {
            "unit_id": unit.unit_id,
            "pair_id": unit.pair_id,
            "metrics": {
                metric: _clean_number(unit.metrics[metric]) for metric in sorted(unit.metrics)
            },
            "source_rows": unit.source_rows,
            "dates": list(unit.dates),
        }
        for unit in sorted(units, key=lambda item: item.unit_id)
    ]
    baseline_units_sha256 = _sha256_bytes(
        json.dumps(
            baseline_units,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )
    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "experiment_id": spec.experiment_id,
        "design": spec.design,
        "unit_id_column": spec.unit_id_column,
        "preregistration": {
            "primary_metric": spec.primary_metric,
            "primary_metric_direction": spec.primary_metric_direction,
            "guardrails": [guardrail.as_dict() for guardrail in spec.guardrails],
            "seed": spec.seed,
            "treatment_fraction": _clean_number(spec.treatment_fraction),
            "baseline_window": spec.baseline.as_dict(),
            "observation_window": spec.observation.as_dict(),
            "minimum_detectable_effect": {
                "value": _clean_number(spec.mde_value),
                "scale": spec.mde_scale,
            },
            "alpha": _clean_number(spec.alpha),
        },
        "frozen_inputs": {
            "spec_sha256": spec.sha256,
            "baseline_sha256": baseline_sha256,
            "baseline_source_rows": row_count,
            "baseline_temporal_grain": "date"
            if any(unit.dates for unit in units)
            else "window_aggregate",
            "baseline_units": baseline_units,
            "baseline_units_sha256": baseline_units_sha256,
        },
        "measurement_contract": spec.measurement_contract,
        "assignments": assignments,
        "assignments_sha256": _sha256_bytes(assignments_bytes),
        "balance": _balance_summary(units, assignments, metrics),
        "boundaries": {
            "causality": CAUSALITY_BOUNDARY,
            "paid_search": PAID_SEARCH_BOUNDARY,
            "power": POWER_BOUNDARY,
        },
    }
    plan["plan_hash"] = compute_plan_hash(plan)
    return plan, assignments_bytes


def _write_new(path: Path, raw: bytes, *, label: str) -> None:
    try:
        with path.open("xb") as handle:
            handle.write(raw)
    except FileExistsError as exc:
        raise ExperimentError(f"{label}已存在，为保护冻结计划拒绝覆盖：{path}") from exc
    except OSError as exc:
        raise ExperimentError(f"无法写入{label} {path}：{exc}") from exc


def plan_experiment(spec_path: str | Path, baseline_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    spec = load_spec(spec_path)
    units, baseline_hash, row_count = load_baseline(baseline_path, spec)
    plan, assignments_bytes = build_plan(spec, units, baseline_hash, row_count)
    target = Path(out_dir)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ExperimentError(f"无法创建输出目录 {target}：{exc}") from exc
    assignments_path = target / "assignments.csv"
    plan_path = target / "plan.json"
    if assignments_path.exists() or plan_path.exists():
        existing = assignments_path if assignments_path.exists() else plan_path
        raise ExperimentError(f"冻结计划文件已存在，拒绝覆盖：{existing}")
    _write_new(assignments_path, assignments_bytes, label="assignments.csv")
    try:
        _write_new(
            plan_path,
            (json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"),
            label="plan.json",
        )
    except Exception:
        # 避免 plan.json 失败后留下看似有效的孤立分组文件。
        try:
            assignments_path.unlink()
        except OSError:
            pass
        raise
    return plan


def _validate_frozen_preregistration(
    preregistration: Mapping[str, Any], design: str
) -> None:
    """Validate every canonical numeric/option field consumed during analysis."""

    primary_metric = _text(
        preregistration.get("primary_metric"), "preregistration.primary_metric"
    )
    direction = preregistration.get("primary_metric_direction")
    if direction not in PRIMARY_METRIC_DIRECTIONS:
        raise ExperimentError(
            "plan.json 的 preregistration.primary_metric_direction 无效"
        )
    guardrails = preregistration.get("guardrails")
    if not isinstance(guardrails, list) or any(
        not isinstance(item, dict) for item in guardrails
    ):
        raise ExperimentError("plan.json 的 preregistration.guardrails 必须是对象数组")
    for index, item in enumerate(guardrails):
        required = {"metric", "direction", "threshold", "scale"}
        missing = sorted(required - set(item))
        if missing:
            raise ExperimentError(
                f"plan.json 的 preregistration.guardrails[{index}] 缺少字段："
                + "、".join(missing)
            )
    _parse_guardrails(guardrails, primary_metric)

    seed = preregistration.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, (int, str)) or (
        isinstance(seed, str) and not seed.strip()
    ):
        raise ExperimentError("plan.json 的 preregistration.seed 必须是整数或非空字符串")
    treatment_fraction = _number(
        preregistration.get("treatment_fraction"),
        "preregistration.treatment_fraction",
    )
    if not 0 < treatment_fraction < 1:
        raise ExperimentError("plan.json 的 treatment_fraction 必须在 0 和 1 之间")
    if design == "matched_page_did" and not math.isclose(treatment_fraction, 0.5):
        raise ExperimentError("matched_page_did 的冻结 treatment_fraction 必须为 0.5")

    mde = preregistration.get("minimum_detectable_effect")
    if not isinstance(mde, dict) or set(("value", "scale")) - set(mde):
        raise ExperimentError(
            "plan.json 的 preregistration.minimum_detectable_effect 结构无效"
        )
    _parse_mde(mde, primary_metric)
    alpha = _number(preregistration.get("alpha"), "preregistration.alpha")
    if not 0 < alpha < 1:
        raise ExperimentError("plan.json 的 preregistration.alpha 必须在 0 和 1 之间")


def load_and_verify_plan(path: str | Path) -> tuple[dict[str, Any], bytes]:
    value, raw = _read_json(path, label="冻结 plan")
    if not isinstance(value, dict):
        raise ExperimentError("plan.json 顶层必须是对象")
    required = {
        "schema_version",
        "tool",
        "experiment_id",
        "design",
        "unit_id_column",
        "preregistration",
        "frozen_inputs",
        "measurement_contract",
        "assignments",
        "assignments_sha256",
        "balance",
        "boundaries",
        "plan_hash",
    }
    missing = sorted(required - set(value))
    if missing:
        raise ExperimentError("plan.json 缺少正式计划字段：" + "、".join(missing))
    if value.get("schema_version") != SCHEMA_VERSION or value.get("tool") != TOOL_NAME:
        raise ExperimentError("plan.json 不是受支持的正式实验计划")
    _text(value.get("experiment_id"), "experiment_id")
    _text(value.get("unit_id_column"), "unit_id_column")
    expected = value.get("plan_hash")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ExperimentError("plan.json 缺少有效 plan_hash")
    actual = compute_plan_hash(value)
    if actual != expected:
        raise ExperimentError(f"plan hash 不匹配：期望 {expected}，实际 {actual}")
    if value.get("design") not in SUPPORTED_DESIGNS:
        raise ExperimentError("plan.json 包含不受支持的设计，不接受纯前后对比")
    preregistration = value.get("preregistration")
    if not isinstance(preregistration, dict):
        raise ExperimentError("plan.json 缺少 preregistration")
    _validate_frozen_preregistration(preregistration, str(value["design"]))
    baseline_window = _window_from_plan(value, "baseline_window")
    observation_window = _window_from_plan(value, "observation_window")
    if baseline_window.start > baseline_window.end:
        raise ExperimentError("plan.json 的基线窗口顺序无效")
    if observation_window.start > observation_window.end:
        raise ExperimentError("plan.json 的观察窗口顺序无效")
    if baseline_window.end >= observation_window.start:
        raise ExperimentError("plan.json 的基线与观察窗口重叠")
    assignments = value.get("assignments")
    if not isinstance(assignments, list) or not assignments:
        raise ExperimentError("plan.json 缺少分组 assignments")
    seen: dict[str, str] = {}
    pair_members: dict[str, list[str]] = defaultdict(list)
    assignment_by_unit: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(assignments):
        if not isinstance(row, dict):
            raise ExperimentError(f"assignments[{index}] 必须是对象")
        unit_id = _text(row.get("unit_id"), f"assignments[{index}].unit_id")
        group = row.get("group")
        if group not in GROUPS:
            raise ExperimentError(f"assignments[{index}].group 无效")
        if unit_id in seen:
            raise ExperimentError(f"非法分组重叠：实验单位 {unit_id} 被重复分配")
        seen[unit_id] = group
        assignment_by_unit[unit_id] = row
        if value["design"] == "matched_page_did":
            pair_id = _text(row.get("pair_id"), f"assignments[{index}].pair_id")
            pair_members[pair_id].append(group)
    if set(seen.values()) != set(GROUPS):
        raise ExperimentError("分组必须同时包含 treatment 和 control")
    if value["design"] == "matched_page_did" and any(
        len(groups) != 2 or set(groups) != set(GROUPS)
        for groups in pair_members.values()
    ):
        raise ExperimentError(
            "matched_page_did 的每个 pair_id 必须恰好包含一条实验组和一条对照组"
        )
    assignments_bytes = _assignments_csv(
        assignments, _text(value.get("unit_id_column"), "unit_id_column"), value["design"] == "matched_page_did"
    )
    actual_assignments_hash = _sha256_bytes(assignments_bytes)
    if actual_assignments_hash != value.get("assignments_sha256"):
        raise ExperimentError("plan.json 内的 assignments_sha256 不匹配")

    frozen_inputs = value.get("frozen_inputs")
    if not isinstance(frozen_inputs, dict):
        raise ExperimentError("plan.json 缺少 frozen_inputs")
    for hash_field in ("spec_sha256", "baseline_sha256", "baseline_units_sha256"):
        hash_value = frozen_inputs.get(hash_field)
        if not isinstance(hash_value, str) or not re.fullmatch(r"[0-9a-f]{64}", hash_value):
            raise ExperimentError(f"frozen_inputs.{hash_field} 必须是 SHA-256")
    baseline_units = frozen_inputs.get("baseline_units")
    if not isinstance(baseline_units, list) or not baseline_units:
        raise ExperimentError("plan.json 缺少冻结的 baseline_units")
    normalized_baseline = json.dumps(
        baseline_units,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if _sha256_bytes(normalized_baseline) != frozen_inputs.get("baseline_units_sha256"):
        raise ExperimentError("plan.json 内的 baseline_units_sha256 不匹配")
    baseline_ids: list[str] = []
    prereg = preregistration
    required_metrics = {
        _text(prereg.get("primary_metric"), "preregistration.primary_metric"),
        *{
            _text(item.get("metric"), "preregistration.guardrails.metric")
            for item in prereg.get("guardrails", [])
            if isinstance(item, dict)
        },
    }
    baseline_window = _window_from_plan(value, "baseline_window")
    temporal_grain = frozen_inputs.get("baseline_temporal_grain")
    if temporal_grain not in {"date", "window_aggregate"}:
        raise ExperimentError("frozen_inputs.baseline_temporal_grain 无效")
    expected_baseline_dates = {
        item.isoformat() for item in _window_dates(baseline_window)
    }
    reconstructed_units: list[BaselineUnit] = []
    for index, row in enumerate(baseline_units):
        if not isinstance(row, dict):
            raise ExperimentError(f"frozen_inputs.baseline_units[{index}] 必须是对象")
        unit_id = _text(
            row.get("unit_id"), f"frozen_inputs.baseline_units[{index}].unit_id"
        )
        baseline_ids.append(unit_id)
        assignment = assignment_by_unit.get(unit_id)
        if assignment is None:
            raise ExperimentError("冻结 baseline_units 包含未分组的实验单位")
        metrics = row.get("metrics")
        if not isinstance(metrics, dict) or set(metrics) != required_metrics:
            raise ExperimentError(
                f"frozen_inputs.baseline_units[{index}].metrics 必须精确覆盖预注册指标"
            )
        for metric, metric_value in metrics.items():
            if (
                not isinstance(metric_value, (int, float))
                or isinstance(metric_value, bool)
                or not math.isfinite(float(metric_value))
            ):
                raise ExperimentError(
                    f"frozen_inputs.baseline_units[{index}].metrics.{metric} 必须是有限数"
                )
        source_rows = row.get("source_rows")
        dates = row.get("dates")
        if (
            not isinstance(source_rows, int)
            or isinstance(source_rows, bool)
            or source_rows < 1
            or not isinstance(dates, list)
            or any(not isinstance(item, str) for item in dates)
            or len(dates) != len(set(dates))
        ):
            raise ExperimentError(
                f"frozen_inputs.baseline_units[{index}] 的 source_rows/dates 无效"
            )
        if temporal_grain == "date" and (
            set(dates) != expected_baseline_dates or source_rows != len(expected_baseline_dates)
        ):
            raise ExperimentError("冻结 date 基线未完整覆盖预注册窗口")
        if temporal_grain == "window_aggregate" and (dates or source_rows != 1):
            raise ExperimentError("冻结窗口聚合基线必须每单位一行且 dates 为空")
        frozen_pair = row.get("pair_id")
        assigned_pair = assignment.get("pair_id")
        if value["design"] == "matched_page_did":
            if frozen_pair != assigned_pair:
                raise ExperimentError("冻结 baseline pair_id 与 assignment 不匹配")
        elif frozen_pair is not None:
            raise ExperimentError("随机 holdout 的冻结 baseline pair_id 必须为 null")
        reconstructed_units.append(
            BaselineUnit(
                unit_id=unit_id,
                pair_id=frozen_pair if isinstance(frozen_pair, str) else None,
                metrics={str(key): float(item) for key, item in metrics.items()},
                source_rows=source_rows,
                dates=tuple(sorted(dates)),
            )
        )
    if len(baseline_ids) != len(set(baseline_ids)):
        raise ExperimentError("冻结 baseline_units 包含重复实验单位")
    if set(baseline_ids) != set(seen):
        raise ExperimentError("冻结 baseline_units 与 assignments 的实验单位不一致")
    baseline_source_rows = frozen_inputs.get("baseline_source_rows")
    if (
        not isinstance(baseline_source_rows, int)
        or isinstance(baseline_source_rows, bool)
        or baseline_source_rows != sum(int(row["source_rows"]) for row in baseline_units)
    ):
        raise ExperimentError(
            "frozen_inputs.baseline_source_rows 与各实验单位 source_rows 总和不一致"
        )

    measurement_contract = value.get("measurement_contract")
    if not isinstance(measurement_contract, dict):
        raise ExperimentError("plan.json 的 measurement_contract 必须是对象")
    _normalize_measurement_contract({"measurement_contract": measurement_contract})
    balance = value.get("balance")
    boundaries = value.get("boundaries")
    if not isinstance(balance, dict) or not isinstance(boundaries, dict):
        raise ExperimentError("plan.json 的 balance/boundaries 必须是对象")
    for field in ("causality", "paid_search", "power"):
        _text(boundaries.get(field), f"boundaries.{field}")

    guardrails = _parse_guardrails(preregistration["guardrails"], str(preregistration["primary_metric"]))
    mde_value, mde_scale = _parse_mde(
        preregistration["minimum_detectable_effect"], str(preregistration["primary_metric"])
    )
    frozen_spec = ParsedSpec(
        raw={},
        sha256=str(frozen_inputs["spec_sha256"]),
        experiment_id=str(value["experiment_id"]),
        design=str(value["design"]),
        unit_id_column=str(value["unit_id_column"]),
        primary_metric=str(preregistration["primary_metric"]),
        primary_metric_direction=str(preregistration["primary_metric_direction"]),
        guardrails=guardrails,
        seed=preregistration["seed"],
        treatment_fraction=float(preregistration["treatment_fraction"]),
        baseline=baseline_window,
        observation=observation_window,
        mde_value=mde_value,
        mde_scale=mde_scale,
        alpha=float(preregistration["alpha"]),
        measurement_contract=measurement_contract,
    )
    expected_assignments = assign_units(reconstructed_units, frozen_spec)
    if assignments != expected_assignments:
        raise ExperimentError("冻结 assignments 与 seed/design/treatment_fraction 重放结果不一致")
    metrics_order = [
        frozen_spec.primary_metric,
        *(guardrail.metric for guardrail in frozen_spec.guardrails),
    ]
    expected_balance = _balance_summary(
        reconstructed_units, expected_assignments, metrics_order
    )
    if balance != expected_balance:
        raise ExperimentError("冻结 balance 与 baseline_units/assignments 重算结果不一致")

    sibling = Path(path).with_name("assignments.csv")
    if sibling.exists():
        try:
            sibling_hash = _sha256_bytes(sibling.read_bytes())
        except OSError as exc:
            raise ExperimentError(f"无法校验 {sibling}：{exc}") from exc
        if sibling_hash != value["assignments_sha256"]:
            raise ExperimentError("assignments.csv 与冻结 plan 不匹配")
    return value, raw


def _window_from_plan(plan: Mapping[str, Any], name: str) -> Window:
    prereg = plan.get("preregistration")
    if not isinstance(prereg, dict) or not isinstance(prereg.get(name), dict):
        raise ExperimentError(f"plan.json 缺少 preregistration.{name}")
    raw = prereg[name]
    return Window(_parse_date(raw.get("start"), f"{name}.start"), _parse_date(raw.get("end"), f"{name}.end"))


def _parse_group(raw: str, *, label: str) -> str:
    group = GROUP_ALIASES.get(raw.strip().casefold())
    if group is None:
        raise ExperimentError(f"{label}不是有效分组：{raw!r}")
    return group


def _parse_bool(raw: str, *, label: str) -> bool:
    normalized = raw.strip().casefold()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ExperimentError(f"{label}必须是 true/false（也支持是/否、1/0）")


def _load_panel(path: str | Path, plan: Mapping[str, Any]) -> tuple[list[PanelRow], str, list[dict[str, Any]], bool]:
    rows, headers, raw = _read_csv(path, label="panel CSV")
    unit_column = _text(plan.get("unit_id_column"), "unit_id_column")
    prereg = plan["preregistration"]
    primary = _text(prereg.get("primary_metric"), "primary_metric")
    guardrails = prereg.get("guardrails", [])
    if not isinstance(guardrails, list):
        raise ExperimentError("plan.json 的 guardrails 无效")
    metrics = [primary, *[_text(item.get("metric"), "guardrail.metric") for item in guardrails]]
    required = [unit_column, "date", "group", *metrics]
    missing_headers = [field for field in required if field not in headers]
    issues: list[dict[str, Any]] = []
    if missing_headers:
        return [], _sha256_bytes(raw), [{"code": "missing_columns", "detail": "缺少列：" + "、".join(missing_headers)}], False

    assignments = {row["unit_id"]: row["group"] for row in plan["assignments"]}
    observed_groups: dict[str, set[str]] = defaultdict(set)
    parsed: list[PanelRow] = []
    seen_keys: set[tuple[str, date]] = set()
    contamination_observable = "treatment_applied" in headers
    for row_number, row in enumerate(rows, start=2):
        unit_id = row[unit_column].strip()
        if not unit_id:
            issues.append({"code": "missing_unit_id", "row": row_number})
            continue
        try:
            day = _parse_date(row["date"], f"panel CSV 第 {row_number} 行 date")
            group = _parse_group(row["group"], label=f"panel CSV 第 {row_number} 行 group")
        except ExperimentError as exc:
            issues.append({"code": "invalid_dimension", "row": row_number, "detail": str(exc)})
            continue
        observed_groups[unit_id].add(group)
        key = (unit_id, day)
        if key in seen_keys:
            issues.append({"code": "duplicate_unit_date", "row": row_number, "unit_id": unit_id, "date": day.isoformat()})
            continue
        seen_keys.add(key)
        if unit_id not in assignments:
            issues.append({"code": "unknown_unit", "row": row_number, "unit_id": unit_id})
        elif assignments[unit_id] != group:
            issues.append({"code": "assignment_mismatch", "row": row_number, "unit_id": unit_id})

        metric_values: dict[str, float | None] = {}
        for metric in metrics:
            try:
                metric_values[metric] = _csv_number(
                    row[metric], label=f"panel CSV 第 {row_number} 行 {metric}"
                )
            except ExperimentError as exc:
                metric_values[metric] = None
                issues.append({"code": "missing_or_invalid_metric", "row": row_number, "metric": metric, "detail": str(exc)})
        contaminated: bool | None = None
        treatment_applied: bool | None = None
        if "contaminated" in headers:
            try:
                contaminated = _parse_bool(row["contaminated"], label=f"panel CSV 第 {row_number} 行 contaminated")
            except ExperimentError as exc:
                issues.append({"code": "invalid_contamination_flag", "row": row_number, "detail": str(exc)})
        if "treatment_applied" in headers:
            try:
                treatment_applied = _parse_bool(row["treatment_applied"], label=f"panel CSV 第 {row_number} 行 treatment_applied")
            except ExperimentError as exc:
                issues.append({"code": "invalid_treatment_flag", "row": row_number, "detail": str(exc)})
        parsed.append(PanelRow(row_number, unit_id, day, group, metric_values, contaminated, treatment_applied))

    overlap = {unit: groups for unit, groups in observed_groups.items() if len(groups) > 1}
    if overlap:
        units = "、".join(sorted(overlap))
        raise ExperimentError(f"非法 panel 分组重叠：同一实验单位出现在多组：{units}")
    if not contamination_observable:
        issues.append({
            "code": "contamination_not_observable",
            "detail": "panel 需要 treatment_applied 列才能核验 treatment/control 依从性；contaminated 可作为附加标记。",
        })
    return parsed, _sha256_bytes(raw), issues, contamination_observable


def _artifact_status(path: str | Path, plan: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    value, raw = _read_json(path, label="artifact report")
    if not isinstance(value, dict):
        raise ExperimentError("artifact report 顶层必须是对象")
    missing = [
        field
        for field in ("experiment_id", "plan_hash", "passed", "evidence")
        if field not in value
    ]
    if missing:
        raise ExperimentError("artifact report 缺少必需字段：" + "、".join(missing))
    passed = value.get("passed")
    if not isinstance(passed, bool):
        raise ExperimentError("artifact report 的 passed 必须是布尔值")
    if value["plan_hash"] != plan["plan_hash"]:
        raise ExperimentError("artifact report 的 plan_hash 与冻结计划不匹配")
    if value["experiment_id"] != plan["experiment_id"]:
        raise ExperimentError("artifact report 的 experiment_id 与冻结计划不匹配")
    evidence = value["evidence"]
    if not (
        (isinstance(evidence, str) and evidence.strip())
        or (isinstance(evidence, (list, dict)) and bool(evidence))
    ):
        raise ExperimentError("artifact report 的 evidence 必须是非空证据")
    return {
        "experiment_id": value["experiment_id"],
        "plan_hash": value["plan_hash"],
        "passed": passed,
        "status": "passed" if passed is True else "failed" if passed is False else "unverified",
        "evidence": evidence,
    }, _sha256_bytes(raw)


def _period_for(day: date, baseline: Window, observation: Window) -> str | None:
    if baseline.contains(day):
        return "baseline"
    if observation.contains(day):
        return "current"
    return None


def _metric_estimate(
    metric: str,
    panel: Sequence[PanelRow],
    plan: Mapping[str, Any],
    baseline: Window,
    observation: Window,
) -> dict[str, Any]:
    # 先对每个页面和窗口求均值，然后按随机化单位求组均值。
    unit_values: dict[tuple[str, str], list[float]] = defaultdict(list)
    assignment_rows = {row["unit_id"]: row for row in plan["assignments"]}
    for row in panel:
        period = _period_for(row.day, baseline, observation)
        value = row.metrics.get(metric)
        if period is not None and value is not None and row.unit_id in assignment_rows:
            unit_values[(row.unit_id, period)].append(value)

    unit_period_means = {
        key: statistics.fmean(values) for key, values in unit_values.items() if values
    }
    changes: dict[str, list[float]] = {group: [] for group in GROUPS}
    levels: dict[str, dict[str, list[float]]] = {
        group: {"baseline": [], "current": []} for group in GROUPS
    }
    unit_changes: dict[str, float] = {}
    for unit_id, assignment in assignment_rows.items():
        before = unit_period_means.get((unit_id, "baseline"))
        after = unit_period_means.get((unit_id, "current"))
        if before is None or after is None:
            continue
        group = assignment["group"]
        levels[group]["baseline"].append(before)
        levels[group]["current"].append(after)
        change = after - before
        changes[group].append(change)
        unit_changes[unit_id] = change

    arms: dict[str, Any] = {}
    for group in GROUPS:
        baseline_mean = _mean(levels[group]["baseline"])
        current_mean = _mean(levels[group]["current"])
        absolute = current_mean - baseline_mean if baseline_mean is not None and current_mean is not None else None
        relative = absolute / abs(baseline_mean) if absolute is not None and baseline_mean not in (None, 0) else None
        arms[group] = {
            "units": len(changes[group]),
            "baseline_mean": _clean_number(baseline_mean),
            "current_mean": _clean_number(current_mean),
            "absolute_change": _clean_number(absolute),
            "relative_change": _clean_number(relative),
        }

    treatment_change = arms["treatment"]["absolute_change"]
    control_change = arms["control"]["absolute_change"]
    did = (
        float(treatment_change) - float(control_change)
        if treatment_change is not None and control_change is not None
        else None
    )
    se: float | None = None
    inference_units = 0
    if plan["design"] == "randomized_page_holdout":
        treatment_var = _sample_variance(changes["treatment"])
        control_var = _sample_variance(changes["control"])
        if treatment_var is not None and control_var is not None:
            se = math.sqrt(treatment_var / len(changes["treatment"]) + control_var / len(changes["control"]))
            inference_units = len(changes["treatment"]) + len(changes["control"])
    else:
        pair_differences: list[float] = []
        pairs: dict[str, dict[str, str]] = defaultdict(dict)
        for item in plan["assignments"]:
            pairs[item["pair_id"]][item["group"]] = item["unit_id"]
        for members in pairs.values():
            treatment_unit = members.get("treatment")
            control_unit = members.get("control")
            if treatment_unit in unit_changes and control_unit in unit_changes:
                pair_differences.append(unit_changes[treatment_unit] - unit_changes[control_unit])
        pair_variance = _sample_variance(pair_differences)
        if pair_variance is not None:
            se = math.sqrt(pair_variance / len(pair_differences))
            inference_units = len(pair_differences)

    alpha = float(plan["preregistration"]["alpha"])
    confidence = 1 - alpha
    z_score = statistics.NormalDist().inv_cdf(1 - alpha / 2)
    lower = upper = half_width = None
    if did is not None and se is not None:
        half_width = z_score * se
        lower, upper = did - half_width, did + half_width

    mde_config = plan["preregistration"]["minimum_detectable_effect"]
    mde = float(mde_config["value"])
    control_baseline = arms["control"]["baseline_mean"]
    if mde_config.get("scale") == "relative_to_control_baseline":
        mde_absolute = mde * abs(float(control_baseline)) if control_baseline not in (None, 0) else None
    else:
        mde_absolute = mde
    precision_sufficient = (
        half_width <= mde_absolute if half_width is not None and mde_absolute is not None else False
    )
    relative_did = (
        did / abs(float(control_baseline)) if did is not None and control_baseline not in (None, 0) else None
    )
    return {
        "metric": metric,
        "unit_of_analysis": "page" if plan["design"] == "randomized_page_holdout" else "matched_pair",
        "arms": arms,
        "difference_in_differences": _clean_number(did),
        "relative_difference_in_differences": _clean_number(relative_did),
        "standard_error": _clean_number(se),
        "confidence_interval": {
            "level": _clean_number(confidence),
            "method": "normal_approximation",
            "lower": _clean_number(lower),
            "upper": _clean_number(upper),
            "half_width": _clean_number(half_width),
        },
        "inference_units": inference_units,
        "detectability": {
            "preregistered_mde": _clean_number(mde),
            "mde_scale": mde_config.get("scale", "absolute"),
            "mde_in_metric_units": _clean_number(mde_absolute),
            "precision_sufficient_for_mde": precision_sufficient,
            "power": None,
            "note": POWER_BOUNDARY,
        },
    }


def _window_dates(window: Window) -> set[date]:
    return {
        window.start + timedelta(days=offset)
        for offset in range((window.end - window.start).days + 1)
    }


def _validate_panel_quality(
    rows: Sequence[PanelRow],
    plan: Mapping[str, Any],
    baseline: Window,
    observation: Window,
    initial_issues: list[dict[str, Any]],
    analysis_as_of: date,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    issues = list(initial_issues)
    expected = {row["unit_id"]: row["group"] for row in plan["assignments"]}
    periods_by_unit: dict[str, set[str]] = defaultdict(set)
    dates_by_unit_period: dict[tuple[str, str], set[date]] = defaultdict(set)
    for row in rows:
        period = _period_for(row.day, baseline, observation)
        if period is None:
            issues.append({
                "code": "outside_preregistered_windows",
                "row": row.row_number,
                "date": row.day.isoformat(),
            })
            continue
        periods_by_unit[row.unit_id].add(period)
        if row.unit_id in expected:
            dates_by_unit_period[(row.unit_id, period)].add(row.day)
        if row.contaminated is True:
            issues.append({"code": "contamination_detected", "row": row.row_number, "unit_id": row.unit_id})
        if row.treatment_applied is not None:
            expected_applied = period == "current" and expected.get(row.unit_id) == "treatment"
            if row.treatment_applied != expected_applied:
                issues.append({
                    "code": "treatment_contamination",
                    "row": row.row_number,
                    "unit_id": row.unit_id,
                    "expected_applied": expected_applied,
                })
    for unit_id in sorted(expected):
        missing_periods = {"baseline", "current"} - periods_by_unit.get(unit_id, set())
        if missing_periods:
            issues.append({
                "code": "missing_unit_period",
                "unit_id": unit_id,
                "periods": sorted(missing_periods),
            })
    expected_dates = {
        "baseline": _window_dates(baseline),
        "current": _window_dates(observation),
    }
    coverage_periods: dict[str, Any] = {}
    for period, period_dates in expected_dates.items():
        observed_unit_days = 0
        for unit_id in sorted(expected):
            observed = dates_by_unit_period.get((unit_id, period), set())
            observed_unit_days += len(observed)
            missing = sorted(period_dates - observed)
            if missing:
                issues.append(
                    {
                        "code": "missing_unit_dates",
                        "unit_id": unit_id,
                        "period": period,
                        "missing_count": len(missing),
                        "missing_date_examples": [item.isoformat() for item in missing[:5]],
                    }
                )
        expected_unit_days = len(expected) * len(period_dates)
        coverage_periods[period] = {
            "expected_dates": len(period_dates),
            "expected_unit_days": expected_unit_days,
            "observed_unit_days": observed_unit_days,
            "complete": observed_unit_days == expected_unit_days,
        }

    frozen = plan.get("frozen_inputs", {})
    frozen_units = frozen.get("baseline_units", []) if isinstance(frozen, Mapping) else []
    frozen_by_unit = {
        item.get("unit_id"): item
        for item in frozen_units
        if isinstance(item, Mapping) and isinstance(item.get("unit_id"), str)
    }
    baseline_metric_values: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        if baseline.contains(row.day) and row.unit_id in expected:
            for metric, value in row.metrics.items():
                if value is not None:
                    baseline_metric_values[(row.unit_id, metric)].append(value)
    for unit_id in sorted(expected):
        frozen_metrics = frozen_by_unit.get(unit_id, {}).get("metrics", {})
        if not isinstance(frozen_metrics, Mapping):
            issues.append({"code": "frozen_baseline_missing", "unit_id": unit_id})
            continue
        for metric, expected_value in frozen_metrics.items():
            observed_values = baseline_metric_values.get((unit_id, str(metric)), [])
            if not observed_values:
                continue
            observed_mean = statistics.fmean(observed_values)
            if not math.isclose(
                observed_mean,
                float(expected_value),
                rel_tol=1e-9,
                abs_tol=1e-12,
            ):
                issues.append(
                    {
                        "code": "frozen_baseline_mismatch",
                        "unit_id": unit_id,
                        "metric": metric,
                        "expected": _clean_number(float(expected_value)),
                        "observed": _clean_number(observed_mean),
                    }
                )
    if analysis_as_of <= observation.end:
        issues.append({
            "code": "observation_not_mature",
            "observation_end": observation.end.isoformat(),
            "as_of": analysis_as_of.isoformat(),
        })
    return issues, {
        "temporal_grain": "date",
        "expected_units": len(expected),
        "periods": coverage_periods,
        "complete": all(item["complete"] for item in coverage_periods.values()),
        "frozen_baseline_bound": not any(
            item.get("code") in {"frozen_baseline_missing", "frozen_baseline_mismatch"}
            for item in issues
        ),
    }


def _merge_measurement_contract(
    frozen: Mapping[str, Any], override: Mapping[str, Any]
) -> dict[str, Any]:
    """Merge only collection-time status into an immutable preregistration."""

    merged = copy.deepcopy(dict(frozen))
    frozen_sources = merged.get("sources", {})
    if not isinstance(frozen_sources, dict):
        frozen_sources = {}
    override_sources = _source_declaration(
        override, "measurement metadata", fallback={}
    )
    if override_sources is not None:
        override_sources = _source_mapping(override_sources, "measurement metadata sources")
        for source_id, item in override_sources.items():
            previous = frozen_sources.get(source_id)
            if not isinstance(previous, dict):
                continue
            for field in MEASUREMENT_COLLECTION_STATUS_FIELDS:
                if field in item:
                    previous[field] = copy.deepcopy(item[field])
    merged["sources"] = frozen_sources
    return merged


def _data_as_of_covers_observation(
    value: str, source_timezone: str | None, observation_end: date
) -> bool:
    if "T" not in value and " " not in value:
        # 日期值按“完整 through date”解释。
        return date.fromisoformat(value) >= observation_end
    parsed = datetime.fromisoformat(
        value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ExperimentError("data_as_of 时间必须包含 UTC offset 或 Z")
    if source_timezone is None:
        raise ExperimentError("datetime data_as_of 必须同时声明 source_timezone")
    source_zone = ZoneInfo(source_timezone)
    local = parsed.astimezone(source_zone)
    exclusive_end = datetime(
        *(observation_end + timedelta(days=1)).timetuple()[:3],
        tzinfo=source_zone,
    )
    return local >= exclusive_end


def _data_as_of_is_future(
    value: str, source_timezone: str | None, now_utc: datetime
) -> bool:
    if source_timezone is None:
        raise ExperimentError("data_as_of 必须声明 source_timezone")
    source_zone = ZoneInfo(source_timezone)
    if "T" not in value and " " not in value:
        # 日期代表整日最终化，因此今天尚未结束也不能声明为 complete through date。
        return date.fromisoformat(value) >= now_utc.astimezone(source_zone).date()
    parsed = datetime.fromisoformat(
        value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ExperimentError("data_as_of 时间必须包含 UTC offset 或 Z")
    return parsed.astimezone(timezone.utc) > now_utc


def _analysis_measurement_contract(
    plan: Mapping[str, Any],
    observation: Window,
    metadata_path: str | Path | None,
) -> tuple[dict[str, Any], str | None]:
    frozen_raw = plan.get("measurement_contract", {})
    frozen = frozen_raw if isinstance(frozen_raw, dict) else {}
    metadata_hash: str | None = None
    merged = dict(frozen)
    consistency_issues: list[dict[str, str]] = []
    if metadata_path is not None:
        value, raw = _read_json(metadata_path, label="measurement metadata")
        if not isinstance(value, dict):
            raise ExperimentError("measurement metadata 顶层必须是对象")
        if "measurement_contract" in value:
            wrapper_siblings = sorted(set(value) - {"measurement_contract"})
            if wrapper_siblings:
                raise ExperimentError(
                    "measurement metadata 使用 measurement_contract 包装时"
                    "不得同时声明同级字段："
                    + "、".join(wrapper_siblings)
                )
        override = value.get("measurement_contract", value)
        if not isinstance(override, dict):
            raise ExperimentError("measurement metadata.measurement_contract 必须是对象")
        allowed_contract_fields = {
            *MEASUREMENT_CONTRACT_IMMUTABLE_FIELDS,
            "sources",
            "source_metadata",
        }
        for key in sorted(set(override) - allowed_contract_fields):
            consistency_issues.append(
                {
                    "code": "measurement_metadata_field_not_allowed",
                    "source": "measurement_contract",
                    "detail": f"analysis metadata 不允许字段 {key}。",
                }
            )
        for key in MEASUREMENT_CONTRACT_IMMUTABLE_FIELDS:
            if key in override and override.get(key) != frozen.get(key):
                consistency_issues.append(
                    {
                        "code": f"{key}_changed_after_preregistration",
                        "source": "measurement_contract",
                        "detail": f"{key} 与冻结计划不一致。",
                    }
                )
        frozen_sources = frozen.get("sources", {}) if isinstance(frozen.get("sources"), dict) else {}
        override_sources = _source_declaration(
            override, "measurement metadata", fallback={}
        )
        if isinstance(override_sources, (dict, list)):
            for source_id, item in _source_mapping(
                override_sources, "measurement metadata sources"
            ).items():
                previous = frozen_sources.get(source_id)
                if not isinstance(previous, dict):
                    consistency_issues.append(
                        {
                            "code": "source_added_after_preregistration",
                            "source": source_id,
                            "detail": "analysis metadata 不得新增未冻结的数据来源。",
                        }
                    )
                    continue
                allowed_source_fields = {
                    *MEASUREMENT_SOURCE_IMMUTABLE_FIELDS,
                    *MEASUREMENT_COLLECTION_STATUS_FIELDS,
                    "source_id",
                }
                for field in sorted(set(item) - allowed_source_fields):
                    consistency_issues.append(
                        {
                            "code": "source_metadata_field_not_allowed",
                            "source": source_id,
                            "detail": f"analysis metadata 不允许来源字段 {field}。",
                        }
                    )
                for field in MEASUREMENT_SOURCE_IMMUTABLE_FIELDS:
                    if field in item and item.get(field) != previous.get(field):
                        consistency_issues.append(
                            {
                                "code": f"source_{field}_changed_after_preregistration",
                                "source": source_id,
                                "detail": f"{field} 与冻结计划不一致。",
                            }
                        )
        merged = _merge_measurement_contract(frozen, override)
        metadata_hash = _sha256_bytes(raw)
    normalized = _normalize_measurement_contract({"measurement_contract": merged})
    issues = [*normalized["issues"], *consistency_issues]
    metrics = {
        plan["preregistration"]["primary_metric"],
        *[
            item["metric"]
            for item in plan["preregistration"].get("guardrails", [])
            if isinstance(item, dict) and isinstance(item.get("metric"), str)
        ],
    }
    metric_sources: dict[str, list[str]] = defaultdict(list)
    for source_id, source in normalized["sources"].items():
        for metric in source.get("metrics", []):
            metric_sources[metric].append(source_id)
    mapped_metrics = set(metric_sources)
    missing_metrics = sorted(metrics - mapped_metrics)
    if missing_metrics:
        issues.append(
            {
                "code": "metric_source_mapping_missing",
                "source": "measurement_contract",
                "detail": "未映射指标来源：" + "、".join(missing_metrics),
            }
        )
    unexpected_metrics = sorted(mapped_metrics - metrics)
    if unexpected_metrics:
        issues.append(
            {
                "code": "metric_source_mapping_unregistered",
                "source": "measurement_contract",
                "detail": "来源映射包含未预注册指标：" + "、".join(unexpected_metrics),
            }
        )
    for metric in sorted(metrics):
        source_ids = metric_sources.get(metric, [])
        if len(source_ids) > 1:
            issues.append(
                {
                    "code": "metric_source_mapping_ambiguous",
                    "source": ",".join(sorted(source_ids)),
                    "detail": (
                        f"指标 {metric} 同时映射到多个来源："
                        + "、".join(sorted(source_ids))
                        + "。"
                    ),
                }
            )
    for source_id, source in normalized["sources"].items():
        data_as_of = source.get("data_as_of")
        source_timezone = source.get("source_timezone")
        if (
            isinstance(data_as_of, str)
            and isinstance(source_timezone, str)
            and not _data_as_of_covers_observation(
                data_as_of,
                source_timezone,
                observation.end,
            )
        ):
            issues.append(
                {
                    "code": "data_as_of_before_observation_end",
                    "source": source_id,
                    "detail": "数据截止日期早于预注册观察窗口结束日。",
                }
            )
        if (
            isinstance(data_as_of, str)
            and isinstance(source_timezone, str)
            and _data_as_of_is_future(
            data_as_of,
            source_timezone,
            datetime.now(timezone.utc),
            )
        ):
            issues.append(
                {
                    "code": "data_as_of_in_future",
                    "source": source_id,
                    "detail": "数据截止点晚于当前可完成的来源时间。",
                }
            )
    normalized["issues"] = list(
        {
            (item["code"], item["source"], item.get("detail", "")): item
            for item in issues
        }.values()
    )
    normalized["complete"] = not normalized["issues"]
    normalized["status"] = "complete" if normalized["complete"] else "inconclusive"
    normalized["metadata_file_sha256"] = metadata_hash
    return normalized, metadata_hash


def analyze_experiment(
    plan_path: str | Path,
    panel_path: str | Path,
    artifact_report_path: str | Path,
    measurement_metadata_path: str | Path | None = None,
) -> dict[str, Any]:
    plan, plan_raw = load_and_verify_plan(plan_path)
    baseline = _window_from_plan(plan, "baseline_window")
    observation = _window_from_plan(plan, "observation_window")
    artifact, artifact_hash = _artifact_status(artifact_report_path, plan)
    measurement_contract, measurement_metadata_hash = _analysis_measurement_contract(
        plan, observation, measurement_metadata_path
    )
    panel, panel_hash, initial_issues, contamination_observable = _load_panel(panel_path, plan)
    analysis_timezone = measurement_contract.get("analysis_timezone")
    analysis_zone = (
        ZoneInfo(analysis_timezone)
        if isinstance(analysis_timezone, str)
        else timezone.utc
    )
    analysis_as_of = datetime.now(analysis_zone).date()
    issues, coverage = _validate_panel_quality(
        panel, plan, baseline, observation, initial_issues, analysis_as_of
    )
    issues.extend(measurement_contract["issues"])

    primary = plan["preregistration"]["primary_metric"]
    primary_direction = plan["preregistration"].get("primary_metric_direction")
    if primary_direction not in PRIMARY_METRIC_DIRECTIONS:
        raise ExperimentError(
            "plan.json 缺少有效 preregistration.primary_metric_direction"
        )
    guardrail_configs = plan["preregistration"].get("guardrails", [])
    metric_names = [primary, *[item["metric"] for item in guardrail_configs]]
    estimates = {
        metric: _metric_estimate(metric, panel, plan, baseline, observation)
        for metric in metric_names
    }
    guardrail_results: list[dict[str, Any]] = []
    for config in guardrail_configs:
        estimate = estimates[config["metric"]]
        did = estimate["difference_in_differences"]
        threshold = float(config.get("threshold", 0))
        direction = config.get("direction", "non_decrease")
        if did is None:
            passed = None
        elif direction == "non_decrease":
            passed = float(did) >= -threshold
        else:
            passed = float(did) <= threshold
        guardrail_results.append({
            "metric": config["metric"],
            "direction": direction,
            "threshold": _clean_number(threshold),
            "difference_in_differences": did,
            "passed": passed,
        })

    primary_estimate = estimates[primary]
    reasons: list[str] = []
    if artifact["passed"] is False:
        eligibility = "implementation-failed"
        reasons.append("artifact_verification_failed")
    else:
        if artifact["passed"] is not True:
            reasons.append("artifact_verification_missing")
        if issues:
            reasons.extend(sorted({str(item["code"]) for item in issues}))
        if primary_estimate["difference_in_differences"] is None:
            reasons.append("primary_metric_not_estimable")
        if primary_estimate["standard_error"] is None:
            reasons.append("confidence_interval_not_estimable")
        if not primary_estimate["detectability"]["precision_sufficient_for_mde"]:
            reasons.append("mde_precision_not_met")
        if any(item["passed"] is False for item in guardrail_results):
            reasons.append("guardrail_breached")
        if any(item["passed"] is None for item in guardrail_results):
            reasons.append("guardrail_not_estimable")
        eligibility = "inconclusive" if reasons else "eligible_incremental"

    primary_did = primary_estimate["difference_in_differences"]
    primary_ci = primary_estimate["confidence_interval"]
    if primary_did is None:
        point_estimate_supports_direction = False
    elif primary_direction == "increase":
        point_estimate_supports_direction = float(primary_did) > 0
    else:
        point_estimate_supports_direction = float(primary_did) < 0
    if primary_ci["lower"] is None or primary_ci["upper"] is None:
        confidence_interval_supports_direction = False
    elif primary_direction == "increase":
        confidence_interval_supports_direction = float(primary_ci["lower"]) > 0
    else:
        confidence_interval_supports_direction = float(primary_ci["upper"]) < 0
    incremental_positive_allowed = (
        eligibility == "eligible_incremental"
        and point_estimate_supports_direction
        and confidence_interval_supports_direction
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "experiment_id": plan["experiment_id"],
        "design": plan["design"],
        "plan_hash": plan["plan_hash"],
        "analyzed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_hashes": {
            "plan_file_sha256": _sha256_bytes(plan_raw),
            "panel_sha256": panel_hash,
            "artifact_report_sha256": artifact_hash,
            "measurement_metadata_sha256": measurement_metadata_hash,
            **{
                key: value
                for key, value in plan["frozen_inputs"].items()
                if key != "baseline_units"
            },
        },
        "windows": {"baseline": baseline.as_dict(), "observation": observation.as_dict()},
        "artifact_verification": artifact,
        "measurement_contract": measurement_contract,
        "data_quality": {
            "passed": not issues,
            "contamination_observable": contamination_observable,
            "coverage": coverage,
            "issues": issues,
        },
        "metrics": estimates,
        "primary_metric": primary_estimate,
        "guardrails": {
            "passed": all(item["passed"] is True for item in guardrail_results)
            if guardrail_results
            else True,
            "results": guardrail_results,
        },
        "eligibility": eligibility,
        "eligibility_details": {
            "eligible_incremental": eligibility == "eligible_incremental",
            "reasons": list(dict.fromkeys(reasons)),
            "business_verdict": None,
            "primary_metric_direction": primary_direction,
            "point_estimate_supports_direction": point_estimate_supports_direction,
            "confidence_interval_supports_direction": confidence_interval_supports_direction,
            "incremental_positive_allowed": incremental_positive_allowed,
            "no_detectable_change_allowed": False,
        },
        "methodology": {
            "estimand": "page-level difference-in-differences",
            "causal_claim_automated": False,
            "power_calculated": False,
            "causality_boundary": CAUSALITY_BOUNDARY,
            "paid_search_boundary": PAID_SEARCH_BOUNDARY,
            "power_boundary": POWER_BOUNDARY,
        },
    }


def _report_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExperimentError(f"实验报告字段 {field} 必须是对象")
    return value


def _report_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ExperimentError(f"实验报告字段 {field} 必须是数组")
    return value


def _report_exact_keys(
    value: Mapping[str, Any], expected: set[str], field: str
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    if missing:
        prefix = "实验报告" if field == "顶层" else f"实验报告字段 {field} "
        raise ExperimentError(prefix + "缺少字段：" + "、".join(missing))
    unexpected = sorted(actual - expected)
    if unexpected:
        prefix = "实验报告" if field == "顶层" else f"实验报告字段 {field} "
        raise ExperimentError(prefix + "包含额外字段：" + "、".join(unexpected))


def _report_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ExperimentError(f"实验报告字段 {field} 必须是 SHA-256")
    return value


def _report_finite_or_none(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExperimentError(f"实验报告字段 {field} 必须是有限数或 null")
    number = float(value)
    if not math.isfinite(number):
        raise ExperimentError(f"实验报告字段 {field} 必须是有限数或 null")
    return number


def _report_number_equal(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def _report_json_equal(left: Any, right: Any) -> bool:
    return _canonical_json({"value": left}) == _canonical_json({"value": right})


def _validate_metric_report(
    metric_name: str, estimate: Mapping[str, Any], plan: Mapping[str, Any]
) -> None:
    _report_exact_keys(
        estimate,
        {
            "metric",
            "unit_of_analysis",
            "arms",
            "difference_in_differences",
            "relative_difference_in_differences",
            "standard_error",
            "confidence_interval",
            "inference_units",
            "detectability",
        },
        f"metrics.{metric_name}",
    )
    if estimate.get("metric") != metric_name:
        raise ExperimentError(f"实验报告 metrics.{metric_name}.metric 与对象键不匹配")
    expected_unit = "page" if plan.get("design") == "randomized_page_holdout" else "matched_pair"
    if estimate.get("unit_of_analysis") != expected_unit:
        raise ExperimentError(f"实验报告 metrics.{metric_name}.unit_of_analysis 无效")
    arms = _report_mapping(estimate.get("arms"), f"metrics.{metric_name}.arms")
    _report_exact_keys(arms, set(GROUPS), f"metrics.{metric_name}.arms")
    arm_values: dict[str, Mapping[str, Any]] = {}
    for group in GROUPS:
        arm = _report_mapping(arms.get(group), f"metrics.{metric_name}.arms.{group}")
        _report_exact_keys(
            arm,
            {
                "units",
                "baseline_mean",
                "current_mean",
                "absolute_change",
                "relative_change",
            },
            f"metrics.{metric_name}.arms.{group}",
        )
        units = arm.get("units")
        if not isinstance(units, int) or isinstance(units, bool) or units < 0:
            raise ExperimentError(f"实验报告 metrics.{metric_name}.arms.{group}.units 无效")
        baseline_mean = _report_finite_or_none(arm.get("baseline_mean"), f"{metric_name}.{group}.baseline_mean")
        current_mean = _report_finite_or_none(arm.get("current_mean"), f"{metric_name}.{group}.current_mean")
        absolute = _report_finite_or_none(arm.get("absolute_change"), f"{metric_name}.{group}.absolute_change")
        relative = _report_finite_or_none(arm.get("relative_change"), f"{metric_name}.{group}.relative_change")
        expected_absolute = (
            current_mean - baseline_mean
            if baseline_mean is not None and current_mean is not None
            else None
        )
        expected_relative = (
            expected_absolute / abs(baseline_mean)
            if expected_absolute is not None and baseline_mean not in (None, 0)
            else None
        )
        if not _report_number_equal(absolute, expected_absolute) or not _report_number_equal(
            relative, expected_relative
        ):
            raise ExperimentError(f"实验报告 metrics.{metric_name}.arms.{group} 变化值矛盾")
        arm_values[group] = arm

    did = _report_finite_or_none(
        estimate.get("difference_in_differences"),
        f"metrics.{metric_name}.difference_in_differences",
    )
    treatment_change = _report_finite_or_none(
        arm_values["treatment"].get("absolute_change"), f"{metric_name}.treatment.absolute_change"
    )
    control_change = _report_finite_or_none(
        arm_values["control"].get("absolute_change"), f"{metric_name}.control.absolute_change"
    )
    expected_did = (
        treatment_change - control_change
        if treatment_change is not None and control_change is not None
        else None
    )
    if not _report_number_equal(did, expected_did):
        raise ExperimentError(f"实验报告 metrics.{metric_name}.DID 与 arms 矛盾")
    control_baseline = _report_finite_or_none(
        arm_values["control"].get("baseline_mean"), f"{metric_name}.control.baseline_mean"
    )
    relative_did = _report_finite_or_none(
        estimate.get("relative_difference_in_differences"),
        f"metrics.{metric_name}.relative_difference_in_differences",
    )
    expected_relative_did = (
        did / abs(control_baseline)
        if did is not None and control_baseline not in (None, 0)
        else None
    )
    if not _report_number_equal(relative_did, expected_relative_did):
        raise ExperimentError(f"实验报告 metrics.{metric_name}.relative DID 矛盾")

    standard_error = _report_finite_or_none(
        estimate.get("standard_error"), f"metrics.{metric_name}.standard_error"
    )
    if standard_error is not None and standard_error < 0:
        raise ExperimentError(f"实验报告 metrics.{metric_name}.standard_error 不得为负")
    inference_units = estimate.get("inference_units")
    if not isinstance(inference_units, int) or isinstance(inference_units, bool) or inference_units < 0:
        raise ExperimentError(f"实验报告 metrics.{metric_name}.inference_units 无效")
    prereg = _report_mapping(plan.get("preregistration"), "plan.preregistration")
    alpha = _number(prereg.get("alpha"), "preregistration.alpha")
    confidence = 1 - alpha
    ci = _report_mapping(estimate.get("confidence_interval"), f"metrics.{metric_name}.confidence_interval")
    _report_exact_keys(
        ci,
        {"level", "method", "lower", "upper", "half_width"},
        f"metrics.{metric_name}.confidence_interval",
    )
    level = _report_finite_or_none(ci.get("level"), f"metrics.{metric_name}.confidence_interval.level")
    lower = _report_finite_or_none(ci.get("lower"), f"metrics.{metric_name}.confidence_interval.lower")
    upper = _report_finite_or_none(ci.get("upper"), f"metrics.{metric_name}.confidence_interval.upper")
    half_width = _report_finite_or_none(ci.get("half_width"), f"metrics.{metric_name}.confidence_interval.half_width")
    if not _report_number_equal(level, confidence) or ci.get("method") != "normal_approximation":
        raise ExperimentError(f"实验报告 metrics.{metric_name}.confidence_interval 合同无效")
    expected_half = (
        statistics.NormalDist().inv_cdf(1 - alpha / 2) * standard_error
        if did is not None and standard_error is not None
        else None
    )
    expected_lower = did - expected_half if did is not None and expected_half is not None else None
    expected_upper = did + expected_half if did is not None and expected_half is not None else None
    if not all(
        (
            _report_number_equal(half_width, expected_half),
            _report_number_equal(lower, expected_lower),
            _report_number_equal(upper, expected_upper),
        )
    ):
        raise ExperimentError(f"实验报告 metrics.{metric_name}.CI 与 DID/SE/alpha 矛盾")

    detectability = _report_mapping(estimate.get("detectability"), f"metrics.{metric_name}.detectability")
    _report_exact_keys(
        detectability,
        {
            "preregistered_mde",
            "mde_scale",
            "mde_in_metric_units",
            "precision_sufficient_for_mde",
            "power",
            "note",
        },
        f"metrics.{metric_name}.detectability",
    )
    mde = _report_mapping(prereg.get("minimum_detectable_effect"), "preregistration.minimum_detectable_effect")
    mde_value = _number(mde.get("value"), "minimum_detectable_effect.value", positive=True)
    mde_scale = mde.get("scale")
    expected_mde_units = (
        mde_value * abs(control_baseline)
        if mde_scale == "relative_to_control_baseline" and control_baseline not in (None, 0)
        else mde_value
        if mde_scale == "absolute"
        else None
    )
    reported_mde = _report_finite_or_none(detectability.get("preregistered_mde"), f"metrics.{metric_name}.detectability.preregistered_mde")
    reported_mde_units = _report_finite_or_none(detectability.get("mde_in_metric_units"), f"metrics.{metric_name}.detectability.mde_in_metric_units")
    expected_precision = (
        half_width <= expected_mde_units
        if half_width is not None and expected_mde_units is not None
        else False
    )
    if (
        not _report_number_equal(reported_mde, mde_value)
        or detectability.get("mde_scale") != mde_scale
        or not _report_number_equal(reported_mde_units, expected_mde_units)
        or detectability.get("precision_sufficient_for_mde") is not expected_precision
        or detectability.get("power") is not None
        or detectability.get("note") != POWER_BOUNDARY
    ):
        raise ExperimentError(f"实验报告 metrics.{metric_name}.detectability 与冻结 MDE/CI 矛盾")


def validate_experiment_report(
    result: Mapping[str, Any], plan: Mapping[str, Any]
) -> None:
    """Validate the complete semantic contract emitted by ``analyze_experiment``.

    This standard-library validator is shared with ``state_manager.py`` so a
    strong review cannot accept a hand-written subset of the runtime report.
    """

    _report_exact_keys(
        result,
        {
            "schema_version",
            "tool",
            "experiment_id",
            "design",
            "plan_hash",
            "analyzed_at",
            "source_hashes",
            "windows",
            "artifact_verification",
            "measurement_contract",
            "data_quality",
            "metrics",
            "primary_metric",
            "guardrails",
            "eligibility",
            "eligibility_details",
            "methodology",
        },
        "顶层",
    )
    if result.get("schema_version") != SCHEMA_VERSION or result.get("tool") != TOOL_NAME:
        raise ExperimentError("实验报告不是受支持的正式运行时产物")
    for field in ("experiment_id", "design", "plan_hash"):
        if result.get(field) != plan.get(field):
            raise ExperimentError(f"实验报告 {field} 与冻结计划不匹配")
    analyzed_at = _text(result.get("analyzed_at"), "report.analyzed_at")
    try:
        analyzed = datetime.fromisoformat(
            analyzed_at[:-1] + "+00:00" if analyzed_at.endswith("Z") else analyzed_at
        )
    except ValueError as exc:
        raise ExperimentError("实验报告 analyzed_at 必须是 ISO 8601 时间") from exc
    if analyzed.tzinfo is None or analyzed.utcoffset() is None:
        raise ExperimentError("实验报告 analyzed_at 必须包含 UTC offset 或 Z")

    frozen = _report_mapping(plan.get("frozen_inputs"), "plan.frozen_inputs")
    source_hashes = _report_mapping(result.get("source_hashes"), "source_hashes")
    _report_exact_keys(
        source_hashes,
        {
            "plan_file_sha256",
            "panel_sha256",
            "artifact_report_sha256",
            "measurement_metadata_sha256",
            *(field for field in frozen if field != "baseline_units"),
        },
        "source_hashes",
    )
    for field in (
        "plan_file_sha256",
        "panel_sha256",
        "artifact_report_sha256",
        "spec_sha256",
        "baseline_sha256",
        "baseline_units_sha256",
    ):
        _report_sha256(source_hashes.get(field), f"source_hashes.{field}")
    metadata_hash = source_hashes.get("measurement_metadata_sha256")
    if metadata_hash is not None:
        _report_sha256(metadata_hash, "source_hashes.measurement_metadata_sha256")
    for field, value in frozen.items():
        if field != "baseline_units" and not _report_json_equal(
            source_hashes.get(field), value
        ):
            raise ExperimentError(f"实验报告 source_hashes.{field} 与冻结计划不匹配")

    prereg = _report_mapping(plan.get("preregistration"), "plan.preregistration")
    windows = _report_mapping(result.get("windows"), "windows")
    _report_exact_keys(windows, {"baseline", "observation"}, "windows")
    for report_name, plan_name in (
        ("baseline", "baseline_window"),
        ("observation", "observation_window"),
    ):
        window = _report_mapping(windows.get(report_name), f"windows.{report_name}")
        _report_exact_keys(window, {"start", "end"}, f"windows.{report_name}")
        if not _report_json_equal(window, prereg.get(plan_name)):
            raise ExperimentError("实验报告窗口与冻结计划不匹配")

    artifact = _report_mapping(result.get("artifact_verification"), "artifact_verification")
    _report_exact_keys(
        artifact,
        {"experiment_id", "plan_hash", "passed", "status", "evidence"},
        "artifact_verification",
    )
    artifact_passed = artifact.get("passed")
    if not isinstance(artifact_passed, bool):
        raise ExperimentError("实验报告 artifact_verification.passed 必须是布尔值")
    expected_artifact_status = "passed" if artifact_passed else "failed"
    if (
        artifact.get("status") != expected_artifact_status
        or artifact.get("experiment_id") != result.get("experiment_id")
        or artifact.get("plan_hash") != result.get("plan_hash")
        or not (
            isinstance(artifact.get("evidence"), (str, list, dict))
            and bool(artifact.get("evidence"))
        )
    ):
        raise ExperimentError("实验报告的产物验证字段互相矛盾")

    measurement = _report_mapping(result.get("measurement_contract"), "measurement_contract")
    _report_exact_keys(
        measurement,
        {
            "analysis_timezone",
            "temporal_grain",
            "source_timezones",
            "daily_cross_source_join_allowed",
            "window_aggregation_allowed",
            "sources",
            "issues",
            "complete",
            "status",
            "metadata_file_sha256",
        },
        "measurement_contract",
    )
    frozen_measurement = _report_mapping(
        plan.get("measurement_contract"), "plan.measurement_contract"
    )
    for field in MEASUREMENT_CONTRACT_IMMUTABLE_FIELDS:
        if not _report_json_equal(measurement.get(field), frozen_measurement.get(field)):
            raise ExperimentError(
                f"实验报告 measurement_contract.{field} 与冻结计划不匹配"
            )
    analysis_timezone = measurement.get("analysis_timezone")
    if analysis_timezone is not None:
        _optional_timezone(analysis_timezone, "report.measurement_contract.analysis_timezone")
    if measurement.get("temporal_grain") != "date":
        raise ExperimentError("实验报告 measurement_contract.temporal_grain 必须为 date")
    if not isinstance(measurement.get("daily_cross_source_join_allowed"), bool):
        raise ExperimentError(
            "实验报告 measurement_contract.daily_cross_source_join_allowed 必须是布尔值"
        )
    if measurement.get("window_aggregation_allowed") is not True:
        raise ExperimentError(
            "实验报告 measurement_contract.window_aggregation_allowed 必须为 true"
        )
    reported_metadata_hash = measurement.get("metadata_file_sha256")
    if reported_metadata_hash is not None:
        _report_sha256(
            reported_metadata_hash, "measurement_contract.metadata_file_sha256"
        )
    if reported_metadata_hash != metadata_hash:
        raise ExperimentError(
            "实验报告 measurement metadata 哈希与 source_hashes 不匹配"
        )

    source_timezones = _report_mapping(
        measurement.get("source_timezones"), "measurement_contract.source_timezones"
    )
    sources = _report_mapping(measurement.get("sources"), "measurement_contract.sources")
    frozen_sources = _report_mapping(
        frozen_measurement.get("sources"), "plan.measurement_contract.sources"
    )
    if set(sources) != set(frozen_sources):
        raise ExperimentError("实验报告测量来源未精确绑定冻结计划")
    if set(source_timezones) != set(sources):
        raise ExperimentError("实验报告 source_timezones 未精确覆盖测量来源")

    expected_source_timezones: dict[str, str | None] = {}
    for source_id, source_value in sources.items():
        if not isinstance(source_id, str) or not source_id:
            raise ExperimentError("实验报告测量来源键必须是非空字符串")
        source = _report_mapping(source_value, f"measurement_contract.sources.{source_id}")
        _report_exact_keys(
            source,
            {
                "source_id",
                "source_kind",
                "source_timezone",
                "metrics",
                "data_as_of",
                "finality",
                "preliminary",
                "row_limit_hit",
                "pagination_complete",
                "sampling_rate",
                "thresholding_applied",
                "data_quality",
                "attribution_model",
            },
            f"measurement_contract.sources.{source_id}",
        )
        source_quality = _report_mapping(
            source.get("data_quality"),
            f"measurement_contract.sources.{source_id}.data_quality",
        )
        _report_exact_keys(
            source_quality,
            {"declared", "status", "issues"},
            f"measurement_contract.sources.{source_id}.data_quality",
        )
        if source.get("source_id") != source_id:
            raise ExperimentError("测量来源 source_id 与对象键不匹配")
        timezone_value = source_timezones.get(source_id)
        if timezone_value is not None:
            _optional_timezone(
                timezone_value, f"measurement_contract.source_timezones.{source_id}"
            )
        normalized_source, source_issues = _normalize_measurement_source(
            source_id,
            source,
            timezone_value if isinstance(timezone_value, str) else None,
        )
        if not _report_json_equal(source, normalized_source):
            raise ExperimentError(
                f"实验报告测量来源 {source_id} 状态或类型与规范化结果不一致"
            )
        frozen_source = _report_mapping(
            frozen_sources.get(source_id), f"plan.measurement_contract.sources.{source_id}"
        )
        for field in MEASUREMENT_SOURCE_IMMUTABLE_FIELDS:
            if not _report_json_equal(source.get(field), frozen_source.get(field)):
                raise ExperimentError(
                    f"实验报告测量来源 {source_id}.{field} 与冻结计划不匹配"
                )
        if metadata_hash is None:
            for field in MEASUREMENT_COLLECTION_STATUS_FIELDS:
                if not _report_json_equal(source.get(field), frozen_source.get(field)):
                    raise ExperimentError(
                        f"未绑定 measurement metadata 时不得改变来源 {source_id}.{field}"
                    )
        expected_source_timezones[source_id] = source.get("source_timezone")

    if not _report_json_equal(source_timezones, expected_source_timezones):
        raise ExperimentError("实验报告 source_timezones 与来源内时区不匹配")
    known_timezones = {
        value for value in expected_source_timezones.values() if value is not None
    }
    expected_daily_join = len(sources) > 1 and (
        len(known_timezones) == 1 and all(expected_source_timezones.values())
    )
    if measurement.get("daily_cross_source_join_allowed") is not expected_daily_join:
        raise ExperimentError("实验报告逐日跨源 join 状态与来源时区矛盾")

    normalized_contract = _normalize_measurement_contract(
        {"measurement_contract": dict(measurement)}
    )
    deterministic_measurement_issues = list(normalized_contract["issues"])
    registered_metrics = {
        _text(prereg.get("primary_metric"), "preregistration.primary_metric"),
        *[
            _text(
                _report_mapping(item, "preregistration.guardrail").get("metric"),
                "guardrail.metric",
            )
            for item in _report_list(
                prereg.get("guardrails"), "preregistration.guardrails"
            )
        ],
    }
    metric_sources: dict[str, list[str]] = defaultdict(list)
    for source_id, source_value in sources.items():
        source = _report_mapping(source_value, f"measurement_contract.sources.{source_id}")
        for metric in _report_list(source.get("metrics"), f"sources.{source_id}.metrics"):
            metric_sources[str(metric)].append(source_id)
    mapped_metrics = set(metric_sources)
    missing_metrics = sorted(registered_metrics - mapped_metrics)
    if missing_metrics:
        deterministic_measurement_issues.append(
            {
                "code": "metric_source_mapping_missing",
                "source": "measurement_contract",
                "detail": "未映射指标来源：" + "、".join(missing_metrics),
            }
        )
    unexpected_metrics = sorted(mapped_metrics - registered_metrics)
    if unexpected_metrics:
        deterministic_measurement_issues.append(
            {
                "code": "metric_source_mapping_unregistered",
                "source": "measurement_contract",
                "detail": "来源映射包含未预注册指标：" + "、".join(unexpected_metrics),
            }
        )
    for metric in sorted(registered_metrics):
        source_ids = metric_sources.get(metric, [])
        if len(source_ids) > 1:
            deterministic_measurement_issues.append(
                {
                    "code": "metric_source_mapping_ambiguous",
                    "source": ",".join(sorted(source_ids)),
                    "detail": (
                        f"指标 {metric} 同时映射到多个来源："
                        + "、".join(sorted(source_ids))
                        + "。"
                    ),
                }
            )
    observation = _window_from_plan(plan, "observation_window")
    now_utc = datetime.now(timezone.utc)
    for source_id, source_value in sources.items():
        source = _report_mapping(source_value, f"measurement_contract.sources.{source_id}")
        data_as_of = source.get("data_as_of")
        source_timezone = source.get("source_timezone")
        if (
            isinstance(data_as_of, str)
            and isinstance(source_timezone, str)
            and not _data_as_of_covers_observation(
                data_as_of, source_timezone, observation.end
            )
        ):
            deterministic_measurement_issues.append(
                {
                    "code": "data_as_of_before_observation_end",
                    "source": source_id,
                    "detail": "数据截止日期早于预注册观察窗口结束日。",
                }
            )
        if (
            isinstance(data_as_of, str)
            and isinstance(source_timezone, str)
            and _data_as_of_is_future(data_as_of, source_timezone, now_utc)
        ):
            deterministic_measurement_issues.append(
                {
                    "code": "data_as_of_in_future",
                    "source": source_id,
                    "detail": "数据截止点晚于当前可完成的来源时间。",
                }
            )

    measurement_issue_values = _report_list(
        measurement.get("issues"), "measurement_contract.issues"
    )
    measurement_issues: list[Mapping[str, Any]] = []
    for index, issue_value in enumerate(measurement_issue_values):
        issue = _report_mapping(issue_value, f"measurement_contract.issues[{index}]")
        _report_exact_keys(
            issue,
            {"code", "source", "detail"},
            f"measurement_contract.issues[{index}]",
        )
        _text(issue.get("code"), f"measurement_contract.issues[{index}].code")
        _text(issue.get("source"), f"measurement_contract.issues[{index}].source")
        _text(issue.get("detail"), f"measurement_contract.issues[{index}].detail")
        measurement_issues.append(issue)
    measurement_issue_json = [_canonical_json(dict(item)) for item in measurement_issues]
    if len(measurement_issue_json) != len(set(measurement_issue_json)):
        raise ExperimentError("实验报告 measurement_contract.issues 不得重复")
    measurement_issue_set = set(measurement_issue_json)
    if any(
        _canonical_json(issue) not in measurement_issue_set
        for issue in deterministic_measurement_issues
    ):
        raise ExperimentError("确定性测量 issue 未进入 measurement_contract.issues")
    measurement_complete = not measurement_issues
    if (
        measurement.get("complete") is not measurement_complete
        or measurement.get("status")
        != ("complete" if measurement_complete else "inconclusive")
    ):
        raise ExperimentError("实验报告 measurement_contract 状态与 issues 矛盾")

    quality = _report_mapping(result.get("data_quality"), "data_quality")
    _report_exact_keys(
        quality,
        {"passed", "contamination_observable", "coverage", "issues"},
        "data_quality",
    )
    quality_issue_values = _report_list(quality.get("issues"), "data_quality.issues")
    quality_issues: list[Mapping[str, Any]] = []
    quality_issue_codes: list[str] = []
    for index, issue_value in enumerate(quality_issue_values):
        issue = _report_mapping(issue_value, f"data_quality.issues[{index}]")
        code = _text(issue.get("code"), f"data_quality.issues[{index}].code")
        quality_issues.append(issue)
        quality_issue_codes.append(code)
    if quality.get("passed") is not (not quality_issues) or not isinstance(
        quality.get("contamination_observable"), bool
    ):
        raise ExperimentError("实验报告 data_quality.passed 与 issues 矛盾")
    quality_issue_json = {_canonical_json(dict(item)) for item in quality_issues}
    if not measurement_issue_set <= quality_issue_json:
        raise ExperimentError(
            "measurement_contract.issues 必须逐项进入 data_quality.issues"
        )
    coverage = _report_mapping(quality.get("coverage"), "data_quality.coverage")
    _report_exact_keys(
        coverage,
        {"temporal_grain", "expected_units", "periods", "complete", "frozen_baseline_bound"},
        "data_quality.coverage",
    )
    expected_units = len(_report_list(plan.get("assignments"), "plan.assignments"))
    reported_expected_units = coverage.get("expected_units")
    if (
        coverage.get("temporal_grain") != "date"
        or not isinstance(reported_expected_units, int)
        or isinstance(reported_expected_units, bool)
        or reported_expected_units != expected_units
        or not isinstance(coverage.get("frozen_baseline_bound"), bool)
    ):
        raise ExperimentError("实验报告 coverage 的粒度/单位数无效")
    periods = _report_mapping(coverage.get("periods"), "data_quality.coverage.periods")
    _report_exact_keys(periods, {"baseline", "current"}, "data_quality.coverage.periods")
    period_complete: list[bool] = []
    for period in ("baseline", "current"):
        row = _report_mapping(periods.get(period), f"coverage.periods.{period}")
        _report_exact_keys(
            row,
            {"expected_dates", "expected_unit_days", "observed_unit_days", "complete"},
            f"coverage.periods.{period}",
        )
        window_key = "baseline_window" if period == "baseline" else "observation_window"
        window = _window_from_plan(plan, window_key)
        expected_dates = len(_window_dates(window))
        reported_expected_dates = row.get("expected_dates")
        expected_days = row.get("expected_unit_days")
        observed_days = row.get("observed_unit_days")
        if (
            not isinstance(reported_expected_dates, int)
            or isinstance(reported_expected_dates, bool)
            or reported_expected_dates != expected_dates
            or not isinstance(expected_days, int)
            or isinstance(expected_days, bool)
            or expected_days < 1
            or not isinstance(observed_days, int)
            or isinstance(observed_days, bool)
            or observed_days < 0
        ):
            raise ExperimentError("实验报告 coverage 行数无效")
        if expected_days != expected_units * expected_dates or observed_days > expected_days:
            raise ExperimentError("实验报告 coverage 期望单位日或观测数无效")
        complete = observed_days == expected_days
        if row.get("complete") is not complete:
            raise ExperimentError("实验报告 coverage.complete 与行数矛盾")
        period_complete.append(complete)
    if coverage.get("complete") is not all(period_complete):
        raise ExperimentError("实验报告总 coverage.complete 与分期状态矛盾")
    if quality.get("passed") is True and (
        coverage.get("complete") is not True
        or coverage.get("frozen_baseline_bound") is not True
    ):
        raise ExperimentError("数据质量通过时必须完整覆盖并绑定冻结基线")

    primary_name = _text(prereg.get("primary_metric"), "preregistration.primary_metric")
    planned_guardrails = _report_list(prereg.get("guardrails"), "preregistration.guardrails")
    expected_metric_names = {
        primary_name,
        *[
            _text(_report_mapping(item, "preregistration.guardrail").get("metric"), "guardrail.metric")
            for item in planned_guardrails
        ],
    }
    metrics = _report_mapping(result.get("metrics"), "metrics")
    if set(metrics) != expected_metric_names:
        raise ExperimentError("实验报告 metrics 未精确覆盖预注册指标")
    for metric_name, estimate_value in metrics.items():
        estimate = _report_mapping(estimate_value, f"metrics.{metric_name}")
        _validate_metric_report(metric_name, estimate, plan)
    primary = _report_mapping(result.get("primary_metric"), "primary_metric")
    if not _report_json_equal(primary, metrics.get(primary_name)):
        raise ExperimentError("实验报告 primary_metric 与 metrics 映射不一致")

    guardrails = _report_mapping(result.get("guardrails"), "guardrails")
    _report_exact_keys(guardrails, {"passed", "results"}, "guardrails")
    guardrail_rows = _report_list(guardrails.get("results"), "guardrails.results")
    if len(guardrail_rows) != len(planned_guardrails):
        raise ExperimentError("实验报告 guardrails 未完整绑定冻结计划")
    recomputed_guardrail_passes: list[bool | None] = []
    for planned_value, observed_value in zip(planned_guardrails, guardrail_rows):
        planned = _report_mapping(planned_value, "preregistration.guardrail")
        observed = _report_mapping(observed_value, "guardrails.result")
        _report_exact_keys(
            observed,
            {
                "metric",
                "direction",
                "threshold",
                "difference_in_differences",
                "passed",
            },
            "guardrails.result",
        )
        if observed.get("metric") != planned.get("metric") or observed.get(
            "direction"
        ) != planned.get("direction"):
            raise ExperimentError("实验报告 guardrail 与冻结计划不匹配")
        metric_name = str(planned["metric"])
        estimate = _report_mapping(metrics.get(metric_name), f"metrics.{metric_name}")
        did = _report_finite_or_none(
            observed.get("difference_in_differences"),
            f"guardrails.{metric_name}.difference_in_differences",
        )
        metric_did = _report_finite_or_none(
            estimate.get("difference_in_differences"),
            f"metrics.{metric_name}.difference_in_differences",
        )
        if did != metric_did:
            raise ExperimentError("实验报告 guardrail DID 与指标估计不一致")
        threshold = _number(planned.get("threshold"), f"guardrail.{metric_name}.threshold")
        reported_threshold = _report_finite_or_none(
            observed.get("threshold"), f"guardrails.{metric_name}.threshold"
        )
        if reported_threshold is None or not _report_number_equal(
            reported_threshold, threshold
        ):
            raise ExperimentError("实验报告 guardrail 阈值与冻结计划不匹配")
        if did is None:
            recomputed = None
        elif planned.get("direction") == "non_decrease":
            recomputed = did >= -threshold
        elif planned.get("direction") == "non_increase":
            recomputed = did <= threshold
        else:
            raise ExperimentError("冻结 guardrail.direction 无效")
        if observed.get("passed") is not recomputed:
            raise ExperimentError("实验报告 guardrail.passed 与 DID 矛盾")
        recomputed_guardrail_passes.append(recomputed)
    overall_guardrail_passed = (
        all(item is True for item in recomputed_guardrail_passes)
        if recomputed_guardrail_passes
        else True
    )
    if guardrails.get("passed") is not overall_guardrail_passed:
        raise ExperimentError("实验报告 guardrails.passed 与子项矛盾")

    primary_did = _report_finite_or_none(
        primary.get("difference_in_differences"),
        "primary_metric.difference_in_differences",
    )
    primary_ci = _report_mapping(primary.get("confidence_interval"), "primary_metric.confidence_interval")
    lower = _report_finite_or_none(primary_ci.get("lower"), "primary_metric.confidence_interval.lower")
    upper = _report_finite_or_none(primary_ci.get("upper"), "primary_metric.confidence_interval.upper")
    if lower is not None and upper is not None and lower > upper:
        raise ExperimentError("实验报告置信区间上下界颠倒")
    direction = prereg.get("primary_metric_direction")
    if direction not in PRIMARY_METRIC_DIRECTIONS:
        raise ExperimentError("冻结 primary_metric_direction 无效")
    point_supports = (
        primary_did is not None
        and (primary_did > 0 if direction == "increase" else primary_did < 0)
    )
    interval_supports = (
        lower is not None
        and upper is not None
        and (lower > 0 if direction == "increase" else upper < 0)
    )
    details = _report_mapping(result.get("eligibility_details"), "eligibility_details")
    _report_exact_keys(
        details,
        {
            "eligible_incremental",
            "reasons",
            "business_verdict",
            "primary_metric_direction",
            "point_estimate_supports_direction",
            "confidence_interval_supports_direction",
            "incremental_positive_allowed",
            "no_detectable_change_allowed",
        },
        "eligibility_details",
    )
    primary_standard_error = _report_finite_or_none(
        primary.get("standard_error"), "primary_metric.standard_error"
    )
    primary_detectability = _report_mapping(
        primary.get("detectability"), "primary_metric.detectability"
    )
    precision_sufficient = primary_detectability.get("precision_sufficient_for_mde")

    expected_reasons: list[str] = []
    if artifact_passed is False:
        expected_eligibility = "implementation-failed"
        expected_reasons.append("artifact_verification_failed")
    else:
        expected_reasons.extend(sorted(set(quality_issue_codes)))
        if primary_did is None:
            expected_reasons.append("primary_metric_not_estimable")
        if primary_standard_error is None:
            expected_reasons.append("confidence_interval_not_estimable")
        if precision_sufficient is not True:
            expected_reasons.append("mde_precision_not_met")
        if any(item is False for item in recomputed_guardrail_passes):
            expected_reasons.append("guardrail_breached")
        if any(item is None for item in recomputed_guardrail_passes):
            expected_reasons.append("guardrail_not_estimable")
        expected_reasons = list(dict.fromkeys(expected_reasons))
        expected_eligibility = "inconclusive" if expected_reasons else "eligible_incremental"

    eligibility = result.get("eligibility")
    if eligibility != expected_eligibility:
        raise ExperimentError(
            "实验报告 eligibility 与产物、数据质量、MDE 或护栏重算结果矛盾"
        )
    reasons = _report_list(details.get("reasons"), "eligibility_details.reasons")
    if (
        any(not isinstance(item, str) or not item for item in reasons)
        or len(reasons) != len(set(reasons))
        or reasons != expected_reasons
    ):
        raise ExperimentError("实验报告 eligibility_details.reasons 与完整重算结果不匹配")
    incremental_allowed = (
        expected_eligibility == "eligible_incremental"
        and point_supports
        and interval_supports
    )
    if (
        details.get("eligible_incremental")
        is not (expected_eligibility == "eligible_incremental")
        or details.get("primary_metric_direction") != direction
        or details.get("point_estimate_supports_direction") is not point_supports
        or details.get("confidence_interval_supports_direction") is not interval_supports
        or details.get("incremental_positive_allowed") is not incremental_allowed
        or details.get("business_verdict") is not None
        or details.get("no_detectable_change_allowed") is not False
    ):
        raise ExperimentError("实验报告 eligibility_details 与指标数值矛盾")

    methodology = _report_mapping(result.get("methodology"), "methodology")
    _report_exact_keys(
        methodology,
        {
            "estimand",
            "causal_claim_automated",
            "power_calculated",
            "causality_boundary",
            "paid_search_boundary",
            "power_boundary",
        },
        "methodology",
    )
    if (
        methodology.get("estimand") != "page-level difference-in-differences"
        or methodology.get("causal_claim_automated") is not False
        or methodology.get("power_calculated") is not False
        or methodology.get("causality_boundary") != CAUSALITY_BOUNDARY
        or methodology.get("paid_search_boundary") != PAID_SEARCH_BOUNDARY
        or methodology.get("power_boundary") != POWER_BOUNDARY
    ):
        raise ExperimentError("实验报告 methodology 边界无效")


def render_markdown(result: Mapping[str, Any]) -> str:
    primary = result["primary_metric"]
    ci = primary["confidence_interval"]
    lines = [
        f"# SEO 实验增量资格报告：{result['experiment_id']}",
        "",
        f"- 资格状态：`{result['eligibility']}`",
        f"- 设计：`{result['design']}`",
        f"- 主指标：`{primary['metric']}`",
        f"- DiD：{_format_value(primary['difference_in_differences'])}",
        f"- 标准误：{_format_value(primary['standard_error'])}",
        (
            f"- {_format_percent(ci['level'])} 近似置信区间："
            f"[{_format_value(ci['lower'])}, {_format_value(ci['upper'])}]"
        ),
        f"- 预注册 MDE 精度门槛：{'通过' if primary['detectability']['precision_sufficient_for_mde'] else '未通过'}",
        f"- 分析时区：`{result['measurement_contract']['analysis_timezone'] or '未记录'}`",
        f"- 时间粒度：`{result['measurement_contract']['temporal_grain']}`；逐日跨源 join："
        f"{'允许' if result['measurement_contract']['daily_cross_source_join_allowed'] else '禁止'}",
        f"- 测量完整性：`{result['measurement_contract']['status']}`",
        "",
        "## 资格原因",
        "",
    ]
    reasons = result["eligibility_details"]["reasons"]
    lines.extend(f"- `{reason}`" for reason in reasons)
    if not reasons:
        lines.append("- 预注册、实现、对照、数据完整性及 MDE 精度门槛均通过。")
    lines.extend(
        [
            "",
            "## 边界",
            "",
            f"- {CAUSALITY_BOUNDARY}",
            f"- {PAID_SEARCH_BOUNDARY}",
            f"- {POWER_BOUNDARY}",
            "",
        ]
    )
    return "\n".join(lines)


def _format_value(value: Any) -> str:
    return "不可计算" if value is None else f"{float(value):.6g}"


def _format_percent(value: Any) -> str:
    return "未知" if value is None else f"{float(value) * 100:.1f}%"


def _write_output(path: str | Path, content: str, *, label: str) -> None:
    output = Path(path)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ExperimentError(f"无法写入{label} {output}：{exc}") from exc


def _parser() -> ChineseArgumentParser:
    parser = ChineseArgumentParser(
        description="冻结 SEO 页面对照实验，并检查结果是否具备增量解读资格。"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, title="子命令")
    plan_parser = subparsers.add_parser("plan", help="冻结 spec、基线和稳定分组")
    plan_parser.add_argument("--spec", required=True, help="实验 spec JSON")
    plan_parser.add_argument("--baseline", required=True, help="页面基线 CSV")
    plan_parser.add_argument("--out-dir", required=True, help="输出 plan.json 与 assignments.csv 的目录")

    analyze_parser = subparsers.add_parser("analyze", help="校验面板并计算 DiD 与资格")
    analyze_parser.add_argument("--plan", required=True, help="冻结 plan.json")
    analyze_parser.add_argument("--panel", required=True, help="含基线和观察窗口的 panel CSV")
    analyze_parser.add_argument("--artifact-report", required=True, help="实现/产物验证 JSON")
    analyze_parser.add_argument(
        "--measurement-metadata",
        help="可选：分析时的数据截止、finality、分页、采样、阈值与归因元数据 JSON",
    )
    analyze_parser.add_argument("--out", required=True, help="结果 JSON 路径")
    analyze_parser.add_argument(
        "--markdown-out",
        nargs="?",
        const="",
        help="可选 Markdown 路径；不给值时使用 --out 同名 .md",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            plan = plan_experiment(args.spec, args.baseline, args.out_dir)
            print(f"已冻结实验计划：{Path(args.out_dir) / 'plan.json'}")
            print(f"plan hash：{plan['plan_hash']}")
        else:
            result = analyze_experiment(
                args.plan,
                args.panel,
                args.artifact_report,
                args.measurement_metadata,
            )
            _write_output(
                args.out,
                json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                label="结果 JSON",
            )
            if args.markdown_out is not None:
                markdown_path = args.markdown_out or str(Path(args.out).with_suffix(".md"))
                _write_output(markdown_path, render_markdown(result), label="Markdown 报告")
            print(f"已生成实验资格结果：{args.out}")
            print(f"资格状态：{result['eligibility']}")
        return 0
    except ExperimentError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
