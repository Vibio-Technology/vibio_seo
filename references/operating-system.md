# Operating System (PLAN mode engine)

The execution method for turning a site/business into a sequenced SEO plan. Distilled from Vibio's `seo-project-operator`. The output goes through `delivery-template.md`.

## Phase 0 — Kickoff

Reach a usable diagnosis fast. Use inputs in this priority: (1) real artifacts — codebase, live pages, sitemap, content inventory, docs; (2) user business context; (3) reasonable inference (state assumptions). Ask a question only if the answer would materially change sequencing.

Capture:
- **Business:** model (ecommerce / B2B / service / SaaS / media / local), main offer, primary conversion (purchase / quote / demo / lead / WhatsApp / call), target geography, primary + secondary languages, customer type (consumer / buyer / distributor / procurement).
- **Site:** status (new / existing-weak / content-heavy / migrating), stack, domain state (new vs aged), major page types, whether GSC + GA4 exist, robots/sitemap present, existing blog/resource center.
- **Resources:** weekly execution capacity, who writes content, dev support available, whether outreach/PR is realistic.

## Phase 1 — Classify

Pick **one** primary class:
- `New site` — little/no indexation, low authority, thin content
- `Existing weak site` — exists but targeting/content system poor
- `Existing content site` — enough pages to optimize/refresh/consolidate
- `Ecommerce / catalog site`
- `Service / B2B site`

Add one secondary tag: `Technical debt`, `Content debt`, `Authority gap`, `Measurement gap`, `International`.

## Phase 2 — Diagnose the dominant bottleneck

Choose ONE, not five. Sequence everything around it.
- **Technical baseline** — GSC missing, sitemap missing/broken, robots blocks important areas, key pages not indexed, severe mobile speed, hard-to-crawl architecture.
- **Keyword / architecture** — site exists but targeting is vague, pages don't map to intent, no keyword map, no cluster hierarchy.
- **Content system** — too few useful pages, inconsistent/empty blog, content doesn't match intent, thin commercial pages.
- **Optimization / refresh** — pages rank but underperform, positions `11-20`, high impressions + weak CTR, cannibalization, stale content.
- **Authority** — pages, technical, and intent are fine but the site can't break competitive SERPs; backlink profile clearly weaker than competitors.
- **Measurement** — team can't tell what's working, no review rhythm, nothing tracked usefully.

State the **90-day objective**: specific, completable, tied to pages/systems, never a ranking promise.
- Good: "Build a clean technical baseline, define keyword architecture, publish the first 12 high-intent pages."
- Bad: "Rank #1 for our main keyword."

## Phase 3 — 90-day roadmap

Sequence by dependency. Don't stack technical cleanup + keyword planning + full production + link building + analytics into one week.

- **Week 1 — Technical baseline & measurement:** verify GSC, confirm GA4, inspect robots.txt + sitemap.xml, check indexation (`site:` + URL inspection on homepage + 3-5 core pages), PageSpeed + mobile baseline, flag noindex/canonical/redirect issues. Done = critical blockers identified and bucketed into `critical / important / later`.
- **Week 2 — Keyword architecture & page mapping:** 10-15 seed topics → candidate set → classify by intent → commercial vs informational → map each family to an owning page (existing / new / merge / deprioritize) → define 3-5 clusters. Done = usable keyword map, each theme has an owner page, cannibalization visible.
- **Weeks 3-4 — First priority pages:** improve homepage + primary service/collection pages, build first commercial landing pages + first supporting articles, fix titles/H1s/meta/internal links, ensure new pages are linked + indexable. Done = real target pages for top themes, internally connected, publish rhythm started.
- **Month 2 — Depth & on-page:** next wave of supporting pages, tighten cluster + commercial↔informational links, improve impressions-but-weak-CTR pages and near-page-one pages, add/validate schema. Done = at least one cluster has real depth, intentional internal linking, early GSC patterns reviewable.
- **Month 3 — Authority + review cadence:** identify linkable assets, build a prospect list (guest post / review / partner / media request), start light weekly outreach, review ranking/impression/index data, decide refresh/expand/deprioritize. Done = outreach is operational, monthly review loop exists, next iteration is evidence-based.

Adapt output volume to capacity: lean `3-5h/wk` (month 1: baseline + map + 2-4 page updates), moderate `6-10h/wk` (month 1: baseline + architecture + 4-8 pages), strong `10+h/wk` (broader but still sequenced).

## Phase 4 — Operating cadence

