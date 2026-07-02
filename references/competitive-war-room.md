# Competitive War Room

Monitor competitors systematically. Know their moves before they impact your rankings. This is not occasional competitor checks — it's a standing intelligence system.

---

## 1. Competitor Identification

### Who actually competes (not who the business thinks)
Scrape the top 10 SERP for your 20-30 priority keywords. Count domain appearances. The domains appearing most frequently are your real competitors — not the companies the CEO names in pitch decks.

### Categorize competitors:
- **Direct competitors** — same products/services, targeting same keywords
- **Content competitors** — different business but ranking for your informational keywords (publishers, media, aggregators)
- **Emerging competitors** — new entrants climbing fast on 3+ of your keywords

---

## 2. Monitoring Dimensions

### Content Velocity
Track per competitor:
- New pages published per week/month
- Content type mix (blog vs product vs resource)
- Average content depth (word count trend)
- Topic expansion (which new keyword clusters are they entering)

### Keyword Overlap & Gap
- Shared keywords: where you both rank, who's gaining/losing
- Their unique keywords: what they rank for that you don't → gap list
- Your unique keywords: what you rank for that they don't → defend

### Backlink Growth
- New referring domains per month
- Link type (editorial, directory, paid, UGC)
- High-value links (DR 60+ sites)

### Technical Changes
- Schema additions/removals
- Site speed changes (Core Web Vitals)
- Site structure changes (new sections, IA shifts)
- Platform migrations

### SERP Feature Ownership
- Featured snippets won/lost
- PAA presence
- Image pack rankings
- Video carousel presence

### AI Search Visibility (unified — traditional SEO signals power AI citations)
- AI Overviews citations: which competitor pages get cited, for which queries
- ChatGPT/Perplexity source appearances: track competitor brand mentions
- llms.txt completeness comparison (page count, freshness)
- Schema coverage (who has FAQPage/HowTo/Product that AI engines parse)
- Entity authority (Knowledge Panel presence, Wikidata/Wikipedia status)
- Answer-first content adoption (who structures content for citability)

---

## 3. Alert Triggers

Check weekly. Escalate when:

| Trigger | Action |
|---------|--------|
| Competitor publishes 5+ pages targeting your keywords in one week | Content velocity counter: accelerate your pipeline |
| Competitor gains 10+ backlinks in a month (3× their normal rate) | Investigate: earned media, campaign, or paid links? |
| Competitor jumps 5+ positions on 3+ shared keywords | Deep dive their page: what improved? Match or exceed. |
| New competitor enters top 10 for 3+ of your keywords | Profile them: authority, content strategy, backlinks |
| Competitor adds new schema type you don't have | Evaluate: should you add it? |
| Competitor's site speed improves by 20%+ | Check if they changed stack/hosting; may signal bigger changes |

---

## 4. Moat Analysis

What you have that competitors cannot easily copy:

| Moat Type | Examples | Defense Strategy |
|-----------|----------|-----------------|
| **First-party data** | Original research, customer data, proprietary benchmarks | Publish regularly, cite with your brand name |
| **Unique expertise** | Founder/team experience, case studies, certifications | Author pages with credentials, EEAT signals |
| **Proprietary tools** | Calculators, configurators, databases | Embed on-site, make them link targets |
| **Brand authority** | Wikipedia page, major media mentions, industry awards | Maintain and expand, add sameAs links |
| **Operational speed** | Content velocity, rapid iteration | Keep pace high — speed is a moat |

---

## 5. Counter-Move Playbook

### Response to Competitor Content Push
1. Audit their new pages: what gap are they filling?
2. Write a better page (more depth, better data, EEAT, GEO formatting)
3. Update your existing pages on the same topic to be definitively better
4. Build internal links from all related pages to your improved page

### Response to Competitor Backlink Surge
1. Analyze their new links: what type of content attracts them?
2. Create a more linkable asset (original data > listicles)
3. Outreach to the same sites that linked to them (HARO/podcasts/reviews)

### Response to Competitor Ranking Gains
1. Check if they improved content or gained links
2. If content: refresh your page with substantial improvements (not minor edits)
3. If links: focus on linkable asset creation
4. If both: consider whether this keyword is still worth fighting for

### Response to New Entrant
1. Profile aggressively: authority, strategy, pace
2. If they're weak: they'll plateau — just maintain your quality lead
3. If they're strong and fast: preemptively strengthen your position now

---

## 6. Monitoring Cadence

| Frequency | Activity | Time |
|-----------|----------|------|
| **Weekly** | Quick SERP scan for priority keywords, check GSC for competitor impression gains | 30 min |
| **Monthly** | Full competitor content audit, backlink check, technical diff | 2-3 hours |
| **Quarterly** | Deep moat analysis, strategy review, full gap analysis | 4-6 hours |

---

## 7. Tools Routing

| Need | Route to |
|------|----------|
| SERP data + keyword overlap | `seo-dataforseo` |
| Backlink profile | `seo-backlinks` |
| Content change detection | `seo-firecrawl` (re-crawl competitor) or manual WebFetch |
| Technical changes | `seo-technical` + manual speed test |
| Schema changes | `seo-schema` (validate their page) |
| Ranking tracking | `seo-google` (GSC) or `seo-dataforseo` |
