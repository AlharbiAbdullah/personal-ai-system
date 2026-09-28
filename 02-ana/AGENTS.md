# 02-ana/ — Your Life OS

Everything about you lives here: identity, family, health, finances, admin, travel,
journal, todos, quotes, shopping, soul (reflective writing).

> `ana` means "I / me" in Arabic — this is your own folder. Rename it if you like, but the
> auto-load and several skills reference `02-ana/identity/`, so update those too if you do.

## Auto-load contract
`02-ana/identity/` is auto-loaded at session start. To add or remove a file from
session context, move it in or out of `identity/`. No code changes needed.

Non-`.md` files in identity/ are NOT auto-loaded — they're read by specific hooks/skills.

## Top-level layout
- `identity/` — your self-model + reference (auto-loaded every session)
- `soul/` — reflective writing (own AGENTS.md)
- `journal/` — occasional, trigger-based reflection (managed by `/routine journal`). Not daily. See that skill for the triggers.
- `monthly/` — Rai-authored monthly mirrors, one per reviewed month (managed by `/routine monthly-mirror`).
- `weekly/` — created on the first `/routine weekly-retro` run.
- `todos/` — managed by `/routine today-prep` and `/routine tomorrow-prep`
- `quotes/` — captured quotes (managed by `/life quote`)
- `family/` — the people closest to you
- `health/` — overview, medications, recovery, specialists, supplements
- `financial/` — assets, budget, debt-plan, optional investment practice
- `admin/` — documents, maintenance
- `travel/` — trips, bookings
- `shopping/` — live purchase-research plans. A plan for something you bought moves whole to `13-archive/shopping/` (its end-of-life home; see `13-archive/AGENTS.md`).
- `voice-samples/` — writing samples that teach the `/writing` skill your voice

## Notes on identity/ideas.md
The *top-ideas shortlist*. Ideas that graduated out of `09-ideas/` and are
committed to pursuit. They either grow into `05-projects/` or stay as "future ideas."
Not a dump. A short curated list.
`09-ideas/` is the nursery where ideas grow or die.

## Rules
- Write in your working language. Keep one source of truth per fact — update in place, don't duplicate.
- Before creating a new file, check if it fits in an existing one.
- This whole folder is private. Never publish it.
