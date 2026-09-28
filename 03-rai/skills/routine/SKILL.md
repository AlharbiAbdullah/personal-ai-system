---
name: routine
description: >
  Daily, weekly, and monthly rhythm router. USE WHEN the user wants to
  journal, prep today, prep tomorrow, run a weekly retrospective, do
  the monthly bill-pay run, or run the monthly mirror (Rai's month
  look-back / drift check). Time-based cadence skills, split out of
  `/life`. All sub-skills read/write `~/helm/02-ana/`.
---

# Routine

Time-based rhythm — the daily, weekly, and monthly beats that keep the Life OS alive.
Self-model capture (telos, quotes) lives in `/life`; this router owns the cadence.

## Routing table

| Cadence | Task | Sub-skill | File to Read |
|---------|------|-----------|--------------|
| Occasional | Trigger-based journal, prose output. NOT daily | journal | `journal.md` |
| Daily | Morning: prioritize today's plans + fill vault gaps | today-prep | `today-prep.md` |
| Daily | Evening: list tomorrow's items, classify work/personal | tomorrow-prep | `tomorrow-prep.md` |
| Weekly | End-of-week retrospective: shipped, blocked, learned, change | weekly-retro | `weekly-retro.md` |
| Monthly | Bill-pay run — open every portal, pay all recurring bills in one sitting | bills | `bills.md` |
| Monthly | Rai-authored month look-back: drift check, good/bad/ugly/funny, one change | monthly-mirror | `monthly-mirror.md` |

## How to use

1. Pick the sub-skill by rhythm.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## When two could fit

- **journal vs tomorrow-prep:** journal is reflective prose about today; tomorrow-prep is operational list for tomorrow.
- **today-prep vs tomorrow-prep:** morning activation (today) vs. evening commitment (tomorrow).
- **weekly-retro vs journal:** retro is the scheduled week-level synthesis and the floor that catches ordinary days in bulk; journal is unscheduled, fires only on a trigger.
- **bills vs monthly-mirror:** bills is operational (pay everything, after salary lands); monthly-mirror is reflective (Rai reviews the month). Same sitting works: bills first, mirror after.
- **monthly-mirror vs weekly-retro:** retro is John's own weekly synthesis; the mirror is Rai's monthly outside-perspective verdict built from vault receipts.

## Cross-references

- Self-model + wisdom capture → `/life/telos`, `/life/quote`
- Cross-session memory retrieval → `/recall/history`
- Work-side weekly planning → `/work/weekly-planner`
- Bills manifest → `~/helm/02-ana/financial/bills.md`
