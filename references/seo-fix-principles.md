# SEO Fix Principles (stack-agnostic)

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
Key landing pages link to each other with descriptive anchors; footer/nav cover top pages; no orphan pages. Internal links pass equity to commercial pages.

### 9. Sitemap & robots
`sitemap.xml` lists all indexable URLs (generated from the same data source as the pages so it never drifts), referenced from `robots.txt`. `robots.txt` allows `/`, disallows API/admin/cart, sets the correct host.

### 10. International (if multi-language/region)
`hreflang` tags reciprocal and complete, valid language-region codes, an `x-default`. Validate with `seo-hreflang`.

### 11. AI search readiness → see §13 for the complete spec
llms.txt, AI crawler access, passage citability, entity signals, and citation quality requirements are covered in full under §13 "AI Search Readiness." This section was the original stub; §13 is the authoritative, merged specification.

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

---

## 13. AI Search Readiness (unified — traditional SEO + GEO are the same foundation)

AI-powered search (Google AI Overviews, ChatGPT, Perplexity, Bing Copilot) uses the same quality signals as traditional search. The techniques below make content rank everywhere — blue links and AI citations alike.

### llms.txt — AI crawler entry map
- Path: `/llms.txt` at site root
- Format: https://llmstxt.org — H1 title, blockquote summary, sectioned link lists with short descriptions
- Generate from the same data sources as the sitemap so it never drifts
- Each stack adapter covers implementation

### AI crawler access (robots.txt)
Do NOT block these user-agents unless you explicitly want to opt out of AI search:
- `Google-Extended` — Google AI Overviews data source
- `GPTBot` — OpenAI / ChatGPT
- `CCBot` — Common Crawl (used by multiple AI engines)
- `anthropic-ai` — Claude
- `PerplexityBot` — Perplexity

### Server-rendered content requirement
AI crawlers typically don't execute JavaScript. Critical content must be visible in the raw HTML:
```bash
curl -sL https://example.com/page | grep "critical keyword"  # Must return results
```

### Passage-level citability
Content must be structured so AI can extract self-contained answers:
- Each H2 section starts with a 40-60 word complete answer
- No cross-paragraph dependencies ("as mentioned above", "see below")
- Key data in tables/lists, not buried in prose
- First occurrence of technical terms includes a definition

### Entity signals for AI recognition
- `Organization` schema with complete `sameAs` (≥5 authoritative profile URLs)
- `WebSite` schema with full legal name (not bare domain)
- Wikidata entry (even without Wikipedia)
- Consistent entity naming across all platforms

### Citation quality
- Cited pages load in <1 second
- No paywall/login-wall on content meant to be cited
- Correct self-referential canonicals
- Multi-source data consistency (same figure everywhere)
