#!/usr/bin/env python3
"""对静态构建、HTTP 源码或浏览器 DOM 执行可复现的 SEO 产物检查。"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Sequence


TOOL_NAME = "vibio-seo-inspect"
TOOL_VERSION = "1.3.0"
SCHEMA_VERSION = "1.3"
USER_AGENT = "VibioSEOInspect/1.0 (+bounded evidence audit)"
MAX_REDIRECTS = 10
DEFAULT_MAX_RESPONSE_BYTES = 20 * 1024 * 1024
EVIDENCE_MODES = {"http_source", "static_build", "browser_dom"}
SKIP_SCHEMES = {"mailto", "tel", "javascript", "data", "blob"}
TRACKING_QUERY_KEYS = {"gclid", "dclid", "fbclid", "msclkid", "yclid", "_gl"}
ROBOTS_DIRECTIVES_WITH_VALUES = {
    "max-image-preview",
    "max-snippet",
    "max-video-preview",
    "unavailable_after",
}
GOOGLE_ROBOT_SCOPES = {"googlebot"}
IMAGE_URL_ATTRIBUTES = (
    "src",
    "data-src",
    "data-lazy-src",
    "data-original",
    "data-flickity-lazyload",
    "data-echo",
)
IMAGE_SRCSET_ATTRIBUTES = (
    "srcset",
    "data-srcset",
    "data-lazy-srcset",
    "data-original-srcset",
)
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
FINDING_LABELS = {
    "critical": "严重阻断",
    "high": "高",
    "medium": "中",
    "low": "低",
    "info": "信息",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalized_url(url: str, *, keep_query: bool = True) -> str:
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    display_hostname = f"[{hostname}]" if ":" in hostname else hostname
    netloc = display_hostname if not port or default_port else f"{display_hostname}:{port}"
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    return urllib.parse.urlunsplit((scheme, netloc, path, parsed.query if keep_query else "", ""))


def canonicalize_crawl_url(url: str) -> str:
    """保留未知业务参数，只移除明确跟踪参数和 fragment。"""
    parsed = urllib.parse.urlsplit(url)
    kept: list[tuple[str, str]] = []
    for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.casefold()
        if lowered.startswith("utm_") or lowered in TRACKING_QUERY_KEYS:
            continue
        kept.append((key, value))
    query = urllib.parse.urlencode(kept, doseq=True)
    return urllib.parse.urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            re.sub(r"/{2,}", "/", parsed.path or "/"),
            query,
            "",
        )
    )


def origin(url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").casefold().rstrip(".")
    port = parsed.port
    default_port = (scheme == "http" and port in (None, 80)) or (
        scheme == "https" and port in (None, 443)
    )
    return scheme, hostname if default_port else f"{hostname}:{port}"


def is_http_url(url: str) -> bool:
    return urllib.parse.urlsplit(url).scheme.lower() in {"http", "https"}


def report_file_reference(path: Path, fallback: str = "input") -> str:
    """返回不会泄漏本机目录、但可与摘要配对的文件名。"""
    return path.name or fallback


def report_source_label(value: str | Path) -> str:
    raw = str(value)
    return canonicalize_crawl_url(raw) if is_http_url(raw) else report_file_reference(Path(raw))


def resolve_url(base: str, raw: str) -> str | None:
    value = raw.strip()
    if not value or value.startswith("#"):
        return None
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme.lower() in SKIP_SCHEMES:
        return None
    resolved = urllib.parse.urljoin(base, value)
    return canonicalize_crawl_url(resolved)


def normalize_response_headers(
    headers: Mapping[str, str | Sequence[str]] | Iterable[tuple[str, str]] | None,
) -> dict[str, list[str]]:
    """保留重复响应头；HTTPMessage.items() 转 dict 会静默丢值。"""
    if headers is None:
        return {}
    items: Iterable[tuple[str, str | Sequence[str]]]
    if isinstance(headers, Mapping):
        items = headers.items()
    else:
        items = headers
    normalized: dict[str, list[str]] = defaultdict(list)
    for raw_key, raw_values in items:
        key = str(raw_key).strip().lower()
        if not key:
            continue
        values = [raw_values] if isinstance(raw_values, str) else raw_values
        for value in values:
            normalized[key].append(str(value).strip())
    return dict(normalized)


def first_header(headers: Mapping[str, Sequence[str]], name: str) -> str:
    values = headers.get(name.casefold(), ())
    return values[0] if values else ""


def directive_tokens(values: Iterable[str]) -> set[str]:
    """返回适用于 Google 网页索引的 robots 指令，识别 user-agent 作用域。"""
    tokens: set[str] = set()
    for value in values:
        scope: str | None = None
        for raw_item in re.split(r"[,;]", value.casefold()):
            item = raw_item.strip()
            if not item:
                continue
            prefix, separator, remainder = item.partition(":")
            prefix = prefix.strip()
            if (
                separator
                and re.fullmatch(r"[a-z0-9_-]+", prefix)
                and prefix not in ROBOTS_DIRECTIVES_WITH_VALUES
            ):
                scope = prefix
                item = remainder.strip()
            token = item.partition(":")[0].strip()
            if token and (scope is None or scope in GOOGLE_ROBOT_SCOPES):
                tokens.add(token)
                if token == "none":
                    tokens.update({"noindex", "nofollow"})
    return tokens


def parse_srcset(value: str) -> list[str]:
    """按 srcset 候选边界提取 URL，并保留 data URL 中的逗号。"""
    candidates: list[str] = []
    position = 0
    length = len(value)
    while position < length:
        while position < length and (value[position].isspace() or value[position] == ","):
            position += 1
        if position >= length:
            break
        start = position
        while position < length and not value[position].isspace():
            position += 1
        candidate = value[start:position]
        if candidate.endswith(","):
            candidate = candidate.rstrip(",")
            if candidate:
                candidates.append(candidate)
            continue
        if candidate:
            candidates.append(candidate)
        parentheses = 0
        while position < length:
            char = value[position]
            if char == "(":
                parentheses += 1
            elif char == ")" and parentheses:
                parentheses -= 1
            elif char == "," and parentheses == 0:
                position += 1
                break
            position += 1
    return candidates


def document_resolution_base(document_url: str, base_hrefs: Iterable[str]) -> str:
    for raw_href in base_hrefs:
        value = raw_href.strip()
        if not value:
            continue
        parsed = urllib.parse.urlsplit(value)
        if parsed.scheme.casefold() in SKIP_SCHEMES:
            continue
        resolved = urllib.parse.urljoin(document_url, value)
        if is_http_url(resolved):
            return canonicalize_crawl_url(resolved)
    return canonicalize_crawl_url(document_url)


def json_ld_types(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, list):
        for item in value:
            found.update(json_ld_types(item))
    elif isinstance(value, dict):
        raw_type = value.get("@type")
        if isinstance(raw_type, str):
            found.add(raw_type)
        elif isinstance(raw_type, list):
            found.update(str(item) for item in raw_type if isinstance(item, str))
        for key, item in value.items():
            if key != "@type":
                found.update(json_ld_types(item))
    return found


class PageHTMLParser(HTMLParser):
    """提取结构化字段；不会把简单字符串命中当作完整 HTML 解析。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_depth = 0
        self.title_chunks: list[str] = []
        self.titles: list[str] = []
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.base_hrefs: list[str] = []
        self.anchors: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.image_resource_elements: list[tuple[str, dict[str, str]]] = []
        self.json_ld_scripts: list[str] = []
        self.script_is_json_ld = False
        self.script_chunks: list[str] = []
        self.html_lang = ""
        self.h1_count = 0
        self.main_count = 0
        self.body_depth = 0
        self.ignored_text_depth = 0
        self.visible_chunks: list[str] = []
        self.non_anchor_link_controls: list[str] = []
        self.anchor_context: dict[str, str] | None = None
        self.anchor_chunks: list[str] = []
        self.picture_depth = 0

    @staticmethod
    def attrs_dict(attrs: Sequence[tuple[str, str | None]]) -> dict[str, str]:
        return {str(key).lower(): value or "" for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = self.attrs_dict(attrs)
        if tag == "picture":
            self.picture_depth += 1
        if tag == "body":
            self.body_depth += 1
        if tag in {"head", "script", "style", "template", "noscript"}:
            self.ignored_text_depth += 1
        if tag != "a" and values.get("role", "").casefold() == "link":
            self.non_anchor_link_controls.append(tag)
        if tag == "html" and not self.html_lang:
            self.html_lang = values.get("lang", "").strip()
        elif tag == "title":
            self.title_depth += 1
            self.title_chunks = []
        elif tag == "meta":
            self.meta.append(values)
        elif tag == "link":
            self.links.append(values)
        elif tag == "base":
            self.base_hrefs.append(values.get("href", ""))
        elif tag == "a":
            self.anchor_context = values
            self.anchor_chunks = []
        elif tag == "img":
            self.images.append(values)
            self.image_resource_elements.append(("img", values))
        elif tag == "source" and self.picture_depth:
            self.image_resource_elements.append(("source", values))
        elif tag == "script":
            content_type = values.get("type", "").lower().split(";", 1)[0].strip()
            self.script_is_json_ld = content_type == "application/ld+json"
            self.script_chunks = []
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "main":
            self.main_count += 1

    def handle_startendtag(self, tag: str, attrs: Sequence[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title_chunks.append(data)
        if self.script_is_json_ld:
            self.script_chunks.append(data)
        if self.anchor_context is not None:
            self.anchor_chunks.append(data)
        if self.body_depth and self.ignored_text_depth == 0:
            self.visible_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title" and self.title_depth:
            self.titles.append(normalize_space("".join(self.title_chunks)))
            self.title_chunks = []
            self.title_depth -= 1
        elif tag == "script" and self.script_is_json_ld:
            self.json_ld_scripts.append("".join(self.script_chunks).strip())
            self.script_chunks = []
            self.script_is_json_ld = False
        elif tag == "a" and self.anchor_context is not None:
            self.anchors.append(
                self.anchor_context
                | {"_text": normalize_space("".join(self.anchor_chunks))}
            )
            self.anchor_context = None
            self.anchor_chunks = []
        if tag in {"head", "script", "style", "template", "noscript"} and self.ignored_text_depth:
            self.ignored_text_depth -= 1
        if tag == "body" and self.body_depth:
            self.body_depth -= 1
        if tag == "picture" and self.picture_depth:
            self.picture_depth -= 1


@dataclass
class Page:
    url: str
    source: str
    evidence_mode: str
    requested_url: str
    status: int | None
    final_url: str
    content_type: str
    response_headers: dict[str, list[str]]
    document_base_url: str
    html_sha256: str
    visible_text_sha256: str
    visible_text_length: int
    redirect_chain: list[dict[str, Any]] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)
    canonicals: list[str] = field(default_factory=list)
    robots: list[str] = field(default_factory=list)
    hreflang: list[dict[str, str]] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    link_edges: list[dict[str, Any]] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    image_resources: list[dict[str, str]] = field(default_factory=list)
    json_ld_types: list[str] = field(default_factory=list)
    json_ld_errors: list[str] = field(default_factory=list)
    html_lang: str = ""
    h1_count: int = 0
    main_count: int = 0
    anchor_count: int = 0
    anchors_without_href: list[str] = field(default_factory=list)
    non_anchor_link_controls: list[str] = field(default_factory=list)
    depth: int | None = None

    @property
    def noindex(self) -> bool:
        return "noindex" in directive_tokens(self.robots)


@dataclass
class Finding:
    code: str
    severity: str
    category: str
    observation: str
    urls: list[str]
    evidence: list[str]
    impact_boundary: str
    verification: str
    confidence: str = "high"

    def key(self) -> tuple[int, str, str]:
        return SEVERITY_ORDER[self.severity], self.code, self.urls[0] if self.urls else ""


@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    status: int | None
    content_type: str
    headers: dict[str, list[str]]
    body: bytes
    error: str = ""
    redirect_chain: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class PublicFetchTarget:
    url: str
    scheme: str
    hostname: str
    port: int
    host_header: str
    request_target: str
    family: int
    sockaddr: tuple[Any, ...]


@dataclass(frozen=True)
class RawHTTPResponse:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes


class ResponseTooLargeError(ValueError):
    """响应声明或实际 body 超出有界抓取预算。"""


@dataclass(frozen=True)
class BrowserProvenance:
    source: str
    schema_version: str
    capture_method: str
    browser: str
    captured_at: str
    javascript_enabled: bool
    documents_verified: int
    provenance_sha256: str


def resolve_public_targets(
    url: str,
    *,
    allowed_origin: tuple[str, str] | None = None,
) -> tuple[PublicFetchTarget, ...]:
    """解析并固定全部公网目标；任一 DNS 结果非公网时整次请求都拒绝。"""
    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise ValueError("HTTP URL 含控制字符")
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("抓取目标必须是带主机名的 HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("抓取目标不得在 URL 中携带用户名或密码")
    try:
        port = parsed.port or (443 if scheme == "https" else 80)
    except ValueError as exc:
        raise ValueError("抓取目标端口无效") from exc
    if allowed_origin is not None and origin(url) != allowed_origin:
        raise ValueError(
            f"抓取目标 {canonicalize_crawl_url(url)} 不属于允许的同源范围"
        )

    hostname = parsed.hostname.casefold().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("抓取目标解析到本机名称，已拒绝")
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
        records = socket.getaddrinfo(
            ascii_hostname,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except (UnicodeError, socket.gaierror, OSError) as exc:
        raise ValueError(f"无法安全解析抓取目标 {hostname}：{exc}") from exc

    candidates: list[tuple[int, tuple[Any, ...]]] = []
    blocked: set[str] = set()
    seen: set[tuple[int, str]] = set()
    for family, socktype, protocol, _canonname, sockaddr in records:
        if family not in {socket.AF_INET, socket.AF_INET6} or socktype != socket.SOCK_STREAM:
            continue
        address_text = str(sockaddr[0])
        try:
            address = ipaddress.ip_address(address_text.split("%", 1)[0])
        except ValueError:
            blocked.add(address_text)
            continue
        key = (family, address.compressed)
        if key in seen:
            continue
        seen.add(key)
        if not address.is_global or "%" in address_text:
            blocked.add(address_text)
            continue
        candidates.append((family, sockaddr))
    if blocked:
        raise ValueError(
            f"抓取目标 {hostname} 的 DNS 结果包含非公网地址，已拒绝"
        )
    if not candidates:
        raise ValueError(f"抓取目标 {hostname} 没有可用的公网 IP 地址")

    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    display_hostname = f"[{ascii_hostname}]" if ":" in ascii_hostname else ascii_hostname
    host_header = display_hostname if default_port else f"{display_hostname}:{port}"
    path = urllib.parse.quote(
        parsed.path or "/",
        safe="/%:@!$&'()*+,;=-._~",
    )
    query = urllib.parse.quote(parsed.query, safe="=&;%:@/?+$,!~*'()[]-._")
    request_target = path + (f"?{query}" if query else "")
    return tuple(
        PublicFetchTarget(
            url=canonicalize_crawl_url(url),
            scheme=scheme,
            hostname=ascii_hostname,
            port=port,
            host_header=host_header,
            request_target=request_target,
            family=family,
            sockaddr=sockaddr,
        )
        for family, sockaddr in candidates
    )


def resolve_public_target(
    url: str,
    *,
    allowed_origin: tuple[str, str] | None = None,
) -> PublicFetchTarget:
    """兼容单目标调用方；网络抓取本身会尝试全部已验证公网地址。"""
    return resolve_public_targets(url, allowed_origin=allowed_origin)[0]


def _read_bounded_response_body(
    response: http.client.HTTPResponse,
    max_response_bytes: int,
) -> bytes:
    content_lengths = response.headers.get_all("Content-Length", failobj=[]) or []
    declared_lengths: set[int] = set()
    for raw_value in content_lengths:
        for value in raw_value.split(","):
            value = value.strip()
            if not value.isdecimal():
                raise ResponseTooLargeError(
                    "响应的 Content-Length 无效，拒绝无界读取"
                )
            declared_lengths.add(int(value))
    if len(declared_lengths) > 1:
        raise ResponseTooLargeError(
            "响应包含互相冲突的 Content-Length，拒绝无界读取"
        )
    if declared_lengths and next(iter(declared_lengths)) > max_response_bytes:
        raise ResponseTooLargeError(
            f"响应声明大小超过单响应上限 {max_response_bytes} 字节"
        )
    body = response.read(max_response_bytes + 1)
    if len(body) > max_response_bytes:
        raise ResponseTooLargeError(
            f"响应实际大小超过单响应上限 {max_response_bytes} 字节"
        )
    return body


def _fetch_once(
    target: PublicFetchTarget,
    timeout: float,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> RawHTTPResponse:
    """连接已验证并固定的 IP，Host 与 TLS SNI 仍使用原始主机名。"""
    raw_socket = socket.socket(target.family, socket.SOCK_STREAM)
    raw_socket.settimeout(timeout)
    connection: socket.socket | ssl.SSLSocket = raw_socket
    response: http.client.HTTPResponse | None = None
    try:
        raw_socket.connect(target.sockaddr)
        if target.scheme == "https":
            connection = ssl.create_default_context().wrap_socket(
                raw_socket,
                server_hostname=target.hostname,
            )
            connection.settimeout(timeout)
        request = (
            f"GET {target.request_target} HTTP/1.1\r\n"
            f"Host: {target.host_header}\r\n"
            f"User-Agent: {USER_AGENT}\r\n"
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        connection.sendall(request)
        response = http.client.HTTPResponse(connection)
        response.begin()
        body = _read_bounded_response_body(response, max_response_bytes)
        return RawHTTPResponse(
            status=response.status,
            headers=tuple(response.getheaders()),
            body=body,
        )
    finally:
        if response is not None:
            response.close()
        connection.close()


def parse_page(
    *,
    html: bytes,
    url: str,
    source: str,
    evidence_mode: str = "static_build",
    requested_url: str | None = None,
    status: int | None = 200,
    final_url: str | None = None,
    content_type: str = "text/html",
    response_headers: (
        Mapping[str, str | Sequence[str]] | Iterable[tuple[str, str]] | None
    ) = None,
    redirect_chain: list[dict[str, Any]] | None = None,
    site_origin: tuple[str, str] | None = None,
) -> Page:
    if evidence_mode not in EVIDENCE_MODES:
        raise ValueError(f"未知 evidence_mode：{evidence_mode}")
    decoded = html.decode("utf-8", errors="replace")
    parser = PageHTMLParser()
    parser.feed(decoded)
    page_origin = site_origin or origin(url)
    resolution_base = document_resolution_base(url, parser.base_hrefs)

    descriptions: list[str] = []
    robots: list[str] = []
    for meta in parser.meta:
        name = meta.get("name", "").lower().strip()
        if name == "description":
            descriptions.append(normalize_space(meta.get("content", "")))
        if name in {"robots", "googlebot"}:
            robots.append(meta.get("content", ""))

    headers = normalize_response_headers(response_headers)
    robots.extend(value for value in headers.get("x-robots-tag", []) if value)

    canonicals: list[str] = []
    hreflang: list[dict[str, str]] = []
    for link in parser.links:
        rel_tokens = {item.lower() for item in link.get("rel", "").split()}
        href = link.get("href", "").strip()
        if "canonical" in rel_tokens and href:
            resolved = resolve_url(resolution_base, href)
            if resolved:
                canonicals.append(normalized_url(resolved))
        language = link.get("hreflang", "").strip()
        if "alternate" in rel_tokens and language and href:
            resolved = resolve_url(resolution_base, href)
            if resolved:
                hreflang.append({"lang": language, "url": normalized_url(resolved)})

    internal_links: set[str] = set()
    external_links: set[str] = set()
    link_edges: list[dict[str, Any]] = []
    for anchor in parser.anchors:
        raw_href = anchor.get("href", "")
        resolved = resolve_url(resolution_base, raw_href)
        if not resolved or not is_http_url(resolved):
            continue
        clean = normalized_url(resolved)
        crawl_url = canonicalize_crawl_url(resolved)
        if origin(crawl_url) == page_origin:
            internal_links.add(crawl_url)
            link_edges.append(
                {
                    "source": normalized_url(url),
                    "target": crawl_url,
                    "anchor": anchor.get("_text", ""),
                    "rel": sorted(set(anchor.get("rel", "").lower().split())),
                }
            )
        else:
            external_links.add(crawl_url)

    images: list[dict[str, Any]] = []
    for image in parser.images:
        images.append(
            {
                "src": image.get("src", "").strip(),
                "alt_present": "alt" in image,
                "alt": image.get("alt", ""),
                "width_present": bool(image.get("width", "").strip()),
                "height_present": bool(image.get("height", "").strip()),
            }
        )

    image_resources: list[dict[str, str]] = []
    seen_resources: set[tuple[str, str, str]] = set()
    for element, attributes in parser.image_resource_elements:
        for attribute in IMAGE_URL_ATTRIBUTES:
            raw = attributes.get(attribute, "").strip()
            candidates = [raw] if raw else []
            for candidate in candidates:
                resolved = resolve_url(resolution_base, candidate)
                if not resolved or not is_http_url(resolved):
                    continue
                item = (element, attribute, normalized_url(resolved))
                if item in seen_resources:
                    continue
                seen_resources.add(item)
                image_resources.append(
                    {
                        "element": element,
                        "attribute": attribute,
                        "raw": candidate,
                        "url": item[2],
                    }
                )
        for attribute in IMAGE_SRCSET_ATTRIBUTES:
            raw_srcset = attributes.get(attribute, "").strip()
            for candidate in parse_srcset(raw_srcset):
                resolved = resolve_url(resolution_base, candidate)
                if not resolved or not is_http_url(resolved):
                    continue
                item = (element, attribute, normalized_url(resolved))
                if item in seen_resources:
                    continue
                seen_resources.add(item)
                image_resources.append(
                    {
                        "element": element,
                        "attribute": attribute,
                        "raw": candidate,
                        "url": item[2],
                    }
                )

    structured_types: set[str] = set()
    structured_errors: list[str] = []
    for index, script in enumerate(parser.json_ld_scripts, start=1):
        if not script:
            structured_errors.append(f"JSON-LD #{index} 为空")
            continue
        try:
            structured_types.update(json_ld_types(json.loads(script)))
        except json.JSONDecodeError as exc:
            structured_errors.append(f"JSON-LD #{index}: 第 {exc.lineno} 行第 {exc.colno} 列：{exc.msg}")

    visible_text = normalize_space(" ".join(parser.visible_chunks))
    anchors_without_href = [
        anchor.get("_text", "") or "<无文本链接>"
        for anchor in parser.anchors
        if not anchor.get("href", "").strip()
    ]

    return Page(
        url=normalized_url(url),
        source=source,
        evidence_mode=evidence_mode,
        requested_url=normalized_url(requested_url or url, keep_query=True),
        status=status,
        final_url=normalized_url(final_url or url, keep_query=True),
        content_type=content_type,
        response_headers=headers,
        document_base_url=normalized_url(resolution_base),
        html_sha256=hashlib.sha256(html).hexdigest(),
        visible_text_sha256=hashlib.sha256(visible_text.encode("utf-8")).hexdigest(),
        visible_text_length=len(visible_text),
        redirect_chain=redirect_chain or [],
        titles=parser.titles,
        descriptions=descriptions,
        canonicals=sorted(set(canonicals)),
        robots=robots,
        hreflang=hreflang,
        internal_links=sorted(internal_links),
        external_links=sorted(external_links),
        link_edges=link_edges,
        images=images,
        image_resources=image_resources,
        json_ld_types=sorted(structured_types),
        json_ld_errors=structured_errors,
        html_lang=parser.html_lang,
        h1_count=parser.h1_count,
        main_count=parser.main_count,
        anchor_count=len(parser.anchors),
        anchors_without_href=anchors_without_href,
        non_anchor_link_controls=parser.non_anchor_link_controls,
    )


def url_for_local_file(file: Path, root: Path, base_url: str) -> str:
    if root.is_file():
        return normalized_url(base_url)
    relative = file.relative_to(root).as_posix()
    if relative == "index.html":
        relative = ""
    elif relative.endswith("/index.html"):
        relative = relative[: -len("index.html")]
    return normalized_url(urllib.parse.urljoin(base_url.rstrip("/") + "/", relative))


def local_asset_urls(root: Path, base_url: str) -> set[str]:
    if root.is_file():
        return set()
    urls: set[str] = set()
    for file in root.rglob("*"):
        if not file.is_file():
            continue
        if file.suffix.casefold() in {".html", ".htm"}:
            continue
        relative = file.relative_to(root).as_posix()
        urls.add(normalized_url(urllib.parse.urljoin(base_url.rstrip("/") + "/", relative)))
    return urls


def local_html_files(source: Path) -> list[Path]:
    if source.is_file():
        if source.suffix.casefold() not in {".html", ".htm"}:
            raise ValueError(f"本地输入文件必须是 .html 或 .htm：{source}")
        return [source]
    if not source.is_dir():
        raise ValueError(f"本地输入不存在或不是文件/目录：{source}")
    return sorted(
        file
        for file in source.rglob("*")
        if file.is_file() and file.suffix.casefold() in {".html", ".htm"}
    )


def load_local_pages(
    site_input: Path,
    base_url: str,
    *,
    evidence_mode: str = "static_build",
) -> tuple[dict[str, Page], set[str]]:
    pages: dict[str, Page] = {}
    for file in local_html_files(site_input):
        url = url_for_local_file(file, site_input, base_url)
        raw = file.read_bytes()
        source_reference = (
            report_file_reference(file, "index.html")
            if site_input.is_file()
            else file.relative_to(site_input).as_posix()
        )
        pages[url] = parse_page(
            html=raw,
            url=url,
            source=source_reference,
            evidence_mode=evidence_mode,
            status=None,
            content_type=(
                "text/html (浏览器导出 DOM；HTTP 未验证)"
                if evidence_mode == "browser_dom"
                else "text/html (静态构建文件；HTTP 与浏览器 DOM 未验证)"
            ),
            site_origin=origin(base_url),
        )
    return pages, local_asset_urls(site_input, base_url)


def load_browser_provenance(
    path: Path,
    pages: Mapping[str, Page],
) -> BrowserProvenance:
    """验证外部浏览器采集声明，并把每个 URL 绑定到导入 DOM 的 SHA-256。"""
    try:
        raw_bytes = path.read_bytes()
        raw = json.loads(raw_bytes.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 --browser-provenance：{exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("--browser-provenance 顶层必须是 JSON object")
    if raw.get("schema_version") != "1.0":
        raise ValueError("--browser-provenance schema_version 必须为 1.0")
    capture_method = str(raw.get("capture_method", "")).strip()
    browser = str(raw.get("browser", "")).strip()
    captured_at = str(raw.get("captured_at", "")).strip()
    if not capture_method or not browser or not captured_at:
        raise ValueError("--browser-provenance 必须包含 capture_method、browser 与 captured_at")
    try:
        parsed_time = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("--browser-provenance captured_at 必须是 ISO 8601 datetime") from exc
    if parsed_time.tzinfo is None or parsed_time.utcoffset() is None:
        raise ValueError("--browser-provenance captured_at 必须包含 UTC offset")
    if raw.get("javascript_enabled") is not True:
        raise ValueError("--browser-provenance javascript_enabled 必须为 true")
    documents = raw.get("documents")
    if not isinstance(documents, list) or not documents:
        raise ValueError("--browser-provenance documents 必须是非空数组")
    declared: dict[str, str] = {}
    for index, document in enumerate(documents, start=1):
        if not isinstance(document, dict):
            raise ValueError(f"--browser-provenance documents[{index}] 必须是 object")
        raw_url = str(document.get("url", "")).strip()
        digest = str(document.get("sha256", "")).strip().casefold()
        if not is_http_url(raw_url):
            raise ValueError(f"--browser-provenance documents[{index}].url 必须是 HTTP(S) URL")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"--browser-provenance documents[{index}].sha256 必须是 64 位十六进制")
        url = normalized_url(canonicalize_crawl_url(raw_url))
        if url in declared:
            raise ValueError(f"--browser-provenance documents 包含重复 URL：{url}")
        declared[url] = digest
    if not pages:
        raise ValueError("没有 DOM 页面可与 --browser-provenance 绑定")
    for url, page in pages.items():
        if url not in declared:
            raise ValueError(f"--browser-provenance 缺少 DOM URL：{url}")
        if declared[url] != page.html_sha256:
            raise ValueError(f"--browser-provenance SHA-256 与导入 DOM 不一致：{url}")
    return BrowserProvenance(
        source=report_file_reference(path, "browser-provenance.json"),
        schema_version="1.0",
        capture_method=capture_method,
        browser=browser,
        captured_at=captured_at,
        javascript_enabled=True,
        documents_verified=len(pages),
        provenance_sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )


def fetch_url(
    url: str,
    timeout: float,
    *,
    allowed_origin: tuple[str, str] | None = None,
    max_redirects: int = MAX_REDIRECTS,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> FetchResult:
    """抓取公开 HTTP(S) URL，并在每次重定向前重新执行 SSRF 边界。"""
    requested_url = url
    current_url = url
    chain: list[dict[str, Any]] = []
    for _hop in range(max_redirects + 1):
        try:
            targets = resolve_public_targets(current_url, allowed_origin=allowed_origin)
            last_connection_error: Exception | None = None
            raw: RawHTTPResponse | None = None
            for target in targets:
                try:
                    raw = _fetch_once(target, timeout, max_response_bytes)
                    break
                except (TimeoutError, OSError, ssl.SSLError, http.client.HTTPException) as exc:
                    last_connection_error = exc
            if raw is None:
                raise OSError(
                    f"全部 {len(targets)} 个已验证公网地址均连接失败："
                    f"{last_connection_error or 'unknown error'}"
                )
        except (ValueError, TimeoutError, OSError, ssl.SSLError, http.client.HTTPException) as exc:
            return FetchResult(
                requested_url,
                current_url,
                None,
                "",
                {},
                b"",
                str(exc),
                chain,
            )
        headers = normalize_response_headers(raw.headers)
        location = first_header(headers, "location")
        if raw.status in {301, 302, 303, 307, 308} and location:
            redirected = urllib.parse.urljoin(current_url, location)
            chain.append(
                {
                    "url": canonicalize_crawl_url(current_url),
                    "status": raw.status,
                    "location": canonicalize_crawl_url(redirected),
                }
            )
            current_url = redirected
            continue
        return FetchResult(
            requested_url=requested_url,
            final_url=current_url,
            status=raw.status,
            content_type=first_header(headers, "content-type"),
            headers=headers,
            body=raw.body,
            error=f"HTTP {raw.status}" if raw.status >= 400 else "",
            redirect_chain=chain,
        )
    return FetchResult(
        requested_url,
        current_url,
        None,
        "",
        {},
        b"",
        f"重定向超过上限 {max_redirects}",
        chain,
    )


def crawl_remote(
    start_url: str,
    max_pages: int,
    timeout: float,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> tuple[dict[str, Page], dict[str, FetchResult], list[str]]:
    start = normalized_url(start_url)
    expected_origin = origin(start)
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    queued = {start}
    pages: dict[str, Page] = {}
    fetches: dict[str, FetchResult] = {}
    errors: list[str] = []

    while queue and len(fetches) < max_pages:
        requested, depth = queue.popleft()
        result = fetch_url(
            requested,
            timeout,
            allowed_origin=expected_origin,
            max_response_bytes=max_response_bytes,
        )
        fetches[normalized_url(requested)] = replace(result, body=b"")
        if result.status is None:
            errors.append(f"{requested}: {result.error}")
            continue
        content_type = result.content_type.lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            continue
        final = normalized_url(result.final_url)
        if origin(final) != expected_origin:
            continue
        page = parse_page(
            html=result.body,
            url=final,
            source=result.final_url,
            evidence_mode="http_source",
            requested_url=result.requested_url,
            status=result.status,
            final_url=result.final_url,
            content_type=result.content_type,
            response_headers=result.headers,
            redirect_chain=result.redirect_chain,
            site_origin=expected_origin,
        )
        page.depth = depth
        pages[final] = page
        for link in page.internal_links:
            clean = normalized_url(link)
            if clean not in queued and origin(clean) == expected_origin:
                queued.add(clean)
                queue.append((clean, depth + 1))
    if queue:
        errors.append(f"达到 --max-pages={max_pages}，仍有 {len(queue)} 个已发现 URL 未抓取。")
    return pages, fetches, errors


def read_text_source(
    value: str,
    timeout: float,
    *,
    allowed_origin: tuple[str, str] | None = None,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> tuple[str, str]:
    if is_http_url(value):
        result = fetch_url(
            value,
            timeout,
            allowed_origin=allowed_origin,
            max_response_bytes=max_response_bytes,
        )
        if result.status is None or result.status >= 400:
            raise ValueError(f"无法读取 {value}: HTTP {result.status or 'unknown'} {result.error}".strip())
        return result.body.decode("utf-8", errors="replace"), result.final_url
    path = Path(value)
    try:
        return path.read_text(encoding="utf-8-sig"), str(path)
    except OSError as exc:
        detail = exc.strerror or exc.__class__.__name__
        raise ValueError(
            f"无法读取本地文件 {report_file_reference(path)}：{detail}"
        ) from exc


def parse_sitemap(
    value: str,
    timeout: float,
    max_sitemaps: int = 20,
    *,
    allowed_origin: tuple[str, str] | None = None,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> tuple[set[str], list[str], list[str]]:
    urls: set[str] = set()
    duplicates: list[str] = []
    errors: list[str] = []
    queue: deque[str] = deque([value])
    seen_sources: set[str] = set()

    while queue and len(seen_sources) < max_sitemaps:
        source = queue.popleft()
        if source in seen_sources:
            continue
        seen_sources.add(source)
        display_source = report_source_label(source)
        try:
            text, resolved_source = read_text_source(
                source,
                timeout,
                allowed_origin=allowed_origin,
                max_response_bytes=max_response_bytes,
            )
            root = ET.fromstring(text)
        except (OSError, ValueError, ET.ParseError) as exc:
            errors.append(f"{display_source}: {exc}")
            continue
        root_name = root.tag.rsplit("}", 1)[-1].lower()
        entry_name = "sitemap" if root_name == "sitemapindex" else "url"
        locs = [
            normalize_space(item.text or "")
            for entry in list(root)
            if entry.tag.rsplit("}", 1)[-1].lower() == entry_name
            for item in list(entry)
            if item.tag.rsplit("}", 1)[-1].lower() == "loc"
        ]
        if root_name == "sitemapindex":
            for loc in locs:
                if loc:
                    child = urllib.parse.urljoin(resolved_source, loc)
                    if allowed_origin is not None and (
                        not is_http_url(child) or origin(child) != allowed_origin
                    ):
                        errors.append(
                            f"{display_source}: 递归 sitemap 不属于允许的同源范围："
                            f"{report_source_label(child)}"
                        )
                        continue
                    queue.append(child)
            continue
        if root_name != "urlset":
            errors.append(
                f"{display_source}: 根元素是 {root_name!r}，不是 urlset 或 sitemapindex"
            )
            continue
        for loc in locs:
            if not is_http_url(loc):
                errors.append(f"{display_source}: loc 不是绝对 HTTP(S) URL：{loc!r}")
                continue
            clean = normalized_url(loc)
            if clean in urls:
                duplicates.append(clean)
            urls.add(clean)
    if queue:
        errors.append(f"达到 sitemap 上限 {max_sitemaps}，仍有 {len(queue)} 个 sitemap 未读取。")
    return urls, sorted(set(duplicates)), errors


def parse_robots(text: str) -> dict[str, Any]:
    groups: list[dict[str, list[str]]] = []
    current: dict[str, list[str]] | None = None
    sitemap_urls: list[str] = []
    unsupported_noindex: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field_name, raw_value = line.split(":", 1)
        name = field_name.strip().lower()
        value = raw_value.strip()
        if name == "user-agent":
            if current is None or current.get("rules"):
                current = {"agents": [], "rules": []}
                groups.append(current)
            current["agents"].append(value.lower())
        elif name in {"allow", "disallow"}:
            if current is None:
                current = {"agents": ["*"], "rules": []}
                groups.append(current)
            current["rules"].append(f"{name}:{value}")
        elif name == "sitemap" and value:
            sitemap_urls.append(value)
        elif name == "noindex":
            unsupported_noindex.append(value)
    return {"groups": groups, "sitemaps": sitemap_urls, "unsupported_noindex": unsupported_noindex}


def robots_rules_for(parsed: dict[str, Any], agent_name: str = "googlebot") -> list[tuple[str, str]]:
    target = agent_name.casefold()
    specific_groups = [
        group
        for group in parsed.get("groups", [])
        if any(agent != "*" and agent in target for agent in group.get("agents", []))
    ]
    selected = specific_groups or [
        group for group in parsed.get("groups", []) if "*" in group.get("agents", [])
    ]
    rules: list[tuple[str, str]] = []
    for group in selected:
        for raw in group.get("rules", []):
            name, value = raw.split(":", 1)
            rules.append((name, value))
    return rules


def robots_rule_match(path_query: str, pattern: str) -> tuple[bool, int]:
    if not pattern:
        return False, 0
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    expression = "^" + re.escape(body).replace(r"\*", ".*")
    if anchored:
        expression += "$"
    matched = re.search(expression, path_query) is not None
    specificity = len(body.replace("*", ""))
    return matched, specificity


def path_blocked_by_robots(url: str, parsed: dict[str, Any]) -> bool:
    split = urllib.parse.urlsplit(url)
    path = split.path or "/"
    if split.query:
        path += "?" + split.query
    matched: list[tuple[int, str]] = []
    for directive, pattern in robots_rules_for(parsed):
        is_match, specificity = robots_rule_match(path, pattern)
        if is_match:
            matched.append((specificity, directive))
    if not matched:
        return False
    longest = max(length for length, _ in matched)
    winning = {directive for length, directive in matched if length == longest}
    return "disallow" in winning and "allow" not in winning


def local_route_lookup_variants(url: str) -> list[str]:
    """生成文件路由别名；仅用于判断本地构建是否有可承载该请求的文件。"""
    clean = normalized_url(url)
    parsed = urllib.parse.urlsplit(clean)
    path = parsed.path
    variants = [clean]
    if parsed.query:
        variants.append(urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", "")))
    if path.endswith("/"):
        variants.append(urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path + "index.html", parsed.query, "")))
        variants.append(urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path + "index.html", "", "")))
    elif path.endswith("/index.html"):
        variants.append(urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path[: -len("index.html")], parsed.query, "")))
        variants.append(urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path[: -len("index.html")], "", "")))
    elif not Path(path).suffix:
        variants.append(urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path + "/", parsed.query, "")))
        variants.append(urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path + "/", "", "")))
    return list(dict.fromkeys(variants))


