# SEO Fix Principles (stack-agnostic)

<!-- SYNCED COPY. Authoritative source: vibio-fix/references/seo-fix-principles.md.
     vibio-audit carries its own copy so it stays self-contained when installed alone.
     If you edit the spec, update both copies. -->

The target spec for what correct SEO output looks like, independent of how the site is built. Every SEO problem shows up in the **rendered HTML + HTTP responses** — not in the source language. So the fix is always two layers:

1. **Target spec (this file)** — what the rendered `<head>`, JSON-LD, robots, sitemap, status codes *should* be. Same for every stack.
2. **Landing method (`stack-adapters/<stack>.md`)** — where and how to make that true in a specific stack (Next.js / WordPress / Shopify / static / URL-only).

Diagnose and define the target from this file; then open the matching adapter for the concrete edit. If you only have a URL and no code, use `stack-adapters/url-only.md` to hand the user a precise spec + snippet to paste.

**Golden rule:** every SEO truth must be verifiable in the *rendered* output, not just the source. After any change, fetch/inspect the served HTML (or build output) and confirm the intended tag is actually there. SERP-facing changes only appear after the search engine re-crawls — tell the user to request indexing in Search Console.

---

## The target spec — what correct looks like

### 1. Metadata coverage
Every indexable page emits a unique `<title>` and `<meta name="description">`. Titles ~50-60 chars, descriptions ~150-160, both unique per page, both reflecting the page's primary intent. Redirect/utility pages exempt.

### 2. Canonical
Every indexable page declares `<link rel="canonical">` pointing to its own clean absolute URL (one canonical host, https, no tracking params). Self-referential by default; cross-canonical only for genuine duplicates.

### 3. Indexability
`<meta name="robots">` does **not** say `noindex` on pages you want ranked (the #1 silent killer — check it first). `robots.txt` doesn't block important paths or CSS/JS needed to render. Status codes are honest: 200 for live pages, 301 for moved, 404/410 for gone, no soft-404s.

### 4. Structured data (JSON-LD)
Site-wide `Organization` + `WebSite`. Page-type specific where relevant: `Product` (+`Offer`/`AggregateRating`) on product pages, `Article`/`BlogPosting` on posts, `BreadcrumbList` on nested pages, `FAQPage` on FAQ sections, `LocalBusiness` for physical/service-area businesses. Valid against schema.org, no required-field warnings. Validate with the `seo-schema` skill.

### 5. Open Graph / Twitter
`og:title`, `og:description`, `og:url`, `og:type`, `og:site_name` (set to the brand/legal name, not the domain), and a real `og:image`. OG image is landscape ~1.91:1 (1200×630 ideal); declared `width`/`height` must match the actual file; a representative photo beats a bare logo. `twitter:card` = `summary_large_image`.

### 6. Headings
Exactly one `<h1>` per page, reflecting the primary keyword/intent. No level skips (h1→h3). Headings describe content, not styling.

### 7. Images
Every meaningful image has descriptive `alt`. Modern formats (WebP/AVIF) where possible, explicit dimensions to prevent CLS, lazy-load below the fold. Use the `seo-images` skill for depth; generate missing OG/hero images with `seo-image-gen`.

### 8. Internal linking
Key landing pages link to each other with descriptive anchors; footer/nav cover top pages; no orphan pages. Internal links pass equity to commercial pages: money pages ≤3 clicks from home, 2-5 contextual in-content links per 1,000 words, every new page gets 2-3 inbound links from existing pages on publish day. Full operational manual (topology, anchor bank, backfill protocol, audits): 主库 `references/link-architecture.md`.

### 9. Sitemap & robots
`sitemap.xml` lists all indexable URLs (generated from the same data source as the pages so it never drifts), referenced from `robots.txt`. `robots.txt` allows `/`, disallows API/admin/cart, sets the correct host.

### 10. International (if multi-language/region)
`hreflang` tags reciprocal and complete, valid language-region codes, an `x-default`. Validate with `seo-hreflang`.

### 11. AI search / GEO
`llms.txt` present at the root (https://llmstxt.org format: H1 title, blockquote summary, sectioned link lists). Content is passage-citable. Deepen with `seo-geo`.

### 12. Brand in the SERP (two distinct mechanisms — people conflate them)
- **Site-name line** (under the title) comes from `WebSite` JSON-LD `name` + `og:site_name`. If neither states the full name, the engine falls back to the bare domain. Fix: `WebSite` JSON-LD with legal `name` + short `alternateName`, and `og:site_name` = legal name.
- **Bold highlighting** when someone searches your company name comes from the query matching text in your meta description / indexed copy. If the full legal name never appears there, nothing highlights. Fix: include the full legal name naturally in the homepage description and visible copy.
Both only show after re-crawl.

---

## Verification (stack-agnostic)

The check is always against rendered output. Pick whichever applies:

- **Have a build step / served site:** fetch the page and grep the HTML.
  ```bash
  # served URL
  curl -sL https://example.com/ | grep -oiE '<title>[^<]*|name="description"[^>]*|rel="canonical"[^>]*|property="og:site_name"[^>]*|"@type":"(Organization|WebSite|Product|Article)"'
  # or a build output dir (Next.js .next/server, Astro dist, Hugo public, etc.)
  grep -oE 'property="og:site_name" content="[^"]*"' <build-dir>/index.html
  ```
- **Code change in a known stack:** run that stack's build/lint, then grep the produced HTML (see the adapter).
- **No code (URL-only):** re-fetch after the user applies the change and confirm.

Report exactly what passed and what can't be verified yet (live SERP changes pending re-crawl). For OG/social, remind the user to re-scrape via the platform debuggers (Facebook Sharing Debugger, LinkedIn Post Inspector, Twitter Card Validator) — they cache.

---

## Priority when fixing

Fix in impact order, not file order:
1. **Indexability blockers** — stray `noindex`, robots blocks, wrong canonicals, soft-404s. (A perfect page that's `noindex` ranks nowhere.)
2. **Missing/duplicate titles & descriptions** on commercial pages.
3. **Structured data** for brand SERP + rich results.
4. **OG/social correctness.**
5. **Internal linking, headings, images, llms.txt** — optimization layer.

Always confirm there's no indexability blocker before optimizing anything downstream.
