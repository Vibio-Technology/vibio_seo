# State Templates

Standard formats for `.vibio/` files. Keep fields consistent so the next session can read them mechanically. Dates as `YYYY-MM-DD`. Fill what's known, leave the rest blank — don't invent.

---

## project.md

```md
# <Project Name> — SEO State

> Single source of truth. Updated by vibio-plan (diagnosis/roadmap) and vibio-audit (status/stack). Read this first.

## Snapshot
- Site / URL:
- Stack: (Next.js / WordPress / Shopify / static / unknown)
- Edit mode: (code / template / CMS-paste)
- Business model:
- Primary conversion:
- Target market / language:
- Domain state: (new / aged)
- GSC verified: (yes/no)   GA4: (yes/no)

## Diagnosis (from vibio-plan)
- Primary class:
- Secondary tag:
- Dominant bottleneck:
- 90-day objective:
- Last reviewed: YYYY-MM-DD

## Roadmap progress
- [ ] Week 1 — technical baseline & measurement
- [ ] Week 2 — keyword architecture & page mapping
- [ ] Weeks 3-4 — first priority pages
- [ ] Month 2 — depth & on-page
- [ ] Month 3 — authority + review loop
(check off / annotate with date + note as phases complete)

## Current phase & next bottleneck
- Now in:
- Done so far:
- Next action:

## Open questions / risks
- ...
```

---

## trackers/content.md

```md
# Content Tracker

| Title | URL | Page type | Keyword family | Intent | Status | Published | Updated | Owner | Notes |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | planned | | | | |

Status values: planned / drafting / published / refresh-needed / merged / redirected / retired
```

---

## trackers/keywords.md

```md
# Keyword Tracker (keep lean: 20-60 meaningful terms)

| Keyword | Intent | Owner page | Priority | Difficulty | Current rank | Last rank | Trend | Notes |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | not-yet-ranking | |

Trend values: improving / flat / declining / not-yet-ranking
Review monthly.
```

---

## trackers/outreach.md

```md
# Outreach Tracker (create once authority work starts)

| Target site | Contact / channel | Type | Promoted page | Date sent | Follow-up | Status | Result |
|---|---|---|---|---|---|---|---|
| | | | | | | not-started | |

Type values: guest-post / product-review / partner / media-request / resource
Status values: not-started / sent / follow-up-due / in-conversation / won / lost
```

---

## changelog.md

```md
# Change Log

> Append-only. Every AUDIT finding and FIX change, newest at top. Never overwrite.

## YYYY-MM-DD — <AUDIT|FIX> — <short title>
- Type: AUDIT finding | FIX change
- Severity (audit): Critical / High / Medium / Low
- What: <what was found or changed>
- Where: <file / template / CMS location / URL>
- Verified: <build/lint result, or grep of rendered HTML, or "pending re-crawl">
- Status: open / fixed / deferred
- Ref: <official doc URL if it cites a Google policy>

## YYYY-MM-DD — ...
```

---

## Optional: technical-log

Only if technical work volume justifies a fourth tracker (per operating-system.md). Otherwise technical issues live as entries in `changelog.md` with `Type: AUDIT finding`.
