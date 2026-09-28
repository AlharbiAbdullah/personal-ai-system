# Rai Brain Instructions

Canonical brain entry file. This is the source of truth for how Rai loads. `AGENTS.md` is the
only instruction filename in the vault: Claude Code 2.1.277+ reads it natively at the root and
per folder. The one exception is `~/.claude/CLAUDE.md`, a symlink to this file made by
`setup.sh`, because Claude Code has no user-level `AGENTS.md`. Last updated: 2026-09-28.

## Folder map

Full layout in `ARCHITECTURE.md`. Skill groupings in `skills/MANIFEST.md`. Agent tiers in
`agents/MANIFEST.md`. The vault root `AGENTS.md` documents folders 00-13.

## Identity auto-load contract

At session start, Rai auto-loads every `*.md` file in:
- `03-rai/identity/`: Rai config (persona, steering, response format, coding format)
- `02-ana/identity/`: John's self-model (who-i-am, goals, vision, mindset, story, wrong,
  projects, ideas, contacts, definitions, environment, tech-stack)

To add or remove a file from session context, move it in or out of an `identity/` folder.
No code changes needed. Non-`.md` files in identity/ are NOT auto-loaded. They are read by
specific hooks or skills only.

John's broader Life OS (journal, family, health, financial, admin, travel, todos, quotes,
shopping, soul) lives in `~/helm/02-ana/` and is read on-demand via `/life` (self-model +
quotes) and `/routine` (daily/weekly rhythm) skills.

## Session Memory (Memory v3, hybrid)

The rule: live writes append to TEXT only. The ChromaDB vector store is batch-written by the
memory pipeline, never during a live turn. Full design in `ARCHITECTURE.md`.

- **Live capture**: `turn-capture.py` (Stop hook) has a model write observer bullets per turn
  into `semantic-memory/daily/YYYY-MM-DD.md` (interactive sessions only; headless, thin, and
  debounced turns are skipped). The daily log is a plain-text recency buffer, batch-indexed
  into the `rai-daily` collection later. Blocks whose session is already distilled are marked
  `distilled: true` and down-ranked at recall (daily = recency buffer, semantic = quality
  record). The drain also feeds each session's bullets to the distill as a turn-by-turn map,
  and distills long transcripts in chunked windows plus one reduce pass.
- **Curated working memory**: `identity/working-memory.md` (cap 2,500 chars), written via the
  `/remember` skill ("remember this", "note that", "تذكر", "احفظ"). Auto-loads by the identity
  contract. This plus the daily log are the only live writes; everything else is derived by the
  batch pipeline.
- **Deep stores**: ChromaDB holds four collections: `rai-semantic` (distilled facts,
  decisions, summaries), `rai-episodic` (raw whole sessions), `rai-daily` (live-log blocks),
  and `rai-preferences` (derived dedup index). The public kit ships these empty; the store is
  rebuilt locally from your own sessions.
- **Capture**: `sync_claude_sessions.py` scans native Claude Code transcripts under
  `~/.claude/projects/**/*.jsonl`, classifies each session through one gate
  (`hooks/lib/session_gate.py`: explicit-remember / memory-worthy / archive-only / ephemeral),
  and queues survivors into `semantic-memory/pending/`. The ledger is
  `semantic-memory/processed-sessions.jsonl`.
- **Repo truth lives in the repo.** In a repo with `.project.toml`, project facts
  (requirements, decisions, commands, lessons) are written to its `specs/` or
  `project_memory/`, never only to Rai memory. Rai memory keeps preferences John states
  himself, cross-project lessons with a link, and one `worked in <repo>` pointer per session;
  `turn-capture.py` and `distill_session.py` enforce it via `hooks/lib/sdd_repo.py`. On
  conflict the repo wins; `/recall` hits about a repo are hints to verify.
- **Injection**: SessionStart reads a frozen snapshot: identity `*.md` files plus the
  pre-rendered `memory/state/memory-block.md` plus today's daily-log tail. No ChromaDB call at
  startup. Identity surface budget: 4KB per file and 44KB total, an advisory warning, never a
  truncation. Per-prompt pointer RAG (`memory-injection.py`) is relevance-floored and
  session-deduped.
- **Recall**: `/recall` escalates only when needed: T0 (already in context) to T1 (semantic +
  daily) to T2 (episodic pointers) to T3 (verbatim receipts).
- **Self-evolve**: preferences that re-confirm semantically collect in
  `learned-candidates.jsonl`; a weekly curate pass (merge, decay, promote) renders the capped
  active slice to `identity/learned.md`, which auto-loads. Git-tracked and reversible.

Skills: `/rai process-sessions`, `/recall`, `/remember`, `/rai eval` (manual quality check;
`/rai sanity` certifies that the pipeline works, eval certifies the quality of what it stores).

## Skill routing

In a repo with `.project.toml`: talk = `/grill`, build = `/compile`; both follow the repo's
own `.claude/skills/sdd`. Elsewhere, `/grill` writes `.agent/decisions.md` and
`.agent/plan.md`, `/spec-improve` tightens the plan before approval, and `/compile` executes
it, offering `/orchestrator` for disjoint parallel groups and `/adversarial-review` after.

## PRD

The post-hoc summary of a memory-worthy session is its distill record in `rai-semantic`
(summary, decisions, facts). A product's own requirements live in its repo's `specs/`
(`/project-init`, then `/grill` and `/compile`).
