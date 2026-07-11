from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
import runtime.seo_inspect as seo_inspect

from runtime.seo_inspect import (
    RawHTTPResponse,
    analyze,
    canonicalize_crawl_url,
    fetch_url,
    main,
    matching_local_route,
    matching_seo_url,
    parse_page,
    parse_robots,
    parse_sitemap,
    path_blocked_by_robots,
    resolve_public_target,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime" / "seo_inspect.py"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_browser_provenance(path: Path, documents: dict[str, Path]) -> None:
    write(
        path,
        json.dumps(
            {
                "schema_version": "1.0",
                "capture_method": "Playwright page.content()",
                "browser": "Chromium 140",
                "captured_at": "2026-07-11T10:00:00+08:00",
                "javascript_enabled": True,
                "documents": [
                    {
                        "url": url,
                        "sha256": hashlib.sha256(document.read_bytes()).hexdigest(),
                    }
                    for url, document in documents.items()
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


def make_site(tmp_path: Path) -> tuple[Path, Path, Path]:
    site = tmp_path / "dist"
    write(
        site / "index.html",
        """<!doctype html>
<html lang="zh-CN"><head>
<title>Vibio 工业传感器</title>
<meta name="description" content="工业传感器选型与应用。">
<link rel="canonical" href="https://example.com/">
<link rel="alternate" hreflang="zh-CN" href="https://example.com/">
<link rel="alternate" hreflang="de-DE" href="https://example.com/de/">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebSite","name":"Vibio"}</script>
</head><body><main><h1>工业传感器</h1>
<a href="/products/">产品</a><a href="/missing/">失效入口</a>
<img src="/assets/logo.png" alt="">
</main></body></html>""",
    )
    write(
        site / "products" / "index.html",
        """<!doctype html>
<html lang="zh-CN"><head>
<title>Vibio 工业传感器</title>
<meta name="robots" content="noindex,follow">
<meta name="description" content="工业传感器选型与应用。">
<link rel="canonical" href="https://example.com/other/">
<script type="application/ld+json">{"@type":"Product",}</script>
</head><body><main><h1>产品</h1>
<a href="/">首页</a><img src="/assets/product.jpg">
</main></body></html>""",
    )
    write(
        site / "de" / "index.html",
        """<!doctype html>
<html lang="de"><head><title>Industriesensoren</title>
<meta name="description" content="Industriesensoren für Einkauf und Technik.">
<link rel="canonical" href="https://example.com/de/">
<link rel="alternate" hreflang="de-DE" href="https://example.com/de/">
<script type="application/ld+json">{"@type":"WebSite","name":"Vibio"}</script>
</head><body><main><h1>Industriesensoren</h1><a href="/">Startseite</a></main></body></html>""",
    )
    write(site / "assets" / "logo.png", "not-a-real-image")
    sitemap = tmp_path / "sitemap.xml"
    write(
        sitemap,
        """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://example.com/</loc></url>
<url><loc>https://example.com/products/</loc></url>
<url><loc>https://example.com/ghost/</loc></url>
</urlset>""",
    )
    robots = tmp_path / "robots.txt"
    write(robots, "User-agent: *\nDisallow: /private/\nNoindex: /legacy/\nSitemap: https://example.com/sitemap.xml\n")
    return site, sitemap, robots


def finding_codes(report: dict) -> set[str]:
    return {item["code"] for item in report["findings"]}


def test_local_artifact_audit_detects_signal_conflicts_and_scope_limits(tmp_path: Path) -> None:
    site, sitemap, robots = make_site(tmp_path)
    json_out = tmp_path / "report.json"
    markdown_out = tmp_path / "report.md"

    result = main(
        [
            "--site-dir",
            str(site),
            "--base-url",
            "https://example.com/",
            "--sitemap",
            str(sitemap),
            "--robots",
            str(robots),
            "--production",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    assert result == 0
    report = json.loads(json_out.read_text(encoding="utf-8"))
    codes = finding_codes(report)
    assert report["scope"]["pages_parsed"] == 3
    assert report["scope"]["mode"] == "local"
    assert report["scope"]["evidence_mode"] == "static_build"
    assert report["scope"]["javascript_rendered"] is False
    assert report["scope"]["client_side_dom_verified"] is False
    assert report["scope"]["http_response_verified"] is False
    assert all(page["status"] is None for page in report["pages"])
    assert report["scope"]["robots_source"] == "robots.txt"
    assert {page["source"] for page in report["pages"]} == {
        "index.html",
        "products/index.html",
        "de/index.html",
    }
    assert str(tmp_path) not in json.dumps(report, ensure_ascii=False)
    assert "robots.noindex" in codes
    assert "signals.noindex-cross-canonical" in codes
    assert "sitemap.noindex-url" in codes
    assert "sitemap.noncanonical-url" in codes
    assert "sitemap.url-missing-artifact" in codes
    assert "links.broken-internal" in codes
    assert "metadata.duplicate-title" in codes
    assert "structured-data.invalid-json" in codes
    assert "images.alt-attribute-missing" in codes
    assert "images.missing-local-asset" in codes
    assert "hreflang.return-link-missing" in codes
    assert "structured-data.website-multi-page" in codes
    assert "robots.unsupported-noindex" in codes
    markdown = markdown_out.read_text(encoding="utf-8")
    assert "evidence_mode=static_build" in markdown
    assert "客户端信号未经 JavaScript 渲染验证" in markdown
    assert "不保证富结果、排名或生成式 AI 展示" in markdown
    assert "健康分" in markdown


def test_browser_dom_file_compares_source_hashes_and_client_signals(tmp_path: Path) -> None:
    source = tmp_path / "source.html"
    rendered = tmp_path / "rendered.html"
    write(
        source,
        """<!doctype html><html><head><title>Loading</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="https://example.com/old/">
</head><body><div id="app"></div></body></html>""",
    )
    write(
        rendered,
        """<!doctype html><html><head><title>Product</title>
<link rel="canonical" href="https://example.com/product/">
</head><body><main><h1>Product</h1><p>Rendered product facts.</p>
<a href="/products/">Products</a><button role="link">Quote</button>
</main></body></html>""",
    )
    output = tmp_path / "report.json"
    markdown = tmp_path / "report.md"
    provenance = tmp_path / "browser-provenance.json"
    write_browser_provenance(
        provenance,
        {"https://example.com/product/": rendered},
    )

    assert main(
        [
            "--rendered-dom",
            str(rendered),
            "--source-input",
            str(source),
            "--browser-provenance",
            str(provenance),
            "--base-url",
            "https://example.com/product/",
            "--json-out",
            str(output),
            "--markdown-out",
            str(markdown),
        ]
    ) == 0

    report = json.loads(output.read_text(encoding="utf-8"))
    scope = report["scope"]
    comparison = report["rendering_comparison"]
    codes = finding_codes(report)

    assert scope["evidence_mode"] == "browser_dom"
    assert scope["fetch_mode"] == "browser-exported-dom"
    assert scope["javascript_rendered"] is True
    assert scope["client_side_dom_verified"] is True
    assert scope["browser_provenance_verified"] is True
    assert scope["browser_provenance"]["documents_verified"] == 1
    assert scope["browser_provenance"]["source"] == "browser-provenance.json"
    assert scope["http_response_verified"] is False
    assert scope["source_comparison_provided"] is True
    assert scope["javascript_runtime_executed_by_tool"] is False
    assert report["pages"][0]["status"] is None
    assert comparison["matched_pages"] == 1
    assert comparison["source_input"] == "source.html"
    assert comparison["pages"][0]["source_source"] == "source.html"
    assert comparison["pages"][0]["rendered_source"] == "rendered.html"
    assert str(tmp_path) not in json.dumps(report, ensure_ascii=False)
    assert comparison["pages"][0]["html_changed"] is True
    assert comparison["pages"][0]["source_html_sha256"] != comparison["pages"][0]["rendered_html_sha256"]
    assert comparison["pages"][0]["differences"]["canonicals"]["changed"] is True
    assert {
        "rendering.initial-noindex-removed",
        "rendering.canonical-changed",
        "rendering.content-client-only",
        "rendering.links-client-added",
        "links.non-crawlable-control",
    } <= codes
    report_markdown = markdown.read_text(encoding="utf-8")
    assert "evidence_mode=browser_dom" in report_markdown
    assert "源码与浏览器 DOM 对比" in report_markdown
    assert "soft-404" in report_markdown


def test_browser_dom_without_source_marks_initial_state_unverified(tmp_path: Path) -> None:
    rendered = tmp_path / "dom"
    write(
        rendered / "index.html",
        '<html><head><title>Home</title></head><body><main><a href="/about/">About</a></main></body></html>',
    )
    output = tmp_path / "report.json"

    assert main(
        [
            "--rendered-dom",
            str(rendered),
            "--base-url",
            "https://example.com/",
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "report.md"),
        ]
    ) == 0
    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["rendering_comparison"] is None
    assert report["scope"]["source_comparison_provided"] is False
    assert report["scope"]["javascript_rendered"] is False
    assert report["scope"]["client_side_dom_verified"] is False
    assert report["scope"]["browser_provenance_verified"] is False
    assert report["scope"]["browser_provenance"] is None
    assert any("初始 noindex" in item for item in report["limitations"])
    assert any("--browser-provenance" in item for item in report["limitations"])


def test_browser_dom_rejects_provenance_with_mismatched_hash(tmp_path: Path) -> None:
    rendered = tmp_path / "rendered.html"
    write(rendered, "<html><head><title>Verified?</title></head><body></body></html>")
    provenance = tmp_path / "browser-provenance.json"
    write_browser_provenance(
        provenance,
        {"https://example.com/": rendered},
    )
    write(rendered, "<html><head><title>Changed</title></head><body></body></html>")
    output = tmp_path / "report.json"

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--rendered-dom",
                str(rendered),
                "--browser-provenance",
                str(provenance),
                "--base-url",
                "https://example.com/",
                "--json-out",
                str(output),
                "--markdown-out",
                str(tmp_path / "report.md"),
            ]
        )
    assert exc_info.value.code == 2
    assert not output.exists()


def test_duplicate_x_robots_headers_preserve_values_and_googlebot_scope() -> None:
    page = parse_page(
        html=b"<html><head><title>X</title></head><body></body></html>",
        url="https://example.com/",
        source="fixture",
        evidence_mode="http_source",
        response_headers=[
            ("X-Robots-Tag", "otherbot: noindex"),
            ("X-Robots-Tag", "googlebot: noindex, nofollow"),
        ],
    )
    otherbot_only = parse_page(
        html=b"<html><head><title>X</title></head><body></body></html>",
        url="https://example.com/other/",
        source="fixture",
        evidence_mode="http_source",
        response_headers=[("X-Robots-Tag", "otherbot: noindex")],
    )
    google_none = parse_page(
        html=b"<html><head><title>X</title></head><body></body></html>",
        url="https://example.com/none/",
        source="fixture",
        evidence_mode="http_source",
        response_headers=[("X-Robots-Tag", "googlebot: none")],
    )

    assert page.response_headers["x-robots-tag"] == [
        "otherbot: noindex",
        "googlebot: noindex, nofollow",
    ]
    assert page.noindex is True
    assert otherbot_only.noindex is False
    assert google_none.noindex is True


def test_first_valid_base_href_resolves_canonical_links_and_images() -> None:
    page = parse_page(
        html=(
            b'<html><head><base href="javascript:alert(1)">'
            b'<base href="/catalog/"><base href="/ignored/">'
            b'<title>X</title><link rel="canonical" href="item/">'
            b'</head><body><a href="next/">Next</a>'
            b'<img src="media/photo.webp" alt="Photo"></body></html>'
        ),
        url="https://example.com/original/page/",
        source="fixture",
        evidence_mode="static_build",
    )

    assert page.document_base_url == "https://example.com/catalog/"
    assert page.canonicals == ["https://example.com/catalog/item/"]
    assert page.internal_links == ["https://example.com/catalog/next/"]
    assert [item["url"] for item in page.image_resources] == [
        "https://example.com/catalog/media/photo.webp"
    ]


def test_empty_alt_is_not_reported_but_missing_alt_is(tmp_path: Path) -> None:
    site, sitemap, robots = make_site(tmp_path)
    json_out = tmp_path / "report.json"
    main(
        [
            "--site-dir",
            str(site),
            "--base-url",
            "https://example.com/",
            "--sitemap",
            str(sitemap),
            "--robots",
            str(robots),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(tmp_path / "report.md"),
        ]
    )
    report = json.loads(json_out.read_text(encoding="utf-8"))
    image_findings = [
        item for item in report["findings"] if item["code"] == "images.alt-attribute-missing"
    ]

    assert len(image_findings) == 1
    assert image_findings[0]["urls"] == ["https://example.com/products/"]
    assert "/assets/logo.png" not in image_findings[0]["evidence"]

    missing_asset_findings = [
        item for item in report["findings"] if item["code"] == "images.missing-local-asset"
    ]
    assert len(missing_asset_findings) == 1
    assert set(missing_asset_findings[0]["urls"]) == {
        "https://example.com/products/",
        "https://example.com/assets/product.jpg",
    }
    assert all("logo.png" not in item for item in missing_asset_findings[0]["evidence"])


def test_responsive_and_lazy_images_check_real_assets_not_html_routes(tmp_path: Path) -> None:
    site = tmp_path / "dist"
    write(
        site / "index.html",
        """<html><head><title>Home</title></head><body><main>
<picture>
  <source srcset="/assets/hero-640.webp 640w, /assets/missing-1280.webp 1280w"
          data-srcset="/assets/lazy-existing.webp 1x, /assets/lazy-missing.webp 2x">
  <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yw="
       data-src="/media/photo" alt="Product">
</picture>
</main></body></html>""",
    )
    write(site / "assets" / "hero-640.webp", "asset")
    write(site / "assets" / "lazy-existing.webp", "asset")
    write(
        site / "media" / "photo" / "index.html",
        "<html><head><title>HTML route</title></head><body></body></html>",
    )
    output = tmp_path / "report.json"

    assert main(
        [
            "--site-dir",
            str(site),
            "--base-url",
            "https://example.com/",
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "report.md"),
        ]
    ) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    page = next(item for item in report["pages"] if item["url"] == "https://example.com/")
    missing = next(
        item for item in report["findings"] if item["code"] == "images.missing-local-asset"
    )

    assert {(item["element"], item["attribute"], item["url"]) for item in page["image_resources"]} == {
        ("source", "srcset", "https://example.com/assets/hero-640.webp"),
        ("source", "srcset", "https://example.com/assets/missing-1280.webp"),
        ("source", "data-srcset", "https://example.com/assets/lazy-existing.webp"),
        ("source", "data-srcset", "https://example.com/assets/lazy-missing.webp"),
        ("img", "data-src", "https://example.com/media/photo"),
    }
    assert set(missing["urls"]) == {
        "https://example.com/",
        "https://example.com/assets/missing-1280.webp",
        "https://example.com/assets/lazy-missing.webp",
        "https://example.com/media/photo",
    }
    assert "images.alt-attribute-missing" not in finding_codes(report)


def test_robots_longest_match_and_allow_tie() -> None:
    parsed = parse_robots(
        "User-agent: *\nDisallow: /\nAllow: /public/\nDisallow: /public/private/\n"
    )

    assert path_blocked_by_robots("https://example.com/", parsed) is True
    assert path_blocked_by_robots("https://example.com/public/page", parsed) is False
    assert path_blocked_by_robots("https://example.com/public/private/a", parsed) is True


def test_robots_wildcard_end_anchor_and_specific_user_agent() -> None:
    parsed = parse_robots(
        "User-agent: *\nDisallow: /public/\n"
        "User-agent: Googlebot\nDisallow: /*?sort=*\nAllow: /public/\nDisallow: /private$\n"
    )

    assert path_blocked_by_robots("https://example.com/public/page", parsed) is False
    assert path_blocked_by_robots("https://example.com/list?sort=price", parsed) is True
    assert path_blocked_by_robots("https://example.com/private", parsed) is True
    assert path_blocked_by_robots("https://example.com/private/more", parsed) is False


def test_url_normalization_keeps_business_parameters_but_drops_tracking() -> None:
    normalized = canonicalize_crawl_url(
        "https://EXAMPLE.com/products/?size=30mm&utm_source=ad&gclid=secret#spec"
    )

    assert normalized == "https://example.com/products/?size=30mm"


def test_seo_url_matching_does_not_collapse_business_parameters() -> None:
    candidates = {"https://example.com/products/"}

    assert matching_seo_url("https://example.com/products/?size=30mm", candidates) is None
    assert matching_local_route(
        "https://example.com/products/?size=30mm", candidates
    ) == "https://example.com/products/"


def test_link_edges_keep_anchor_and_rel_without_collapsing_query_variants() -> None:
    page = parse_page(
        html=(
            b'<html><head><title>X</title></head><body>'
            b'<a href="/products/?size=30mm&utm_source=nav" rel="nofollow sponsored">'
            b'30 mm tube</a></body></html>'
        ),
        url="https://example.com/",
        source="fixture",
        evidence_mode="http_source",
    )

    assert page.internal_links == ["https://example.com/products/?size=30mm"]
    assert page.link_edges == [
        {
            "source": "https://example.com/",
            "target": "https://example.com/products/?size=30mm",
            "anchor": "30 mm tube",
            "rel": ["nofollow", "sponsored"],
        }
    ]


def test_parameter_link_resolves_to_static_base_without_false_broken_link(tmp_path: Path) -> None:
    site = tmp_path / "dist"
    write(
        site / "index.html",
        '<html><head><title>Home</title></head><body><a href="/products/?size=30mm">30 mm</a></body></html>',
    )
    write(
        site / "products/index.html",
        '<html><head><title>Products</title></head><body><a href="/">Home</a></body></html>',
    )
    output = tmp_path / "report.json"

    assert main(
        [
            "--site-dir",
            str(site),
            "--base-url",
            "https://example.com/",
            "--json-out",
            str(output),
            "--markdown-out",
            str(tmp_path / "report.md"),
        ]
    ) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    codes = finding_codes(report)

    assert "links.parameter-url-observed" in codes
    assert "links.broken-internal" not in codes


def test_fail_on_high_returns_two_but_still_writes_reports(tmp_path: Path) -> None:
    site, sitemap, robots = make_site(tmp_path)
    json_out = tmp_path / "report.json"

    result = main(
        [
            "--site-dir",
            str(site),
            "--base-url",
            "https://example.com/",
            "--sitemap",
            str(sitemap),
            "--robots",
            str(robots),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(tmp_path / "report.md"),
            "--fail-on",
            "high",
        ]
    )

    assert result == 2
    assert json_out.is_file()


def test_remote_mode_records_each_redirect_hop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        seo_inspect.socket,
        "getaddrinfo",
        lambda host, port, **kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", port),
            )
        ],
    )
    responses = iter(
        [
            RawHTTPResponse(301, (("Location", "/middle"),), b""),
            RawHTTPResponse(302, (("Location", "/final"),), b""),
            RawHTTPResponse(
                200,
                (("Content-Type", "text/html"),),
                b"<html><head><title>Final</title></head><body><main>OK</main></body></html>",
            ),
        ]
    )
    monkeypatch.setattr(
        seo_inspect,
        "_fetch_once",
        lambda target, timeout, max_response_bytes: next(responses),
    )

    result = fetch_url(
        "https://example.com/start",
        1,
        allowed_origin=("https", "example.com"),
    )
    page = parse_page(
        html=result.body,
        url=result.final_url,
        requested_url=result.requested_url,
        final_url=result.final_url,
        source=result.final_url,
        status=result.status,
        content_type=result.content_type,
        response_headers=result.headers,
        redirect_chain=result.redirect_chain,
    )
    report = analyze(
        {page.url: page},
        base_url="https://example.com/",
        assets=set(),
        fetches={},
        sitemap_urls=set(),
        sitemap_duplicates=[],
        sitemap_errors=[],
        robots=None,
        robots_source=None,
        production=False,
        scope_mode="remote",
        crawl_notes=[],
    )

    assert [hop["status"] for hop in report["pages"][0]["redirect_chain"]] == [301, 302]
    assert "http.redirect-chain" in finding_codes(report)
    assert report["scope"]["fetch_mode"] == "raw-http-source"
    assert report["scope"]["evidence_mode"] == "http_source"
    assert report["scope"]["javascript_rendered"] is False
    assert any("有界 HTTP 抓取器只读取响应源码" in item for item in report["limitations"])


