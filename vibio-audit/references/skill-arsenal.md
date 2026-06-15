# Skill Arsenal

Vibio's SEO work is backed by 27 specialist sub-skills. This skill's job is to **route** to them and synthesize results — not to re-implement their analysis by hand.

How to use this file:
- Match the user's need to a skill below.
- Fire independent skills in parallel when doing a broad audit.
- If a skill depends on an MCP server or API key that isn't available, note it and fall back to source-level inspection.
- After a skill returns, integrate its findings into the prioritized output — don't just relay raw dumps.

## Tier 1 — Orchestration & strategy

### seo
Comprehensive SEO analysis for any site or business type. Full audits, single-page analysis, technical, schema, content (E-E-A-T), images, sitemap, and GEO. The generalist entry point when the request is broad but you want one skill to coordinate.

### seo-audit
Full website audit with parallel sub-agent delegation. Crawls up to 500 pages, detects business type, delegates to up to 15 specialists, produces a 0–100 health score and a prioritized action plan. Fire when the user says "audit", "full SEO check", "analyze my site", "website health check". Best for live sites.

### seo-plan
Strategic SEO planning for new or existing sites: industry templates, competitive analysis, content strategy, implementation roadmap. Fire for "SEO plan/strategy", "keyword strategy", "content calendar".

### b2b-seo
B2B/SaaS-focused strategist: B2B keyword research, buyer-journey content, enterprise SEO strategy, content plans. **Default strategy skill for Vibio's export-manufacturing/B2B clients.**

## Tier 2 — Page & content

### seo-page
Deep single-page analysis: on-page elements, content quality, technical meta, schema, images, performance. Fire for "analyze this page", "check this URL".

### seo-content
Content quality and E-E-A-T analysis with AI-citation-readiness scoring. Fire for "content quality", "E-E-A-T", "readability", "thin content", "content audit".

### seo-content-brief
Competitive content briefs with per-section word counts, competitor scoring, keyword-density guidance, page-type templates. Supports both new-page and improve-existing-page briefs. Fire for "content brief", "outline", "blog brief".

### seo-cluster
SERP-overlap-based semantic topic clustering (groups by actual Google SERP overlap, not text similarity). Designs hub-and-spoke clusters with internal-link matrices. Fire for "topic clusters", "content architecture", "pillar pages".

### seo-programmatic
Programmatic SEO for pages generated at scale from data: template engines, URL patterns, internal-linking automation, thin-content safeguards, index-bloat prevention. Fire for "programmatic SEO", "pages at scale", "dynamic pages".

### seo-competitor-pages
Generates "X vs Y", "alternatives to X", feature-matrix, comparison pages with schema and conversion optimization. Fire for "comparison page", "vs page", "alternatives page".

## Tier 3 — Technical & structured data

### seo-technical
Technical audit across 9 categories: crawlability, indexability, security, URL structure, mobile, Core Web Vitals, structured data, JS rendering, IndexNow. Fire for "technical SEO", "crawl issues", "robots.txt", "Core Web Vitals", "site speed".

### seo-schema
Detect, validate, and generate Schema.org structured data (JSON-LD preferred). Fire for "schema", "structured data", "rich results", "JSON-LD", "markup". Use this to validate the `WebSite`/`Organization`/`Product`/`Article`/`FAQ`/`Breadcrumb` JSON-LD in a codebase.

### seo-sitemap
Analyze existing XML sitemaps or generate new ones with industry templates; validates format, URLs, structure. Fire for "sitemap", "generate sitemap", "sitemap issues".

### seo-hreflang
Hreflang and international SEO audit, validation, and generation. Detects common mistakes, validates language/region codes. Fire for "hreflang", "i18n SEO", "international SEO", "multi-language/region".

### seo-images
Image optimization for SEO + performance: alt text, file sizes, formats, responsive images, lazy loading, CLS prevention, image SERP rankings, WebP/AVIF conversion, IPTC/XMP metadata. Fire for "image SEO", "alt text", "image optimization".

### seo-image-gen
AI image generation for SEO assets: OG/social-preview images, blog hero images, schema images, product photography, infographics. Powered by Gemini via nanobanana-mcp (requires `banana` extension). Fire for "generate image", "OG image", "social preview", "hero image". Pairs naturally with the OG-image fix in `vibio-fix` (seo-fix-principles + the stack adapter) when no suitable landscape image exists.

