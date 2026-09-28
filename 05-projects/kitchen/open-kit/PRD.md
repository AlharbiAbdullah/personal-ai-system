---
title: "open-kit"
status: DRAFT
created: "2026-01-01"
updated: "2026-01-01"
type: prd
---

# open-kit

> Example PRD. This is what the algorithm writes for non-trivial work — kept here so you can
> see the shape. The `/ideas graduate` and project-init flows create these.

## Problem

Developers rewrite the same boilerplate every new project: scaffolding, linting config, repo
hygiene, small automations. It's a tax paid over and over. There's no single, opinionated,
well-crafted CLI that handles the boring setup the way I'd actually want it done.

## Success Criteria

- [ ] `open-kit new <template>` scaffolds a clean project in one command.
- [ ] Ships as a single binary / install with no heavy runtime.
- [ ] v1.0 has docs good enough that a stranger succeeds without asking me.
- [ ] 500 GitHub stars from people I didn't recruit (proof of real usefulness).

## Scope

### In Scope
- Project scaffolding from a few opinionated templates.
- Repo-hygiene commands (gitignore, license, CI starter).
- A plugin hook so others can add templates.

### Out of Scope
- A GUI.
- Language/framework coverage beyond the two I use first.

## Ideal State Criteria (ISC)

| # | Criterion | Tag | Status | Verify |
|---|-----------|-----|--------|--------|
| 1 | `new` command scaffolds and builds clean | E | PENDING | run it on a fresh machine |
| 2 | Docs let a stranger succeed unaided | E | PENDING | hand it to a friend |
| 3 | Install is one step, no heavy deps | I | PENDING | fresh-env install test |

### Anti-Criteria
- Don't turn it into a framework. It scaffolds and gets out of the way.

## Phases

### Phase 1: Core
- `new` command + one template.
- Build + release pipeline.

### Phase 2: Useful
- Repo-hygiene commands.
- Docs + landing page.

### Phase 3: Open
- Plugin hook for community templates.

## Decisions

| Decision | Options Considered | Choice | Reason |
|----------|-------------------|--------|--------|
| Language | Go, Rust, Python | Go | single-binary distribution, fast, easy installs |

## Log

| Date | Session | Action | Notes |
|------|---------|--------|-------|
| 2026-01-01 | initial | Created PRD | graduated from `09-ideas` |
