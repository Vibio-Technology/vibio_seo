# Predictive SEO — Ranking Probability & Traffic Forecasting

Estimate ranking potential and traffic before writing or investing. Use these frameworks to answer "is this keyword worth targeting?" with numbers, not intuition.

---

## 1. Site Authority Assessment

Without paid tools, estimate domain authority from observable signals.

### How to obtain each signal (data-gathering procedure)
Run these BEFORE filling the score table — never guess the numbers:
- **Pages ranking top 10/top 3**: if GSC connected → `seo-google` Search Analytics, count queries with avg position ≤10 and ≤3. No GSC → `seo-dataforseo` SERP lookup on 10 brand-adjacent seed keywords, count top-10 appearances; extrapolate qualitatively (label "estimated").
- **Branded search volume**: GSC → filter queries containing the brand name, sum impressions. No GSC → `seo-dataforseo` keyword_info for the brand name; if 0 data, mark "unknown, treat as <100".
- **Referring domains**: `seo-backlinks` (Moz/Common Crawl free tier) for RD count. No tool → check `site:` indexed page count as a weak proxy and label low-confidence.
- **Domain age**: WebFetch `https://who.is/whois/DOMAIN` or check the copyright year / earliest Wayback Machine capture (`http://web.archive.org/web/*/DOMAIN`).
- **Indexed pages** (proxy for site size): Google `site:domain.com` approximate count.

If a signal cannot be obtained, score it 0 and lower the overall confidence band (§7) — do not fabricate a value.

### Ranking Footprint Score
| Signal | Strong (3pts) | Moderate (2pts) | Weak (1pt) | None (0pt) |
|---|---|---|---|---|
| Pages ranking top 10 for ANY term | 50+ pages | 10-49 pages | 1-9 pages | 0 pages |
| Pages ranking top 3 for ANY term | 10+ pages | 3-9 pages | 1-2 pages | 0 pages |
| Branded search volume (GSC) | 1000+/mo | 100-999/mo | 1-99/mo | 0 |
| Referring domains (estimated) | 200+ RD | 50-199 RD | 5-49 RD | <5 RD |
| Domain age | 5+ years | 2-5 years | 6mo-2yr | <6 months |

**Composite Score:** 12-15 = Strong authority (DA 40+) | 8-11 = Moderate (DA 20-40) | 3-7 = Weak (DA 10-20) | 0-2 = New (<DA 10)

### Topical Authority Bonus
Add +1 to the composite for each:
- 3+ pages ranking top 20 for related keywords in the same topic cluster
- Existing content hub/pillar page structure for this topic
- External links from authoritative sites in this topic space

---

## 2. Keyword Difficulty Calibration

### Competitor Analysis (for target keyword)
Check the top 10 ranking pages:
1. **Authority distribution:** Count how many top-10 pages are "weak." A page is **weak** if it meets 2+ of: (a) forum/UGC/Q&A site (Reddit, Quora, forums), (b) no structured data in the HTML, (c) thin ranking page (<800 words), (d) no HTTPS, (e) domain with no recognizable brand / no Wikipedia presence. If 3+ of the top 10 are weak → beatable.
2. **Content depth gap:** Score the top 3 pages on: word count, H2 count, table/media usage, source citations, EEAT signals, freshness. Your content needs to beat the median on at least 3 dimensions.
3. **Intent match:** Does the SERP show the page type you plan to create? If SERP is all product pages and you plan a blog post → mismatch = much harder.

### Difficulty Tiers
| Tier | Conditions | Beatability |
|---|---|---|
| **Very Low (KD <15)** | 3+ weak sites in top 10, thin content on page 1 | New site with good content can rank in 3-6 months |
| **Low (KD 15-30)** | 1-3 weak sites, moderate content depth | Established site can rank in 1-3 months; new site 6-12 months |
| **Medium (KD 30-50)** | Mostly established sites, good content depth | Need solid topical authority + backlinks; 6-18 months |
| **High (KD 50-70)** | Strong sites only, excellent depth | Need significant authority investment; 12-24+ months |
| **Very High (KD 70+)** | Top-tier domains, near-perfect content | Only viable as long-term strategic target |

---

## 3. Traffic Estimation

### Formula
```
Estimated Monthly Traffic = Search Volume × CTR_by_position × Seasonal_Adjustment × SERP_Feature_Discount
```

### CTR by Position (blended desktop + mobile, 2024 estimates)
| Position | CTR | Cumulative |
|----------|-----|------------|
| 1 | 28% | 28% |
| 2 | 15% | 43% |
| 3 | 10% | 53% |
| 4 | 7% | 60% |
| 5 | 5% | 65% |
| 6 | 4% | 69% |
| 7 | 3% | 72% |
| 8 | 2.5% | 74.5% |
| 9 | 2% | 76.5% |
| 10 | 1.5% | 78% |

### SERP Feature Discounts (multiply CTR by)
- AI Overview present at top: ×0.75
- Featured Snippet present: ×0.85 for position 1, ×0.70 for positions 2-3
- Image Pack / Video Carousel: ×0.90
- Knowledge Panel (right rail): ×0.95
- People Also Ask dominating above fold: ×0.85

