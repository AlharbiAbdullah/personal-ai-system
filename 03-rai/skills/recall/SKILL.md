---
name: recall
description: >
  Memory recall router. USE WHEN the user wants to retrieve past
  conversations, session summaries, or cross-session patterns from
  ChromaDB. Currently routes to history (semantic + filter queries).
---

# Recall

Reach into past sessions. Currently a single-sub-skill router; a `synthesize`
sub-skill (pattern detection across notes + sessions) is planned.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Tiered recall (T0–T3) over rai-semantic + rai-episodic | history | `history.md` |

## How to use

1. `Read` `history.md`.
2. Follow its instructions.

## Not yet built

- `synthesize` — surface patterns across recent vault notes + sessions (unnamed themes, contradictions, bridges between domains)

## Cross-references

- Ingest sessions into memory → `/rai/process-sessions`
- Self-model update based on recall → `/life/telos`
