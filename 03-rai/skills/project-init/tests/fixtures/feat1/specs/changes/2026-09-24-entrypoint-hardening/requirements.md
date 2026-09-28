---
change: "2026-09-24-entrypoint-hardening"
lane: feat
status: draft                                   # draft | approved | done
roadmap: "entrypoint-hardening"
title: "fix(cli): clear errors instead of tracebacks"   # becomes the squash commit + CHANGELOG line
---
<!-- requirements.md: why this change exists and what it decided. status moves only via approve and merge; frozen at done. title is a YAML double-quoted string, so escape any " or \ in it. Cap 120 lines. -->
## Why
`tipcalc`, `tipcalc abc`, `tipcalc --help` and an empty TIPCALC_DEFAULT_PERCENT all end in a traceback.
## Scope
In: argument and env validation. Out: new flags (backlog: percent-flag).
## Decisions
- Usage errors exit 2 with one `error:` line (argparse convention). Rejected: exit 1, it collides with runtime failure.
- An empty env knob means unset, so the default applies. Rejected: failing on empty, it punishes a copied `.env`.
## Context
- argparse in `main()`; env via a pydantic-settings model with `env_ignore_empty=True` in `src/tipcalc/config.py` (tech-stack S-1).
## Rollback
revert: the change stays inside the CLI; a revert of the squash brings the tracebacks back
