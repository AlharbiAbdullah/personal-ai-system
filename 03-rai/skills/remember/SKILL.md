---
name: remember
description: >
  Write a durable fact to Rai's capped working memory (identity/working-memory.md) immediately.
  USE WHEN the user says "remember this", "note that", "save this", "update memory",
  "forget about X", "تذكر", "احفظ" — or explicitly invokes /remember. This is the ONLY
  sanctioned live write besides turn-capture's daily logs; everything else is derived
  by the batch pipeline.
allowed-tools: Read, Edit, Bash
argument-hint: [the fact to remember | forget: <substring>]
---

# Remember — curated working memory write

Target file: `~/helm/03-rai/identity/working-memory.md` — **hard cap 2,500 characters** (Hermes
pattern). It auto-loads at every SessionStart via the identity contract. Frozen-snapshot
semantics: what you write here persists to disk now and enters context **next session**.

## Steps

1. `Read` `~/helm/03-rai/identity/working-memory.md` in full.
2. Determine the action:
   - **add** — a new fact. Pick the right section: `## Active Threads` (current work,
     open questions), `## Environment Notes` (URLs, tool versions, machine facts),
     `## Pending Decisions` (decisions waiting on John).
   - **replace** — the fact updates an existing entry (substring overlap): edit that
     entry in place rather than appending a near-duplicate.
   - **remove** — "forget about X": find the matching entry, **confirm with the user
     before deleting**, then remove it.
3. **Dedup check** — if the fact (or its meaning) is already present, update/skip; never
   append a duplicate.
4. **Cap check** — `wc -c < ~/helm/03-rai/identity/working-memory.md`. If the write would exceed
   **2,500 chars**: consolidate first — merge related entries, drop stale threads
   (resolved work, decided decisions) — then add. Never exceed the cap; never silently
   drop the NEW fact (it's the freshest).
5. Write the change with `Edit`.
6. Confirm to the user: `Saved — active from next session. (N/2,500 chars)`

## Rules

- One line per fact, terse, no prose paragraphs.
- This file is for **working state** (threads, environment, pending decisions) — durable
  identity/preferences belong to the batch pipeline (`learned.md`) and the self-model
  (`02-ana/identity/`), not here.
- Facts worth keeping forever will also be picked up by the nightly distill from the
  transcript — this file is the instant-access copy, not the archive.
