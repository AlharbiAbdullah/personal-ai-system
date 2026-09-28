---
name: telos
description: >
  Life OS and personal organizational analysis.
  USE WHEN the user wants to update life goals, extract wisdom from
  conversations, review their belief system, or generate life reports.
---

# Telos

Personal operating system for goals, beliefs, mental models, and wisdom.
Reads from and writes to `~/helm/02-ana/`. Provides structured introspection and narrative synthesis.

## Source of truth

All telos content lives in `~/helm/02-ana/`. There is no single index file;
`identity/` is the auto-loaded surface, and it points into the rest.

### Identity (`identity/`, auto-loaded every session)

- `who-i-am.md` — current self-snapshot
- `story.md`, `vision.md`, `mindset.md` — DIGESTS, capped at 4KB each. Full
  texts live in `~/helm/02-ana/self/` (same filenames), one read away. When
  updating one of these, write the full text in `self/` first, then
  regenerate the ≤4KB digest for `identity/`.
- `goals.md` — this year's targets
- `projects.md` — active, completed, personal projects
- `wrong.md` — things I was wrong about
- `contacts.md` — people I know
- `environment.md` — digital assets (directories, accounts, hardware)
- `tech-stack.md` — technical preferences
- `definitions.md` — personal terminology
- `ideas.md` — ideas in exploration (full lifecycle in `09-ideas/`)
- `influences.md`: people and works that shaped my thinking

### Soul (`soul/`)

Timeless reflective writing. Authoring rules in `soul/AGENTS.md`.

- `on-failure.md` and any future soul essays

### Living data

- `family/` — one `{name}.md` per person, `calendar.md`
- `health/` — `health-overview.md`, `medications.md`, `supplements.md`, `recovery-plan.md`, `specialists.md`
- `financial/` — `budget.md`, `assets.md`, `debt-plan.md`
- `admin/` — `documents.md`, `maintenance.md`
- `travel/` — `bucket-list.md`, `log.md`
- `journal/` — occasional, trigger-based reflection (managed by `/routine journal`), not daily
- `monthly/`: Rai-authored monthly mirrors, one per reviewed month (managed by `/routine monthly-mirror`)
- `todos/` — `today-plans/`, `tomorrow-plans/` (managed by `/routine today-prep`, `/routine tomorrow-prep`)
- `quotes/` — external quotes, one file per quote
- `wisdom/`: full rule-sets and creeds (Jante, Dokkodo, Enchiridion, Meditations, Al-Hikam, Al-Shafi'i, Kipling, Gita, Franklin)
- `shopping/` — active purchase research

## Workflows

### Update
Modify any telos file based on new information.
Steps: read current state, identify what changed, update file, note the reason for the change.

### InterviewExtraction
Extract telos-relevant insights from a conversation or text.
Steps: scan content for beliefs, goals, principles, mental models, or narrative points.
Cross-reference with existing telos content. Present new findings for user approval before writing.

### CreateNarrativePoints
Generate a narrative summary of the user's current trajectory.
Steps: read `identity/` files and `soul/` essays, identify themes, synthesize into a coherent story about where the user is heading.

### WriteReport
Produce a structured life report.
Steps: compile goal progress from `identity/goals.md`, active work from `identity/projects.md`, belief or principle changes in `identity/mindset.md` since last report, new entries in `identity/wrong.md`.
Output as a dated report document.

## Guidelines

- Never modify telos files without user confirmation
- Track change history (what changed and why)
- Cross-reference new entries against existing beliefs for conflicts
- Flag goal-belief misalignment when detected
- Write in English. Never Arabic.

## Examples

- "Update my goals: I'm shifting focus to [new area]"
- "Extract principles from today's conversation"
- "Write a telos report for this month"
- "Review my beliefs for internal contradictions"
