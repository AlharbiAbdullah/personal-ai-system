---
name: rai
description: >
  Rai brain maintenance router. USE WHEN the user wants to healthcheck
  the brain, eval memory quality, ingest sessions to memory, compose
  specialized agents, create or validate skills, or extract upgrade
  opportunities. Routes between sanity, eval, process-sessions,
  compose-agents, create-skill, upgrade.
---

# Rai

Maintain the brain itself. Meta-skills that operate on Rai's own
structure (skills, memory, agents, config).

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| End-to-end healthcheck (memory, pipeline, hooks, jobs, harness edges, skills, vault, doc drift) | sanity | `sanity.md` |
| Memory QUALITY certification (golden-set eval, judged sections), manual only | eval | `eval.md` |
| Drain `semantic-memory/pending/` into ChromaDB | process-sessions | `process-sessions.md` |
| Spawn specialized custom agents; orchestrate parallel runs | compose-agents | `compose-agents.md` |
| Create a new skill (naming, folder layout, SKILL.md validation) | create-skill | `create-skill.md` |
| Extract improvement opportunities for the Rai system | upgrade | `upgrade.md` |

## How to use

1. Pick the sub-skill by maintenance task.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## When two could fit

- **sanity vs create-skill:** sanity verifies the whole brain is healthy; create-skill validates ONE skill's structure.
- **sanity vs process-sessions:** sanity reports on state; process-sessions changes state (writes to memory).
- **sanity vs eval:** sanity certifies FUNCTION (subsystems produce fresh output); eval certifies QUALITY (memory retrieves the RIGHT things). Sanity runs every cycle; eval only when John asks.
- **compose-agents vs create-skill:** agents are persona+capability specs; skills are workflow definitions.
- **upgrade vs sanity:** upgrade identifies what to improve; sanity identifies what is broken.

## Cross-references

- Memory retrieval → `/recall/history`
- Skill gaps inbox → `skills/GAPS.md`
- Skill ownership map → `skills/MANIFEST.md`