SEO is weekly execution + monthly review, never daily rank-checking. Default weekly budget `4-10h`, split into 3 blocks:
- **Block 1 — Content (2-3h):** draft/publish 1-2 pages OR refresh 1-2 older pages, expand weak commercial sections, fix titles/H1s/FAQs/internal links. Not every week needs new content; refreshing often has higher leverage.
- **Block 2 — Data & authority (1-2h):** scan GSC for drops/spikes, check newly indexed pages, review impressions/CTR on priority pages, send/follow up outreach. Action signals, not dashboard admiration. Thresholds: +50% impressions WoW for a page = investigate (new query or cannibalization?). −30% impressions sustained 2+ weeks = flag for review. CTR deviation >25% from position-expected = investigate title/meta/SERP-feature change.
- **Block 3 — Technical & internal (30-60m):** confirm new pages indexed, add internal links from older pages to new ones, resolve GSC technical issues, validate schema/canonical on new key pages. Maintenance, not inventing complex work.

**Monthly deep review (2-3h):** compare month-over-month in GSC (biggest growth/decline pages, strong-impression-weak-CTR queries, positions `11-20`); check AI Overviews impressions/clicks (GSC → Search Appearance filter); spot-check brand mentions in ChatGPT/Perplexity for 5 priority queries; pick pages to refresh/merge/deprioritize; check whether organic landing pages feed the conversion path; reconcile any predictions made ≥3 months ago against actuals (per predictive-seo.md §9); choose next month's 2-5 priorities.

**3-month health check:** if after 3 months, zero target keywords have entered top 50 AND organic impressions have not increased >10% from baseline → escalate to strategy review (not full reset, but deeper diagnosis: wrong keywords? weak authority? technical gap?). Don't wait 6 months before course-correcting.

**6-month reset trigger:** revisit only when justified — 6 months of no movement on a core direction, repeated failure of a content type, major technical blockers, business/market change, or organic traffic that's irrelevant to commercial goals. Don't change direction just because the first 1-3 months are slow.

## Phase 5 — Tracking

Tracking preserves decision history and reveals the next move — not reporting theater. Maintain four trackers (add a fifth for GEO only if AI search is a primary channel):
- **Content tracker:** title, URL, page type, primary keyword family, intent, status (`planned/drafting/published/refresh needed/merged/redirected/retired`), publish date, last updated, owner, notes.
- **Keyword tracker:** keep it lean (`20-60` meaningful terms). keyword, intent, owner page, priority, difficulty note, current vs last ranking, trend (`improving/flat/declining/not yet ranking`), notes. Review monthly.
- **Outreach tracker** (once authority work starts): target site, contact/channel, type (`guest post/product review/partner/media request/resource`), promoted page, dates, status (`not started/sent/follow-up due/in conversation/won/lost`), result.
- **Technical issues log** (only if enough technical work): issue, affected pages/templates, severity (`critical/important/later`), source, owner, date found, status, resolution.
- **GEO tracker** (create once site is live and AI-search is relevant): 10-20 priority queries checked monthly — AI Overviews citation (✓/✗), ChatGPT web search mention (✓/✗), Perplexity source appearance (✓/✗), llms.txt last updated, Knowledge Panel status, brand entity mentions. Track trend month-over-month. Use manual spot-checks + GSC AI Overviews filter when available.

## Task SOPs (pull only 2-4 per deliverable)

Include one for the current bottleneck, one for the current production motion, one for maintenance, plus authority if ready:
- **Technical baseline** — verify measurement, crawl access, discovery, indexation, page health; bucket issues.
- **Keyword seed expansion & intent sorting** — 10-15 seeds → 50-300 candidates → label intent → score actionability (relevance, can the site answer it, beatable SERP, deserves a page).
- **Keyword-to-page mapping** — assign one keyword family to one primary page; mark existing/new/merge/deprioritize; expose cannibalization.
- **Commercial page build** — pick intent, define structure (H1, value prop, trust, proof, FAQ, CTA), add title/meta/internal links/schema.
- **Support content build** — pick a clear-intent query, define which commercial page it supports, answer completely, link up to parent + siblings.
- **Old content refresh** — select `11-20` / high-impression-low-CTR / declining pages, compare to top SERP, refresh surgically, re-submit for indexing.
- **Internal linking pass** — link priority pages from relevant older pages with descriptive anchors; kill orphans.
- **Authority launch** — choose linkable assets, build a relevance-first prospect list, steady weekly outreach, log results.

## Branching by class

- **New site:** technical setup first → long-tail targeting → first 10-20 quality pages → commercial foundation before broad blog ambition → delayed link building.
- **Existing weak site:** fix targeting/hierarchy → rewrite weak core pages → create missing commercial pages → clean internal structure.
- **Existing content site:** content audit → merge/redirect/rewrite → refresh `11-20` → CTR repair → internal-link upgrades.
- **Ecommerce:** collection/category targeting → product/collection schema → crawl & faceted-nav control → review signals → category-supporting content.
- **Service / B2B (Vibio default):** service & use-case pages → industry pages only with real differentiation → comparison/alternative/FAQ assets → proof-rich trust pages → buyer-education content → authority after page quality exists.

