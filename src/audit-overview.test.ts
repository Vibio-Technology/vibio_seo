import { describe, expect, it } from "vitest";

import { parseAuditOverview } from "./audit-overview";

function report(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    analysis_kind: "bounded_seo_artifact_inspection",
    scope: {
      base_url: "https://example.com/",
      evidence_mode: "http_source",
      pages_parsed: 2,
      fetches: 5,
      sitemap_urls: 8,
    },
    findings: [],
    pages: [],
    limitations: [],
    ...overrides,
  };
}

function finding(
  code: string,
  category: string,
  severity: "critical" | "high" | "medium" | "low" | "info",
): Record<string, unknown> {
  return {
    code,
    category,
    severity,
    observation: `${code} observation`,
    evidence: [`${code}=observed`],
    urls: ["https://example.com/path"],
    impact_boundary: "Only the bounded HTTP source was observed.",
    verification: "Fetch the same URL again.",
    confidence: "high",
  };
}

describe("parseAuditOverview", () => {
  it("returns null for absent, malformed, or unrelated reports", () => {
    expect(parseAuditOverview(undefined)).toBeNull();
    expect(parseAuditOverview([])).toBeNull();
    expect(parseAuditOverview({ analysis_kind: "other", findings: [] })).toBeNull();
  });

  it("tolerates malformed fields without inventing findings or metrics", () => {
    const parsed = parseAuditOverview(report({
      scope: "invalid",
      findings: [
        null,
        { severity: "high", observation: 12 },
        { severity: "unknown", observation: "unsupported severity" },
      ],
      pages: [null, { url: 42 }, { final_url: "https://example.com/final", status: "200" }],
      limitations: ["Known boundary", 42, "  "],
    }));

    expect(parsed).not.toBeNull();
    expect(parsed?.scope).toEqual({
      baseUrl: null,
      evidenceMode: null,
      pagesParsed: 1,
      fetches: null,
      sitemapUrls: null,
    });
    expect(parsed?.severityCounts).toEqual({ critical: 0, high: 0, medium: 0, low: 0, info: 0 });
    expect(parsed?.groups).toHaveLength(4);
    expect(parsed?.pages).toEqual([
      expect.objectContaining({ url: "https://example.com/final", status: null }),
    ]);
    expect(parsed?.limitations).toEqual(["Known boundary"]);
  });

  it("groups valid findings, derives severity counts, and puts unknown categories in other", () => {
    const parsed = parseAuditOverview(report({
      findings: [
        finding("http.server-error", "http", "critical"),
        finding("sitemap.noindex-url", "url-signals", "high"),
        finding("canonical.missing", "url-signals", "high"),
        finding("structured-data.invalid-json", "structured-data", "medium"),
        finding("links.internal-http-error", "internal-links", "low"),
        finding("future.unmapped", "future-category", "info"),
      ],
      pages: [
        {
          url: "https://example.com/",
          status: 200,
          content_type: "text/html",
          titles: ["Example"],
          canonicals: ["https://example.com/"],
          noindex: false,
          h1_count: 1,
          depth: 0,
          inbound_links_in_scope: 2,
          internal_links: ["https://example.com/a", "https://example.com/b"],
        },
      ],
      limitations: ["Does not execute JavaScript."],
    }));

    expect(parsed?.scope).toMatchObject({ pagesParsed: 2, fetches: 5, sitemapUrls: 8 });
    expect(parsed?.severityCounts).toEqual({ critical: 1, high: 2, medium: 1, low: 1, info: 1 });
    expect(parsed?.groups.map((group) => [group.id, group.findings.map((item) => item.code)])).toEqual([
      ["access", ["http.server-error", "sitemap.noindex-url"]],
      ["page-signals", ["canonical.missing"]],
      ["content", ["structured-data.invalid-json"]],
      ["discovery", ["links.internal-http-error"]],
      ["other", ["future.unmapped"]],
    ]);
    expect(parsed?.pages[0]).toEqual({
      url: "https://example.com/",
      status: 200,
      contentType: "text/html",
      title: "Example",
      canonical: "https://example.com/",
      noindex: false,
      h1Count: 1,
      depth: 0,
      inboundLinks: 2,
      internalLinks: 2,
    });
    expect(parsed).not.toHaveProperty("score");
    expect(parsed?.groups.every((group) => !("score" in group))).toBe(true);
  });
});