@pytest.mark.parametrize(
    "addresses",
    [
        ["127.0.0.1"],
        ["10.0.0.8"],
        ["169.254.169.254"],
        ["::1"],
        ["fc00::1"],
        ["93.184.216.34", "127.0.0.1"],
    ],
)
def test_public_fetch_target_rejects_private_local_and_mixed_dns(
    monkeypatch: pytest.MonkeyPatch,
    addresses: list[str],
) -> None:
    def fake_getaddrinfo(host: str, port: int, **_kwargs):
        records = []
        for address in addresses:
            family = socket.AF_INET6 if ":" in address else socket.AF_INET
            sockaddr = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
            records.append((family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr))
        return records

    monkeypatch.setattr(seo_inspect.socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(ValueError, match="非公网地址"):
        resolve_public_target("https://audit.example/path")


def test_public_fetch_target_pins_validated_public_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        seo_inspect.socket,
        "getaddrinfo",
        lambda host, port, **kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", port),
            )
        ],
    )

    target = resolve_public_target("https://audit.example/path?q=seo")

    assert target.sockaddr == ("93.184.216.34", 443)
    assert target.hostname == "audit.example"
    assert target.host_header == "audit.example"
    assert target.request_target == "/path?q=seo"


def test_fetch_retries_next_validated_public_ip_after_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        seo_inspect.socket,
        "getaddrinfo",
        lambda host, port, **kwargs: [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("2001:4860:4860::8888", port, 0, 0),
            ),
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", port),
            ),
        ],
    )
    attempts: list[tuple] = []

    def fake_fetch_once(target, timeout, max_response_bytes):
        attempts.append(target.sockaddr)
        if target.family == socket.AF_INET6:
            raise OSError("IPv6 route unavailable")
        return RawHTTPResponse(
            200,
            (("Content-Type", "text/html"),),
            b"<html><body>ok</body></html>",
        )

    monkeypatch.setattr(seo_inspect, "_fetch_once", fake_fetch_once)

    result = fetch_url("https://audit.example/", 1)

    assert result.status == 200
    assert attempts == [
        ("2001:4860:4860::8888", 443, 0, 0),
        ("93.184.216.34", 443),
    ]


