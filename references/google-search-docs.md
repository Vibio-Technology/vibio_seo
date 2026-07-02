# Google Search Docs (audit baseline)

The authority for auditing. Every finding should trace to a Google rule, not to "best practice" folklore. This file distills the official docs with their canonical URLs; cite the URL in findings so a conclusion reads "per Google's X, this violates Y" instead of "I think".

**Hybrid usage:** use the distilled rules below for the common cases (fast, offline, traceable). When a feature is new, a requirement is ambiguous, or the user pushes back, **WebFetch the official URL** to confirm the current wording — Google updates these pages and policies (e.g. the 2024-2025 spam-policy additions). Treat this file as a cache, not gospel; the live page wins.

Docs root: https://developers.google.com/search/docs

---

## 1. Technical requirements (the floor — check first)

Source: https://developers.google.com/search/docs/essentials/technical

Three hard requirements for a page to be indexable. A page failing any of these is a **Critical** finding — nothing downstream matters if the page can't be indexed.

1. **Googlebot can access it** — not blocked by `robots.txt`, not behind login/paywall, publicly reachable. Verify with URL Inspection / Page Indexing report (route to `seo-google`).
2. **HTTP 200** — Google only indexes pages served with a `200 (success)` status. 4xx/5xx and soft-404s don't get indexed.
3. **Indexable content** — text in a supported format, not blocked by `noindex`, not violating spam policies.

Meeting these does **not** guarantee indexing — Google still applies quality assessment on top.

Related best-practice docs:
- Crawlable links: https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- JavaScript SEO: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- Control what's shared (noindex/robots/canonical): https://developers.google.com/search/docs/crawling-indexing/control-what-you-share
- Canonicalization: https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls

Audit checks: stray `noindex` on pages meant to rank (the #1 silent killer), `robots.txt` blocking important paths or render-critical CSS/JS, honest status codes, self-referential canonicals, JS-rendered content actually present in the rendered HTML.

---

## 2. Structured data (rich results eligibility)

Gallery (all 30+ types): https://developers.google.com/search/docs/appearance/structured-data/search-gallery
Intro: https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data

JSON-LD is Google's preferred format. Each type has **required** vs **recommended** fields; missing a required field disqualifies the rich result. Validate with the Rich Results Test and the `seo-schema` skill. Common types + doc URLs:

| Type | Doc path (under .../structured-data/) | Use on |
|---|---|---|
| Article / BlogPosting | `article` | news / blog posts |
| Product | `product` | product pages (+ Offer, AggregateRating) |
| Breadcrumb | `breadcrumb` | nested pages |
| FAQ | `faqpage` | FAQ content (note: Google restricted FAQ rich-result display to authoritative gov/health sites — still valid markup, limited display) |
| Local Business | `local-business` | physical / service-area businesses |
| Organization | `organization` | site-wide (logo, contact, social) |
| Recipe / Event / Video / JobPosting / Review / Course / Dataset / SoftwareApp / etc. | resp. slug | per content type |

Audit checks: site-wide `Organization` + `WebSite` present; page-type schema where relevant; required fields complete; markup matches visible content (mismatched/invisible structured data is a spam violation — see §3); no deprecated types.

Brand SERP: the site-name line comes from `WebSite` JSON-LD `name` + `og:site_name`; logo from `Organization.logo`.

---

## 3. Spam policies (penalty risk — Critical when matched)

Source: https://developers.google.com/search/docs/essentials/spam-policies

A match here is **Critical** — it risks ranking demotion or removal. Don't ever recommend a tactic that trips one. The current policy list (confirm live wording for the newer ones):

- **Cloaking** — different content to crawler vs user.
- **Doorway abuse** — many pages funneling to a final destination.
- **Expired domain abuse** — buying expired domains for low-value content (2023+ policy).
- **Hacked content** — unauthorized injected content.
- **Hidden text / link abuse** — white-on-white text, off-screen links, etc.
- **Keyword stuffing** — overloading keywords.
- **Link spam** — buying/exchanging/auto-generating links for ranking.
- **Machine-generated traffic** — automated queries to Google.
- **Malicious practices** — malware, unwanted software, back-button hijacking.
- **Misleading functionality** — pages claiming a service they don't deliver.
- **Scaled content abuse** — mass-producing pages (incl. with generative AI) primarily to manipulate rankings, with little value (2024 policy — relevant to programmatic/AI content; pair with `seo-programmatic` thin-content safeguards).
- **Scraping** — republishing others' content for ranking.
- **Site reputation abuse** — third-party content riding a host's ranking signals ("parasite SEO", 2024 policy).
- **Sneaky redirects** — different destination for users vs crawler.
- **Thin affiliation** — affiliate pages copying merchant descriptions with no added value.
- **User-generated spam** — spam posted in open areas (comments/forums).

Audit checks: structured data matches visible content; no programmatic/AI page farms without genuine value; redirects honest; affiliate pages add original value; no third-party "parasite" sections on an authoritative host.

---

## 4. Helpful content & E-E-A-T (quality assessment)

Source: https://developers.google.com/search/docs/fundamentals/creating-helpful-content

Not a checklist of tags — a quality judgment Google's systems apply site-wide. Audit content against the official self-assessment lens, route depth to `seo-content`.

**People-first test:** content should serve an existing/intended audience who'd find it useful arriving directly — not be made primarily to rank. Key official question: *"Would you bookmark this, or recommend it to a friend?"*

**E-E-A-T** — Experience, Expertise, Authoritativeness, **Trust** (trust is the most important). Extra weight on **YMYL** (Your Money or Your Life: health, finance, safety) topics. Signals: clear sourcing, evidence of expertise, author background, factual accuracy.

**Official AI-content position:** AI-assisted content is allowed; what matters is **why** it's made. Producing content primarily to manipulate rankings violates spam policy (§3 scaled content abuse). Google emphasizes purpose and value over how it was produced; be transparent about automation where it helps readers.

Audit checks: original value vs rewrite of existing sources; sourcing/author/expertise present (esp. YMYL); content matches the intent it targets; not mass-generated filler.

---

## 5. AI search / GEO (emerging, verify live)

Google's official surface here moves fast — **always WebFetch to confirm** rather than trusting cached claims. Anchors:
- Structured data and helpful, people-first content are Google's stated foundations for appearing in AI-driven results; there is no separate "AI Overviews markup".
- AI crawler access (Google-Extended token) and `llms.txt` (an emerging cross-engine convention, not a Google standard) are handled in stack adapters + the `seo-geo` skill.
- For ChatGPT/Perplexity/Bing visibility (non-Google engines), route to `seo-geo`; those aren't governed by Google's docs.

When auditing AI-search readiness, lean on §2 (structured data) + §4 (helpful content) as the verifiable base, and flag anything beyond as "confirm against live official guidance".

---

## How to cite in findings

Each finding gets: **what** (the issue, quoted from rendered output), **rule** (which Google doc + URL), **severity** (Critical for technical-floor/spam matches; High/Medium/Low otherwise), **fix** (hand to FIX mode via stack adapter). Example:

> **High — Missing self-referential canonical on /products/x**
> Per Google's canonicalization guide (developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), pages should declare a canonical; without it Google guesses and may consolidate wrongly. Fix via FIX mode (stack adapter).
