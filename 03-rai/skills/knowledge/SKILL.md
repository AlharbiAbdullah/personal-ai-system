---
name: knowledge
description: >
  Knowledge base router for topic notes, MOCs, and insight notes. USE WHEN the
  user wants to create a new topic note with Simplicity Theorem, propose an
  Insight Note, audit a MOC for drift, or find cross-note connections. All
  sub-skills operate on `~/helm/10-knowledge/`.
---

# Knowledge

Compounding knowledge base. Simplicity Theory is the living rule: every note starts with a Simplicity Theorem + Diagram.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Scaffold a new topic note (with Simplicity Theorem + sections) | new-topic-note | `new-topic-note.md` |
| Propose an Insight Note from two existing notes | insight | `insight.md` |
| Check a MOC for drift (missing notes, broken links) | audit-moc | `audit-moc.md` |
| Scan notes for emergent-insight opportunities | find-connections | `find-connections.md` |

## How to use

1. Pick the sub-skill by what you want to do.
2. `Read` the file in this directory.
3. Follow that file's instructions.
