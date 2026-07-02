# Recovery Playbook — Algorithm Updates & Traffic Drops

When traffic or rankings drop, don't panic. Diagnose systematically, apply the cause-specific playbook, monitor recovery.

## 1. Drop Detection

1. Open GSC → compare last 28 days vs previous 28 days (or 7 vs 7 for acute drops)
2. Isolate: which pages dropped? which queries? site-wide or specific?
3. Match drop date to: known Google updates, your deployments (check `.vibio/changelog.md`), competitor moves

| Drop | Classification | Urgency |
|------|---------------|---------|
| 10-20% traffic, gradual 2+ months | Content decay | Schedule refresh within 2 weeks |
| 20-40% traffic, sudden | Possible update hit | Investigate within 48 hours |
| 40%+ traffic, acute | Technical issue or manual action | Immediate |
| Site-wide deindexation | Critical | Emergency |

## 2. Cause Classification

```
Traffic dropped
├─ Sudden drop (day-level)
│   ├─ Matches known Google update date → ALGORITHM UPDATE
│   ├─ Matches your deployment date → TECHNICAL REGRESSION
│   └─ GSC shows Manual Action → MANUAL ACTION
├─ Gradual decline (weeks/months)
│   ├─ Competitors gained on your keywords → COMPETITOR DISPLACEMENT
│   └─ Content aging, slowly losing positions → CONTENT DECAY
└─ Specific pages only
    ├─ Pages no longer indexed → TECHNICAL (check noindex, robots, status codes)
    └─ Pages indexed but dropped → ALGORITHM or COMPETITOR
```

## 3. Recovery by Cause

### Algorithm Update
- Wait 1-2 weeks before changes (updates often roll back partially)
- Identify what the update targeted (core quality, spam, helpful content, reviews)
- Core Update: improve EEAT across affected pages, add original value, cut thin content
- Helpful Content Update: audit against Google's self-assessment, improve substantially
- Spam Update: check for policy violations (→ `google-search-docs.md` §3)
- Recovery timeline: 2-6 months after substantial improvements

### Technical Regression
- Check `.vibio/changelog.md` for recent changes
- Verify no: stray noindex, robots changes, broken canonicals, wrong status codes, redirect chains
- Run `seo-drift` to compare vs last baseline
- If caused by deployment: rollback SEO-breaking change, then fix properly
- Resubmit affected URLs in GSC
- Recovery timeline: days to 2-3 weeks

### Manual Action
- Read GSC notice carefully — it specifies the violation
- Fix thoroughly (not superficially — Google re-reviews)
- Document all fixes
- Submit Reconsideration Request with explanation
- Recovery timeline: 1-4 weeks (can take multiple rounds)

### Competitor Displacement
- Analyze what competitor improved (content, links, technical, freshness)
- Match or exceed their improvement on your page
- Add information gain: 3+ things their page doesn't have
- Strengthen internal linking to affected page
- Re-submit in GSC
- Recovery timeline: 4-12 weeks

### Content Decay
- Update statistics, dates, sources to current year
- Add new sections covering developments since original publish
- Cut outdated information (or mark as historical context)
- Refresh publish date and resubmit
- Recovery timeline: 2-8 weeks

## 4. Recovery Timeline Summary

| Cause | Fastest | Typical | Worst Case |
|-------|---------|---------|------------|
| Technical Regression | Days | 1-2 weeks | 3-4 weeks |
| Content Decay | 2-4 weeks | 4-8 weeks | 12 weeks |
| Competitor Displacement | 4 weeks | 8-12 weeks | 6 months |
| Algorithm Update | 2 weeks | 1-3 months | Until next update |
| Core Update | Until next update | 2-6 months | 12+ months |
| Manual Action | 1-2 weeks | 2-4 weeks | Multiple rounds |

## 5. Monitoring During Recovery

- Weekly GSC check: impressions, clicks, avg position for affected queries
- Do NOT make further changes during 4-8 week stabilization period
- Log all observations in `.vibio/changelog.md`
- If recovery partial after 8 weeks, re-assess cause classification
- After stabilization, resume monthly REVIEW mode cadence

## 6. Prevention

- Run `seo-drift` after every deployment to catch regressions immediately
- Content freshness calendar: quarterly review of dates, statistics, competitor content
- Follow Google Search Status Dashboard for announced updates
- Pre-deployment SEO checklist: verify noindex, robots, canonicals, redirects
- Backup SEO config before major deployments