def test_private_redirect_is_blocked_before_second_network_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_getaddrinfo(host: str, port: int, **_kwargs):
        address = "93.184.216.34" if host == "audit.example" else "127.0.0.1"
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (address, port),
            )
        ]

    network_requests: list[str] = []

    def fake_fetch_once(target, timeout, max_response_bytes):
        network_requests.append(target.url)
        return RawHTTPResponse(
            302,
            (("Location", "http://internal.example/admin"),),
            b"",
        )

    monkeypatch.setattr(seo_inspect.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(seo_inspect, "_fetch_once", fake_fetch_once)

    result = fetch_url("https://audit.example/start", 1)

    assert result.status is None
    assert "非公网地址" in result.error
    assert network_requests == ["https://audit.example/start"]
    assert result.redirect_chain[0]["location"] == "http://internal.example/admin"


def test_dns_rebinding_on_same_host_is_blocked_before_second_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolutions = iter(["93.184.216.34", "127.0.0.1"])

    def fake_getaddrinfo(host: str, port: int, **_kwargs):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (next(resolutions), port),
            )
        ]

    network_requests: list[tuple[str, tuple]] = []

    def fake_fetch_once(target, timeout, max_response_bytes):
        network_requests.append((target.url, target.sockaddr))
        return RawHTTPResponse(302, (("Location", "/next"),), b"")

    monkeypatch.setattr(seo_inspect.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(seo_inspect, "_fetch_once", fake_fetch_once)

    result = fetch_url("https://audit.example/start", 1)

    assert result.status is None
    assert "非公网地址" in result.error
    assert network_requests == [
        ("https://audit.example/start", ("93.184.216.34", 443))
    ]


def test_same_origin_fetch_policy_blocks_cross_origin_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        seo_inspect.socket,
        "getaddrinfo",
        lambda host, port, **kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", port),
            )
        ],
    )
    network_requests: list[str] = []

    def fake_fetch_once(target, timeout, max_response_bytes):
        network_requests.append(target.url)
        return RawHTTPResponse(
            302,
            (("Location", "https://cdn.example/sitemap.xml"),),
            b"",
        )

    monkeypatch.setattr(seo_inspect, "_fetch_once", fake_fetch_once)

    result = fetch_url(
        "https://audit.example/sitemap.xml",
        1,
        allowed_origin=("https", "audit.example"),
    )

    assert result.status is None
    assert "不属于允许的同源范围" in result.error
    assert network_requests == ["https://audit.example/sitemap.xml"]


