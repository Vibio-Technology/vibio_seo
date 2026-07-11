#!/usr/bin/env python3
"""Run the deterministic offline contract regression for Vibio SEO.

This program does not execute a Skill, invoke an LLM, test runtime Skill
triggering, access live search data, or measure SEO outcomes. It checks authored
contract examples and repository invariants only. The routing helper is a
design-time keyword heuristic, not the runtime Skill router.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
DEFAULT_RESPONSES = Path("evals/fixtures/responses.json")
RESPONSES_SCHEMA = Path("evals/schema/responses.schema.json")
EVALUATION_KIND = "offline_contract_regression"
EVALUATION_SCOPE = {
    "executes_skill": False,
    "invokes_model": False,
    "tests_runtime_triggering": False,
    "measures_seo_outcomes": False,
    "note": "手写静态示例的离线合同回归；不是 Skill 效果、触发率或 SEO 结果评测。",
}


@dataclass(frozen=True)
class AssertionResult:
    case_key: str
    assertion_id: str
    assertion_type: str
    passed: bool
    hard_gate: bool
    weight: float
    detail: str


@dataclass(frozen=True)
class ContractFixture:
    fixture_kind: str
    provenance: dict[str, Any]
    sources: dict[str, Any]
    responses: dict[str, Any]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def contains_any(text: str, phrases: Iterable[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def classify_route(prompt: str) -> dict[str, str]:
    """Run a designed keyword heuristic for contract self-checks only.

    This function does not read Skill descriptions and does not approximate a
    model's actual Skill-trigger decision. Keep it useful for deterministic
    boundary tests, but never report its result as runtime routing accuracy.
    """

    text = normalize_text(prompt)

    factory_actions = ("创建", "新建", "做成", "封装", "改进", "优化", "重构", "create", "build", "improve")
    skill_build_request = contains_any(text, ("skill", "技能")) and contains_any(text, factory_actions)
    if skill_build_request and contains_any(text, ("vibio", "seo", "搜索优化")):
        return {"skill": "vibio-factory", "mode": "FACTORY"}
    if skill_build_request:
        return {"skill": "skill-creator", "mode": "GENERIC_SKILL"}

    ad_operations = ("广告组", "campaign", "出价", "预算", "投放计划", "广告文案", "否定关键词", "转化出价")
    seo_intelligence = ("用于 seo", "帮助 seo", "自然搜索", "自然排名", "搜索词报告", "seo 情报")
    if contains_any(text, ad_operations) and not contains_any(text, seo_intelligence):
        return {"skill": "NONE", "mode": "NONE"}

    concept_openers = ("什么是 seo", "seo 是什么", "解释一下 seo", "seo 和 sem 的区别", "what is seo")
    project_markers = ("我的", "我们", "这个站", "网站", "页面", "项目", "代码库", "url", "http")
    if contains_any(text, concept_openers) and not contains_any(text, project_markers):
        return {"skill": "NONE", "mode": "NONE"}

    if contains_any(text, ("大纲", "字数规划", "列一下字数", "content brief")):
        return {"skill": "seo-content-brief", "mode": "WRITE_BRIEF"}

    if contains_any(text, ("流量暴跌", "流量下降", "流量掉", "索引暴跌", "排名集体下降", "恢复流量", "recover")):
        return {"skill": "vibio-seo", "mode": "RECOVER"}

    if contains_any(text, ("继续上次", "之前做到哪", "上次做到哪", "记下来", "记录下来", "项目记忆", "建一下项目记忆")):
        return {"skill": "vibio-memory", "mode": "MEMORY"}

    if contains_any(text, ("90 天", "90天", "路线图", "执行计划", "seo 计划", "启动 seo", "每周做什么", "每月看什么", "接下来 30-90", "接下来该干嘛")):
        return {"skill": "vibio-plan", "mode": "PLAN"}

    if contains_any(text, ("见效", "复盘", "有没有效果", "排名涨", "流量有变化", "改动效果", "月度 seo")):
        return {"skill": "vibio-review", "mode": "REVIEW"}

    if contains_any(text, ("内链", "外链", "反向链接", "孤儿页", "链接方面", "link building", "backlink", "outreach")):
        return {"skill": "vibio-link", "mode": "LINK"}

    if contains_any(text, ("写一篇", "写篇", "重写", "成稿", "稿子", "seo 文章", "博客出来", "文章交付")):
        return {"skill": "vibio-content", "mode": "WRITE"}

    paid_search_for_seo = contains_any(text, ("搜索词报告", "search terms", "paid search terms")) and contains_any(
        text, seo_intelligence
    )
    if paid_search_for_seo or contains_any(text, ("关键词", "哪些词", "高意图", "搜索量", "这个词", "几个词", "大词", "keyword")):
        return {"skill": "vibio-keyword", "mode": "KEYWORD"}

    fix_actions = ("帮我改", "帮我修", "补上", "修复", "直接改", "加 schema", "加结构化数据", "改好", "能改", "implement")
    if contains_any(text, fix_actions):
        return {"skill": "vibio-fix", "mode": "FIX"}

    audit_actions = ("审查", "体检", "看看", "检查", "查一下", "为什么", "排不上", "有没有风险", "诊断", "audit")
    if contains_any(text, audit_actions) or URL_RE.search(prompt):
        return {"skill": "vibio-audit", "mode": "AUDIT"}

    return {"skill": "NONE", "mode": "NONE"}


def parse_frontmatter(skill_path: Path) -> dict[str, Any]:
    text = skill_path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data = yaml.safe_load(match.group(1))
    return data if isinstance(data, dict) else {}


def discover_cases(root: Path) -> list[tuple[Path, dict[str, Any], dict[str, Any]]]:
    manifest = yaml.safe_load((root / "vibio.manifest.yaml").read_text(encoding="utf-8"))
    cases: list[tuple[Path, dict[str, Any], dict[str, Any]]] = []
    for skill in manifest.get("skills", []):
        skill_dir = root / str(skill["path"])
        eval_path = skill_dir / "evals" / "evals.json"
        data = load_json(eval_path)
        for case in data["evals"]:
            cases.append((skill_dir, data, case))
    return cases


def load_contract_fixture(root: Path, response_path: Path | None) -> ContractFixture:
    path = response_path if response_path is not None else DEFAULT_RESPONSES
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        raise ValueError(f"contract fixture does not exist: {path}")
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"contract fixture must be an object in {path}")

    schema_path = root / RESPONSES_SCHEMA
    if not schema_path.is_file():
        raise ValueError(f"contract fixture schema does not exist: {schema_path}")
    schema = load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "root"
        raise ValueError(f"invalid contract fixture {path}: {location}: {first.message}")

    return ContractFixture(
        fixture_kind=str(data["fixture_kind"]),
        provenance=dict(data["provenance"]),
        sources=dict(data["sources"]),
        responses=dict(data["responses"]),
    )


def load_responses(root: Path, response_path: Path | None) -> dict[str, Any]:
    """Compatibility helper returning only authored response examples."""

    return load_contract_fixture(root, response_path).responses


def nested_value(value: Any, path: str) -> Any:
    current = value
    if not path:
        return current
    for raw_part in path.split("."):
        if isinstance(current, list) and raw_part.isdigit():
            current = current[int(raw_part)]
        elif isinstance(current, dict) and raw_part in current:
            current = current[raw_part]
        else:
            raise KeyError(path)
    return current


def resolve_target(
    target: str,
    case: dict[str, Any],
    skill_text: str,
    response: Any,
) -> Any:
    if target == "skill":
        return skill_text
    if target == "prompt":
        return case["prompt"]
    if target == "expected_output":
        return case["expected_output"]
    if target == "output":
        return response
    if target.startswith("output."):
        return nested_value(response, target.removeprefix("output."))
    raise KeyError(target)


def printable(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def normalized_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        raise TypeError("value must be an array")
    return {printable(item) for item in value}


def valid_public_url(value: Any, domains: set[str] | None = None) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    if domains and not any(parsed.netloc == domain or parsed.netloc.endswith(f".{domain}") for domain in domains):
        return False
    return True


def claim_source_ids(claim: dict[str, Any]) -> list[str]:
    single = claim.get("source_id")
    multiple = claim.get("source_ids")
    if isinstance(single, str) and single.strip():
        return [single]
    if isinstance(multiple, list) and multiple and all(isinstance(item, str) and item.strip() for item in multiple):
        return list(dict.fromkeys(multiple))
    return []


def source_support_failures(
    claim: dict[str, Any],
    sources: dict[str, Any],
    official_domains: set[str] | None = None,
) -> list[str]:
    """Verify a claim against an offline evidence snapshot.

    This verifies provenance structure, not the truth of the source. Public web
    evidence must have a recorded successful HTTP status, and every source must
    contain a claim-specific supporting excerpt copied into its saved snapshot.
    """

    claim_id = str(claim.get("id", "")).strip()
    claim_text = str(claim.get("text", "")).strip()
    source_ids = claim_source_ids(claim)
    failures: list[str] = []
    if not claim_id:
        failures.append("claim id is missing")
    if not claim_text:
        failures.append("claim text is missing")
    if not source_ids:
        failures.append("source_id/source_ids is missing")
        return failures

    normalized_claim = normalize_text(claim_text)
    for source_id in source_ids:
        source = sources.get(source_id)
        prefix = f"{source_id}: "
        if not isinstance(source, dict):
            failures.append(prefix + "source is absent from the evidence registry")
            continue

        source_type = source.get("source_type")
        locator = source.get("locator")
        if source_type == "public_web":
            if not valid_public_url(locator, official_domains):
                failures.append(prefix + "public URL is invalid or outside the allowed domains")
            snapshot = source.get("snapshot")
            if not isinstance(snapshot, dict) or not 200 <= int(snapshot.get("http_status", 0)) < 300:
                failures.append(prefix + "snapshot does not record a successful HTTP status")
        elif source_type == "provided_data":
            parsed = urlparse(locator) if isinstance(locator, str) else None
            if parsed is None or not parsed.scheme or not (parsed.netloc or parsed.path):
                failures.append(prefix + "provided-data locator is invalid")
            snapshot = source.get("snapshot")
        else:
            failures.append(prefix + "unsupported source_type")
            snapshot = source.get("snapshot")

        if not isinstance(snapshot, dict):
            failures.append(prefix + "snapshot is missing")
            continue
        if snapshot.get("status") != "captured":
            failures.append(prefix + "snapshot status is not captured")
        snapshot_excerpt = snapshot.get("excerpt")
        if not isinstance(snapshot_excerpt, str) or len(snapshot_excerpt.strip()) < 20:
            failures.append(prefix + "snapshot excerpt is missing or too short")
            continue

        support = snapshot.get("supports", {}).get(claim_id) if isinstance(snapshot.get("supports"), dict) else None
        if not isinstance(support, dict):
            failures.append(prefix + f"has no support record for claim {claim_id!r}")
            continue
        supported_claim = support.get("claim")
        supporting_excerpt = support.get("excerpt")
        if not isinstance(supported_claim, str) or not supported_claim.strip():
            failures.append(prefix + "support claim is missing")
        elif normalize_text(supported_claim) not in normalized_claim:
            failures.append(prefix + "support claim is not present in the asserted claim text")
        if not isinstance(supporting_excerpt, str) or len(supporting_excerpt.strip()) < 10:
            failures.append(prefix + "claim-specific excerpt is missing or too short")
        elif normalize_text(supporting_excerpt) not in normalize_text(snapshot_excerpt):
            failures.append(prefix + "claim-specific excerpt is not present in the saved snapshot")
    return failures


def evaluate_assertion(
    assertion: dict[str, Any],
    case: dict[str, Any],
    skill_dir: Path,
    skill_text: str,
    response: Any,
    sources: dict[str, Any] | None = None,
) -> tuple[bool, str, str | None]:
    kind = assertion["type"]
    expected = assertion["expected"]
    target = assertion["target"]

    if kind in {"route_equals", "route_not_equals"}:
        route = classify_route(case["prompt"])
        route_key = target.removeprefix("routing.") if target.startswith("routing.") else "skill"
        actual = route.get(route_key, "")
        passed = actual == expected if kind == "route_equals" else actual != expected
        operator = "==" if kind == "route_equals" else "!="
        return passed, f"{actual!r} {operator} {expected!r}", actual

    if kind == "file_exists":
        exists = (skill_dir / target).is_file()
        return exists is bool(expected), f"exists={exists}, expected={bool(expected)}", None

    try:
        actual = resolve_target(target, case, skill_text, response)
    except (KeyError, IndexError, TypeError) as exc:
        return False, f"target {target!r} unavailable: {exc}", None

    if kind in {"regex_all", "regex_none"}:
        patterns = expected if isinstance(expected, list) else [expected]
        haystack = printable(actual)
        matches = [bool(re.search(str(pattern), haystack, re.IGNORECASE | re.DOTALL)) for pattern in patterns]
        passed = all(matches) if kind == "regex_all" else not any(matches)
        failed = [str(pattern) for pattern, matched in zip(patterns, matches) if matched != (kind == "regex_all")]
        return passed, "patterns satisfied" if passed else f"pattern failures: {failed}", None

    if kind == "jsonpath_equals":
        passed = actual == expected
        return passed, f"actual={actual!r}, expected={expected!r}", None

    if kind == "fact_set_equals":
        try:
            actual_set = normalized_set(actual)
            expected_set = normalized_set(expected)
        except TypeError as exc:
            return False, str(exc), None
        passed = actual_set == expected_set
        return passed, f"missing={sorted(expected_set - actual_set)}, extra={sorted(actual_set - expected_set)}", None

    if kind == "citation_coverage":
        if not isinstance(actual, list) or not isinstance(expected, dict):
            return False, "citation_coverage requires a claims array and an expected object", None
        required = set(expected.get("claim_ids", []))
        domains = set(expected.get("official_domains", [])) or None
        claims = {str(item.get("id")): item for item in actual if isinstance(item, dict) and item.get("id")}
        source_registry = sources or {}
        failures = {
            claim_id: source_support_failures(claims[claim_id], source_registry, domains)
            for claim_id in required
            if claim_id in claims
        }
        covered = {claim_id for claim_id, reasons in failures.items() if not reasons}
        ratio = len(covered) / len(required) if required else 1.0
        threshold = float(expected.get("min_ratio", 1.0))
        passed = required.issubset(claims) and ratio >= threshold
        unsupported = {claim_id: reasons for claim_id, reasons in failures.items() if reasons}
        return (
            passed,
            f"coverage={ratio:.3f}, missing_or_unsupported={sorted(required - covered)}, details={unsupported}",
            None,
        )

    if kind == "numeric_claims_have_source":
        if not isinstance(actual, list):
            return False, "numeric_claims_have_source requires a structured claims array", None
        offenders: list[str] = []
        numeric_count = 0
        for index, claim in enumerate(actual):
            if not isinstance(claim, dict):
                continue
            is_numeric = claim.get("numeric") is True or "numeric_value" in claim
            if is_numeric:
                numeric_count += 1
                failures = source_support_failures(claim, sources or {})
                if failures:
                    offenders.append(f"{claim.get('id', index)}: {'; '.join(failures)}")
        minimum = int(expected.get("min_numeric_claims", 1)) if isinstance(expected, dict) else 1
        passed = not offenders and numeric_count >= minimum
        return passed, f"numeric claims={numeric_count}, minimum={minimum}, unsupported={offenders}", None

    if kind in {"file_changed", "file_unchanged"}:
        if not isinstance(actual, list):
            return False, f"{kind} requires a files array", None
        wanted = set(expected if isinstance(expected, list) else [expected])
        states = {
            str(item.get("path")): item.get("before_sha256") != item.get("after_sha256")
            for item in actual
            if isinstance(item, dict) and item.get("path")
        }
        expected_changed = kind == "file_changed"
        failed = sorted(path for path in wanted if states.get(path) is not expected_changed)
        return not failed, f"unexpected file states={failed}", None

    if kind == "path_confined":
        if not isinstance(actual, list):
            return False, "path_confined requires a path array", None
        root = Path(str(expected))
        escaped: list[str] = []
        for raw in actual:
            candidate = Path(str(raw))
            if candidate.is_absolute() or ".." in candidate.parts:
                escaped.append(str(raw))
                continue
            try:
                (root / candidate).resolve().relative_to(root.resolve())
            except ValueError:
                escaped.append(str(raw))
        return not escaped, f"escaped paths={escaped}", None

    if kind == "command_succeeds":
        if not isinstance(actual, list):
            return False, "command_succeeds requires a command-results array", None
        wanted = set(expected if isinstance(expected, list) else [expected])
        status = {
            str(item.get("command")): item.get("exit_code") == 0
            for item in actual
            if isinstance(item, dict)
        }
        failed = sorted(command for command in wanted if not status.get(command, False))
        return not failed, f"failed or missing commands={failed}", None

    if kind == "changelog_preserves_and_adds":
        if not isinstance(actual, dict):
            return False, "changelog assertion requires before/after arrays", None
        before, after = actual.get("before"), actual.get("after")
        minimum = int(expected.get("min_new", 1)) if isinstance(expected, dict) else 1
        if not isinstance(before, list) or not isinstance(after, list):
            return False, "changelog before/after must be arrays", None
        added = len(after) - len(before)
        preserved = not before or after[-len(before) :] == before
        return preserved and added >= minimum, f"preserved={preserved}, added={added}", None

    if kind == "internal_link_graph_equals":
        if not isinstance(actual, dict) or not isinstance(expected, dict):
            return False, "link graphs must be objects", None
        normalize = lambda graph: {key: sorted(set(value)) for key, value in graph.items()}
        passed = normalize(actual) == normalize(expected)
        return passed, "graphs equal" if passed else "link graph differs", None

    return False, f"unsupported assertion type: {kind}", None


def validate_contract_output(response: Any) -> tuple[bool, str]:
    """Reject empty examples and obvious repeated-keyword placeholders."""

    if response is None or response == {} or response == []:
        return False, "authored contract output is empty"
    if isinstance(response, str):
        stripped = response.strip()
        if not stripped:
            return False, "authored contract output is empty"
        tokens = re.findall(r"[a-z0-9][a-z0-9+.#-]*|[\u4e00-\u9fff]{2,}", stripped.lower())
        if len(tokens) >= 8:
            counts = Counter(tokens)
            most_common = counts.most_common(1)[0][1]
            if most_common / len(tokens) >= 0.50 or len(counts) / len(tokens) <= 0.20:
                return False, "authored contract output looks like repeated keyword stuffing"
    return True, "authored contract output is non-empty and not an obvious keyword placeholder"


def weighted_pass_rate(results: list[AssertionResult]) -> float | None:
    total_weight = sum(item.weight for item in results)
    if not total_weight:
        return None
    return sum(item.weight for item in results if item.passed) / total_weight


def run_suite(root: Path, response_path: Path | None = None) -> dict[str, Any]:
    fixture = load_contract_fixture(root, response_path)
    responses = fixture.responses
    results: list[AssertionResult] = []
    fixture_cases = 0
    missing_response_cases: list[str] = []
    cases = discover_cases(root)

    for skill_dir, eval_data, case in cases:
        case_key = f"{eval_data['skill_name']}:{case['id']}"
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        output_assertions = [
            assertion
            for assertion in case["assertions"]
            if str(assertion.get("target", "")).startswith("output")
        ]
        has_response = case_key in responses
        response = responses.get(case_key)
        if has_response:
            fixture_cases += 1
        elif output_assertions:
            missing_response_cases.append(case_key)

        if has_response and output_assertions:
            passed, detail = validate_contract_output(response)
            results.append(
                AssertionResult(
                    case_key=case_key,
                    assertion_id="fixture-output-sanity",
                    assertion_type="fixture_output_sanity",
                    passed=passed,
                    hard_gate=True,
                    weight=0.0,
                    detail=detail,
                )
            )

        assertion_ids: set[str] = set()
        for assertion in case["assertions"]:
            assertion_id = str(assertion["id"])
            if assertion_id in assertion_ids:
                passed, detail = False, f"duplicate assertion id: {assertion_id}"
            else:
                assertion_ids.add(assertion_id)
                if str(assertion.get("target", "")).startswith("output") and not has_response:
                    passed, detail = False, "authored contract response fixture is missing"
                else:
                    passed, detail, _ = evaluate_assertion(
                        assertion,
                        case,
                        skill_dir,
                        skill_text,
                        response,
                        fixture.sources,
                    )
            results.append(
                AssertionResult(
                    case_key=case_key,
                    assertion_id=assertion_id,
                    assertion_type=str(assertion["type"]),
                    passed=passed,
                    hard_gate=bool(assertion["hard_gate"]),
                    weight=float(assertion["weight"]),
                    detail=detail,
                )
            )

    heuristic_results = [
        item for item in results if item.assertion_type in {"route_equals", "route_not_equals"}
    ]
    non_route_results = [
        item
        for item in results
        if item.assertion_type not in {"route_equals", "route_not_equals", "fixture_output_sanity"}
    ]
    hard_failures = [item for item in results if item.hard_gate and not item.passed]
    soft_results = [item for item in results if not item.hard_gate]

    return {
        "evaluation_kind": EVALUATION_KIND,
        "scope": EVALUATION_SCOPE,
        "fixture": {
            "fixture_kind": fixture.fixture_kind,
            "provenance": fixture.provenance,
        },
        "summary": {
            "cases": len(cases),
            "contract_assertions": len(results),
            "contract_assertions_passed": sum(item.passed for item in results),
            "contract_weighted_pass_rate": weighted_pass_rate(results),
            "non_route_contract_assertions": len(non_route_results),
            "non_route_contract_weighted_pass_rate": weighted_pass_rate(non_route_results),
            "hard_failures": len(hard_failures),
            "soft_contract_assertions": len(soft_results),
            "soft_contract_weighted_pass_rate": weighted_pass_rate(soft_results),
            "designed_heuristic_route_checks": {
                "passed": sum(item.passed for item in heuristic_results),
                "total": len(heuristic_results),
                "note": "内置关键词启发式的设计自检；不读取 Skill description，不是实际触发测试。",
            },
            "fixture_response_cases": fixture_cases,
            "response_required_cases": sum(
                any(str(assertion.get("target", "")).startswith("output") for assertion in case["assertions"])
                for _, _, case in cases
            ),
            "missing_response_cases": len(missing_response_cases),
        },
        "missing_responses": missing_response_cases,
        "failures": [asdict(item) for item in results if not item.passed],
        "results": [asdict(item) for item in results],
    }


def strict_failure_reasons(report: dict[str, Any], min_soft_contract_rate: float = 0.90) -> list[str]:
    if not 0 <= min_soft_contract_rate <= 1:
        raise ValueError("min_soft_contract_rate must be between 0 and 1")
    summary = report["summary"]
    reasons: list[str] = []
    if summary["hard_failures"]:
        reasons.append(f"{summary['hard_failures']} hard contract assertion(s) failed")
    if summary["missing_response_cases"]:
        reasons.append(f"{summary['missing_response_cases']} authored response fixture(s) are missing")
    soft_rate = summary["soft_contract_weighted_pass_rate"]
    if soft_rate is not None and soft_rate < min_soft_contract_rate:
        reasons.append(
            f"soft contract rate {soft_rate:.3f} is below the minimum {min_soft_contract_rate:.3f}"
        )
    return reasons


def render_human(report: dict[str, Any]) -> str:
    summary = report["summary"]
    route_checks = summary["designed_heuristic_route_checks"]
    contract_rate = summary["contract_weighted_pass_rate"]
    non_route_rate = summary["non_route_contract_weighted_pass_rate"]
    soft_rate = summary["soft_contract_weighted_pass_rate"]
    lines = [
        "Vibio SEO 离线合同回归",
        report["scope"]["note"],
        f"用例: {summary['cases']}  合同断言: "
        f"{summary['contract_assertions_passed']}/{summary['contract_assertions']}",
        f"合同加权通过率: {contract_rate:.1%}" if contract_rate is not None else "合同加权通过率: n/a",
        f"非路由合同通过率: {non_route_rate:.1%} ({summary['non_route_contract_assertions']} 条)"
        if non_route_rate is not None
        else "非路由合同通过率: n/a",
        f"软合同通过率: {soft_rate:.1%} ({summary['soft_contract_assertions']} 条)"
        if soft_rate is not None
        else "软合同通过率: n/a（当前没有软断言）",
        f"设计内路由启发式自检: {route_checks['passed']}/{route_checks['total']}（非实际 Skill 触发）",
        f"硬闸门失败: {summary['hard_failures']}",
        f"手写 fixture 输出: {summary['fixture_response_cases']}/{summary['response_required_cases']}  "
        f"缺失: {summary['missing_response_cases']}",
    ]
    if report["failures"]:
        lines.append("失败明细:")
        for failure in report["failures"]:
            lines.append(
                f"- {failure['case_key']}::{failure['assertion_id']} "
                f"[{failure['assertion_type']}] {failure['detail']}"
            )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--responses", type=Path, help="Authored offline contract fixture JSON.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON report.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on hard contract failures, missing fixtures, or a weak soft-contract rate.",
    )
    parser.add_argument("--min-soft-contract-rate", type=float, default=0.90)
    args = parser.parse_args()

    try:
        root = args.root.resolve()
        report = run_suite(root, args.responses)
        strict_reasons = strict_failure_reasons(report, args.min_soft_contract_rate)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"eval runner error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render_human(report))
    return 1 if args.strict and strict_reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())
