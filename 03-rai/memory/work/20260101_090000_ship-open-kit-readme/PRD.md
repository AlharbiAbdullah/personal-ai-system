---
type: prd
slug: "ship-open-kit-readme"
tier: Standard
status: COMPLETED
created: "2026-01-01"
updated: "2026-01-01"
capabilities_used: [writing]
---

# Ship the open-kit README

> Example work record. The Algorithm mints one of these per non-trivial task under
> `03-rai/memory/work/{slug}/`. On disk the authoritative ledger is a hook-written `META.yaml`
> (id, title, session_id, created_at, status, completed_at); this `PRD.md` is the *in-session*
> structure the AI follows — shown here so the otherwise-invisible memory format is visible.
> Most of `03-rai/memory/` ships empty and fills as you work; this is a sample.

## Context

open-kit's [[05-projects/kitchen/open-kit/PRD|PRD]] success criterion says "a stranger succeeds
unaided". The repo had code but a one-line README. Desired state: a README good enough that a
first-time user installs, runs `new`, and ships a project without asking a question.

## Criteria

- [x] ISC: README covers install, first command, and one full example
- [x] ISC: a non-user follows it start to finish without questions
- [x] ISC: every command shown actually runs as written

### Anti-criteria

- [x] ISC-A: no unexplained jargon or assumed setup steps

## Decision Log

| Date | Decision | Why |
|------|----------|-----|
| 2026-01-01 | Lead with the one command, not the philosophy | Show value in 10 seconds; philosophy can wait |
| 2026-01-01 | Test the README on a friend before merge | The "stranger succeeds" criterion isn't self-verifiable |

## Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Covers install + first command + example | PASS | README sections present, commands copy-pasteable |
| Stranger succeeds unaided | PASS | maker friend ran it cold, shipped a scaffold, zero questions |
| Every command runs as written | PASS | re-ran each block on a clean container |

## Capability invocation log

| Capability | Invoked via | When | Result |
|------------|-------------|------|--------|
| writing | Skill(/writing) | drafting the README prose | clear, on-voice, jargon removed |