def test_declared_response_size_is_rejected_before_body_read() -> None:
    class Headers:
        @staticmethod
        def get_all(name: str, failobj=None):
            return ["101"] if name == "Content-Length" else failobj

    class Response:
        headers = Headers()

        @staticmethod
        def read(limit: int) -> bytes:
            raise AssertionError("超限 Content-Length 不应读取 body")

    with pytest.raises(seo_inspect.ResponseTooLargeError, match="声明大小超过"):
        seo_inspect._read_bounded_response_body(Response(), 100)


def test_actual_response_size_is_bounded_when_content_length_is_missing() -> None:
    reads: list[int] = []

    class Headers:
        @staticmethod
        def get_all(name: str, failobj=None):
            return failobj

    class Response:
        headers = Headers()

        @staticmethod
        def read(limit: int) -> bytes:
            reads.append(limit)
            return b"x" * limit

    with pytest.raises(seo_inspect.ResponseTooLargeError, match="实际大小超过"):
        seo_inspect._read_bounded_response_body(Response(), 100)
    assert reads == [101]


def test_same_origin_recursive_sitemap_cannot_switch_to_cdn(tmp_path: Path) -> None:
    sitemap = tmp_path / "index.xml"
    write(
        sitemap,
        "<sitemapindex><sitemap><loc>https://cdn.example/child.xml</loc></sitemap></sitemapindex>",
    )

    urls, duplicates, errors = parse_sitemap(
        str(sitemap),
        1,
        allowed_origin=("https", "example.com"),
    )

    assert urls == set()
    assert duplicates == []
    assert len(errors) == 1
    assert "不属于允许的同源范围" in errors[0]
    assert str(tmp_path) not in errors[0]


