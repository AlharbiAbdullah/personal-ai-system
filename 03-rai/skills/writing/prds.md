---
name: prds
description: >
  Requirements document drafting for someone else (work, a client). USE WHEN
  a work or client product, feature, or initiative needs a reviewable spec
  with problem, solution, success criteria, and scope. John's own products
  and Rai or helm changes go to /grill instead.
---

# PRDs

Draft a Product Requirements Document that survives stakeholder review.

## Voice mandate

Read `references/voice.md` before drafting. PRDs read by stakeholders are the document that pretends to be objective. AI fluff makes scope slip. Concrete numbers, active voice, no hedging.

## When to use

- New feature or product scope is vague; team needs alignment before build
- Cross-functional work (eng + design + product + data) needs one shared source
- An executive asked "what are we building?" and the answer has >3 moving parts

## When NOT to use

- Bug fixes or tiny patches — just ship
- Internal refactors that don't change product behavior — use an ADR instead
- Sales proposals — use `/writing/proposals` (different audience, different format)
- Long-form essay or write-up about a feature post-ship — use `/writing/blog`
- John's own product (OpenKit) or a Rai or helm change (the ChromaDB memory rewrite): use `/grill`. It writes the repo's spec in an SDD repo, or `.agent/decisions.md` + `.agent/plan.md` elsewhere

## Process

1. **Clarify** — ask the requester three questions before drafting:
   - Who is the user / customer?
   - What's the problem in their words?
   - What does "done" look like?

2. **Draft structure** — fill each section, mark anything unclear with `TBD`:
   - **Problem** — user pain in one paragraph; data point if available
   - **Goal** — outcome metric (not feature) that proves we fixed it
   - **Non-goals** — what this deliberately does NOT address
   - **Solution** — 1–2 paragraphs on approach; diagram if it helps
   - **Success criteria** — 2–4 measurable conditions (latency, retention, conversion, etc.)
   - **Scope** — in-scope list + out-of-scope list
   - **Risks** — known unknowns + mitigations
   - **Milestones** — key dates, owners
   - **Stakeholders** — reviewers + approvers + informed parties

3. **Review loop** — circulate, capture feedback inline, version with date

4. **Freeze** — mark as approved with date + approver name; future changes become amendments

## Anti-patterns

- Solution-first PRDs (no problem statement) — reviewers can't evaluate
- Laundry-list requirements without priority — everyone agrees on P0 but then asks for P2
- Success metrics that are activities, not outcomes ("ship the feature" is not a success metric)
- Non-goals list missing — scope creeps in review

## Output

A markdown PRD saved with that work's other documents, wherever the business requires. Never save it in `05-projects/kitchen/`, which contains only a product's `specs/` and `research/`. A product John builds himself takes the SDD templates in `12-system/templates/sdd/` instead (`/ideas → graduate`, then `/project-init`).

Voice anchor: `~/helm/05-projects/active/taskflow/PRD.md` holds Taskflow's PRD-shaped spec. Match its density: problem in one paragraph, scope as a list, success metrics with numbers.

## Examples

- "Write a PRD for the new Taskflow sync engine"
- "Review this PRD draft" → read + critique against this workflow
