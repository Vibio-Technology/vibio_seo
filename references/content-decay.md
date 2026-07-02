# Content Decay — Detection & Refresh

Content doesn't last forever. Rankings erode as information ages, competitors publish fresher content, and user expectations shift. Detect decay early and refresh before rankings drop.

## 1. Decay Signals

### Quantitative signals (GSC, 30/60/90-day trends):
- Declining impressions for a page (compare last 28 days vs previous 28 days, and vs same period last year)
- Declining clicks (impressions stable but CTR dropping = SERP features stealing clicks)
- Dropping average position (same queries, worse rankings = content being outranked)
- Declining click-through rate (same position, fewer clicks = title/meta less compelling or SERP features absorbing clicks)

### Qualitative signals:
- Publish date >18 months old on a fast-moving topic
- Statistics/sources older than 2-3 years
- Competitor content visibly fresher (check their publish dates and content depth)
- New products/standards/regulations not covered in your content

## 2. Detection Methodology

### Weekly light scan:
- GSC → filter to pages with declining impressions (30-day trend)
- Flag any page showing >15% decline for 2+ consecutive weeks

### Monthly deep scan:
- Export GSC data for all pages, sort by impression decline %
- Cross-reference with publish date (pages >12 months old get higher decay risk score)
- Spot-check SERP for top 5 declining pages: what changed? new competitors? fresher content?

### Quarterly full audit:
- Every page older than 12 months assessed for freshness
- Priority: highest-traffic pages declining fastest get refreshed first

## 3. Refresh Decision Matrix

| Action | When | Time Investment | Impact |
|--------|------|----------------|--------|
| **Minor update** | Stats/sources outdated, content still accurate | 1-2 hours | Maintain rankings |
| **Substantial update** | Missing new subtopics, competitor content deeper | 3-6 hours | Regain lost positions |
| **Rewrite** | Content fundamentally outdated or thin | 8-16 hours | Significant ranking recovery |
| **Consolidate** | Multiple similar pages declining | 4-8 hours | Merge authority, kill cannibalization |
| **Retire** | Content no longer relevant, no traffic value | 1 hour | 301 to best alternative page |

### Decision logic:
```
Page declining?
├─ Stats/sources outdated + content still valid → Minor update
├─ Missing 2+ subtopics competitors cover now → Substantial update
├─ Core information wrong/outdated + thin → Rewrite
├─ Multiple pages declining on same topic → Consolidate
├─ Zero traffic + no backlinks + no relevance → Retire (301 redirect)
└─ Seasonal page (declines every year at same time) → Leave alone, note pattern
```

## 4. Refresh Priority

Priority score = Traffic_Impact × Decline_Rate × Commercial_Value

1. **Highest:** High-traffic commercial pages with fast decline → refresh immediately
2. **High:** High-traffic informational pages declining steadily → schedule this month
3. **Medium:** Medium-traffic pages declining slowly → schedule this quarter
4. **Low:** Low-traffic pages, gradual decline → refresh if time allows, else consolidate/retire

### Always prioritize:
- Commercial/money pages over informational
- Pages ranking 4-15 (close to page 1 — small improvements push them over the edge)
- Pages with backlinks (link equity being wasted on decaying content)

## 5. Refresh Checklist

For every refreshed page:
- [ ] Update publish date (show "Updated: [current date]" alongside original date)
- [ ] Replace outdated statistics with current year data
- [ ] Update all source citations to current versions
- [ ] Add 1-3 new subtopics competitors now cover that you don't
- [ ] Cut sections that are no longer relevant
- [ ] Verify all internal and external links still work
- [ ] Check keyword usage still matches current SERP intent
- [ ] Re-submit URL in GSC after publishing

## 6. Refresh Cadence

| Content Type | Review Frequency | Typical Decay Window |
|-------------|-----------------|---------------------|
| News/trends | Monthly | 3-6 months |
| Technical specs/standards | Quarterly | 12-18 months |
| Evergreen guides | Bi-annual | 18-24 months |
| Product pages | Quarterly | 12-18 months |
| Case studies | Annual | 24+ months |
| Company info/about | Annual | 24+ months |

## 7. Prevention

- Publish date + "Last updated" date visible on every page
- Content tracker (`.vibio/trackers/content.md`) includes publish and last-updated dates
- Quarterly freshness audit as standing task in monthly cadence
- When writing new content, note expected decay window (fast-moving topic = schedule refresh 12 months out)