def test_sitemap_ignores_image_and_video_loc_elements(tmp_path: Path) -> None:
    sitemap = tmp_path / "sitemap.xml"
    write(
        sitemap,
        """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
  <url>
    <loc>https://example.com/product/</loc>
    <image:image><image:loc>https://cdn.example/product.jpg</image:loc></image:image>
    <video:video><video:loc>https://cdn.example/product.mp4</video:loc></video:video>
  </url>
</urlset>""",
    )

    urls, duplicates, errors = parse_sitemap(str(sitemap), 1)

    assert urls == {"https://example.com/product/"}
    assert duplicates == []
    assert errors == []


def test_remote_crawl_passes_same_origin_policy_to_every_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, tuple[str, str] | None]] = []

    def fake_fetch(url: str, timeout: float, **kwargs):
        calls.append((url, kwargs.get("allowed_origin")))
        return seo_inspect.FetchResult(
            requested_url=url,
            final_url=url,
            status=200,
            content_type="text/html",
            headers={},
            body=b"<html><body></body></html>",
        )

    monkeypatch.setattr(seo_inspect, "fetch_url", fake_fetch)

    seo_inspect.crawl_remote("https://audit.example/", 1, 1)

    assert calls == [("https://audit.example/", ("https", "audit.example"))]


def test_remote_crawl_discards_consumed_response_bodies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = b"<html><head><title>Home</title></head><body><main>OK</main></body></html>"

    def fake_fetch(url: str, timeout: float, **kwargs):
        return seo_inspect.FetchResult(
            requested_url=url,
            final_url=url,
            status=200,
            content_type="text/html",
            headers={},
            body=body,
        )

    monkeypatch.setattr(seo_inspect, "fetch_url", fake_fetch)

    pages, fetches, errors = seo_inspect.crawl_remote(
        "https://audit.example/", 1, 1
    )

    assert errors == []
    assert pages["https://audit.example/"].html_sha256 == hashlib.sha256(body).hexdigest()
    assert fetches["https://audit.example/"].body == b""


def test_automatic_robots_fetch_uses_same_origin_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, tuple[str, str] | None]] = []
    monkeypatch.setattr(seo_inspect, "resolve_public_target", lambda _url: None)
    monkeypatch.setattr(
        seo_inspect,
        "crawl_remote",
        lambda *_args, **_kwargs: ({}, {}, []),
    )

    def fake_read(value: str, timeout: float, **kwargs):
        observed.append((value, kwargs.get("allowed_origin")))
        return "User-agent: *\n", value

    monkeypatch.setattr(seo_inspect, "read_text_source", fake_read)
    args = seo_inspect.build_parser().parse_args(
        ["--start-url", "https://audit.example/"]
    )

    seo_inspect.run(args)

    assert observed == [
        ("https://audit.example/robots.txt", ("https", "audit.example"))
    ]


def test_script_runs_directly_outside_repository() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd="/tmp",
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "浏览器渲染 DOM" in result.stdout
    assert "内置抓取器不执行 JavaScript" in result.stdout
    assert "严重阻断" in result.stdout
