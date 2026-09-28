---
title: "taskflow"
status: ACTIVE
created: "2026-01-01"
updated: "2026-01-01"
type: prd
---

# taskflow

> Example of an **active** project. It graduated from the kitchen (PRD + arch + design) into
> `active/`, and its code now lives in `~/projects/taskflow/`. This folder holds the non-code
> trace — the PRD, decisions, and [[05-projects/active/taskflow/notes|running notes]].

## Problem

Solo makers juggle work across five tools and a notebook. None of them fit the way one person
actually plans a week: a few real priorities, everything else noise. taskflow is a focused
task/planning app for an audience of one-person teams — see [[02-ana/identity/projects|Projects]].

## Success Criteria

- [ ] A new user can plan their week in under two minutes.
- [ ] 10 paying users who didn't get a personal ask from me.
- [ ] I understand the full loop: auth, billing, support, retention (the real reason it exists).

## Scope

### In Scope
- Weekly planning view (the core), tasks, a "today" cut.
- Auth + Stripe billing + a help email.

### Out of Scope
- Teams, real-time collaboration, mobile apps (web-responsive only for v1).

## Status

| Area | State |
|------|-------|
| Planning view | shipped (prototype) |
| Auth | shipped |
| Billing | in progress — Stripe test mode wired |
| First users | recruiting 3 friendlies before public |

## Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Stack | Next.js + Postgres | on-stack ([[02-ana/identity/tech-stack|tech-stack]]), fast to ship a web app |
| Billing | Stripe Checkout | don't build billing; rent it |
| Hosting | one cloud VM + managed Postgres | cheap, boring, mine |

## Log

| Date | Action | Notes |
|------|--------|-------|
| 2026-01-01 | Promoted to active | code scaffolded in `~/projects/taskflow/` |

## Related
- [[05-projects/active/taskflow/notes|Running notes]] — the working log
- [[09-ideas/local-first-task-sync|Local-first task sync]] — an idea spun out of building this
- [[02-ana/identity/goals|Goals]] — "taskflow to 10 paying users"
