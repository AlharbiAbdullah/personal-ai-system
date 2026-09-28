---
change: "{DATE}-{SLUG}"
lane: feat
status: draft                                   # draft | approved | done
roadmap: "{ROADMAP_SLUG}"
title: "{CONVENTIONAL_TITLE}"   # becomes the squash commit + CHANGELOG line
---
<!-- requirements.md: why this change exists and what it decided. status moves only via approve and merge; frozen at done. title is a YAML double-quoted string, so escape any " or \ in it. Rollback is one line: revert: <why a revert of the squash is enough>, flag: <ENV_NAME> (its flag row in .env.example, off by default), or one-way: <what cannot be undone>. Cap 120 lines. -->
## Why
{WHY}
## Scope
In: {SCOPE_IN}. Out: {SCOPE_OUT}.
## Decisions
- {DECISION}. Rejected: {REJECTED_OPTION}, {REASON}.
## Context
- {CONTEXT}
## Rollback
{ROLLBACK_KIND}: {ROLLBACK_DETAIL}
