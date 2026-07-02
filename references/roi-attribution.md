# ROI Attribution — SEO → Revenue Pipeline

Connect SEO actions to business metrics. Stop reporting rankings; start reporting revenue impact.

## 1. Conversion Tracking Setup

### Must-track events:
- **B2B/Manufacturing:** inquiry form submissions, sample requests, WhatsApp clicks, email clicks, phone call clicks
- **E-commerce:** add-to-cart, checkout start, purchase complete
- **SaaS:** free trial signup, demo request, pricing page visit
- **Content/Media:** newsletter signup, ad click, affiliate click

### Implementation:
- GA4 events for all conversions
- Thank-you page as conversion confirmation (URL-based goal tracking)
- UTM tagging for all non-organic campaigns (to isolate SEO contribution)
- GSC + GA4 integration for landing page → conversion path visibility

## 2. Attribution Models

| Model | How it Works | Best For |
|-------|-------------|----------|
| **Last-click (organic)** | Credits the organic search visit immediately before conversion | Short sales cycles, impulse purchases |
| **First-click (organic)** | Credits the first organic search visit in the journey | Content-driven B2B (research → buy later) |
| **Linear** | Equal credit to all organic touchpoints | Complex B2B with multiple research visits |
| **Position-based** | 40% first + 40% last + 20% middle touchpoints | Most B2B — balances discovery and decision |
| **Time-decay** | More credit to touchpoints closer to conversion | Time-sensitive offers |

**Default for Vibio B2B:** Position-based or first-click (SEO's role is discovery and education).

## 3. SEO Value Calculation

### Core Formula
```
SEO Revenue = Organic Traffic × Conversion Rate × Average Value

Per page:
Page Revenue = Organic Landing Page Sessions × Page Conversion Rate × Conversion Value
```

### B2B Pipeline Model (Vibio default)
```
SEO Revenue = Organic Traffic × Inquiry_Rate × SQL_Rate × Close_Rate × Avg_Deal_Value

Where default estimates:
- Inquiry_Rate: 1-3% for product pages, 0.5-1.5% for blog/informational
- SQL_Rate (inquiry → qualified lead): 30-50%
- Close_Rate (SQL → won deal): 10-30% (use client's actual data)
- Avg_Deal_Value: client provided
```

### Content ROI
```
Content ROI = (Lifetime_Value_of_Organic_Traffic - Content_Production_Cost) / Content_Production_Cost

Lifetime Value = Estimated Monthly Traffic × Avg_Position_CTR × Conversion_Rate × Avg_Value × Content_Lifespan

Content_Lifespan (from content-decay.md §6):
- News/trends articles: 6 months
- Technical specs/standards: 15 months (replaced when standards update)
- Evergreen guides: 21 months
- Product pages: 15 months (SERP refreshes faster for commercial queries)
- Case studies: 24 months
```
**Default when content type unknown: 18 months.** Do NOT use a fixed 24 months for everything — it overestimates ROI for fast-decaying content.

### B2B Cohort Attribution — Handling Long Sales Cycles

B2B sales cycles of 3-18 months break same-period attribution. Today's organic traffic may convert months later. Use this method:

```
Cohort Revenue = Sum of deals where first organic touch was from target page

Per-month attribution:
Month N Attribution = Cohort Revenue / Months_in_Cycle × Lag_Weight

Lag_Weight by month (B2B default):
- Months 1-3: 0.5 (early-stage discovery)
- Months 4-6: 1.0 (active evaluation, heaviest attribution)
- Months 7-12: 0.7 (late-stage decision)
- Months 13-18: 0.3 (delayed close)
```

**If client can't provide cohort data:** use a simplified lag-adjusted formula:
```
Adj_Monthly_Revenue = Monthly Inquiries × Lead_to_Deal_Rate × Avg_Deal_Value × Lag_Factor

Lag_Factor = 0.15 (only ~15% of this month's attributed SEO value is realized this month;
the rest will be realized over the next 3-18 months)
```

**Always label cohort-attributed revenue as "estimated with N-month lag assumption."**

## 4. CPA by Keyword/Page

### Cost Per Acquisition
```
CPA = (SEO_Investment_for_Keyword / Conversions_from_Keyword)

Where SEO Investment = content cost + link building cost + technical optimization cost (allocated)
```

Compare SEO CPA vs Paid Search CPA for the same keyword. A keyword with SEO CPA < Paid CPA is a strong candidate for SEO investment.

## 5. Reporting Structure

### Monthly SEO P&L (recommended format)
```
| Channel/Metric | Traffic | Conversions | Conv. Rate | Revenue | Cost | ROI |
|----------------|---------|-------------|------------|---------|------|-----|
| Organic (total) | | | | | | |
| — Brand queries | | | | | | |
| — Non-brand queries | | | | | | |
| — Blog content | | | | | | |
| — Product pages | | | | | | |
```

### Page-Level ROI
```
| Page | Monthly Traffic | Conversions | Conv. Value | Production Cost | Monthly ROI |
|------|----------------|-------------|-------------|-----------------|-------------|
| /blog/article-1 | | | | | |
| /products/x | | | | | |
```

### Keyword-Level CPA
```
| Keyword | Monthly Volume | Position | Traffic | Conversions | CPA | SEO CPA < Paid CPA? |
|---------|---------------|----------|---------|-------------|-----|---------------------|
```

## 6. Tools Routing

| Need | Route to |
|------|----------|
| Organic traffic data | `seo-google` (GA4 integration) |
| Conversion tracking setup | GA4 configuration |
| Keyword-level position + traffic | `seo-google` (GSC) |
| Competitor traffic estimation | `seo-dataforseo` |
| Attribution modeling | GA4 Attribution reports |

## 7. When Numbers Are Missing

B2B often has long sales cycles and offline conversions. When you can't track end-to-end:
- Use form submissions as proxy conversions
- Ask client for: monthly inquiry count from organic, inquiry-to-deal conversion rate, average deal value
- Calculate: `Monthly SEO Revenue = Organic Inquiries × Lead_to_Deal_Rate × Avg_Deal_Value`
- Mark estimates clearly: "Based on your reported conversion rate of X% and average deal of Y"
