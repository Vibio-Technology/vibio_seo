#!/usr/bin/env python3
"""Vibio SEO 结构化项目状态管理器。

本文件只使用 Python 标准库，可独立复制到 Skill 的 scripts/ 目录执行。
Markdown 只是结构化状态的派生视图，不会被反向解析为状态。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit


SCHEMA_VERSION = "1.1"
STATE_DIR_PARTS = (".vibio", "state")
PROJECT_FILE = "project.json"
PROJECT_DIGEST_FILE = "project.sha256"
CHANGES_FILE = "changes.jsonl"
REVIEWS_FILE = "reviews.jsonl"
LOCK_FILE = ".append.lock"
GENESIS_HASH = "0" * 64
MAX_INPUT_BYTES = 1_048_576
MAX_EVIDENCE_BYTES = 67_108_864
DETECTABILITY_SCHEMA_VERSION = "1.0"
DETECTABILITY_TOOL = "vibio-seo-detectability"
DETECTABILITY_VERSION = "1.0.0"
DETECTABILITY_METHOD = "two_sided_normal_approximation"

PRIMARY_STATUSES = (
    "planned",
    "implemented",
    "artifact_verified",
    "outcome_pending",
    "reviewed",
)
TERMINAL_STATUSES = ("implementation_failed", "rolled_back", "cancelled")
ALL_STATUSES = frozenset((*PRIMARY_STATUSES, *TERMINAL_STATUSES))
ALLOWED_TRANSITIONS = {
    "planned": frozenset(("implemented", "cancelled")),
    "implemented": frozenset(
        ("artifact_verified", "implementation_failed", "rolled_back", "cancelled")
    ),
    "artifact_verified": frozenset(("outcome_pending", "rolled_back")),
    "outcome_pending": frozenset(("reviewed", "rolled_back")),
    "reviewed": frozenset(),
    "implementation_failed": frozenset(),
    "rolled_back": frozenset(),
    "cancelled": frozenset(),
}
VERDICTS = frozenset(
    (
        "implementation-failed",
        "not-yet-observable",
        "directional-positive",
        "incremental-positive",
        "no-detectable-change",
        "negative-or-regression",
        "inconclusive",
    )
)
RESERVED_FIELDS = frozenset(
    (
        "schema_version",
        "record_kind",
        "sequence",
        "recorded_at",
        "previous_hash",
        "project_sha256",
        "changes_head",
        "reviews_head",
        "record_hash",
    )
)

IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", re.I)
CN_PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[ -]?)?1[3-9]\d(?:[ -]?\d){8}(?!\d)")
INTL_PHONE_RE = re.compile(r"(?<!\w)\+[1-9]\d(?:[ .()-]?\d){7,13}(?!\d)")
CREDENTIAL_PATTERNS = (
    ("OpenAI/API token", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("Stripe secret key", re.compile(r"\bsk_(?:live|test)_[0-9A-Za-z]{16,}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("private key", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")),
    (
        "Bearer token",
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I),
    ),
)
SENSITIVE_KEY_RE = re.compile(
    r"(?:^|[_-])(?:api[_-]?key|access[_-]?token|refresh[_-]?token|auth(?:orization)?|"
    r"bearer|client[_-]?secret|private[_-]?key|password|passwd|pwd|secret|session[_-]?id|"
    r"cookie)(?:$|[_-])",
    re.I,
)
HASH_FIELD_RE = re.compile(
    r"(?:^|[_-])(?:hash|sha(?:1|224|256|384|512)?|digest|checksum)(?:$|[_-])",
    re.I,
)
HEX_DIGEST_RE = re.compile(r"[0-9a-f]{32,128}", re.I)
CHAIN_HEAD_FIELDS = frozenset(("changes_head", "reviews_head"))


class StateError(ValueError):
    """可直接向 CLI 用户展示的状态或输入错误。"""


def _experiment_runtime() -> Any:
    """Load the sibling canonical experiment validators in repo and bundles."""

    try:
        from . import experiment as experiment_runtime
    except ImportError:  # 直接执行分发后的 scripts/state_manager.py
        import experiment as experiment_runtime  # type: ignore[no-redef]
    return experiment_runtime


class ChineseArgumentParser(argparse.ArgumentParser):
    """将 argparse 的主要错误提示固定为中文。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._positionals.title = "位置参数"
        self._optionals.title = "选项"
        for action in self._actions:
            if isinstance(action, argparse._HelpAction):
                action.help = "显示帮助并退出"

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法：")

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
        elif "invalid choice:" in message:
            message = (
                message.replace("argument ", "参数 ", 1)
                .replace("invalid choice:", "取值无效：", 1)
                .replace("(choose from", "（可选值：", 1)
            )
            if message.endswith(")"):
                message = message[:-1] + "）"
        elif "expected one argument" in message:
            message = message.replace("expected one argument", "需要提供一个值", 1)
        self.print_usage(sys.stderr)
        self.exit(2, f"错误：{message}\n")


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _reject_constant(value: str) -> None:
    raise StateError(f"JSON 包含非标准数值 {value}")


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StateError(f"JSON 包含重复字段：{key}")
        result[key] = value
    return result