## Tier 4 — AI search (GEO)

### seo-geo
Generative Engine Optimization: optimize for AI Overviews, ChatGPT web search, Perplexity, Bing Copilot. Brand-mention signals, AI-crawler accessibility, llms.txt compliance, passage-level citability scoring. Fire for "GEO", "AI search", "AI Overviews", "ChatGPT/Perplexity visibility", "llms.txt".

### seo-flow
FLOW framework (Find → Leverage → Optimize → Win), evidence-led SEO with 41 stage-specific prompts. Fire for "FLOW", "evidence-led SEO".

### seo-sxo
Search Experience Optimization: reads SERPs backwards to detect page-type mismatch, derives user stories from intent signals, scores pages from multiple personas. Diagnoses *why a well-optimized page still won't rank*. Fire for "why isn't this ranking", "page-type mismatch", "search intent mismatch".

## Tier 5 — External data (most need an MCP/API)

### seo-google
Google's own APIs: Search Console (Search Analytics, URL Inspection, Sitemaps), PageSpeed Insights v5, CrUX field data (25-week history), Indexing API v3, GA4 organic traffic. **The highest-value data skill once a site is live and verified** — confirms indexation, real CWV, and whether brand/queries are being picked up. Fire for "Search Console", "GSC", "indexation status", "field data", "GA4 organic".

### seo-dataforseo
Live SEO data via DataForSEO MCP: SERP analysis (Google/Bing/Yahoo/YouTube/Images), keyword research (volume, difficulty, intent, trends), backlinks, on-page (Lighthouse), competitor & content analysis, business listings. Fire when live ranking/volume data is needed and the MCP is configured.

### seo-backlinks
Backlink profile: referring domains, anchor-text distribution, toxic-link detection, competitor gap. Works with free sources (Moz, Bing Webmaster, Common Crawl) plus DataForSEO. Fire for "backlinks", "link profile", "referring domains", "link gap".

### seo-firecrawl
Full-site crawling/scraping/mapping via Firecrawl MCP. Fire for "crawl site", "map site", "find all pages", "broken links", "site structure", "JS rendering".

## Tier 6 — Local & ecommerce (skip for pure B2B export sites)

### seo-local
Local SEO: Google Business Profile, NAP consistency, citations, review signals, local schema, location-page quality, multi-location. Fire for brick-and-mortar / service-area / hybrid businesses.

### seo-maps
Maps intelligence: geo-grid rank tracking, GBP audit via API, review intelligence (Google/Tripadvisor/Trustpilot), cross-platform NAP verification, competitor radius mapping, LocalBusiness schema generation.

### seo-ecommerce
E-commerce SEO: Google Shopping visibility, Amazon marketplace intelligence, product-schema validation, competitor pricing, marketplace keyword gaps (DataForSEO Merchant API). Fire for "ecommerce SEO", "shopping", "product schema at scale".

## Tier 7 — Monitoring

### seo-drift
SEO drift monitoring: capture baselines of SEO-critical elements, detect changes, track regressions over time ("git for on-page SEO"). Fire for "SEO drift", "baseline", "track changes", "did anything break", "SEO regression". Useful after a redesign or migration.

## Routing patterns

- **Broad audit of a live site** → `seo-audit` (it fans out internally), or fire `seo-technical` + `seo-schema` + `seo-content` + `seo-sitemap` + `seo-geo` in parallel.
- **Codebase SEO review** → `seo-fix-principles.md` spec as a checklist + stack detection first, then `seo-schema` to validate JSON-LD and `seo-technical` for crawl/index logic.
- **New B2B project** → `b2b-seo` for strategy + `seo-content-brief` per page + `seo-cluster` for architecture.
- **"Why no traffic / not ranking"** → `seo-google` (is it even indexed?) → `seo-sxo` (intent/page-type mismatch?) → `seo-content` (depth/E-E-A-T?).
- **AI-search visibility** → `seo-geo` + the `llms.txt` recipe in `vibio-fix` (each stack adapter has one).
- **Post-launch monitoring** → `seo-drift` baseline + monthly `seo-google` review.

