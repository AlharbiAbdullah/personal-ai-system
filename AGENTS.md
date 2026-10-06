# Helm Vault: Claude Instructions

This is John's vault root. Each subfolder owns its own rules in its own `AGENTS.md`. This file holds only vault-wide navigation and workflow. When in doubt about a folder's conventions, read that folder's AGENTS.md.

## Quick Orientation

1. Check the relevant MOC in `10-knowledge/_mocs/` for topic navigation.
2. Follow `[[wiki-links]]` to build understanding.
3. Read the subfolder's AGENTS.md before writing there. Folder-specific rules live there, not here.

## Folder Structure

| Folder          | Purpose                                                                 | Rules                    |
| --------------- | ----------------------------------------------------------------------- | ------------------------ |
| `00-landing/`   | Parking lot. Manual captures only. Exits: promote to inbox OR delete.   | `00-landing/AGENTS.md`   |
| `01-inbox/`     | Research queue. Rai enriches each item + rates A/B/C/D + routes.        | `01-inbox/AGENTS.md`     |
| `02-ana/`       | John's Life OS. `identity/` auto-loads every session.               | `02-ana/AGENTS.md`       |
| `03-rai/`       | Rai's brain: skills, agents, hooks, memory, semantic-memory.            | `03-rai/AGENTS.md`       |
| `04-work/`      | Work footprint. Engagement subfolders + `work-plans/` (ISO week).       | `04-work/AGENTS.md`      |
| `05-projects/`  | `kitchen/` -> `active/` -> `completed/`. Code lives in `~/projects/`.   | `05-projects/AGENTS.md`  |
| `06-learning/`  | Courses & tutorials. Kebab-case topics, Phase/Module allowed.           | `06-learning/AGENTS.md`  |
| `07-reading/`   | Books through Claude Code. Full coverage, not summaries.                | `07-reading/AGENTS.md`   |
| `08-bawaba/`    | News digest output (`/news-digest`). LIVE: never delete `daily/` files. | `08-bawaba/AGENTS.md`    |
| `09-ideas/`     | Seed -> Plant -> Tree -> Graduated. Flat, status in frontmatter.        | `09-ideas/AGENTS.md`     |
| `10-knowledge/` | Topic notes, MOCs, Insights. Simplicity Theorem on every note.          | `10-knowledge/AGENTS.md` |
| `11-workflows/` | Your way of doing each kind of work. Rai follows the match.         | `11-workflows/AGENTS.md` |
| `12-system/`    | Templates (`templates/`), tools, dev notes, diagrams, media. `12-system/manual/README.md` maps each topic to its live doc. | `12-system/AGENTS.md`    |
| `13-archive/`   | Session JSONs + standing exceptions (`news/`, `learning/`, `shopping/`, `audits/`). See its AGENTS.md. | `13-archive/AGENTS.md`   |

## Root items

| Item | Purpose |
| ---- | ------- |
| `AGENTS.md` | This file: vault-wide navigation and workflow. |
| `visual/` | `/visual` output home for topics not tied to a repo (created on first use). |
| `.agent/` | Decision records from `/grill`, `/compile` and audits (created on first use). |
| `.helm-index/` | Navigation index (`helm-index.md`), written by `/map-updater` and injected at session start. |
| `north-star.md` | The learning ladder, kept at the root. Add a `master-plan.md` beside it if you stage your learning. |
| `.vale.ini` | The prose gate config (`03-rai/config/vale/README.md`). |

## Archive vs Delete

**Archive only session JSONs** (`/rai process-sessions` drains them to `13-archive/historical-sessions/`, the archive's core). Sessions are cheap to store and the forensic/wisdom-mining value compounds.

**Delete everything else** once it's no longer live. Git log is the archive for text content.

**Standing exceptions**, each approved by John (dates and terms in `13-archive/AGENTS.md`):

- `13-archive/news/`: prior digests (moved) plus the raw daily dumps and weekly run dirs (copied), all placed there automatically by the news pipeline.
- `13-archive/learning/`: retired curricula, frozen reference.
- `13-archive/shopping/`: closed shopping plans for things John bought.
- `13-archive/audits/`: closed audits, their single home.

Never purge these. A 2026-06-11 maintenance run deleted `news/` and `learning/` plus the live `08-bawaba/daily/` digest. It followed this section without the exceptions, and it all had to be restored. Deleting content is never part of a commit run's job. Commit what exists.

## Capture pipeline

```
00-landing/              01-inbox/                 destination
(manual drops)  ─────▶   (research + rating)  ───▶ 07-reading, 06-learning,
                                                    10-knowledge, 09-ideas,
                                                    05-projects, 04-work
```

Triggered via the `/triage` skill group: `process-landing` for landing triage, `process-inbox` for inbox research.

## Idea pipeline

```
09-ideas/                         05-projects/                  ~/projects/
Seed → Plant → Tree → Graduated ──▶ kitchen/{name}/ ──▶ active/{name}/ + ~/projects/{name}/
                                    (specs/, research/)  (non-code + code)
                                           │
                                           ▼
                                    completed/{name}/
                                    (retrospective + diagrams)
```

Triggered via the `/ideas` skill group: `start-seed`, `promote`, `graduate`, `derive`.

## Identity auto-load

At session start, Rai auto-loads every `*.md` file in `03-rai/identity/` and `02-ana/identity/`. The contract (digests, budget) is in `03-rai/AGENTS.md`.

To add or remove a file from session context, move it in or out of an `identity/` folder.

Non-`.md` files in identity/ are NOT auto-loaded (they're for specific hooks/skills).

## Skills

Every skill is a router or a leaf in `03-rai/skills/`. `03-rai/skills/MANIFEST.md` lists each one with its sub-skills, and its Groups section sorts them by area.

## Templates

Always use existing templates from `12-system/templates/`. Never invent note structures. Full inventory in `12-system/AGENTS.md`.
