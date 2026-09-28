---
name: testing
description: >
  Testing router. USE WHEN the user writes tests, reviews code, audits
  dependencies, or maps technical debt. Covers test-write (tdd, pragmatic,
  unit-test, e2e, api-test, load-test) and test-review (code-review,
  verify-completion, dependency-audit, tech-debt-map).
---

# Testing

Two jobs live here: writing tests, and reviewing code + dependencies +
debt. Pick by the work shape.

## Routing table: test-write

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Build new behaviour test-first (RED-GREEN-REFACTOR); points to the SDD compile loop | tdd | `tdd.md` |
| Ship fast without full TDD (prototypes, spikes, legacy) | pragmatic | `pragmatic.md` |
| Retrofit tests onto existing code | unit-test | `unit-test.md` |
| Behavior / contract tests for APIs | api-test | `api-test.md` |
| End-to-end tests across systems | e2e | `e2e.md` |
| Load / performance / soak tests | load-test | `load-test.md` |

## Routing table: test-review

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Pre-review self-check + structured feedback on someone else's PR | code-review | `code-review.md` |
| Before declaring a task done, verify acceptance criteria hold | verify-completion | `verify-completion.md` |
| Scan deps for outdated, CVEs, license issues, bloat | dependency-audit | `dependency-audit.md` |
| Map coupling hotspots, coverage gaps, architectural drift | tech-debt-map | `tech-debt-map.md` |

## How to use

1. Pick the sub-skill by task shape.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## When two could fit

- **tdd vs pragmatic:** tdd is the default for new production code; pragmatic is explicit escape-hatch for spikes/prototypes/exploration.
- **tdd vs unit-test:** tdd writes tests BEFORE code for new features; unit-test retrofits coverage onto existing code.
- **api-test vs e2e:** api-test is contract-level (single endpoint); e2e walks full flows across endpoints/systems.
- **load-test vs api-test:** load-test is volume/latency under stress; api-test is correctness at low volume.
- **code-review vs verify-completion:** code-review is reading someone else's work; verify-completion is double-checking your own before marking done.
- **dependency-audit vs tech-debt-map:** dependency-audit looks outward (packages); tech-debt-map looks inward (your code's coupling + coverage).

## Cross-references

- Test security-review angle → `/security/security-review`
- Language-idiomatic test writing → `/coding-standards/*`