def matching_seo_url(url: str, candidates: set[str]) -> str | None:
    """只匹配同一规范化 URL；业务参数、斜杠和 index.html 均保留语义。"""
    clean = normalized_url(url)
    return clean if clean in candidates else None


def matching_local_route(url: str, candidates: set[str]) -> str | None:
    for variant in local_route_lookup_variants(url):
        if variant in candidates:
            return variant
    return None


def matching_local_asset(url: str, assets: set[str]) -> str | None:
    """匹配真实媒体文件；查询参数不属于文件名，但不套用 HTML 路由别名。"""
    clean = normalized_url(url)
    if clean in assets:
        return clean
    parsed = urllib.parse.urlsplit(clean)
    if parsed.query:
        without_query = urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, "", "")
        )
        if without_query in assets:
            return without_query
    return None


def add_finding(
    findings: list[Finding],
    *,
    code: str,
    severity: str,
    category: str,
    observation: str,
    urls: Iterable[str] = (),
    evidence: Iterable[str] = (),
    impact_boundary: str,
    verification: str,
    confidence: str = "high",
) -> None:
    findings.append(
        Finding(
            code=code,
            severity=severity,
            category=category,
            observation=observation,
            urls=sorted(set(urls)),
            evidence=list(evidence),
            impact_boundary=impact_boundary,
            verification=verification,
            confidence=confidence,
        )
    )


