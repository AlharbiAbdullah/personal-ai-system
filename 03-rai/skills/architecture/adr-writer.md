---
name: adr-writer
description: >
  Architecture Decision Record drafting. USE WHEN the team has made (or is
  about to make) a significant architectural choice that future-you will
  want context on. ADRs preserve the "why" so it survives staff turnover.
---

# ADR Writer

Capture an architectural decision in ~1 page so future engineers understand
why the current shape exists.

## When to use

- Picking one framework / database / protocol / pattern over alternatives
- Changing a long-standing technical direction
- Any choice that will be questioned 6+ months from now
- Compliance or security decision that must be auditable

## When NOT to use

- Bug fixes or small refactors — commit message is enough
- Product feature scoping: `/grill` (in an SDD repo it writes the scenarios and the change folder). A requirements document for someone else: `/writing → prds`
- Design exploration before the decision is made → `/architecture/system-design`
- After-the-fact documentation of an ancient decision no one disputes

## ADR structure (MADR-style)

```
# ADR-NNNN: [Short title, imperative]

Status: [Proposed | Accepted | Rejected | Superseded by ADR-XXXX]
Date: YYYY-MM-DD
Deciders: [Names / roles]
Consulted: [Names / roles]
Informed: [Names / roles]

## Context + problem statement

[1–2 paragraphs. What's forcing this decision? What's at stake?]

## Decision drivers

- [Driver 1 — e.g. performance requirement]
- [Driver 2 — e.g. team familiarity]
- [Driver 3 — e.g. regulatory constraint]

## Considered options

1. [Option A]
2. [Option B]
3. [Option C]

## Decision outcome

Chosen: **Option X**, because [2–3 sentences on why].

### Consequences

- **Good**: [positive outcomes]
- **Bad**: [tradeoffs accepted]
- **Neutral**: [changes that are neither good nor bad]

## Pros + cons per option

### Option A
- Good: ...
- Bad: ...

### Option B
- Good: ...
- Bad: ...

### Option C
- Good: ...
- Bad: ...

## Links
- [Related ADRs]
- [Supporting docs / benchmarks / research]
```

## Where ADRs live

- **SDD repo** (`.project.toml` at the root): `project_memory/decisions/<date>-<slug>.md`, in the format of the repo's `specs/README.md#formats` (Context, Decision, Rejected, Consequences, and `status: active | superseded by <date>-<slug>`). Only for a choice that later changes must respect. It is committed on the change's branch and frozen after merge, except `status:`. IDs are a date and a slug, never a sequence number.
- Any other repo: `docs/adr/NNNN-title.md`, indexed by a README that lists every ADR and its status. Numbering is sequential per directory, 4-digit zero-padded.
- Never in `05-projects/`: a project's decisions are in its repo, and `active/{name}/` keeps non-code work only.

## Status lifecycle

- **Proposed** — written, under review
- **Accepted** — reviewed + approved, in effect
- **Rejected** — team decided NOT to do this. Keep the ADR anyway — the reasoning is valuable.
- **Superseded** — replaced by a newer ADR. Link both ways.
- **Deprecated** — no longer in effect but not replaced. Rare.

## Anti-patterns

- ADRs that describe the solution in detail instead of the decision — that's a design doc
- Skipping "Considered options" — makes the decision look arbitrary
- No "Consequences" — glosses over tradeoffs that'll bite later
- Writing ADRs retroactively to match the code — loses honesty about tradeoffs
- ADRs too big — 1–2 pages. If you need more, split into multiple ADRs or link to a design doc.

## Examples

- "ADR: choose Postgres over MongoDB for Matchbox"
- "ADR: adopt event-driven arch for Taskflow service-to-service comms"
- "Write the ADR for picking LangGraph over LangChain for OpenKit agents"
- "ADR: move Helios from Dagster to Airflow" (or reverse)