### Seasonal Adjustment
Get seasonality data (in priority order):
1. `seo-dataforseo` keyword_info endpoint → returns a 12-month search-volume array. Use it directly: `monthly multiplier = this_month_volume / annual_average`.
2. WebFetch `https://trends.google.com/trends/explore?q=KEYWORD` → read the relative-interest chart.
3. No data → assume ×1.0 (no adjustment) and label the prediction "seasonality unknown."

Typical multipliers vs annual average:
- Peak month: ×1.3-1.5
- Trough month: ×0.5-0.7
- Stable (no seasonality): ×1.0

---

## 4. Time-to-Rank Estimation

### New Site (<1 year, weak authority)
| KD Tier | First Page (Top 10) | Top 3 | Notes |
|---------|---------------------|-------|-------|
| Very Low | 3-6 months | 6-12 months | With consistent content + basic technical |
| Low | 6-12 months | 12-18 months | Requires topical depth |
| Medium | 12-24 months | 18-36 months | Needs link building |
| High+ | 24+ months | Not guaranteed | Requires significant authority |

### Established Site (2+ years, moderate+ authority)
| KD Tier | First Page (Top 10) | Top 3 |
|---------|---------------------|-------|
| Very Low | 1-3 months | 3-6 months |
| Low | 3-6 months | 6-12 months |
| Medium | 6-12 months | 12-18 months |
| High | 12-24 months | 18-36 months |

**How to apply factors (multiplicative on the estimated time):**
- Acceleration → `time × (1 − factor)`. E.g. "+30% faster" → `time × 0.7`.
- Deceleration → `time × (1 + factor)`. E.g. "+50% slower" → `time × 1.5`.
- Multiple factors multiply together. Example: existing cluster (×0.7) + low content velocity (×1.5) = `time × 0.7 × 1.5 = ×1.05`.

**Acceleration factors:** existing topical cluster (+30% faster, ×0.7), strong internal linking (+20%, ×0.8), GSC submission on publish (+10%, ×0.9, marginal).

**Deceleration factors:** low content velocity (+50% slower, ×1.5), no backlink growth (+40%, ×1.4), poor EEAT signals (+30%, ×1.3).

---

## 5. Revenue Projection

### B2B / Manufacturing (Vibio default)
```
Monthly SEO Revenue = Monthly Traffic × Inquiry_CR × SQL_Rate × Close_Rate × Avg_Deal_Value

Where (use client data first; these are fallback defaults when unknown):
- Inquiry_CR: product pages 1-3% (default 2%), informational 0.5-1.5% (default 1%)
- SQL_Rate (inquiry → qualified lead): 30-50% (default 40%)
- Close_Rate (SQL → won deal): 10-30% (default 20%)
- Avg_Deal_Value: B2B manufacturing $5,000-$50,000 (default $15,000); component/materials repeat orders skew lower
```
**Always label projections built on defaults as "estimated — refine with client's actual inquiry→deal rate and deal value."** Give a range (using low and high ends of each factor), not a single false-precision number.

### E-commerce
```
Monthly SEO Revenue = Monthly Traffic × Purchase_CR × AOV
Purchase_CR: 1-3% for commercial pages, 0.3-0.8% for informational pages
```

### Content/Media
```
Monthly SEO Revenue = Monthly Traffic × RPM / 1000
RPM: $5-30 depending on niche
```

---

## 6. Predictive Model Inputs Checklist

### Required (cannot predict without):
- [ ] Seed keyword + target page URL
- [ ] Search volume (from seo-dataforseo or GSC)
- [ ] Top 10 SERP analysis (who ranks, what page types, content depth)
- [ ] Site's current ranking footprint (any pages ranking for anything?)

### Strongly Recommended:
- [ ] GSC data (existing queries, impressions, CTR)
- [ ] Referring domain estimate
- [ ] Content depth gap analysis vs top 3 competitors
- [ ] Seasonal trend data (Google Trends)

### Nice to Have:
- [ ] Conversion rate data for the site
- [ ] Historical time-to-rank for similar keywords on this site
- [ ] Competitor backlink growth rate

---

## 7. Uncertainty & Confidence Bands

### Confidence Levels
| Level | Conditions | Prediction Range |
|-------|-----------|-----------------|
| **High** | GSC data + ranking history + stable SERP | ±20% on traffic, ±1 month on time |
| **Medium** | Search volume from tool + SERP analysis, no GSC | ±35% on traffic, ±3 months on time |
| **Low** | Estimated volume + incomplete SERP data | ±50% on traffic, ±6 months on time |

### Time Decay on Confidence
Predictions beyond 12 months: multiply confidence band by 1.5×.
Predictions beyond 24 months: too uncertain for actionable decisions.

---

## 8. When NOT to Predict

**Hard stops (do not predict):**
- Brand-new site with zero indexed pages and no GSC data → do AUDIT first, build baseline
- Highly volatile niche (news, trending topics, crypto) → point out volatility
- Pure branded/navigational queries → no prediction needed
- Zero search volume keywords → redirect to long-tail alternatives

**Conditional (predict with heavy caveats):**
- Site mid-migration or redesign → wait for stabilization
- No topical authority but targeting medium+ KD → flag as high-risk
- Seasonal query without 2+ years of trend data → label as low confidence

**Instead of predicting, offer:** a diagnostic plan to build the data needed for prediction.