def group_duplicate(values: dict[str, str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for url, value in values.items():
        normalized = normalize_space(value).casefold()
        if normalized:
            groups[normalized].append(url)
    return {value: urls for value, urls in groups.items() if len(urls) > 1}


def calculate_graph(pages: dict[str, Page], start_url: str) -> tuple[dict[str, int], dict[str, int]]:
    page_urls = set(pages)
    inbound = {url: 0 for url in page_urls}
    adjacency: dict[str, set[str]] = {url: set() for url in page_urls}
    for source, page in pages.items():
        for raw_target in page.internal_links:
            target = matching_seo_url(raw_target, page_urls)
            if target and target != source:
                adjacency[source].add(target)
                inbound[target] += 1
    root = matching_seo_url(start_url, page_urls)
    depths: dict[str, int] = {}
    if root:
        depths[root] = 0
        queue = deque([root])
        while queue:
            current = queue.popleft()
            for target in sorted(adjacency[current]):
                if target not in depths:
                    depths[target] = depths[current] + 1
                    queue.append(target)
    for url, page in pages.items():
        page.depth = depths.get(url)
    return inbound, depths


def signal_difference(source: Any, rendered: Any) -> dict[str, Any]:
    return {"source": source, "rendered": rendered, "changed": source != rendered}


def build_rendering_comparison(
    source_pages: dict[str, Page],
    rendered_pages: dict[str, Page],
    source_input: str,
) -> dict[str, Any]:
    source_urls = set(source_pages)
    rendered_urls = set(rendered_pages)
    matched_source_urls: set[str] = set()
    comparisons: list[dict[str, Any]] = []
    rendered_only_urls: list[str] = []

    for rendered_url in sorted(rendered_urls):
        source_url = matching_seo_url(rendered_url, source_urls)
        if not source_url:
            rendered_only_urls.append(rendered_url)
            continue
        matched_source_urls.add(source_url)
        source = source_pages[source_url]
        rendered = rendered_pages[rendered_url]
        comparisons.append(
            {
                "url": rendered_url,
                "source_source": source.source,
                "rendered_source": rendered.source,
                "source_html_sha256": source.html_sha256,
                "rendered_html_sha256": rendered.html_sha256,
                "html_changed": source.html_sha256 != rendered.html_sha256,
                "differences": {
                    "titles": signal_difference(source.titles, rendered.titles),
                    "descriptions": signal_difference(source.descriptions, rendered.descriptions),
                    "canonicals": signal_difference(source.canonicals, rendered.canonicals),
                    "robots": signal_difference(source.robots, rendered.robots),
                    "internal_links": signal_difference(source.internal_links, rendered.internal_links),
                    "json_ld_types": signal_difference(source.json_ld_types, rendered.json_ld_types),
                    "visible_text_sha256": signal_difference(
                        source.visible_text_sha256, rendered.visible_text_sha256
                    ),
                    "visible_text_length": signal_difference(
                        source.visible_text_length, rendered.visible_text_length
                    ),
                    "h1_count": signal_difference(source.h1_count, rendered.h1_count),
                    "main_count": signal_difference(source.main_count, rendered.main_count),
                },
            }
        )

    return {
        "source_input": source_input,
        "matched_pages": len(comparisons),
        "source_only_urls": sorted(source_urls - matched_source_urls),
        "rendered_only_urls": rendered_only_urls,
        "pages": comparisons,
    }


def analyze(
    pages: dict[str, Page],
    *,
    base_url: str,
    assets: set[str],
    fetches: dict[str, FetchResult],
    sitemap_urls: set[str],
    sitemap_duplicates: list[str],
    sitemap_errors: list[str],
    robots: dict[str, Any] | None,
    robots_source: str | None,
    production: bool,
    scope_mode: str,
    crawl_notes: list[str],
    evidence_mode: str | None = None,
    source_pages: dict[str, Page] | None = None,
    source_input: str | None = None,
    browser_provenance: BrowserProvenance | None = None,
) -> dict[str, Any]:
    evidence_mode = evidence_mode or ("static_build" if scope_mode == "local" else "http_source")
    if evidence_mode not in EVIDENCE_MODES:
        raise ValueError(f"未知 evidence_mode：{evidence_mode}")
    if evidence_mode != "browser_dom" and source_pages is not None:
        raise ValueError("source-vs-rendered 对比只适用于 browser_dom")
    if evidence_mode != "browser_dom" and browser_provenance is not None:
        raise ValueError("浏览器 provenance 只适用于 browser_dom")
    client_side_dom_verified = browser_provenance is not None
    findings: list[Finding] = []
    page_urls = set(pages)
    all_known_targets = page_urls | assets | set(fetches)
    start_url = normalized_url(base_url.rstrip("/") + "/")
    inbound, depths = calculate_graph(pages, start_url)

    if not pages:
        add_finding(
            findings,
            code="scope.no-html",
            severity="high",
            category="scope",
            observation="检查范围内没有解析到 HTML 页面。",
            impact_boundary="这说明当前输入无法支持页面级 SEO 判断，不等同于站点没有页面。",
            verification="确认构建目录、起始 URL、认证/WAF 与 Content-Type 后重新运行。",
        )

    for error in sitemap_errors:
        add_finding(
            findings,
            code="sitemap.parse-error",
            severity="high",
            category="sitemap",
            observation="sitemap 无法完整解析。",
            evidence=[error],
            impact_boundary="错误 sitemap 会削弱 URL 发现与规范信号，但不会单独决定收录或排名。",
            verification="修复后重新解析 XML，并在真实 HTTP 响应中验证。",
        )
    if sitemap_duplicates:
        add_finding(
            findings,
            code="sitemap.duplicate-url",
            severity="medium",
            category="sitemap",
            observation=f"sitemap 中有 {len(sitemap_duplicates)} 个重复 URL。",
            urls=sitemap_duplicates,
            evidence=["同一规范化 loc 出现多次"],
            impact_boundary="重复 loc 通常是维护与信号噪声，不应被描述为必然排名损失。",
            verification="生成 sitemap 后按规范化 URL 去重并重新解析。",
        )

    for page in pages.values():
        if page.status is not None and page.status >= 500:
            add_finding(
                findings,
                code="http.server-error",
                severity="critical" if production else "high",
                category="crawlability",
                observation=f"页面返回 HTTP {page.status}。",
                urls=[page.url],
                evidence=[page.requested_url],
                impact_boundary="持续 5xx 会阻止用户和搜索抓取；一次采样不能证明持续故障。",
                verification="从多个网络位置复测，并检查服务器日志和监控。",
            )
        elif page.status is not None and page.status >= 400:
            add_finding(
                findings,
                code="http.client-error",
                severity="high",
                category="crawlability",
                observation=f"页面返回 HTTP {page.status}。",
                urls=[page.url],
                evidence=[page.requested_url],
                impact_boundary="错误响应无法作为正常可索引页面工作；是否应存在要结合 URL 所有权判断。",
                verification="确认 URL 是否应保留；修复、301 到真正替代页或从入口移除。",
            )
        if normalized_url(page.requested_url) != normalized_url(page.final_url):
            add_finding(
                findings,
                code="http.redirect-observed",
                severity="info",
                category="url-signals",
                observation="请求 URL 被重定向。",
                urls=[page.requested_url, page.final_url],
                evidence=[
                    f"{item['status']} {item['url']} -> {item['location']}"
                    for item in page.redirect_chain
                ] or [f"{page.requested_url} -> {page.final_url}"],
                impact_boundary="重定向本身可为正确行为；需要检查链长、目标相关性和内部链接是否仍指旧 URL。",
                verification="检查完整重定向链及目标状态，并将内部链接更新为最终规范 URL。",
            )
            if len(page.redirect_chain) > 1:
                add_finding(
                    findings,
                    code="http.redirect-chain",
                    severity="medium",
                    category="url-signals",
                    observation=f"请求经过 {len(page.redirect_chain)} 次重定向才到达最终 URL。",
                    urls=[page.requested_url, page.final_url],
                    evidence=[
                        f"{item['status']} {item['url']} -> {item['location']}"
                        for item in page.redirect_chain
                    ],
                    impact_boundary="多跳会增加请求成本和故障面；它不自动证明排名损失。",
                    verification="在保持正确迁移语义的前提下让旧 URL 直接到最终规范目标。",
                )
        if len(page.titles) == 0 or not any(page.titles):
            add_finding(
                findings,
                code="metadata.title-missing",
                severity="high",
                category="search-presentation",
                observation="当前 HTML 证据没有非空 title。",
                urls=[page.url],
                evidence=[f"title_count={len(page.titles)}"],
                impact_boundary="title 是重要的页面主题与搜索标题输入，但 Google 仍可能重写展示标题。",
                verification="在浏览器 DOM 中复查唯一、准确且与可见内容一致的 title。",
            )
        elif len(page.titles) > 1:
            add_finding(
                findings,
                code="metadata.multiple-title",
                severity="medium",
                category="search-presentation",
                observation=f"当前 HTML 证据有 {len(page.titles)} 个 title。",
                urls=[page.url],
                evidence=page.titles,
                impact_boundary="多个所有者可能制造冲突；本检查不使用固定字符数规则。",
                verification="定位框架、主题或插件的 metadata 所有者并保留一个准确 title。",
            )
        if not any(page.descriptions):
            add_finding(
                findings,
                code="metadata.description-missing",
                severity="low",
                category="search-presentation",
                observation="页面没有非空 meta description。",
                urls=[page.url],
                evidence=[f"description_count={len(page.descriptions)}"],
                impact_boundary="description 是摘要候选，不是通用排名因素，Google 也可能从页面生成摘要。",
                verification="只在能更准确概括页面和意图时补充，不使用固定字符数闸门。",
            )
        if len(page.canonicals) > 1:
            add_finding(
                findings,
                code="canonical.multiple",
                severity="high",
                category="url-signals",
                observation=f"页面声明了 {len(page.canonicals)} 个不同 canonical。",
                urls=[page.url],
                evidence=page.canonicals,
                impact_boundary="相互冲突的 canonical 会使规范信号不清；Google 会综合其他信号自行选择。",
                verification="确认唯一 URL 所有者，在 HTTP/渲染产物中只保留一个目标。",
            )
        elif not page.canonicals:
            add_finding(
                findings,
                code="canonical.not-explicit",
                severity="info",
                category="url-signals",
                observation="页面未显式声明 canonical。",
                urls=[page.url],
                impact_boundary="canonical 并非所有页面的强制标签；是否需要取决于重复 URL 风险和其他规范信号。",
                verification="结合重定向、sitemap、参数 URL 与 Google-selected canonical 决定是否补充。",
            )
        else:
            canonical = page.canonicals[0]
            if not is_http_url(canonical):
                add_finding(
                    findings,
                    code="canonical.invalid",
                    severity="high",
                    category="url-signals",
                    observation="canonical 不是可用的 HTTP(S) URL。",
                    urls=[page.url],
                    evidence=[canonical],
                    impact_boundary="无效目标不能表达可靠规范信号。",
                    verification="输出可访问、最终状态正常且属于正确页面的绝对 URL。",
                )
            target = (
                matching_local_route(canonical, all_known_targets)
                if evidence_mode == "static_build"
                else matching_seo_url(canonical, all_known_targets)
            )
            if target is None and evidence_mode == "static_build":
                add_finding(
                    findings,
                    code="canonical.target-outside-artifact",
                    severity="medium",
                    category="url-signals",
                    observation="canonical 目标在本地产物中找不到对应文件。",
                    urls=[page.url, canonical],
                    impact_boundary="目标可能在线上存在，因此这是待发布环境复核的信号，不等同于已证实 404。",
                    verification="发布后请求 canonical 目标并检查状态、内容等价性和索引资格。",
                    confidence="medium",
                )
            fetched_target = fetches.get(normalized_url(canonical))
            if fetched_target and (fetched_target.status is None or fetched_target.status >= 400):
                add_finding(
                    findings,
                    code="canonical.target-error",
                    severity="high",
                    category="url-signals",
                    observation="canonical 目标未返回正常成功响应。",
                    urls=[page.url, canonical],
                    evidence=[f"HTTP {fetched_target.status or 'unknown'}"],
                    impact_boundary="错误目标不能作为稳定规范页面；一次抓取失败仍需复测。",
                    verification="修正目标后从真实 HTTP 与 URL Inspection 复核。",
                )
        if page.noindex:
            severity = "critical" if production and len(pages) > 0 and all(item.noindex for item in pages.values()) else "high"
            add_finding(
                findings,
                code="robots.noindex",
                severity=severity,
                category="indexability",
                observation="页面产物包含 noindex 指令。",
                urls=[page.url],
                evidence=page.robots,
                impact_boundary="noindex 会阻止该页面进入 Google 索引；是否为缺陷取决于页面预期。",
                verification="确认页面所有权与环境；目标可索引页移除指令后复查 HTTP 与渲染输出。",
            )
        if page.noindex and page.canonicals and normalized_url(page.canonicals[0]) != page.url:
            add_finding(
                findings,
                code="signals.noindex-cross-canonical",
                severity="high",
                category="url-signals",
                observation="页面同时 noindex 并 canonical 到其他 URL，规范意图需要明确。",
                urls=[page.url, page.canonicals[0]],
                evidence=page.robots,
                impact_boundary="Google 建议用 canonical 表达重复版本；noindex 与跨页 canonical 混用会让处理目标不清。",
                verification="根据保留、合并或排除意图选择单一策略并在真实产物复验。",
            )
        if page.json_ld_errors:
            add_finding(
                findings,
                code="structured-data.invalid-json",
                severity="medium",
                category="structured-data",
                observation=f"页面有 {len(page.json_ld_errors)} 段 JSON-LD 无法解析。",
                urls=[page.url],
                evidence=page.json_ld_errors,
                impact_boundary="无效 JSON-LD 不能可靠提供结构化线索；修复不保证富结果、排名或 AI 展示。",
                verification="解析完整 JSON 对象，并按当前受支持功能要求和可见内容验证。",
            )
        missing_alt = [image.get("src", "") for image in page.images if not image["alt_present"]]
        if missing_alt:
            add_finding(
                findings,
                code="images.alt-attribute-missing",
                severity="low",
                category="images-accessibility",
                observation=f"有 {len(missing_alt)} 张图片缺少 alt 属性。",
                urls=[page.url],
                evidence=missing_alt[:20],
                impact_boundary="缺失 alt 会损害可访问性和图片语义；空 alt 可能是正确的装饰图处理，工具不会误报为空值。",
                verification="为信息图提供与上下文一致的替代文本；装饰图保留 alt=\"\"。",
            )
        if evidence_mode == "static_build":
            missing_local_images: list[str] = []
            for resource in page.image_resources:
                target = resource["url"]
                if origin(target) != origin(base_url):
                    continue
                if matching_local_asset(target, assets) is None:
                    missing_local_images.append(target)
            if missing_local_images:
                add_finding(
                    findings,
                    code="images.missing-local-asset",
                    severity="medium",
                    category="images-accessibility",
                    observation=f"页面引用了 {len(set(missing_local_images))} 个本地构建中不存在的图片资源。",
                    urls=[page.url] + sorted(set(missing_local_images)),
                    evidence=[
                        f"{page.url} -> {target}"
                        for target in sorted(set(missing_local_images))[:20]
                    ],
                    impact_boundary="本地缺失会造成部署后破图风险，但 CDN、重写或发布管道可能在生产环境补充资源。",
                    verification="恢复真实图片或移除无效引用；重新构建后检查文件存在，并在发布环境请求最终媒体 URL。",
                    confidence="medium",
                )
        if page.hreflang and not page.html_lang:
            add_finding(
                findings,
                code="language.html-lang-missing",
                severity="low",
                category="international",
                observation="页面声明 hreflang，但 html 元素没有 lang。",
                urls=[page.url],
                impact_boundary="html lang 主要帮助可访问性和语言处理；它不替代 hreflang。",
                verification="让 html lang 与页面主要语言一致，并独立验证 hreflang 集合。",
            )
        if page.anchors_without_href or page.non_anchor_link_controls:
            evidence = [
                f"<a> 缺少 href：{item}" for item in page.anchors_without_href[:10]
            ] + [
                f"<{tag} role=\"link\"> 不是 <a href>"
                for tag in page.non_anchor_link_controls[:10]
            ]
            add_finding(
                findings,
                code="links.non-crawlable-control",
                severity="medium",
                category="discovery",
                observation="页面含有未使用可解析 <a href> 的链接式控件。",
                urls=[page.url],
                evidence=evidence,
                impact_boundary="Google 通常从带 href 的 <a> 元素可靠发现 URL；控件仍可能服务站内交互，但不能据此断言目标可被抓取发现。",
                verification="在浏览器 DOM 中确认重要导航和上下文入口是指向真实 URL 的 <a href>，并测试无脚本/直接访问回退。",
                confidence="high" if evidence_mode == "browser_dom" else "medium",
            )

    rendering_comparison = (
        build_rendering_comparison(source_pages, pages, source_input or "")
        if source_pages is not None
        else None
    )
    if source_pages is not None:
        for rendered_url in sorted(page_urls):
            source_url = matching_seo_url(rendered_url, set(source_pages))
            if not source_url:
                continue
            source = source_pages[source_url]
            rendered = pages[rendered_url]
            if source.noindex and not rendered.noindex:
                add_finding(
                    findings,
                    code="rendering.initial-noindex-removed",
                    severity="high",
                    category="javascript-rendering",
                    observation="源码快照含 noindex，但浏览器 DOM 在执行 JavaScript 后移除了该指令。",
                    urls=[rendered_url],
                    evidence=[f"source={source.robots}", f"rendered={rendered.robots}"],
                    impact_boundary="Google 可能在看到初始 noindex 后跳过渲染；不能依赖客户端移除 noindex 来恢复索引资格。",
                    verification="让希望索引的 URL 在初始 HTTP HTML 和最终 DOM 中都不含 noindex，再用 URL Inspection 复核。",
                )
            if source.canonicals != rendered.canonicals:
                add_finding(
                    findings,
                    code="rendering.canonical-changed",
                    severity="high" if source.canonicals and rendered.canonicals else "medium",
                    category="javascript-rendering",
                    observation="源码快照与浏览器 DOM 的 canonical 不一致。",
                    urls=[rendered_url] + source.canonicals + rendered.canonicals,
                    evidence=[
                        f"source={source.canonicals}",
                        f"rendered={rendered.canonicals}",
                    ],
                    impact_boundary="JavaScript 注入 canonical 可以被处理，但初始与最终信号冲突会增加选择不确定性；本观察不证明 Google 选择了任一版本。",
                    verification="由单一所有者在初始 HTML 输出正确 canonical，并在浏览器 DOM、HTTP、sitemap 与内链中复验一致性。",
                )
            if source.visible_text_length == 0 and rendered.visible_text_length > 0:
                add_finding(
                    findings,
                    code="rendering.content-client-only",
                    severity="medium",
                    category="javascript-rendering",
                    observation="浏览器 DOM 出现了源码快照中不存在的可见正文。",
                    urls=[rendered_url],
                    evidence=[
                        f"source_visible_text_sha256={source.visible_text_sha256}",
                        f"rendered_visible_text_sha256={rendered.visible_text_sha256}",
                    ],
                    impact_boundary="Google 可以渲染 JavaScript，但渲染会增加依赖与失败面；该差异本身不证明内容无法索引。",
                    verification="在 URL Inspection 渲染结果、无权限/无缓存访问和服务器日志中确认关键内容可稳定取得。",
                    confidence="medium",
                )
            added_links = sorted(set(rendered.internal_links) - set(source.internal_links))
            if added_links:
                add_finding(
                    findings,
                    code="rendering.links-client-added",
                    severity="medium",
                    category="javascript-rendering",
                    observation="浏览器 DOM 含有源码快照中不存在的内部链接。",
                    urls=[rendered_url] + added_links[:20],
                    evidence=[f"client_added_links={len(added_links)}"],
                    impact_boundary="Google 可以在渲染后发现合规链接，但仅客户端生成会增加发现延迟和运行失败风险；不等同于链接一定未被抓取。",
                    verification="确保重要入口在最终 DOM 中是 <a href>，并优先让主导航和关键上下文链接出现在初始 HTML。",
                    confidence="medium",
                )

    titles = {url: page.titles[0] for url, page in pages.items() if page.titles and page.titles[0]}
    for _, urls in group_duplicate(titles).items():
        add_finding(
            findings,
            code="metadata.duplicate-title",
            severity="medium",
            category="search-presentation",
            observation=f"{len(urls)} 个页面使用相同 title。",
            urls=urls,
            evidence=[titles[urls[0]]],
            impact_boundary="重复 title 可能反映页面所有权或模板问题，但不自动证明页面内容重复。",
            verification="逐页确认搜索意图、主内容和唯一标题，合并真正重复的 URL。",
        )
    descriptions = {url: page.descriptions[0] for url, page in pages.items() if page.descriptions and page.descriptions[0]}
    for _, urls in group_duplicate(descriptions).items():
        add_finding(
            findings,
            code="metadata.duplicate-description",
            severity="low",
            category="search-presentation",
            observation=f"{len(urls)} 个页面使用相同 meta description。",
            urls=urls,
            evidence=[descriptions[urls[0]]],
            impact_boundary="这通常是摘要质量和模板所有权问题，不是直接排名处罚。",
            verification="按页面真实任务改写，或在无法提供准确摘要时允许搜索系统从正文生成。",
        )

    broken_by_source: dict[str, list[str]] = defaultdict(list)
    parameter_edges: dict[str, list[str]] = defaultdict(list)
    for page in pages.values():
        for target in page.internal_links:
            target_clean = normalized_url(target)
            if urllib.parse.urlsplit(target_clean).query:
                parameter_edges[page.url].append(target_clean)
            known = (
                matching_local_route(target_clean, all_known_targets)
                if evidence_mode == "static_build"
                else matching_seo_url(target_clean, all_known_targets)
            )
            fetched = fetches.get(target_clean)
            if evidence_mode == "static_build" and known is None:
                broken_by_source[page.url].append(target_clean)
            elif fetched and (fetched.status is None or fetched.status >= 400):
                broken_by_source[page.url].append(target_clean)
    for source, targets in broken_by_source.items():
        add_finding(
            findings,
            code="links.broken-internal",
            severity="high",
            category="discovery",
            observation=f"页面有 {len(set(targets))} 个已验证或本地产物缺失的内部链接目标。",
            urls=[source] + sorted(set(targets)),
            evidence=[f"{source} -> {target}" for target in sorted(set(targets))[:20]],
            impact_boundary="断链会中断用户和抓取发现路径；本地缺失仍需在部署环境确认重写规则。",
            verification="修正 href 或目标路由后重新构建并请求最终 URL。",
            confidence="high" if evidence_mode == "http_source" else "medium",
        )
    for source, targets in parameter_edges.items():
        add_finding(
            findings,
            code="links.parameter-url-observed",
            severity="info",
            category="url-signals",
            observation=f"页面链接到 {len(set(targets))} 个带业务参数的站内 URL。",
            urls=[source] + sorted(set(targets)),
            evidence=[f"{source} -> {target}" for target in sorted(set(targets))[:20]],
            impact_boundary="参数可能是筛选、排序或合法状态；工具只保留证据，不把参数本身判为抓取陷阱。",
            verification="检查参数用途、可抓取规模、canonical、内部入口和 GSC/日志中的实际抓取。",
            confidence="medium",
        )

    root_match = matching_seo_url(start_url, page_urls)
    for url, count in inbound.items():
        if url == root_match:
            continue
        if count == 0:
            add_finding(
                findings,
                code="links.orphan-in-scope",
                severity="medium" if url in sitemap_urls else "low",
                category="discovery",
                observation="页面在本次 HTML 范围内没有可抓取的内部入链。",
                urls=[url],
                evidence=[f"inbound_links=0; sitemap={'yes' if url in sitemap_urls else 'no'}"],
                impact_boundary="这是范围内的孤儿信号；导航、JS、外部页面或未抓取页面可能仍提供入口。",
                verification="检查完整站点链接图，并从相关、可抓取页面建立有用入口。",
                confidence="medium",
            )

    for page in pages.values():
        by_lang: dict[str, set[str]] = defaultdict(set)
        for item in page.hreflang:
            by_lang[item["lang"].casefold()].add(item["url"])
        for lang, targets in by_lang.items():
            if len(targets) > 1:
                add_finding(
                    findings,
                    code="hreflang.duplicate-language",
                    severity="high",
                    category="international",
                    observation=f"同一页面的 hreflang={lang!r} 指向多个 URL。",
                    urls=[page.url] + sorted(targets),
                    evidence=sorted(targets),
                    impact_boundary="同一语言代码的冲突目标会让国际版本关系不明确。",
                    verification="每个页面、每个语言/地区代码只保留一个正确目标。",
                )
        if page.hreflang and page.url not in {item["url"] for item in page.hreflang}:
            add_finding(
                findings,
                code="hreflang.self-reference-missing",
                severity="medium",
                category="international",
                observation="hreflang 集合没有包含当前页面自身。",
                urls=[page.url],
                evidence=[f"targets={len(page.hreflang)}"],
                impact_boundary="Google 要求语言版本相互并包含自身；canonical 与可索引性也必须一致。",
                verification="补齐自引用后验证每个版本的返回链接。",
            )
        for item in page.hreflang:
            target_url = matching_seo_url(item["url"], page_urls)
            if not target_url:
                continue
            target_page = pages[target_url]
            if page.url not in {entry["url"] for entry in target_page.hreflang}:
                add_finding(
                    findings,
                    code="hreflang.return-link-missing",
                    severity="medium",
                    category="international",
                    observation="范围内 hreflang 目标没有返回链接。",
                    urls=[page.url, target_url],
                    evidence=[f"{page.url} -> {item['lang']} -> {target_url}"],
                    impact_boundary="缺少返回链接会使该关系不完整；范围外版本仍需单独抓取。",
                    verification="在两端渲染 HTML 中验证完整互链集合。",
                )
            if target_page.noindex:
                add_finding(
                    findings,
                    code="hreflang.target-noindex",
                    severity="high",
                    category="international",
                    observation="hreflang 指向范围内 noindex 页面。",
                    urls=[page.url, target_url],
                    evidence=[item["lang"]],
                    impact_boundary="不可索引目标不能稳定充当搜索结果中的语言替代版本。",
                    verification="修正目标索引资格或从集合中移除不应索引的版本。",
                )

    if sitemap_urls:
        for url in sorted(sitemap_urls):
            if origin(url) != origin(base_url):
                add_finding(
                    findings,
                    code="sitemap.cross-origin-url",
                    severity="medium",
                    category="sitemap",
                    observation="sitemap 包含不同主机的 URL。",
                    urls=[url],
                    impact_boundary="跨站点 sitemap 是否有效取决于验证与托管关系，需要检查 property 所有权。",
                    verification="确认 Search Console 所有权与 sitemap 预期主机。",
                    confidence="medium",
                )
            matched = matching_seo_url(url, page_urls)
            if matched:
                page = pages[matched]
                if page.noindex:
                    add_finding(
                        findings,
                        code="sitemap.noindex-url",
                        severity="high",
                        category="url-signals",
                        observation="sitemap 收录了 noindex 页面。",
                        urls=[matched],
                        evidence=page.robots,
                        impact_boundary="sitemap 与索引指令表达冲突意图；这不会迫使 Google 收录。",
                        verification="只在 sitemap 保留希望作为规范、可索引版本的 URL。",
                    )
                if page.canonicals and normalized_url(page.canonicals[0]) != matched:
                    add_finding(
                        findings,
                        code="sitemap.noncanonical-url",
                        severity="high",
                        category="url-signals",
                        observation="sitemap URL 的页面 canonical 指向其他地址。",
                        urls=[matched, page.canonicals[0]],
                        evidence=[f"sitemap={matched}", f"canonical={page.canonicals[0]}"],
                        impact_boundary="sitemap 应表达规范 URL；Google 仍会综合其他信号选择 canonical。",
                        verification="统一重定向、canonical、sitemap 和内部链接的 URL 所有权。",
                    )
            elif evidence_mode == "static_build":
                add_finding(
                    findings,
                    code="sitemap.url-missing-artifact",
                    severity="medium",
                    category="sitemap",
                    observation="sitemap URL 在本地构建产物中没有对应页面。",
                    urls=[url],
                    impact_boundary="部署层重写可能使线上 URL 有效，因此需要真实 HTTP 复核。",
                    verification="发布预览中请求该 URL；修正生成器或构建缺失。",
                    confidence="medium",
                )

    if robots:
        if robots.get("unsupported_noindex"):
            add_finding(
                findings,
                code="robots.unsupported-noindex",
                severity="medium",
                category="indexability",
                observation="robots.txt 使用了 Google 不支持的 noindex 指令。",
                evidence=robots["unsupported_noindex"],
                impact_boundary="robots.txt 的 noindex 不会可靠阻止 Google 收录；需要 meta robots 或 X-Robots-Tag。",
                verification="删除无效规则，并在实际响应/HTML 使用受支持指令。",
            )
        root_blocked = path_blocked_by_robots(start_url, robots)
        if root_blocked:
            add_finding(
                findings,
                code="robots.sitewide-block",
                severity="critical" if production else "high",
                category="crawlability",
                observation="适用于 Googlebot 或 * 的 robots 规则阻止根路径。",
                urls=[start_url],
                evidence=[f"robots_source={robots_source}"] + [f"{name}:{value}" for name, value in robots_rules_for(robots)],
                impact_boundary="抓取阻断会妨碍搜索系统读取页面，但 robots.txt 不是删除已收录 URL 的可靠方法。",
                verification="确认环境与预期；生产目标站解除后用 robots tester/真实抓取复验。",
            )
        for url in sorted(sitemap_urls):
            if path_blocked_by_robots(url, robots):
                add_finding(
                    findings,
                    code="robots.blocks-sitemap-url",
                    severity="high",
                    category="url-signals",
                    observation="sitemap URL 同时被 robots.txt 阻止抓取。",
                    urls=[url],
                    evidence=[f"robots_source={robots_source}"],
                    impact_boundary="发现与抓取信号冲突，搜索系统可能无法读取页面内容或 noindex。",
                    verification="让应索引 URL 可抓取，并重新验证 sitemap 与页面指令。",
                )

    website_pages = [url for url, page in pages.items() if "WebSite" in page.json_ld_types]
    if len(website_pages) > 1:
        add_finding(
            findings,
            code="structured-data.website-multi-page",
            severity="info",
            category="structured-data",
            observation=f"WebSite 类型出现在 {len(website_pages)} 个范围内页面。",
            urls=website_pages,
            impact_boundary="Google 的站点名称 WebSite 标记应位于首页；其他 Schema 用途需结合完整对象判断。",
            verification="解析对象所有者，确保首页输出准确站点实体，并避免模板重复注入。",
            confidence="medium",
        )

    findings.sort(key=Finding.key)
    severity_counts = Counter(item.severity for item in findings)
    status_counts = Counter(str(page.status if page.status is not None else "unknown") for page in pages.values())
    noindex_count = sum(page.noindex for page in pages.values())
    limitations = [
        "本工具验证当前输入产物，不证明 Google 已抓取、已索引、选择了相同 canonical 或将获得排名。",
        "不生成健康分，不使用固定 title/description 字符数、CTR、排名或流量增幅门槛。",
        "Schema 语法存在或修复只说明机器可读线索，不保证富结果、排名或生成式 AI 展示。",
    ]
    if evidence_mode == "http_source":
        limitations.extend(
            [
                "evidence_mode=http_source：内置有界 HTTP 抓取器只读取响应源码，不执行 JavaScript；客户端生成或改写的 metadata、正文、canonical 与链接均未经验证。",
                "线上模式是有限范围、单一用户代理的即时采样，不等同于 Googlebot 完整抓取或浏览器渲染。",
            ]
        )
    elif evidence_mode == "static_build":
        limitations.extend(
            [
                "evidence_mode=static_build：本地构建文件不等同于浏览器执行 JavaScript 后的 DOM；客户端 metadata、正文与链接均未经验证。",
                "静态构建输入无法验证 HTTP 状态、响应头、重定向、CDN/WAF、权限回退或生产重写。",
            ]
        )
    else:
        limitations.extend(
            [
                "evidence_mode=browser_dom：报告解析外部浏览器导出的 DOM；本工具自身没有启动浏览器或执行 JavaScript。",
                "单个 DOM 快照不验证 HTTP 状态/重定向、soft-404、History API 路由、无权限回退、console 异常、失败网络请求或不同用户状态。",
            ]
        )
        if browser_provenance is None:
            limitations.append(
                "未提供通过 SHA-256、URL、浏览器、采集时间与 JavaScript 状态校验的 --browser-provenance，因此导入文件不能标为已验证客户端 DOM。"
            )
        else:
            limitations.append(
                "外部浏览器 provenance 已与导入 DOM 的 URL 和 SHA-256 配对；它仍不能证明 Googlebot 获得相同响应或渲染结果。"
            )
        if source_pages is None:
            limitations.append("未提供 --source-input，因此无法验证初始 noindex、初始 canonical 或客户端新增正文/链接。")
        else:
            limitations.append("source-vs-rendered 差异只适用于已配对页面；仍需保存 URL、浏览器状态、console/network 与真实 HTTP 证据。")
    limitations.extend(crawl_notes)

    fetch_mode = {
        "http_source": "raw-http-source",
        "static_build": "static-build-files",
        "browser_dom": "browser-exported-dom",
    }[evidence_mode]

    report = {
        "schema_version": SCHEMA_VERSION,
        "analysis_kind": "bounded_seo_artifact_inspection",
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "generated_at": utc_now(),
        "scope": {
            "mode": scope_mode,
            "evidence_mode": evidence_mode,
            "base_url": normalized_url(base_url),
            "pages_parsed": len(pages),
            "known_assets": len(assets),
            "fetches": len(fetches),
            "sitemap_urls": len(sitemap_urls),
            "robots_source": robots_source,
            "production_asserted": production,
            "fetch_mode": fetch_mode,
            "javascript_rendered": client_side_dom_verified,
            "client_side_dom_verified": client_side_dom_verified,
            "browser_provenance_verified": client_side_dom_verified,
            "browser_provenance": (
                asdict(browser_provenance) if browser_provenance is not None else None
            ),
            "http_response_verified": evidence_mode == "http_source",
            "source_comparison_provided": source_pages is not None,
            "javascript_runtime_executed_by_tool": False,
            "sitemap_seeded_crawl": False,
        },
        "summary": {
            "finding_counts": {level: severity_counts.get(level, 0) for level in SEVERITY_ORDER},
            "status_counts": dict(sorted(status_counts.items())),
            "noindex_pages": noindex_count,
            "orphan_pages_in_scope": sum(1 for url, count in inbound.items() if count == 0 and url != root_match),
            "reachable_pages_from_root": len(depths),
            "max_observed_click_depth": max(depths.values()) if depths else None,
        },
        "limitations": limitations,
        "findings": [asdict(item) for item in findings],
        "pages": [asdict(pages[url]) | {"noindex": pages[url].noindex, "inbound_links_in_scope": inbound.get(url, 0)} for url in sorted(pages)],
        "rendering_comparison": rendering_comparison,
    }
    return report


def markdown_report(report: dict[str, Any]) -> str:
    scope = report["scope"]
    summary = report["summary"]
    counts = summary["finding_counts"]
    lines = [
        "# Vibio SEO 产物检查",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 模式：{scope['mode']}",
        f"- 证据模式：`{scope['evidence_mode']}`",
        f"- 浏览器 DOM provenance 已验证：{'是' if scope['client_side_dom_verified'] else '否（客户端信号未经 JavaScript 渲染验证；导入文件没有绑定可验证的浏览器采集证据）'}",
        f"- 基准 URL：{scope['base_url']}",
        f"- 已解析页面：{scope['pages_parsed']}",
        f"- sitemap URL：{scope['sitemap_urls']}",
        f"- 发现：严重阻断 {counts['critical']} / 高 {counts['high']} / 中 {counts['medium']} / 低 {counts['low']} / 信息 {counts['info']}",
        "",
        "## 结论边界",
        "",
    ]
    lines.extend(f"- {item}" for item in report["limitations"])
    comparison = report.get("rendering_comparison")
    if comparison:
        lines.extend(
            [
                "",
                "## 源码与浏览器 DOM 对比",
                "",
                f"- 配对页面：{comparison['matched_pages']}",
                f"- 仅源码：{len(comparison['source_only_urls'])}",
                f"- 仅浏览器 DOM：{len(comparison['rendered_only_urls'])}",
                "- 每页源码/DOM SHA-256 与字段差异保存在 JSON 报告的 `rendering_comparison.pages`。",
            ]
        )
    lines.extend(["", "## 发现", ""])
    if not report["findings"]:
        lines.append("当前范围没有命中内置规则；这不代表 SEO 已完整或效果已得到证明。")
    for index, finding in enumerate(report["findings"], start=1):
        lines.extend(
            [
                f"### {index}. [{FINDING_LABELS[finding['severity']]}] {finding['observation']}",
                "",
                f"- 代码：`{finding['code']}`",
                f"- 类别：{finding['category']}",
                f"- 置信度：{finding['confidence']}",
            ]
        )
        if finding["urls"]:
            lines.append("- URL：" + "；".join(f"`{item}`" for item in finding["urls"][:20]))
        if finding["evidence"]:
            lines.append("- 证据：" + "；".join(str(item) for item in finding["evidence"][:20]))
        lines.extend(
            [
                f"- 影响边界：{finding['impact_boundary']}",
                f"- 复验：{finding['verification']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 覆盖摘要",
            "",
            f"- noindex 页面：{summary['noindex_pages']}",
            f"- 范围内无入链页面：{summary['orphan_pages_in_scope']}",
            f"- 从根页面可达：{summary['reachable_pages_from_root']}",
            f"- 已观察最大点击深度：{summary['max_observed_click_depth'] if summary['max_observed_click_depth'] is not None else '未知'}",
            "",
        ]
    )
    return "\n".join(lines)


def write_output(path: str | None, content: str) -> None:
    if path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    else:
        print(content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="区分静态构建、HTTP 源码与浏览器渲染 DOM，检查 SEO 产物并输出有证据边界的中文报告。"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--site-dir", type=Path, help="静态构建 .html 文件目录；不会执行 JavaScript")
    source.add_argument("--start-url", help="线上有限 HTTP 源码抓取起始 URL；内置抓取器不执行 JavaScript")
    source.add_argument("--rendered-dom", type=Path, help="浏览器导出的 rendered DOM .html/.htm 文件或目录")
    parser.add_argument("--source-input", type=Path, help="与 --rendered-dom 配对的初始源码 HTML 文件或目录，用于 hash 与信号差异")
    parser.add_argument(
        "--browser-provenance",
        type=Path,
        help="浏览器 DOM provenance JSON；必须按 URL 提供 DOM SHA-256、浏览器、采集时间与 JavaScript 状态",
    )
    parser.add_argument("--base-url", help="本地文件映射到的生产基准 URL；线上模式默认使用起始 URL 的 origin")
    parser.add_argument("--sitemap", help="本地 sitemap XML 路径或 sitemap URL")
    parser.add_argument("--robots", help="本地 robots.txt 路径或 robots.txt URL；线上模式默认尝试站点根路径")
    parser.add_argument("--max-pages", type=int, default=100, help="线上模式最多请求的站内 URL 数，默认 100")
    parser.add_argument("--timeout", type=float, default=15.0, help="单次网络请求超时秒数，默认 15")
    parser.add_argument(
        "--max-response-bytes",
        type=int,
        default=DEFAULT_MAX_RESPONSE_BYTES,
        help=f"单个 HTML/robots/sitemap/重定向响应最多读取的字节数，默认 {DEFAULT_MAX_RESPONSE_BYTES}",
    )
    parser.add_argument("--production", action="store_true", help="确认输入代表生产目标站；站点级阻断可升级为严重阻断")
    parser.add_argument("--json-out", help="保存完整 JSON 报告的路径")
    parser.add_argument("--markdown-out", help="保存中文 Markdown 报告的路径；未设置时输出到 stdout")
    parser.add_argument(
        "--fail-on",
        choices=["never", "critical", "high", "medium", "low"],
        default="never",
        help="当命中指定或更高严重度时返回退出码 2；默认 never",
    )
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.max_pages < 1:
        raise ValueError("--max-pages 必须大于 0")
    if args.timeout <= 0:
        raise ValueError("--timeout 必须大于 0")
    if args.max_response_bytes < 1:
        raise ValueError("--max-response-bytes 必须大于 0")

    fetches: dict[str, FetchResult] = {}
    notes: list[str] = []
    source_pages: dict[str, Page] | None = None
    source_input: str | None = None
    browser_provenance: BrowserProvenance | None = None
    if args.source_input and not args.rendered_dom:
        raise ValueError("--source-input 只能与 --rendered-dom 一起使用")
    if args.browser_provenance and not args.rendered_dom:
        raise ValueError("--browser-provenance 只能与 --rendered-dom 一起使用")
    if args.site_dir:
        site_dir = args.site_dir.resolve()
        if not site_dir.is_dir():
            raise ValueError(f"--site-dir 不是目录：{site_dir}")
        if not args.base_url or not is_http_url(args.base_url):
            raise ValueError("本地模式必须提供有效的 --base-url HTTP(S) URL")
        base_url = normalized_url(args.base_url)
        pages, assets = load_local_pages(site_dir, base_url, evidence_mode="static_build")
        mode = "local"
        evidence_mode = "static_build"
    elif args.rendered_dom:
        rendered_dom = args.rendered_dom.resolve()
        if not rendered_dom.exists():
            raise ValueError(f"--rendered-dom 不存在：{rendered_dom}")
        if not args.base_url or not is_http_url(args.base_url):
            raise ValueError("浏览器 DOM 模式必须提供有效的 --base-url HTTP(S) URL")
        base_url = normalized_url(args.base_url)
        pages, assets = load_local_pages(
            rendered_dom,
            base_url,
            evidence_mode="browser_dom",
        )
        if args.browser_provenance:
            provenance_path = args.browser_provenance.resolve()
            if not provenance_path.is_file():
                raise ValueError(f"--browser-provenance 不是文件：{provenance_path}")
            browser_provenance = load_browser_provenance(provenance_path, pages)
        if args.source_input:
            source_path = args.source_input.resolve()
            if not source_path.exists():
                raise ValueError(f"--source-input 不存在：{source_path}")
            source_pages, _ = load_local_pages(
                source_path,
                base_url,
                evidence_mode="static_build",
            )
            source_input = report_file_reference(source_path, "source-input")
        mode = "local"
        evidence_mode = "browser_dom"
    else:
        if not is_http_url(args.start_url):
            raise ValueError("--start-url 必须是 HTTP(S) URL")
        resolve_public_target(args.start_url)
        parsed = urllib.parse.urlsplit(args.start_url)
        base_url = normalized_url(args.base_url or f"{parsed.scheme}://{parsed.netloc}/")
        if origin(base_url) != origin(args.start_url):
            raise ValueError("--base-url 与 --start-url 必须属于同一 origin")
        pages, fetches, notes = crawl_remote(
            args.start_url,
            args.max_pages,
            args.timeout,
            args.max_response_bytes,
        )
        assets = set()
        mode = "remote"
        evidence_mode = "http_source"

    sitemap_urls: set[str] = set()
    sitemap_duplicates: list[str] = []
    sitemap_errors: list[str] = []
    if args.sitemap:
        sitemap_urls, sitemap_duplicates, sitemap_errors = parse_sitemap(
            args.sitemap,
            args.timeout,
            max_response_bytes=args.max_response_bytes,
        )

    robots_source: str | None = args.robots
    automatic_robots = robots_source is None and mode == "remote"
    robots: dict[str, Any] | None = None
    if automatic_robots:
        parsed = urllib.parse.urlsplit(base_url)
        robots_source = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
    if robots_source:
        try:
            robots_text, resolved = read_text_source(
                robots_source,
                args.timeout,
                allowed_origin=origin(base_url) if automatic_robots else None,
                max_response_bytes=args.max_response_bytes,
            )
            robots_source = resolved
            robots = parse_robots(robots_text)
            if not args.sitemap and robots.get("sitemaps"):
                all_urls: set[str] = set()
                all_duplicates: list[str] = []
                all_errors: list[str] = []
                for sitemap in robots["sitemaps"]:
                    sitemap_source = urllib.parse.urljoin(resolved, sitemap)
                    urls, duplicates, errors = parse_sitemap(
                        sitemap_source,
                        args.timeout,
                        allowed_origin=origin(base_url),
                        max_response_bytes=args.max_response_bytes,
                    )
                    all_urls.update(urls)
                    all_duplicates.extend(duplicates)
                    all_errors.extend(errors)
                sitemap_urls = all_urls
                sitemap_duplicates = sorted(set(all_duplicates))
                sitemap_errors = all_errors
        except (OSError, ValueError) as exc:
            notes.append(f"robots.txt 未验证：{exc}")
            robots = None
    if robots_source and not is_http_url(robots_source):
        robots_source = report_source_label(robots_source)

    return analyze(
        pages,
        base_url=base_url,
        assets=assets,
        fetches=fetches,
        sitemap_urls=sitemap_urls,
        sitemap_duplicates=sitemap_duplicates,
        sitemap_errors=sitemap_errors,
        robots=robots,
        robots_source=robots_source,
        production=args.production,
        scope_mode=mode,
        crawl_notes=notes,
        evidence_mode=evidence_mode,
        source_pages=source_pages,
        source_input=source_input,
        browser_provenance=browser_provenance,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = run(args)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    json_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        write_output(args.json_out, json_text)
    write_output(args.markdown_out, markdown_report(report))

    if args.fail_on == "never":
        return 0
    threshold = SEVERITY_ORDER[args.fail_on]
    return 2 if any(SEVERITY_ORDER[item["severity"]] <= threshold for item in report["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
