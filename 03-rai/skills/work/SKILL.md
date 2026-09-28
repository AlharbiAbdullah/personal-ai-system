---
name: work
description: >
  Work router. USE WHEN the user wants to plan the week, prep for a meeting,
  or do work-related rituals. Routes between weekly-planner and meeting-prep.
  All sub-skills read/write `~/helm/04-work/`.
---

# Work

Work rituals for John's paid engagements. Parallel to `/routine` but scoped to `04-work/`.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Monday ritual — plan the week | weekly-planner | `weekly-planner.md` |
| Pre-meeting briefing + agenda | meeting-prep | `meeting-prep.md` |

## How to use

1. Pick the sub-skill by ritual.
2. `Read` the file in this directory.
3. Follow that file's instructions.
