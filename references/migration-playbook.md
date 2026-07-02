# Migration Playbook — Domain & Platform Changes

Migrations are the highest-risk SEO event. Follow this playbook to minimize ranking losses.

## 1. Pre-Migration Checklist

- [ ] Crawl current site: full URL list with status codes (`seo-firecrawl`)
- [ ] Export all GSC data: queries, pages, positions (`seo-google`)
- [ ] Export GA4 landing page data: traffic, conversions per URL
- [ ] Backup: robots.txt, sitemap.xml, SEO meta templates, JSON-LD
- [ ] Create 1:1 URL redirect map (every old URL → new URL)
- [ ] Identify: pages being removed (→ 404 or parent redirect), pages being merged
- [ ] Verify new site: no noindex, correct canonicals, valid sitemap, correct robots.txt
- [ ] Test redirect map: spot-check 50+ URLs

## 2. URL Mapping

Every old URL must: (a) 301 redirect to exact new equivalent, or (b) 301 redirect to closest relevant page
- Preserve URL structure where possible
- Handle HTTP→HTTPS, www→non-www, trailing slash, parameter cleanup
- Image and PDF URLs also need redirects
- Create redirect map: Old URL | New URL | Type | Notes

## 3. Platform-Specific

**WordPress → Next.js:** account for trailing slash differences, redirect `/wp-content/uploads/`
**HTTP → HTTPS:** every HTTP URL → HTTPS; update canonicals, OG URLs, sitemap; add HSTS header
**Domain Change:** most disruptive, expect 2-6 month volatility; keep old domain redirecting 1+ year; use GSC Change of Address
**Subdomain → Subdirectory:** generally positive; update internal links; add both to GSC

## 4. Launch Day Protocol

1. Pre-launch: verify staging passes all SEO checks
2. DNS switch: point domain to new hosting
3. Immediate verify: homepage 200, old URLs redirect correctly, robots.txt + sitemap accessible
4. Submit: new sitemap to GSC, request indexing for homepage + 10 key pages
5. Monitor 48h: GSC index coverage, server 404 logs, mobile+desktop rendering

## 5. Post-Migration Monitoring

| Period | Activity |
|--------|----------|
| Days 1-7 | Daily GSC: index coverage, crawl stats, 404s |
| Weeks 2-4 | Weekly GSC: impressions/clicks/positions; fix issues |
| Months 2-3 | Monthly vs pre-migration baseline; expect volatility |
| Months 4-6 | Rankings should stabilize |

**Expected impact:** well-executed (0-10% dip, 2-4wk recovery), URL changes (5-20% dip, 4-12wk), domain change (10-30% dip, 2-6mo).

## 6. Common Mistakes

- No redirect map → ranking tank
- Redirect chains (keep 1-hop)
- Staging noindex copied to production
- robots.txt blocking new site
- Canonical pointing to old domain
- Forgetting internal link updates
- Sitemap with old URLs
- Old domain turned off too early (redirects break, backlinks break)
- Image/PDF redirects forgotten

## 7. Tools

| Need | Route |
|------|-------|
| Pre-migration crawl | `seo-firecrawl` |
| GSC export | `seo-google` |
| Post-migration monitoring | `seo-google` + `seo-drift` |
| Schema validation | `seo-schema` |
