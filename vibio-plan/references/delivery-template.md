# Delivery Template

Use this structure whenever vibio_seo outputs a PLAN deliverable. The structure is part of the skill — it keeps output operational, not a narrative.

## Formatting rules

- Concise but actionable. Short bullets with method details over theory paragraphs.
- Sections in the order below.
- State assumptions explicitly.
- End with immediate next actions.
- Read like an operator handing off a working plan, not a consultant padding a deck.
  - Prefer: "Build 3 collection pages for X, Y, Z", "Refresh 5 pages ranking 11-20".
  - Avoid: "Consider optimizing your content strategy", "Explore backlink opportunities".

## Default output

```md
# [Project Name] SEO Execution Plan

## Project Snapshot
- Site type:
- Business model:
- Primary conversion:
- Target market:
- Primary language:
- Stack:
- Current stage:
- Weekly execution capacity:

## Diagnosis
- Primary mode:
- Secondary tag:
- Main bottleneck:
- Why this is the bottleneck:
- 90-day objective:

## Assumptions
- ...

## Priority Order
1. ...
2. ...
3. ...

## 90-Day Roadmap

### Days 1-14
- Task:
  Purpose:
  Method:
  Done when:

### Days 15-30
- Task:
  Purpose:
  Method:
  Done when:

### Days 31-60
- Task:
  Purpose:
  Method:
  Done when:

### Days 61-90
- Task:
  Purpose:
  Method:
  Done when:

## Weekly Cadence
- Block 1: Focus / Time / Typical tasks
- Block 2: Focus / Time / Typical tasks
- Block 3: Focus / Time / Typical tasks

## Monthly Deep Work
- Review focus:
- Reports to inspect:
- Decisions to make:

## Task SOPs For Current Phase
- SOP: Use it for / Steps / Done when

## Specialist Skills To Run
- Skill: what it will produce for this project (route per references/skill-arsenal.md)

## Tracking System
- Content tracker: Purpose / Fields
- Keyword tracker: Purpose / Fields
- Outreach tracker: Purpose / Fields
- Technical log: Use only if

## Risks And Constraints
- ...

## Next 3 Actions
1. ...
2. ...
3. ...
```

## Compression rule

If the user asks for a narrower deliverable, keep the logic but compress:
- "just the next month" → diagnosis + next-30-days + weekly cadence + next 3 actions.
- "what should I do this week" → diagnosis + this-week priority + micro-SOP + next 3 actions.

## Expansion rule

If given a real codebase/page inventory/site context, expand with project-specific items: name specific page types, name likely missing assets, identify technical risks from the stack, tailor cadence to realistic capacity, and name which `skill-arsenal.md` specialists to fire.

## Continuation rule

If the user is continuing an existing project, don't restart. First identify the current phase, what's done, and the next bottleneck; then output only the next operating slice in the same structure.
