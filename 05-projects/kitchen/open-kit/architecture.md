---
title: "open-kit — architecture"
status: DRAFT
created: "2026-01-01"
updated: "2026-01-01"
type: architecture
---

# open-kit — Architecture

> Example architecture note. In the kitchen, a project gets three docs before any code:
> [[05-projects/kitchen/open-kit/PRD|PRD]] (the why), this (the how), and
> [[05-projects/kitchen/open-kit/design|design]] (the feel). Code lives in `~/projects/`, not here.

## Simplicity Theorem

> A single static binary that turns "set up a new project the way I like it" into one command.

open-kit is a CLI with a tiny core and a template/plugin system around it. Everything is a
template; the core just resolves, renders, and writes. No daemon, no state, no network at runtime.

## Shape

```
open-kit new <template> myapp
        │
        ▼
  ┌───────────────┐     ┌──────────────────┐
  │  CLI (cobra)  │────▶│  Template engine  │
  └───────────────┘     │  (text/template)  │
        │               └────────┬─────────┘
        │                        ▼
        │               ┌──────────────────┐
        │               │  Embedded FS      │  built-in templates
        │               │  + ~/.open-kit/   │  user/community plugins
        │               └────────┬─────────┘
        ▼                        ▼
  ┌───────────────────────────────────────┐
  │  Writer — render → disk, idempotent    │
  └───────────────────────────────────────┘
```

## Components

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| `cli` | Parse commands/flags, help, version | Cobra; thin — no logic here |
| `template engine` | Resolve a template, render with vars | Go `text/template` + a manifest per template |
| `registry` | Find templates: embedded first, then `~/.open-kit/templates/` | Plugin hook = drop a folder here |
| `writer` | Render to a target dir, refuse to clobber | Dry-run flag; idempotent re-runs |

## Key decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Distribution | Single Go binary | One-step install, no runtime — see [[05-projects/kitchen/open-kit/PRD|PRD]] success criteria |
| Templates | Embedded + user dir | Ships useful out of the box; extensible without a rebuild |
| Config | None at runtime | A scaffolder shouldn't carry state; flags + template manifest are enough |

## What this is NOT

- Not a framework. It writes files and exits.
- No plugin *runtime* (no executing arbitrary code) — templates are data, rendered, written.

## Open questions

- Template manifest format: TOML vs a tiny YAML? Leaning TOML (no indentation traps).
- How to version community templates without a registry server.

## Related
- [[05-projects/kitchen/open-kit/PRD|PRD]] — problem + success criteria
- [[05-projects/kitchen/open-kit/design|design]] — CLI ergonomics + output feel
- [[02-ana/identity/projects|Projects]] — where open-kit sits in the active set
