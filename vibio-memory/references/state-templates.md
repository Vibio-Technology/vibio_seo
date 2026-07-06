# State Templates

Standard formats for `.vibio/` files. Keep fields consistent so the next session can read them mechanically. Dates as `YYYY-MM-DD`. Fill what's known, leave the rest blank — don't invent.

Second memory layer: cross-project learnings live outside `.vibio/` at `~/.vibio-global/` (learnings.md + calibration.md) — formats and protocols in `learning-loop.md`, not duplicated here.

---

## project.md

```md
# <Project Name> — SEO State

> Single source of truth. Updated by PLAN (diagnosis/roadmap) and AUDIT (status/stack). Read this first.

## Snapshot
- Site / URL:
- Stack: (Next.js / WordPress / Shopify / static / unknown)
- Edit mode: (code / template / CMS-paste)
- Business model:
- Primary conversion:
- Target market / language:
- Domain state: (new / aged)
- GSC verified: (yes/no)   GA4: (yes/no)

## Diagnosis (from PLAN)
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

| Keyword | Intent | Validated | Cascade | Owner page | Priority | Difficulty | Current rank | Last rank | Trend | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | not-yet-ranking | |

Validated values: pass / conditional (per keyword-validation.md five gates; failed terms don't enter the table — log the reason in Notes of a related term or in changelog)
Cascade values: 1-4 (KD tier per authority-cascade.md)
Trend values: improving / flat / declining / not-yet-ranking
Review monthly.
```

---

## trackers/outreach.md

```md
# Outreach Tracker (create once authority work starts; process defined in backlink-playbook.md)

| Target site | Contact / channel | Type | Promoted page | Date sent | Follow-up | Status | Result |
|---|---|---|---|---|---|---|---|
| | | | | | | not-started | |

Type values: directory / association / certification / trade-show / partner / guest-post / product-review / media-request / digital-PR / expert-quote / reclaim / broken-link / resource
Status values: not-started / drafted / pending-human-review / sent / follow-up-due / in-conversation / won / lost
(The agent advances status only up to pending-human-review; a human sends/registers and backfills sent+. See backlink-playbook.md execution boundary.)
Result: link URL, or "mention-unlinked" (unlinked brand mentions count — they feed AI citations)
```

---

## trackers/links.md (optional — create at first internal-link audit)

```md
# Internal Link Health (per link-architecture.md; refresh quarterly)

Last audit: YYYY-MM-DD

## Orphan pages (inlinks = 0)
- url — planned donor pages

## Weak-linked priority pages (inlinks < 5)
- url — current inlinks — planned donors

## Backfill queue (new pages awaiting inbound links)
- url — published date — donor pages + anchor — done? (clear weekly)

## Money-page inlink counts
| Page | Inlinks | Click depth | Last donor pass |
|---|---|---|---|
```

---

## changelog.md

```md
# Change Log

> Append-only. Every AUDIT finding and FIX change, newest at top. Never overwrite.

## YYYY-MM-DD — <AUDIT|FIX|REVIEW> — <short title>
- Type: AUDIT finding | FIX change | REVIEW conclusion
- Severity (audit): Critical / High / Medium / Low
- What: <what was found, changed, or concluded>
- Where: <file / template / CMS location / URL>
- Verified: <build/lint result, or grep of rendered HTML, or "pending re-crawl">
- Status: open / fixed / deferred
- Ref: <official doc URL if it cites a Google policy>

## YYYY-MM-DD — ...
```

---

## Optional: technical-log

Only if technical work volume justifies a fourth tracker (per operating-system.md). Otherwise technical issues live as entries in `changelog.md` with `Type: AUDIT finding`.
