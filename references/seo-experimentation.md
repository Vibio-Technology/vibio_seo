# SEO Experimentation — A/B Testing Framework

SEO is not guesswork. Test title tags, meta descriptions, content structures, and schema to find what actually improves CTR and rankings. This framework handles the unique constraints of SEO testing (slow feedback, no server-side split for organic, cannibalization risk).

## 1. What You Can Test

| Element | Test Method | Measurement | Typical Duration |
|---------|------------|-------------|-----------------|
| Title tag | GSC impression/CTR before vs after change | CTR change, position change | 2-4 weeks |
| Meta description | GSC CTR before vs after change | CTR change at same position | 2-4 weeks |
| Content structure (H2 order, answer-first vs traditional) | GSC position + CTR | Ranking + CTR | 4-8 weeks |
| Schema addition (FAQ, HowTo, Product) | GSC rich result appearances | Rich result impressions | 2-6 weeks |
| Content depth (adding sections) | GSC position + impressions | Position + new keyword rankings | 4-12 weeks |
| Internal link anchor text | GSC position for target page | Position change | 2-6 weeks |
| OG image | Social share CTR (platform analytics) | Shares, clicks | 1-4 weeks |
| Page speed optimization | CrUX + GSC | CWV scores + position | 2-4 weeks |

## 2. Title Tag Testing Protocol

### Pre-Post Comparison (simplest, works for most sites)

**When:** changing titles on existing ranking pages.

**Protocol:**
1. Record baseline: current title, current GSC data (impressions, clicks, CTR, avg position) for the page over the last 28 days
2. Write the new title following these rules:
   - Keep primary keyword front-loaded (first 30 chars)
   - Target 50-60 characters
   - Include a click trigger: current year, specific number, benefit statement, or uniqueness signal
   - Differentiate from the H1 (title tag ≠ H1)
3. Deploy the change
4. Log the change in `.vibio/changelog.md` with date, old title, new title
5. Wait 2 weeks minimum (4 weeks preferred for statistical significance)
6. Compare: GSC last 28 days vs previous 28 days
   - **Winner:** CTR increased ≥ 10% at similar or better position
   - **Loser:** CTR decreased ≥ 10%
   - **Inconclusive:** CTR change < 10% or position changed significantly (can't isolate title effect)

**Title variants to test:**
- `Keyword: Benefit Statement | Brand` (benefit-led)
- `Keyword (2025 Guide): Expert Tips | Brand` (expertise + year)
- `X Best Keyword Options Compared (2025) | Brand` (comparison signal)
- `Keyword — What You Need to Know [Data] | Brand` (data signal)
- `How to [Outcome] with Keyword | Brand` (how-to + outcome)

### For High-Traffic Pages (split-adjacent testing)
If you have two similar pages targeting different keywords in the same cluster:
1. Apply variant A to page 1, variant B to page 2
2. Compare CTR trends relative to their own baselines
3. The variant with higher CTR uplift wins
4. Roll winner to both pages

## 3. Meta Description Testing

**Protocol (same as title testing):**
1. Baseline: 28-day GSC CTR data
2. Write new description (150-160 chars):
   - Include primary keyword naturally
   - State a clear benefit or answer
   - End with a soft CTA ("Learn how...", "See specs...", "Compare options...")
3. Deploy and wait 2-4 weeks
4. Compare CTR at similar position

**Description variants to test:**
- **Question-led:** "Looking for [keyword]? Our guide covers [benefit 1], [benefit 2], and [benefit 3]. Read more →"
- **Data-led:** "[Number] factors to consider when choosing [keyword]. Compare [spec 1], [spec 2], and [spec 3]. See full specs →"
- **Problem-solution:** "Struggling with [pain point]? Learn how [keyword] solves [problem] with [benefit]. Expert guide →"

## 4. Content Structure Testing

**When:** testing whether answer-first structure beats traditional narrative structure.

**Method:**
1. Choose a page ranking 5-20 (close enough to page 1 that structural changes can push it over)
2. Version A (control): current structure
3. Version B (test): restructured with:
   - Direct answer in first 100 words
   - Each H2 first sentence = complete answer
   - Tables replacing prose for specs/comparisons
   - FAQ section at bottom
4. Deploy B → wait 4-8 weeks → compare GSC data
5. Measure: position change, CTR change, new keyword rankings, AI Overview appearances

## 5. Schema Testing

**Test:** does adding a specific schema type increase rich result appearances?

**Protocol:**
1. Identify 5-10 similar pages (e.g., all product pages or all blog posts)
2. Check baseline: any rich result appearances in GSC?
3. Add target schema to all test pages (e.g., FAQPage, Article, Product with Offer)
4. Wait 2-6 weeks
5. Measure: GSC → Search Appearance → rich result type → impressions

**Schema to test in order of impact:**
1. FAQPage (highest CTR impact for question-based queries)
2. Article with author + dateModified (GEO signal)
3. Product with Offer + AggregateRating (ecommerce)
4. HowTo (step-by-step content)
5. BreadcrumbList (never hurts, low impact alone)

## 6. Experiment Log

Maintain an experiment log in `.vibio/experiments.md`:

```md
# SEO Experiments

| ID | Page | Element | Variant | Start Date | End Date | Baseline CTR | Test CTR | Winner | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 001 | /blog/article-x | Title | Benefit-led | 2025-01-15 | 2025-02-15 | 3.2% | 4.1% | Test | +28% CTR uplift |
```

## 7. Statistical Significance

SEO testing has small sample sizes and long feedback loops. Rules of thumb:
- ≥ 100 impressions/month: minimum for any test
- ≥ 500 impressions/month: can detect ±20% CTR change
- ≥ 1000 impressions/month: can detect ±10% CTR change
- Position must be stable (within ±2 positions) during test period for CTR comparison to be valid
- If position changes > 3 spots during test, the CTR change cannot be attributed to the element change alone

## 8. What NOT to Test

- **Don't A/B test canonical URLs or redirects** — Google sees two versions of the "same" page = cannibalization risk
- **Don't test on pages ranking 1-3** — risking a top position for minor CTR gains is not worth it
- **Don't test during known algorithm updates** — external factors swamp your test signal
- **Don't test too many elements at once** — can't isolate which change caused the effect
- **Don't test on pages with <100 monthly impressions** — insufficient data for any conclusion
- **Don't run simultaneous tests on the same page** — confounding variables

## 9. From Test to Standard

When a test variant wins:
1. Document the winner in experiment log
2. Roll the winning pattern to similar pages
3. Add the winning pattern to the content/style guide
4. Schedule a follow-up check in 3 months (sometimes CTR gains decay)