def _loads_json(text: str, *, source: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except StateError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise StateError(f"{source} 不是有效 UTF-8 JSON：{exc}") from exc


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
        raise StateError(f"记录不能序列化为标准 JSON：{exc}") from exc


def _record_digest(record_without_hash: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(record_without_hash).encode("utf-8")).hexdigest()


def _project_digest(project: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(project).encode("utf-8")).hexdigest()


def _nonempty_text(value: Any, field: str, *, max_length: int = 2048) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateError(f"字段 {field} 必须是非空字符串")
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise StateError(f"字段 {field} 超过 {max_length} 个字符")
    return cleaned


def _identifier(value: Any, field: str) -> str:
    text = _nonempty_text(value, field, max_length=128)
    if not IDENTIFIER_RE.fullmatch(text):
        raise StateError(
            f"字段 {field} 只能包含字母、数字、点、下划线、冒号或连字符"
        )
    return text


def _scan_sensitive(value: Any, *, location: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise StateError(f"{location} 包含非字符串 JSON 字段名")
            if SENSITIVE_KEY_RE.search(key):
                raise StateError(f"拒绝写入可能的凭据字段：{location}.{key}")
            if (
                (HASH_FIELD_RE.search(key) or key in CHAIN_HEAD_FIELDS)
                and isinstance(child, str)
                and HEX_DIGEST_RE.fullmatch(child)
            ):
                continue
            _scan_sensitive(child, location=f"{location}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _scan_sensitive(child, location=f"{location}[{index}]")
        return
    if not isinstance(value, str):
        return
    if EMAIL_RE.search(value):
        raise StateError(f"拒绝写入电子邮箱（{location}）")
    if CN_PHONE_RE.search(value) or INTL_PHONE_RE.search(value):
        raise StateError(f"拒绝写入手机号码（{location}）")
    for label, pattern in CREDENTIAL_PATTERNS:
        if pattern.search(value):
            raise StateError(f"拒绝写入可能的 {label}（{location}）")


def _resolve_project_root(value: str | os.PathLike[str]) -> Path:
    raw = Path(value).expanduser()
    if not raw.exists():
        raise StateError(f"项目根目录不存在：{raw}")
    if not raw.is_dir():
        raise StateError(f"项目根路径不是目录：{raw}")
    return raw.resolve()


def _reject_symlink(path: Path, label: str) -> None:
    if path.is_symlink():
        raise StateError(f"拒绝使用符号链接作为{label}：{path}")


def _state_paths(
    project_root: str | os.PathLike[str], *, require: bool = True
) -> tuple[Path, Path, Path, Path, Path]:
    root = _resolve_project_root(project_root)
    vibio_dir = root / STATE_DIR_PARTS[0]
    state_dir = vibio_dir / STATE_DIR_PARTS[1]
    _reject_symlink(vibio_dir, ".vibio 目录")
    _reject_symlink(state_dir, "state 目录")
    paths = (
        state_dir / PROJECT_FILE,
        state_dir / PROJECT_DIGEST_FILE,
        state_dir / CHANGES_FILE,
        state_dir / REVIEWS_FILE,
    )
    for path in paths:
        _reject_symlink(path, "状态文件")
    if require:
        if not state_dir.is_dir():
            raise StateError(f"未初始化结构化状态：{state_dir}")
        for path in paths:
            if not path.is_file():
                raise StateError(f"状态文件缺失：{path}")
    return (state_dir, *paths)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _append_line(path: Path, record: Mapping[str, Any]) -> None:
    payload = (_canonical_json(record) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        written = os.write(descriptor, payload)
        if written != len(payload):
            raise StateError(f"追加状态记录不完整：{path}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _append_lock(state_dir: Path) -> Any:
    """Serialize read-validate-append across processes on POSIX and Windows."""

    lock_path = state_dir / LOCK_FILE
    _reject_symlink(lock_path, "状态追加锁")
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise StateError(f"无法打开状态追加锁：{exc}") from exc
    acquired = False
    try:
        try:
            if os.name == "nt":
                import msvcrt

                if os.fstat(descriptor).st_size == 0:
                    os.write(descriptor, b"0")
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_EX)
            acquired = True
        except OSError as exc:
            raise StateError(f"无法获取状态追加锁：{exc}") from exc
        yield
    finally:
        unlock_error: OSError | None = None
        if acquired:
            try:
                if os.name == "nt":
                    import msvcrt

                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError as exc:
                unlock_error = exc
        os.close(descriptor)
        if unlock_error is not None:
            raise StateError(f"无法释放状态追加锁：{unlock_error}") from unlock_error


def _read_json_file(path: Path, *, max_bytes: int = MAX_INPUT_BYTES) -> dict[str, Any]:
    if path.stat().st_size > max_bytes:
        raise StateError(f"JSON 文件超过 {max_bytes} 字节：{path}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise StateError(f"无法读取 JSON 文件 {path}：{exc}") from exc
    value = _loads_json(text, source=str(path))
    if not isinstance(value, dict):
        raise StateError(f"{path} 顶层必须是 JSON 对象")
    return value


def load_input(path_value: str | os.PathLike[str]) -> dict[str, Any]:
    path = Path(path_value).expanduser()
    if not path.exists() or not path.is_file():
        raise StateError(f"输入 JSON 文件不存在：{path}")
    _reject_symlink(path, "输入 JSON 文件")
    return _read_json_file(path.resolve())


def _validate_project(project: Mapping[str, Any]) -> None:
    expected = {"schema_version", "project_id", "site_url", "market", "language", "created_at"}
    missing = sorted(expected - set(project))
    if missing:
        raise StateError(f"project.json 缺少字段：{', '.join(missing)}")
    if project.get("schema_version") != SCHEMA_VERSION:
        raise StateError(f"project.json schema_version 必须为 {SCHEMA_VERSION}")
    _identifier(project.get("project_id"), "project_id")
    site_url = _nonempty_text(project.get("site_url"), "site_url", max_length=2048)
    parsed = urlsplit(site_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise StateError("site_url 必须是带 http/https 的绝对 URL")
    if parsed.username is not None or parsed.password is not None:
        raise StateError("site_url 不得包含用户名或密码")
    _nonempty_text(project.get("market"), "market", max_length=128)
    _nonempty_text(project.get("language"), "language", max_length=128)
    _nonempty_text(project.get("created_at"), "created_at", max_length=64)
    _scan_sensitive(dict(project))


def initialize_project(
    project_root: str | os.PathLike[str],
    *,
    project_id: str,
    site_url: str,
    market: str,
    language: str,
) -> dict[str, Any]:
    state_dir, project_path, project_digest_path, changes_path, reviews_path = _state_paths(
        project_root, require=False
    )
    if state_dir.exists():
        if any(
            path.exists()
            for path in (project_path, project_digest_path, changes_path, reviews_path)
        ):
            raise StateError(f"结构化状态已初始化，拒绝覆盖：{state_dir}")
        if any(state_dir.iterdir()):
            raise StateError(f"state 目录非空，拒绝初始化：{state_dir}")
    project = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "site_url": site_url,
        "market": market,
        "language": language,
        "created_at": _now_utc(),
    }
    _validate_project(project)
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    _atomic_write(project_path, json.dumps(project, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    _atomic_write(project_digest_path, _project_digest(project) + "\n")
    _atomic_write(changes_path, "")
    _atomic_write(reviews_path, "")
    return project


def _read_chain(
    path: Path, expected_kind: str, *, project_sha256: str
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    previous_hash = GENESIS_HASH
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise StateError(f"无法读取状态链 {path}：{exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise StateError(f"{path.name} 第 {line_number} 行为空，状态链无效")
        value = _loads_json(line, source=f"{path.name} 第 {line_number} 行")
        if not isinstance(value, dict):
            raise StateError(f"{path.name} 第 {line_number} 行必须是 JSON 对象")
        if value.get("schema_version") != SCHEMA_VERSION:
            raise StateError(f"{path.name} 第 {line_number} 行 schema_version 无效")
        if value.get("record_kind") != expected_kind:
            raise StateError(f"{path.name} 第 {line_number} 行 record_kind 应为 {expected_kind}")
        if value.get("project_sha256") != project_sha256:
            raise StateError(f"{path.name} 第 {line_number} 行未绑定当前 project.json")
        if type(value.get("sequence")) is not int or value["sequence"] != line_number:
            raise StateError(f"{path.name} 第 {line_number} 行 sequence 不连续")
        if value.get("previous_hash") != previous_hash:
            raise StateError(f"{path.name} 第 {line_number} 行 previous_hash 断链")
        supplied_hash = value.get("record_hash")
        if not isinstance(supplied_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", supplied_hash):
            raise StateError(f"{path.name} 第 {line_number} 行 record_hash 格式无效")
        unhashed = dict(value)
        del unhashed["record_hash"]
        calculated_hash = _record_digest(unhashed)
        if supplied_hash != calculated_hash:
            raise StateError(f"{path.name} 第 {line_number} 行 record_hash 不匹配，历史可能被篡改")
        _scan_sensitive(value)
        records.append(value)
        previous_hash = supplied_hash
    return records


def _artifact_result(record: Mapping[str, Any]) -> tuple[bool | None, Any]:
    verification = record.get("artifact_verification")
    if isinstance(verification, dict):
        passed = verification.get("passed")
        evidence = verification.get("evidence")
        return (passed if type(passed) is bool else None, evidence)
    passed = record.get("artifact_verification_passed")
    evidence = record.get("artifact_verification_evidence")
    return (passed if type(passed) is bool else None, evidence)


def _has_evidence(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None and type(value) is not bool


def _validate_change_payload(record: Mapping[str, Any]) -> tuple[str, str]:
    change_id = _identifier(record.get("change_id"), "change_id")
    status = _nonempty_text(record.get("status"), "status", max_length=64)
    if status not in ALL_STATUSES:
        raise StateError(f"change {change_id} 的状态无效：{status}")
    if status == "reviewed":
        raise StateError("reviewed 状态只能由 append-review 产生")
    passed, evidence = _artifact_result(record)
    if status == "artifact_verified" and (passed is not True or not _has_evidence(evidence)):
        raise StateError("artifact_verified 必须提供 passed=true 的产物验证及非空证据")
    if status == "implementation_failed" and (passed is not False or not _has_evidence(evidence)):
        raise StateError("implementation_failed 只能用于 passed=false 的产物验证，且必须有证据")
    registration = record.get("experiment_registration")
    if registration is not None:
        if status != "planned" or not isinstance(registration, Mapping):
            raise StateError("experiment_registration 只能在 planned 记录中声明为对象")
        _identifier(registration.get("experiment_id"), "experiment_registration.experiment_id")
        _nonempty_text(registration.get("plan"), "experiment_registration.plan")
        _required_sha256(
            registration.get("plan_file_sha256"),
            "experiment_registration.plan_file_sha256",
        )
        _required_sha256(
            registration.get("plan_hash"), "experiment_registration.plan_hash"
        )
    return change_id, status


def _state_from_changes(records: Sequence[Mapping[str, Any]]) -> tuple[dict[str, str], dict[str, list[Mapping[str, Any]]]]:
    states: dict[str, str] = {}
    events: dict[str, list[Mapping[str, Any]]] = {}
    for record in records:
        change_id, status = _validate_change_payload(record)
        previous = states.get(change_id)
        if previous is None:
            if status != "planned":
                raise StateError(f"change {change_id} 的首条状态必须是 planned，实际为 {status}")
        elif status not in ALLOWED_TRANSITIONS[previous]:
            raise StateError(f"change {change_id} 存在非法状态转移：{previous} -> {status}")
        states[change_id] = status
        events.setdefault(change_id, []).append(record)
    return states, events


def _project_evidence_file(
    project_root: str | os.PathLike[str], value: Any, field: str
) -> tuple[Path, str]:
    raw = _nonempty_text(value, field, max_length=2048)
    root = _resolve_project_root(project_root)
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=False)
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise StateError(f"字段 {field} 必须引用项目根目录内的文件") from exc
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        _reject_symlink(current, f"{field} 父目录")
    _reject_symlink(candidate, field)
    if not resolved.is_file():
        raise StateError(f"字段 {field} 引用的文件不存在：{raw}")
    return resolved, relative.as_posix()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError as exc:
        raise StateError(f"无法计算证据文件哈希 {path}：{exc}") from exc
    return digest.hexdigest()


def _required_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise StateError(f"字段 {field} 必须是 64 位小写 SHA-256")
    return value


def _validate_experiment_registration(
    project_root: str | os.PathLike[str], record: Mapping[str, Any]
) -> dict[str, str]:
    registration = record.get("experiment_registration")
    if not isinstance(registration, Mapping):
        raise StateError("强 verdict 要求 planned 记录提前绑定 experiment_registration")
    experiment_id = _identifier(
        registration.get("experiment_id"), "experiment_registration.experiment_id"
    )
    plan_path, plan_relative = _project_evidence_file(
        project_root, registration.get("plan"), "experiment_registration.plan"
    )
    plan_file_sha256 = _required_sha256(
        registration.get("plan_file_sha256"),
        "experiment_registration.plan_file_sha256",
    )
    if _file_sha256(plan_path) != plan_file_sha256:
        raise StateError("planned 记录绑定的 experiment plan 文件已变化")
    _read_json_file(plan_path, max_bytes=MAX_EVIDENCE_BYTES)
    experiment_runtime = _experiment_runtime()
    try:
        plan, _ = experiment_runtime.load_and_verify_plan(plan_path)
    except experiment_runtime.ExperimentError as exc:
        raise StateError(f"experiment_registration 计划语义无效：{exc}") from exc
    plan_hash = _required_sha256(
        registration.get("plan_hash"), "experiment_registration.plan_hash"
    )
    if plan.get("experiment_id") != experiment_id or plan.get("plan_hash") != plan_hash:
        raise StateError("experiment_registration 与冻结 plan 身份不匹配")
    if plan.get("schema_version") != "1.1" or plan.get("tool") != "vibio-seo-experiment":
        raise StateError("experiment_registration 引用的不是受支持正式计划")
    unhashed = dict(plan)
    supplied = unhashed.pop("plan_hash", None)
    if supplied != _record_digest(unhashed):
        raise StateError("experiment_registration 的 plan_hash 复算失败")
    return {
        "experiment_id": experiment_id,
        "plan": plan_relative,
        "plan_file_sha256": plan_file_sha256,
        "plan_hash": plan_hash,
    }


def _verify_experiment_plan(
    project_root: str | os.PathLike[str],
    record: Mapping[str, Any],
    result: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    plan_path, plan_relative = _project_evidence_file(
        project_root, record.get("experiment_plan"), "experiment_plan"
    )
    _read_json_file(plan_path, max_bytes=MAX_EVIDENCE_BYTES)
    experiment_runtime = _experiment_runtime()
    try:
        plan, _ = experiment_runtime.load_and_verify_plan(plan_path)
    except experiment_runtime.ExperimentError as exc:
        raise StateError(f"experiment_plan 语义无效：{exc}") from exc
    if plan.get("schema_version") != "1.1" or plan.get("tool") != "vibio-seo-experiment":
        raise StateError("experiment_plan 不是受支持的 1.1 正式计划")
    if plan.get("design") not in {"randomized_page_holdout", "matched_page_did"}:
        raise StateError("experiment_plan.design 无效")
    source_hashes = result.get("source_hashes")
    if not isinstance(source_hashes, Mapping):
        raise StateError("experiment_result 缺少 source_hashes")
    expected_file_hash = _required_sha256(
        source_hashes.get("plan_file_sha256"),
        "experiment_result.source_hashes.plan_file_sha256",
    )
    if _file_sha256(plan_path) != expected_file_hash:
        raise StateError("experiment_plan 文件哈希与 experiment_result 不匹配")
    if plan.get("experiment_id") != result.get("experiment_id"):
        raise StateError("experiment_plan 与 experiment_result 的 experiment_id 不匹配")
    if plan.get("plan_hash") != result.get("plan_hash"):
        raise StateError("experiment_plan 与 experiment_result 的 plan_hash 不匹配")
    unhashed = dict(plan)
    supplied_plan_hash = unhashed.pop("plan_hash", None)
    if supplied_plan_hash != _record_digest(unhashed):
        raise StateError("experiment_plan 的 plan_hash 复算失败")
    return plan, plan_relative


def _finite_number(value: Any, field: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise StateError(f"字段 {field} 必须是有限数")
    return float(value)


def _validate_experiment_inputs(
    project_root: str | os.PathLike[str], record: Mapping[str, Any]
) -> dict[str, Path | None]:
    inputs = record.get("experiment_inputs")
    if not isinstance(inputs, Mapping):
        raise StateError("强 verdict 必须提供结构化 experiment_inputs")
    allowed = {"panel", "artifact_report", "measurement_metadata"}
    unexpected = sorted(set(inputs) - allowed)
    if unexpected:
        raise StateError("experiment_inputs 包含未知字段：" + "、".join(unexpected))

    resolved: dict[str, Path | None] = {}
    for name in ("panel", "artifact_report", "measurement_metadata"):
        entry = inputs.get(name)
        if entry is None:
            if name != "measurement_metadata":
                raise StateError(f"experiment_inputs 缺少必需的 {name}")
            resolved[name] = None
            continue
        if not isinstance(entry, Mapping):
            raise StateError(f"experiment_inputs.{name} 必须是包含 path/sha256 的对象")
        if set(entry) != {"path", "sha256"}:
            raise StateError(f"experiment_inputs.{name} 必须且只能包含 path/sha256")
        path, _ = _project_evidence_file(
            project_root, entry.get("path"), f"experiment_inputs.{name}.path"
        )
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise StateError(f"无法读取 experiment_inputs.{name} 大小：{exc}") from exc
        if size > MAX_EVIDENCE_BYTES:
            raise StateError(
                f"experiment_inputs.{name} 超过 {MAX_EVIDENCE_BYTES} 字节：{path}"
            )
        expected_hash = _required_sha256(
            entry.get("sha256"), f"experiment_inputs.{name}.sha256"
        )
        if _file_sha256(path) != expected_hash:
            raise StateError(f"experiment_inputs.{name} 文件摘要不匹配")
        resolved[name] = path
    return resolved


def _replay_experiment_result(
    project_root: str | os.PathLike[str],
    record: Mapping[str, Any],
    submitted: Mapping[str, Any],
) -> None:
    inputs = _validate_experiment_inputs(project_root, record)
    plan_path, _ = _project_evidence_file(
        project_root, record.get("experiment_plan"), "experiment_plan"
    )
    experiment_runtime = _experiment_runtime()
    try:
        replayed = experiment_runtime.analyze_experiment(
            plan_path,
            inputs["panel"],
            inputs["artifact_report"],
            inputs["measurement_metadata"],
        )
    except (experiment_runtime.ExperimentError, OSError, UnicodeError) as exc:
        raise StateError(f"实验原始输入重放失败：{exc}") from exc
    replayed_canonical = dict(replayed)
    submitted_canonical = dict(submitted)
    replayed_canonical.pop("analyzed_at", None)
    submitted_canonical.pop("analyzed_at", None)
    replayed_json = _canonical_json(replayed_canonical)
    submitted_json = _canonical_json(submitted_canonical)
    if replayed_json != submitted_json:
        differing = sorted(
            key
            for key in set(replayed_canonical) | set(submitted_canonical)
            if (
                key not in replayed_canonical
                or key not in submitted_canonical
                or _canonical_json({"value": replayed_canonical[key]})
                != _canonical_json({"value": submitted_canonical[key]})
            )
        )
        raise StateError(
            "实验重放结果与提交报告不匹配：" + "、".join(differing)
        )


def _validate_formal_experiment_result(
    result: Mapping[str, Any], plan: Mapping[str, Any]
) -> None:
    required = {
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
    }
    missing = sorted(required - set(result))
    if missing:
        raise StateError("experiment_result 缺少正式报告字段：" + "、".join(missing))
    unexpected = sorted(set(result) - required)
    if unexpected:
        raise StateError("experiment_result 包含额外正式报告字段：" + "、".join(unexpected))
    if result.get("schema_version") != "1.1":
        raise StateError("experiment_result.schema_version 必须为 1.1")
    if result.get("design") != plan.get("design"):
        raise StateError("experiment_result.design 与冻结计划不匹配")
    _nonempty_text(result.get("analyzed_at"), "experiment_result.analyzed_at", max_length=64)

    source_hashes = result.get("source_hashes")
    if not isinstance(source_hashes, Mapping):
        raise StateError("experiment_result.source_hashes 必须是对象")
    for field in (
        "plan_file_sha256",
        "panel_sha256",
        "artifact_report_sha256",
        "spec_sha256",
        "baseline_sha256",
        "baseline_units_sha256",
    ):
        _required_sha256(source_hashes.get(field), f"experiment_result.source_hashes.{field}")
    frozen = plan.get("frozen_inputs")
    if not isinstance(frozen, Mapping):
        raise StateError("experiment_plan 缺少 frozen_inputs")
    for field, frozen_value in frozen.items():
        if field == "baseline_units":
            continue
        if source_hashes.get(field) != frozen_value:
            raise StateError(f"experiment_result.source_hashes.{field} 与冻结计划不匹配")

    prereg = plan.get("preregistration")
    if not isinstance(prereg, Mapping):
        raise StateError("experiment_plan 缺少 preregistration")
    windows = result.get("windows")
    if not isinstance(windows, Mapping) or windows.get("baseline") != prereg.get(
        "baseline_window"
    ) or windows.get("observation") != prereg.get("observation_window"):
        raise StateError("experiment_result.windows 与冻结计划不匹配")

    quality = result.get("data_quality")
    coverage = quality.get("coverage") if isinstance(quality, Mapping) else None
    if (
        not isinstance(coverage, Mapping)
        or coverage.get("complete") is not True
        or coverage.get("frozen_baseline_bound") is not True
    ):
        raise StateError("强 verdict 要求完整日期覆盖并绑定冻结基线")
    guardrails = result.get("guardrails")
    guardrail_rows = guardrails.get("results") if isinstance(guardrails, Mapping) else None
    if (
        not isinstance(guardrails, Mapping)
        or guardrails.get("passed") is not True
        or not isinstance(guardrail_rows, list)
        or any(not isinstance(item, Mapping) or item.get("passed") is not True for item in guardrail_rows)
    ):
        raise StateError("强 verdict 要求全部 guardrail 通过")
    planned_guardrails = prereg.get("guardrails")
    if not isinstance(planned_guardrails, list) or len(guardrail_rows) != len(
        planned_guardrails
    ):
        raise StateError("experiment_result.guardrails 未完整绑定冻结计划")
    for planned, observed in zip(planned_guardrails, guardrail_rows):
        if not isinstance(planned, Mapping) or not isinstance(observed, Mapping):
            raise StateError("experiment_result.guardrails 结构无效")
        if any(
            observed.get(field) != planned.get(field)
            for field in ("metric", "direction", "threshold")
        ):
            raise StateError("experiment_result.guardrails 与冻结计划不匹配")
    methodology = result.get("methodology")
    if (
        not isinstance(methodology, Mapping)
        or methodology.get("causal_claim_automated") is not False
        or methodology.get("power_calculated") is not False
    ):
        raise StateError("experiment_result.methodology 边界无效")

    primary_name = _nonempty_text(
        prereg.get("primary_metric"), "experiment_plan.preregistration.primary_metric"
    )
    direction = prereg.get("primary_metric_direction")
    if direction not in {"increase", "decrease"}:
        raise StateError("experiment_plan.primary_metric_direction 无效")
    primary = result.get("primary_metric")
    metrics = result.get("metrics")
    if (
        not isinstance(primary, Mapping)
        or primary.get("metric") != primary_name
        or not isinstance(metrics, Mapping)
        or metrics.get(primary_name) != primary
    ):
        raise StateError("experiment_result.primary_metric 与指标映射不一致")
    did = _finite_number(
        primary.get("difference_in_differences"),
        "experiment_result.primary_metric.difference_in_differences",
    )
    interval = primary.get("confidence_interval")
    if not isinstance(interval, Mapping):
        raise StateError("experiment_result.primary_metric 缺少 confidence_interval")
    lower = _finite_number(interval.get("lower"), "confidence_interval.lower")
    upper = _finite_number(interval.get("upper"), "confidence_interval.upper")
    if lower > upper:
        raise StateError("experiment_result 的置信区间上下界颠倒")
    point_supports = did > 0 if direction == "increase" else did < 0
    interval_supports = lower > 0 if direction == "increase" else upper < 0
    details = result.get("eligibility_details")
    if (
        not isinstance(details, Mapping)
        or details.get("point_estimate_supports_direction") is not point_supports
        or details.get("confidence_interval_supports_direction") is not interval_supports
        or details.get("incremental_positive_allowed")
        is not (point_supports and interval_supports)
        or details.get("primary_metric_direction") != direction
        or details.get("reasons") != []
    ):
        raise StateError("experiment_result 的方向、区间或资格字段与数值矛盾")


def _detectability_power(mde_in_metric_units: float, standard_error: float, alpha: float) -> float:
    if standard_error < 0:
        raise StateError("detectability standard_error 不得为负")
    if not 0 < alpha < 1:
        raise StateError("detectability alpha 必须在 0 和 1 之间")
    if mde_in_metric_units <= 0:
        raise StateError("detectability MDE 必须为正数")
    if standard_error == 0:
        return 1.0
    normal = statistics.NormalDist()
    critical = normal.inv_cdf(1 - alpha / 2)
    noncentrality = mde_in_metric_units / standard_error
    power = normal.cdf(-critical - noncentrality) + 1 - normal.cdf(
        critical - noncentrality
    )
    return round(min(1.0, max(0.0, power)), 12)


def _build_detectability_evidence(
    result: Mapping[str, Any],
    plan: Mapping[str, Any],
    experiment_result_sha256: str,
) -> dict[str, Any]:
    prereg = plan.get("preregistration")
    if not isinstance(prereg, Mapping):
        raise StateError("experiment_plan 缺少 preregistration")
    planned_mde = prereg.get("minimum_detectable_effect")
    if not isinstance(planned_mde, Mapping):
        raise StateError("experiment_plan 缺少结构化 MDE")
    alpha = _finite_number(prereg.get("alpha"), "detectability.alpha")
    primary = result.get("primary_metric")
    if not isinstance(primary, Mapping):
        raise StateError("experiment_result 缺少 primary_metric")
    standard_error = _finite_number(
        primary.get("standard_error"), "detectability.standard_error"
    )
    detectability = primary.get("detectability")
    if not isinstance(detectability, Mapping):
        raise StateError("experiment_result.primary_metric 缺少 detectability")
    mde_in_metric_units = _finite_number(
        detectability.get("mde_in_metric_units"),
        "detectability.mde_in_metric_units",
    )
    interval = primary.get("confidence_interval")
    if not isinstance(interval, Mapping):
        raise StateError("experiment_result.primary_metric 缺少 confidence_interval")
    lower = _finite_number(interval.get("lower"), "detectability.confidence_interval.lower")
    upper = _finite_number(interval.get("upper"), "detectability.confidence_interval.upper")
    if lower > upper:
        raise StateError("detectability confidence_interval 上下界颠倒")
    power = _detectability_power(mde_in_metric_units, standard_error, alpha)
    source_hashes = result.get("source_hashes")
    if not isinstance(source_hashes, Mapping):
        raise StateError("experiment_result 缺少 source_hashes")
    input_hashes = {
        "plan_file_sha256": _required_sha256(
            source_hashes.get("plan_file_sha256"), "source_hashes.plan_file_sha256"
        ),
        "panel_sha256": _required_sha256(
            source_hashes.get("panel_sha256"), "source_hashes.panel_sha256"
        ),
        "artifact_report_sha256": _required_sha256(
            source_hashes.get("artifact_report_sha256"),
            "source_hashes.artifact_report_sha256",
        ),
        "measurement_metadata_sha256": source_hashes.get(
            "measurement_metadata_sha256"
        ),
        "experiment_result_sha256": _required_sha256(
            experiment_result_sha256, "experiment_result_sha256"
        ),
    }
    metadata_hash = input_hashes["measurement_metadata_sha256"]
    if metadata_hash is not None:
        _required_sha256(metadata_hash, "source_hashes.measurement_metadata_sha256")
    supported = power >= 0.8 and lower <= 0 <= upper
    return {
        "schema_version": DETECTABILITY_SCHEMA_VERSION,
        "tool": DETECTABILITY_TOOL,
        "version": DETECTABILITY_VERSION,
        "method": DETECTABILITY_METHOD,
        "experiment_id": result.get("experiment_id"),
        "plan_hash": result.get("plan_hash"),
        "input_hashes": input_hashes,
        "alpha": alpha,
        "minimum_detectable_effect": dict(planned_mde),
        "standard_error": standard_error,
        "mde_in_metric_units": mde_in_metric_units,
        "confidence_interval": {"lower": lower, "upper": upper},
        "power": power,
        "no_detectable_change_supported": supported,
    }


def create_detectability_evidence(
    project_root: str | os.PathLike[str],
    *,
    experiment_plan: str,
    experiment_result: str,
    out: str,
) -> tuple[dict[str, Any], Path]:
    result_path, _ = _project_evidence_file(
        project_root, experiment_result, "experiment_result"
    )
    result = _read_json_file(result_path, max_bytes=MAX_EVIDENCE_BYTES)
    plan, _ = _verify_experiment_plan(
        project_root, {"experiment_plan": experiment_plan}, result
    )
    experiment_runtime = _experiment_runtime()
    try:
        experiment_runtime.validate_experiment_report(result, plan)
    except experiment_runtime.ExperimentError as exc:
        raise StateError(f"experiment_result 语义无效：{exc}") from exc
    payload = _build_detectability_evidence(
        result, plan, _file_sha256(result_path)
    )
    output = _resolve_output(project_root, out)
    output.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(
        output,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return payload, output


def _validate_detectability_evidence(
    project_root: str | os.PathLike[str],
    record: Mapping[str, Any],
    result: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> None:
    evidence_path, _ = _project_evidence_file(
        project_root, record.get("detectability_evidence"), "detectability_evidence"
    )
    expected_hash = _required_sha256(
        record.get("detectability_evidence_sha256"), "detectability_evidence_sha256"
    )
    if _file_sha256(evidence_path) != expected_hash:
        raise StateError("detectability_evidence_sha256 与证据文件不匹配")
    evidence = _read_json_file(evidence_path, max_bytes=MAX_EVIDENCE_BYTES)
    expected = _build_detectability_evidence(
        result,
        plan,
        _required_sha256(
            record.get("experiment_result_sha256"), "experiment_result_sha256"
        ),
    )
    if evidence != expected:
        differing = sorted(
            key
            for key in set(evidence) | set(expected)
            if evidence.get(key) != expected.get(key)
        )
        raise StateError(
            "detectability_evidence 与确定性重算不匹配：" + "、".join(differing)
        )
    if evidence.get("power", 0) < 0.8:
        raise StateError("no-detectable-change 需要确定性重算 power>=0.8")
    if evidence.get("no_detectable_change_supported") is not True:
        raise StateError("确定性 detectability 重算未支持 no-detectable-change")
    prereg = plan.get("preregistration")
    planned_mde = prereg.get("minimum_detectable_effect") if isinstance(prereg, Mapping) else None
    if record.get("preregistered_mde") != planned_mde:
        raise StateError("复盘 preregistered_mde 必须与冻结计划的结构化 MDE 严格一致")
    primary = result.get("primary_metric")
    interval = primary.get("confidence_interval") if isinstance(primary, Mapping) else None
    lower = _finite_number(
        interval.get("lower") if isinstance(interval, Mapping) else None,
        "detectability confidence_interval.lower",
    )
    upper = _finite_number(
        interval.get("upper") if isinstance(interval, Mapping) else None,
        "detectability confidence_interval.upper",
    )
    if not lower <= 0 <= upper:
        raise StateError("no-detectable-change 要求 experiment_result 的置信区间包含零")


def _validate_experiment_result(
    project_root: str | os.PathLike[str], record: Mapping[str, Any], verdict: str
) -> str:
    result_path, relative = _project_evidence_file(
        project_root, record.get("experiment_result"), "experiment_result"
    )
    result = _read_json_file(result_path, max_bytes=MAX_EVIDENCE_BYTES)
    expected_result_hash = _required_sha256(
        record.get("experiment_result_sha256"), "experiment_result_sha256"
    )
    if _file_sha256(result_path) != expected_result_hash:
        raise StateError("experiment_result_sha256 与结果文件不匹配")
    if result.get("tool") != "vibio-seo-experiment":
        raise StateError("experiment_result.tool 必须为 vibio-seo-experiment")
    if not isinstance(result.get("schema_version"), str):
        raise StateError("experiment_result 缺少 schema_version")
    experiment_id = _identifier(record.get("experiment_id"), "experiment_id")
    if result.get("experiment_id") != experiment_id:
        raise StateError("experiment_result 的 experiment_id 与复盘记录不匹配")
    plan_hash = result.get("plan_hash")
    if not isinstance(plan_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", plan_hash):
        raise StateError("experiment_result 缺少有效 plan_hash")
    if result.get("eligibility") != "eligible_incremental":
        raise StateError("强 verdict 要求 experiment_result.eligibility=eligible_incremental")
    artifact = result.get("artifact_verification")
    if (
        not isinstance(artifact, Mapping)
        or artifact.get("passed") is not True
        or artifact.get("status") != "passed"
        or artifact.get("experiment_id") != experiment_id
        or artifact.get("plan_hash") != plan_hash
        or not _has_evidence(artifact.get("evidence"))
    ):
        raise StateError("强 verdict 要求 experiment_result 的产物验证通过")
    quality = result.get("data_quality")
    if (
        not isinstance(quality, Mapping)
        or quality.get("passed") is not True
        or quality.get("issues") != []
    ):
        raise StateError("强 verdict 要求 experiment_result 的数据质量通过")
    measurement = result.get("measurement_contract")
    if (
        not isinstance(measurement, Mapping)
        or measurement.get("status") != "complete"
        or measurement.get("complete") is not True
        or measurement.get("issues") != []
    ):
        raise StateError("强 verdict 要求 experiment_result 的 measurement_contract 完整")
    details = result.get("eligibility_details")
    if not isinstance(details, Mapping) or details.get("eligible_incremental") is not True:
        raise StateError("experiment_result 缺少 eligibility_details")
    plan, _ = _verify_experiment_plan(project_root, record, result)
    experiment_runtime = _experiment_runtime()
    try:
        experiment_runtime.validate_experiment_report(result, plan)
    except experiment_runtime.ExperimentError as exc:
        raise StateError(f"experiment_result 语义无效：{exc}") from exc
    _replay_experiment_result(project_root, record, result)
    _validate_formal_experiment_result(result, plan)
    if verdict == "incremental-positive":
        if (
            details.get("incremental_positive_allowed") is not True
            or details.get("point_estimate_supports_direction") is not True
            or details.get("confidence_interval_supports_direction") is not True
        ):
            raise StateError("incremental-positive 被 experiment_result 的效果方向或区间门禁阻止")
    else:
        _validate_detectability_evidence(project_root, record, result, plan)
    integrity = record.get("measurement_integrity")
    if not isinstance(integrity, Mapping) or integrity.get("evidence") != relative:
        raise StateError("measurement_integrity.evidence 必须与 experiment_result 引用同一文件")
    return relative


def _validate_review_gate(
    record: Mapping[str, Any],
    current_status: str,
    project_root: str | os.PathLike[str],
    change_events: Sequence[Mapping[str, Any]],
) -> str:
    verdict = _nonempty_text(record.get("verdict"), "verdict", max_length=64)
    if verdict not in VERDICTS:
        raise StateError(f"复盘 verdict 无效：{verdict}")
    if verdict == "incremental-positive":
        _identifier(record.get("experiment_id"), "experiment_id")
        _nonempty_text(record.get("counterfactual_method"), "counterfactual_method")
    if verdict == "no-detectable-change":
        if not isinstance(record.get("preregistered_mde"), Mapping):
            raise StateError(
                "no-detectable-change 必须提供与冻结计划一致的结构化 preregistered_mde"
            )
        if not _has_evidence(record.get("detectability_evidence")):
            raise StateError("no-detectable-change 必须提供 detectability_evidence")
        _identifier(record.get("experiment_id"), "experiment_id")
    if verdict in {"incremental-positive", "no-detectable-change"}:
        integrity = record.get("measurement_integrity")
        if not isinstance(integrity, Mapping):
            raise StateError(f"{verdict} 必须提供 measurement_integrity")
        if integrity.get("status") != "complete":
            raise StateError(
                f"{verdict} 要求 measurement_integrity.status=complete"
            )
        issues = integrity.get("issues")
        if not isinstance(issues, list) or issues:
            raise StateError(f"{verdict} 要求 measurement_integrity.issues 为空数组")
        if not _has_evidence(integrity.get("evidence")):
            raise StateError(f"{verdict} 必须提供 measurement_integrity.evidence")
        if not change_events or change_events[0].get("status") != "planned":
            raise StateError("强 verdict 找不到 change 的 planned 记录")
        registration = _validate_experiment_registration(
            project_root, change_events[0]
        )
        if registration["experiment_id"] != record.get("experiment_id"):
            raise StateError("复盘 experiment_id 与 planned 注册不匹配")
        _, review_plan_relative = _project_evidence_file(
            project_root, record.get("experiment_plan"), "experiment_plan"
        )
        if review_plan_relative != registration["plan"]:
            raise StateError("复盘 experiment_plan 与 planned 注册不匹配")
        _validate_experiment_result(project_root, record, verdict)
    passed, evidence = _artifact_result(record)
    if verdict == "implementation-failed":
        if current_status not in {"implemented", "implementation_failed"}:
            raise StateError(
                f"implementation-failed 只能在 implemented/implementation_failed 状态记录，当前为 {current_status}"
            )
        if passed is not False or not _has_evidence(evidence):
            raise StateError("implementation-failed 只能用于 passed=false 的产物验证，且必须有证据")
        return "implementation_failed"
    if current_status != "outcome_pending":
        raise StateError(
            f"复盘前 change 必须处于 outcome_pending，当前为 {current_status}"
        )
    return "reviewed"


def _apply_reviews(
    records: Sequence[Mapping[str, Any]],
    states: dict[str, str],
    events: Mapping[str, Sequence[Mapping[str, Any]]],
    project_root: str | os.PathLike[str],
) -> tuple[dict[str, str], dict[str, Mapping[str, Any]]]:
    effective = dict(states)
    reviews_by_change: dict[str, Mapping[str, Any]] = {}
    seen_review_ids: set[str] = set()
    for record in records:
        review_id = _identifier(record.get("review_id"), "review_id")
        if review_id in seen_review_ids:
            raise StateError(f"review_id 重复：{review_id}")
        seen_review_ids.add(review_id)
        change_id = _identifier(record.get("change_id"), "change_id")
        if change_id not in effective:
            raise StateError(f"复盘 {review_id} 引用了不存在的 change：{change_id}")
        if change_id in reviews_by_change:
            raise StateError(f"change {change_id} 已有复盘记录，不得静默覆盖")
        effective[change_id] = _validate_review_gate(
            record, effective[change_id], project_root, events.get(change_id, [])
        )
        reviews_by_change[change_id] = record
    return effective, reviews_by_change


def validate_state(project_root: str | os.PathLike[str]) -> dict[str, Any]:
    state_dir, project_path, project_digest_path, changes_path, reviews_path = _state_paths(
        project_root
    )
    del state_dir
    project = _read_json_file(project_path)
    _validate_project(project)
    project_sha256 = _project_digest(project)
    try:
        anchored_sha256 = project_digest_path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise StateError(f"无法读取 project.sha256：{exc}") from exc
    if anchored_sha256 != project_sha256:
        raise StateError("project.json 与初始化时的 project.sha256 不匹配")
    changes = _read_chain(
        changes_path, "change", project_sha256=project_sha256
    )
    reviews = _read_chain(
        reviews_path, "review", project_sha256=project_sha256
    )
    change_hashes = {GENESIS_HASH, *(item["record_hash"] for item in changes)}
    review_hashes = {GENESIS_HASH, *(item["record_hash"] for item in reviews)}
    for record in changes:
        if record.get("reviews_head") not in review_hashes:
            raise StateError("change 记录绑定了不存在的 reviews_head")
    for record in reviews:
        if record.get("changes_head") not in change_hashes:
            raise StateError("review 记录绑定了不存在的 changes_head")
    change_states, events = _state_from_changes(changes)
    for change_records in events.values():
        registration = change_records[0].get("experiment_registration")
        if registration is not None:
            _validate_experiment_registration(project_root, change_records[0])
    effective_states, reviews_by_change = _apply_reviews(
        reviews, change_states, events, project_root
    )
    return {
        "valid": True,
        "project": project,
        "changes": changes,
        "reviews": reviews,
        "change_states": effective_states,
        "change_events": events,
        "reviews_by_change": reviews_by_change,
        "integrity": {
            "changes_records": len(changes),
            "reviews_records": len(reviews),
            "project_sha256": project_sha256,
            "changes_head": changes[-1]["record_hash"] if changes else GENESIS_HASH,
            "reviews_head": reviews[-1]["record_hash"] if reviews else GENESIS_HASH,
        },
    }


def _prepare_record(
    kind: str,
    payload: Mapping[str, Any],
    previous: Sequence[Mapping[str, Any]],
    *,
    project_sha256: str,
    other_chain_head: str,
) -> dict[str, Any]:
    conflicting = sorted(RESERVED_FIELDS.intersection(payload))
    if conflicting:
        raise StateError(f"输入不得设置保留字段：{', '.join(conflicting)}")
    _scan_sensitive(dict(payload))
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": kind,
        "sequence": len(previous) + 1,
        "recorded_at": _now_utc(),
        "previous_hash": previous[-1]["record_hash"] if previous else GENESIS_HASH,
        "project_sha256": project_sha256,
        "reviews_head" if kind == "change" else "changes_head": other_chain_head,
        **dict(payload),
    }
    record["record_hash"] = _record_digest(record)
    return record


def append_change(project_root: str | os.PathLike[str], payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise StateError("change 输入必须是 JSON 对象")
    state_dir, _, _, changes_path, _ = _state_paths(project_root)
    with _append_lock(state_dir):
        report = validate_state(project_root)
        change_id, status = _validate_change_payload(payload)
        if status == "planned" and payload.get("experiment_registration") is not None:
            _validate_experiment_registration(project_root, payload)
        current = report["change_states"].get(change_id)
        if current is None:
            if status != "planned":
                raise StateError(f"change {change_id} 的首条状态必须是 planned")
        elif status not in ALLOWED_TRANSITIONS[current]:
            raise StateError(f"change {change_id} 存在非法状态转移：{current} -> {status}")
        record = _prepare_record(
            "change",
            payload,
            report["changes"],
            project_sha256=report["integrity"]["project_sha256"],
            other_chain_head=report["integrity"]["reviews_head"],
        )
        _append_line(changes_path, record)
        return record


def append_review(project_root: str | os.PathLike[str], payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise StateError("review 输入必须是 JSON 对象")
    normalized = dict(payload)
    change_id = _identifier(normalized.get("change_id"), "change_id")
    state_dir, _, _, _, reviews_path = _state_paths(project_root)
    with _append_lock(state_dir):
        report = validate_state(project_root)
        if change_id not in report["change_states"]:
            raise StateError(f"复盘引用了不存在的 change：{change_id}")
        if change_id in report["reviews_by_change"]:
            raise StateError(f"change {change_id} 已有复盘记录")
        if "review_id" not in normalized:
            normalized["review_id"] = f"review-{change_id}-{len(report['reviews']) + 1}"
        _identifier(normalized.get("review_id"), "review_id")
        if any(item.get("review_id") == normalized["review_id"] for item in report["reviews"]):
            raise StateError(f"review_id 重复：{normalized['review_id']}")
        _validate_review_gate(
            normalized,
            report["change_states"][change_id],
            project_root,
            report["change_events"][change_id],
        )
        record = _prepare_record(
            "review",
            normalized,
            report["reviews"],
            project_sha256=report["integrity"]["project_sha256"],
            other_chain_head=report["integrity"]["changes_head"],
        )
        _append_line(reviews_path, record)
        return record


def _markdown_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_markdown(project_root: str | os.PathLike[str]) -> str:
    report = validate_state(project_root)
    project = report["project"]
    lines = [
        f"# {_markdown_cell(project['project_id'])} - SEO 结构化状态",
        "",
        "> 本文档由 `.vibio/state/` 结构化真源派生；不得反向解析或手工当作状态真源。",
        "",
        "## 项目",
        "",
        f"- 站点：{_markdown_cell(project['site_url'])}",
        f"- 市场：{_markdown_cell(project['market'])}",
        f"- 语言：{_markdown_cell(project['language'])}",
        f"- 初始化：{_markdown_cell(project['created_at'])}",
        "",
        "## 变更概览",
        "",
        "| Change ID | 当前状态 | 摘要 | 事件数 | 最后记录 |",
        "|---|---|---|---:|---|",
    ]
    if not report["change_states"]:
        lines.append("| - | - | 暂无变更 | 0 | - |")
    for change_id, state in report["change_states"].items():
        events = report["change_events"][change_id]
        summary = events[0].get("summary", events[-1].get("summary", ""))
        review = report["reviews_by_change"].get(change_id)
        last_record = review or events[-1]
        lines.append(
            f"| {_markdown_cell(change_id)} | `{_markdown_cell(state)}` | "
            f"{_markdown_cell(summary)} | {len(events)} | {_markdown_cell(last_record['recorded_at'])} |"
        )
    lines.extend(
        [
            "",
            "## 追加历史",
            "",
            "| # | Change ID | 状态 | 记录时间 | 记录哈希 |",
            "|---:|---|---|---|---|",
        ]
    )
    if not report["changes"]:
        lines.append("| - | - | - | - | - |")
    for record in report["changes"]:
        lines.append(
            f"| {record['sequence']} | {_markdown_cell(record['change_id'])} | "
            f"`{_markdown_cell(record['status'])}` | {_markdown_cell(record['recorded_at'])} | "
            f"`{record['record_hash'][:12]}` |"
        )
    lines.extend(
        [
            "",
            "## 复盘",
            "",
            "| Review ID | Change ID | Verdict | 证据方法 | 记录时间 |",
            "|---|---|---|---|---|",
        ]
    )
    if not report["reviews"]:
        lines.append("| - | - | 尚未复盘 | - | - |")
    for record in report["reviews"]:
        method = record.get("counterfactual_method", record.get("method", ""))
        lines.append(
            f"| {_markdown_cell(record['review_id'])} | {_markdown_cell(record['change_id'])} | "
            f"`{_markdown_cell(record['verdict'])}` | {_markdown_cell(method)} | "
            f"{_markdown_cell(record['recorded_at'])} |"
        )
    integrity = report["integrity"]
    lines.extend(
        [
            "",
            "## 完整性",
            "",
            f"- 校验：通过",
            f"- 变更链：{integrity['changes_records']} 条，head `{integrity['changes_head']}`",
            f"- 复盘链：{integrity['reviews_records']} 条，head `{integrity['reviews_head']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_output(project_root: str | os.PathLike[str], out: str | os.PathLike[str]) -> Path:
    root = _resolve_project_root(project_root)
    candidate = Path(out).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=False)
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise StateError("--out 必须位于项目根目录内") from exc
    if relative.parts[:2] == STATE_DIR_PARTS:
        raise StateError("--out 不得覆盖 `.vibio/state/` 结构化真源")
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        _reject_symlink(current, "输出目录")
    _reject_symlink(candidate, "输出文件")
    return resolved


def _write_rendered(project_root: str | os.PathLike[str], out: str | os.PathLike[str], content: str) -> Path:
    path = _resolve_output(project_root, out)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, content)
    return path


def build_parser() -> ChineseArgumentParser:
    parser = ChineseArgumentParser(
        description="管理可验证、追加式的 Vibio SEO `.vibio` 结构化状态。"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="命令")

    init_parser = subparsers.add_parser("init", help="初始化项目状态真源")
    init_parser.add_argument(
        "--project-root", required=True, metavar="项目根目录", help="已存在的项目根目录"
    )
    init_parser.add_argument("--project-id", required=True, metavar="项目ID", help="稳定项目 ID")
    init_parser.add_argument("--site-url", required=True, metavar="站点URL", help="站点绝对 URL")
    init_parser.add_argument("--market", required=True, metavar="市场", help="目标市场")
    init_parser.add_argument("--language", required=True, metavar="语言", help="目标语言")

    for command, help_text in (
        ("append-change", "追加变更状态事件"),
        ("append-review", "追加变更复盘结论"),
    ):
        child = subparsers.add_parser(command, help=help_text)
        child.add_argument("--project-root", required=True, metavar="项目根目录", help="项目根目录")
        child.add_argument("--input", required=True, metavar="JSON文件", help="UTF-8 JSON 输入文件")

    validate_parser = subparsers.add_parser("validate", help="验证 schema、哈希链和状态语义")
    validate_parser.add_argument(
        "--project-root", required=True, metavar="项目根目录", help="项目根目录"
    )

    render_parser = subparsers.add_parser("render", help="从结构化真源派生 Markdown")
    render_parser.add_argument("--project-root", required=True, metavar="项目根目录", help="项目根目录")
    render_parser.add_argument(
        "--out", metavar="Markdown路径", help="项目内的 Markdown 输出路径；省略时输出到标准输出"
    )

    detectability_parser = subparsers.add_parser(
        "detectability", help="从冻结计划与正式实验报告确定性生成功效证据"
    )
    detectability_parser.add_argument(
        "--project-root", required=True, metavar="项目根目录", help="项目根目录"
    )
    detectability_parser.add_argument(
        "--experiment-plan", required=True, metavar="计划路径", help="项目内冻结 plan.json"
    )
    detectability_parser.add_argument(
        "--experiment-result", required=True, metavar="报告路径", help="项目内正式 result.json"
    )
    detectability_parser.add_argument(
        "--out", required=True, metavar="证据路径", help="项目内 detectability JSON 输出路径"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            project = initialize_project(
                args.project_root,
                project_id=args.project_id,
                site_url=args.site_url,
                market=args.market,
                language=args.language,
            )
            print(f"已初始化项目状态：{project['project_id']}")
        elif args.command == "append-change":
            record = append_change(args.project_root, load_input(args.input))
            print(f"已追加 change {record['change_id']}：{record['status']}")
        elif args.command == "append-review":
            record = append_review(args.project_root, load_input(args.input))
            print(f"已追加 review {record['review_id']}：{record['verdict']}")
        elif args.command == "validate":
            report = validate_state(args.project_root)
            integrity = report["integrity"]
            print(
                f"验证通过：{integrity['changes_records']} 条变更记录，"
                f"{integrity['reviews_records']} 条复盘记录"
            )
        elif args.command == "render":
            markdown = render_markdown(args.project_root)
            if args.out:
                path = _write_rendered(args.project_root, args.out, markdown)
                print(f"已派生 Markdown：{path}")
            else:
                sys.stdout.write(markdown)
        elif args.command == "detectability":
            evidence, path = create_detectability_evidence(
                args.project_root,
                experiment_plan=args.experiment_plan,
                experiment_result=args.experiment_result,
                out=args.out,
            )
            print(
                f"已生成 detectability 证据：{path}；power={evidence['power']}；"
                f"supported={str(evidence['no_detectable_change_supported']).lower()}"
            )
        else:  # pragma: no cover - argparse 已拦截
            raise StateError(f"未知命令：{args.command}")
    except StateError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
