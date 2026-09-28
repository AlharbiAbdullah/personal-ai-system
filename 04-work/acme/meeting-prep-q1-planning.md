---
type: meeting-prep
engagement: acme
meeting: Q1 Planning
date: 2026-01-09
created: 2026-01-01
---

# Meeting Prep — Q1 Planning (Platform)

> Example meeting-prep note. `04-work/{engagement}/` holds everything for one paid engagement
> (here, `acme/`). The `/work meeting-prep` skill builds a briefing + agenda from the engagement
> context. Formal tone; confidential.

## The meeting
- **What:** Q1 platform roadmap planning.
- **Who:** Platform team + eng manager + a data-team rep.
- **My goal:** get the metrics migration funded as a Q1 priority, not pushed to Q2.

## What I want out of it
1. Agreement that the metrics migration finishes in Q1 (it's half-done; stalling wastes the work).
2. A decision on who owns the data-team dependency.
3. One clear next action with an owner and a date.

## My one-pager (the ask)
- **Problem:** the old metrics pipeline is brittle and blocks three downstream teams.
- **Status:** migration is ~60% done; backfill + validation remain.
- **Ask:** prioritize the remaining 40% in Q1; one data-team reviewer assigned.
- **Cost of waiting:** every quarter on the old pipeline is more downstream workarounds to unwind.

## Likely pushback → my answer
| Pushback | Answer |
|----------|--------|
| "Can it wait for Q2?" | The half-migrated state is the *worst* state — two systems to maintain. |
| "Data team is slammed." | I only need one reviewer for the schema, ~2 hrs/week for 3 weeks. |

## Agenda (proposed)
1. Migration status (5 min)
2. The Q1 vs Q2 decision (10 min)
3. Dependency owner + next action (5 min)

## After
- [ ] Send the one-pager 24h before.
- [ ] Capture the decision + owner in this file right after.
