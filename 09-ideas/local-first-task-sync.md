---
type: idea
status: plant
domain: product
derived_from: ["[[05-projects/active/taskflow/notes]]"]
spawned: []
created: 2026-01-01
grown: 2026-01-01
tags: [idea, plant]
---

# Local-First Task Sync

> Example of a **Plant**-stage idea — a Seed that earned a real plan after Q&A. The pipeline is
> Seed → Plant → Tree → Graduated. Compare the lighter [[09-ideas/learn-in-public-newsletter|Seed]]
> and the ready-to-build [[09-ideas/agent-eval-harness|Tree]]. Advance with `/ideas promote`.

## Spark
> A task app that works fully offline and syncs without a server owning your data.

## Problem
Solo makers (the [[05-projects/active/taskflow/PRD|taskflow]] audience) distrust cloud-only
tools — outages, lock-in, "what happens to my data if they shut down". Today they either accept
the risk or duct-tape together plaintext files. Painful for anyone who's been burned once.

## Insight
The hard part of taskflow isn't the UI — it's *sync*. If sync is local-first (CRDTs, the device
is the source of truth, the server is just a relay), the product is trustworthy by construction.
That's a real differentiator, not a feature bullet.

## Vault Connections
- [[05-projects/active/taskflow/notes|taskflow notes]] — this fell out of building taskflow's sync.
- [[10-knowledge/tools/duckdb|DuckDB]] — local embedded storage thinking.
- [[02-ana/identity/tech-stack|tech-stack]] — "own the data; avoid lock-in" is already a stated value.

## Market Landscape
Local-first is having a moment (CRDT libraries, sync engines). Most are libraries, not products.
The gap: a *finished* opinionated app for makers, not a toolkit for engineers.

## Dialogue Summary
- Q: Is this a taskflow feature or its own thing?
- A: Start as a taskflow spike. If sync is the magic, it might *become* the product.

## Potential
Could be: a taskflow architecture decision, a standalone product, or an open-source sync demo
that feeds [[09-ideas/learn-in-public-newsletter|the newsletter]].

## Open Questions
- Is CRDT complexity worth it for an audience of one-person teams?
- What's the smallest demo that proves the trust benefit?
