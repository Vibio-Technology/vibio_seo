# Multi-Language SEO Operations

Systematic bilingual/multilingual SEO. Each language market is a separate SEO project with its own SERP, competitors, and user expectations.

## 1. Market-First Approach

Decide target language by market opportunity, not by "we should have English."

**Market selection criteria:**
1. Business relevance (do you sell there? do buyers search in that language?)
2. Search volume (validate with seo-dataforseo per language)
3. Competition level (check SERP for each language independently)
4. Content capacity (can you produce quality content in this language?)

## 2. Keyword Research Per Language

### Never translate keywords.
Chinese and English users search differently for the same product. Example:
- EN: "carbon fiber fabric supplier"
- ZH: "碳纤维布厂家" (different structure, different intent modifiers)

### Run independent research per language:
1. Seed keywords in the target language (not translated — brainstormed natively)
2. `seo-dataforseo` for each language separately
3. Intent classification may differ: same product, different buyer journey stages per market
4. Difficulty assessment per market (competitors in EN market may be stronger than ZH market)

## 3. Content Strategy Per Market

Different SERPs demand different content:

| Market | Common Characteristics | Content Strategy |
|--------|----------------------|-----------------|
| EN-US/UK | Long-form guides, EEAT-heavy, data-driven | Comprehensive guides, original data, strong sourcing |
| EN-export markets | Specification-focused, certification-heavy | Spec sheets, standards compliance, comparison tables |
| ZH-CN (mainland) | Baidu-optimized format differs from Google; mobile-first | Shorter paragraphs, WeChat-compatible formatting, domestic examples |
| Multilingual EU | Per-country SERP differences, hreflang critical | Localized content per country, not just language |

## 4. URL Structure

| Approach | URL Pattern | Pros | Cons |
|----------|------------|------|------|
| **Subdirectory** | `example.com/en/`, `example.com/zh/` | Authority consolidated on one domain | Requires robust hosting |
| **Subdomain** | `en.example.com`, `zh.example.com` | Easier to host separately | Authority partially split |
| **ccTLD** | `example.co.uk`, `example.cn` | Strongest geo-signal | Most expensive, hardest to manage |
| **Language params** | `example.com?lang=en` | Easy to implement | Worst for SEO — avoid |

**Recommendation for Vibio B2B:** subdirectory (`/en/`, `/zh/`) — consolidates domain authority, simpler to manage, good geo-flexibility.

## 5. Hreflang Implementation

### Requirements:
- Reciprocal: if `/en/page-a` has `hreflang="zh"` pointing to `/zh/page-a`, then `/zh/page-a` must point back
- Complete: every language version lists ALL language versions including itself
- Valid codes: `en`, `zh-Hans`, `zh-Hant`, `de`, `ja`, `ko`, etc. (ISO 639-1 + optionally ISO 3166-1 region)
- `x-default`: a fallback for users whose language isn't specifically targeted

### Validation:
- Route to `seo-hreflang` for validation
- Check: no missing return links, valid language codes, all pages resolve (200)

## 6. Transcreation Workflow

Transcreate, never translate directly.

1. **Write original** in the strongest language (most fluent writer available)
2. **Transcreate** to second language:
   - Native speaker rewrites, not machine-translates
   - Adjust: cultural references, case studies, examples, units of measurement
   - Adapt: humor, idioms, metaphors (they rarely work across languages)
   - Localize: compliance references, standards, legal disclaimers
3. **Keyword-optimize** in target language (use that language's keyword research, not translated keywords)
4. **Quality check** by native speaker
5. **On-page wiring** per language: title, meta description, OG tags, schema (Article with `inLanguage`)

### Translation quality tiers:
- **Machine translation (MT):** unacceptable. Google can detect it and may demote.
- **MT + human editing:** acceptable for low-priority pages.
- **Human transcreation:** required for commercial pages and key content.
- **Native writer original:** best — content strategy built for that market from scratch.

## 7. Internal Linking Across Languages

- Link to equivalent page in other language where helpful (e.g., a language switcher in header/footer)
- Keep internal link equity within each language (cross-language links are for UX, not primary equity flow)
- Anchor text for cross-language links: use the target language ("中文" not "Chinese" on EN pages)

## 8. Measurement Per Market

- Separate GSC properties (or filtered views) per language/directory
- Per-market KPIs: traffic, conversion rate, bounce rate, time on page
- Per-market keyword tracking in `.vibio/trackers/keywords.md` with language column
- Monthly per-market review in REVIEW mode

## 9. Common Mistakes

- Translating keywords directly → zero search volume in target language
- Machine-translating content → poor quality, potential Google demotion
- Same content strategy for all markets → different SERPs demand different formats
- Missing hreflang tags → Google sees duplicate content, picks wrong language version
- Wrong language codes → `zh` vs `zh-Hans` (simplified) vs `zh-Hant` (traditional)
- Not maintaining hreflang reciprocity → all hreflang signals ignored
- Ignoring Baidu for Chinese market → Google is blocked in China; Baidu has different rules
