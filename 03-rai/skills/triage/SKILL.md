---
name: triage
description: >
  Vault capture triage router. USE WHEN the user wants to process 00-landing
  (promote to inbox or delete) or process 01-inbox (research + rate + route
  each item). Routes between process-landing and process-inbox.
---

# Triage

Vault-capture processing. Two sub-skills for the two capture zones.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Walk each file in `00-landing/`, promote to inbox OR delete | process-landing | `process-landing.md` |
| Research each file in `01-inbox/`, rate relevance, route to destination | process-inbox | `process-inbox.md` |

## How to use

1. Pick the sub-skill by which folder you want to process.
2. `Read` the file in this directory.
3. Follow that file's instructions.
