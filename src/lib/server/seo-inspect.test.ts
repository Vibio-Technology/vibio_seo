import { describe, expect, it } from "vitest";

import { POST as inspectRoute } from "../../app/api/inspect/route";
import {
  assertPublicAddressSet,
  isAllowedByRobots,
  isPublicIpAddress,
  originKey,
  parseHtmlDocument,
  parseRobotsDocument,
  parseSitemapXml,
  resolvePublicTarget,
  validateAuditUrl,
} from "./seo-inspect";

describe("POST /api/inspect", () => {
  it("rejects oversized requests before parsing the body", async () => {
    const response = await inspectRoute(
      new Request("http://localhost/api/inspect", {
        method: "POST",
        headers: { "content-length": String(16 * 1024 + 1) },
        body: "{}",
      }),
    );
    expect(response.status).toBe(413);
    expect(await response.json()).toEqual({ detail: "请求体过大。" });
  });

  it("requires a BYOK session before making a public network request", async () => {
    const response = await inspectRoute(
      new Request("http://localhost/api/inspect", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ url: "https://example.com/", max_pages: 1, production: false }),
      }),
    );
    expect(response.status).toBe(401);
  });

  it("rejects private IP targets without issuing a network request", async () => {
    const response = await inspectRoute(
      new Request("http://localhost/api/inspect", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "X-Vibio-Api-Key": "temporary-test-key",
        },
        body: JSON.stringify({ url: "http://127.0.0.1/", max_pages: 1, production: false }),
      }),
    );
    expect(response.status).toBe(400);
    expect(JSON.stringify(await response.json())).toContain("非公网地址");
  });
});

describe("parseHtmlDocument", () => {
  it("extracts source-visible SEO evidence without executing scripts", () => {
    const page = parseHtmlDocument(
      `<!doctype html>
      <html lang="de-DE">
        <head>
          <base href="https://example.com/catalog/">
          <title> Industrial Pumps </title>
          <meta name="description" content="Pump systems for factories">
          <meta name="robots" content="index, follow">
          <link rel="canonical" href="/products/pumps">
          <link rel="alternate" hreflang="en" href="/en/pumps">
          <script type="application/ld+json">{"@context":"https://schema.org","@type":["Product","Thing"]}</script>
        </head>
        <body>
          <main><h1>Pumps</h1><h2>Specifications</h2></main>
          <a href="../products/pumps?utm_source=test#details" rel="next">Details</a>
          <a href="https://other.example/resource">External</a>
          <img src="/images/pump.jpg" width="800" alt="Industrial pump">
          <img src="/images/detail.jpg">
        </body>
      </html>`,
      "https://example.com/start",
      { "x-robots-tag": ["googlebot: noarchive"] },
    );

    expect(page.titles).toEqual(["Industrial Pumps"]);
    expect(page.descriptions).toEqual(["Pump systems for factories"]);
    expect(page.robots).toEqual(["follow", "index", "noarchive"]);
    expect(page.canonicals).toEqual(["https://example.com/products/pumps"]);
    expect(page.hreflang).toEqual([{ lang: "en", url: "https://example.com/en/pumps" }]);
    expect(page.headings).toEqual([
      { level: 1, text: "Pumps" },
      { level: 2, text: "Specifications" },
    ]);
    expect(page.internal_links).toEqual(["https://example.com/products/pumps"]);
    expect(page.external_links).toEqual(["https://other.example/resource"]);
    expect(page.json_ld_types).toEqual(["Product", "Thing"]);
    expect(page.images).toEqual([
      expect.objectContaining({ src: "https://example.com/images/pump.jpg", alt_present: true, alt: "Industrial pump" }),
      expect.objectContaining({ src: "https://example.com/images/detail.jpg", alt_present: false, alt: "" }),
    ]);
    expect(page.h1_count).toBe(1);
    expect(page.main_count).toBe(1);
    expect(page.html_lang).toBe("de-DE");
  });

  it("records invalid JSON-LD and combines meta/header noindex evidence", () => {
    const page = parseHtmlDocument(
      `<html><head><meta name="robots" content="none"><script type="application/ld+json">{broken</script></head><body>Text</body></html>`,
      "https://example.com/",
      { "x-robots-tag": ["nofollow"] },
    );
    expect(page.noindex).toBe(true);
    expect(page.robots).toEqual(["nofollow", "noindex", "none"]);
    expect(page.json_ld_errors).toEqual(["JSON-LD script 1 is not valid JSON"]);
    expect(page.visible_text_length).toBe(4);
  });
});

describe("network target guards", () => {
  it.each([
    "127.0.0.1",
    "10.0.0.1",
    "100.64.0.1",
    "169.254.169.254",
    "172.16.0.1",
    "192.168.1.1",
    "198.51.100.10",
    "203.0.113.10",
    "::1",
    "fc00::1",
    "fe80::1",
    "2001:db8::1",
    "::ffff:127.0.0.1",
  ])("rejects non-public address %s", (address) => {
    expect(isPublicIpAddress(address)).toBe(false);
  });

  it.each(["8.8.8.8", "1.1.1.1", "2606:4700:4700::1111"])("accepts public address %s", (address) => {
    expect(isPublicIpAddress(address)).toBe(true);
  });

  it("rejects a mixed public/private DNS answer", () => {
    expect(() =>
      assertPublicAddressSet("example.com", [
        { address: "93.184.216.34", family: 4 },
        { address: "127.0.0.1", family: 4 },
      ]),
    ).toThrow(/非公网地址/);
  });

  it("uses injected DNS evidence and enforces the allowed origin without network access", async () => {
    const resolver = async () => [{ address: "93.184.216.34", family: 4 as const }];
    const start = validateAuditUrl("https://example.com/path");
    const target = await resolvePublicTarget(start, originKey(start), resolver);
    expect(target.addresses).toEqual([{ address: "93.184.216.34", family: 4 }]);
    await expect(resolvePublicTarget("https://www.example.com/", originKey(start), resolver)).rejects.toThrow(/同源/);
  });

  it.each([
    "ftp://example.com/file",
    "https://user:secret@example.com/",
    "http://localhost/",
    "http://127.0.0.1/",
    "https://example.com:8443/",
    " https://example.com/",
  ])("rejects unsafe URL input %s", async (url) => {
    await expect(resolvePublicTarget(url, undefined, async () => [])).rejects.toThrow();
  });
});

describe("robots and sitemap parsing", () => {
  it("applies the longest matching allow rule", () => {
    const robots = parseRobotsDocument(
      `User-agent: *\nDisallow: /private/\nAllow: /private/public/\nSitemap: https://example.com/sitemap.xml`,
      "https://example.com/robots.txt",
    );
    expect(isAllowedByRobots(new URL("https://example.com/private/report"), robots)).toBe(false);
    expect(isAllowedByRobots(new URL("https://example.com/private/public/page"), robots)).toBe(true);
    expect(robots.sitemaps).toEqual(["https://example.com/sitemap.xml"]);
  });

  it("extracts URL sets and sitemap indexes without resolving external entities", () => {
    expect(
      parseSitemapXml(`<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/a</loc></url></urlset>`),
    ).toEqual({ pageUrls: ["https://example.com/a"], sitemapUrls: [] });
    expect(
      parseSitemapXml(`<sitemapindex><sitemap><loc>https://example.com/products.xml</loc></sitemap></sitemapindex>`),
    ).toEqual({ pageUrls: [], sitemapUrls: ["https://example.com/products.xml"] });
  });
});
