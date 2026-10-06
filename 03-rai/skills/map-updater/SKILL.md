---
name: map-updater
description: Update navigation maps. Always refreshes the helm vault index (.helm-index/helm-index.md). Also refreshes .codemap/codemap.md when run in a code project.
---

## Purpose

Keep navigation maps current so Claude and John can navigate without burning context on exploration. Two maps, one skill, run in a single pass.

## Maps

### 1. Helm Index (always)

Output: `~/helm/.helm-index/helm-index.md`

Obsidian-style wiki-link index of the vault's knowledge topics. Human-browsable first, Claude-readable second. Absolute path, so it works from any cwd.

What goes in:
- `10-knowledge/`: topic notes, grouped by domain (Data Engineering, AI/ML, System Design, DevOps, etc.). Parent notes first, indented children.
- `10-knowledge/_mocs/`: MOCs (Maps of Content).
- `09-ideas/`: Seed/Plant/Tree notes worth surfacing.
- `05-projects/`: active and completed project notes.
- `06-learning/`: active courses.
- `02-ana/`: self, family, identity, journal pointers (light touch, privacy).
- `11-workflows/`: the workflow table: one row per `NN-*.md` file, in number order, its title and its `**Use when:**` line shortened. Copy the rows from the tables in `11-workflows/AGENTS.md`; never invent a row. One line on top: John's workflows, read and follow the matching one.

What stays out: `03-rai/`, `12-system/`, `13-archive/`, `00-landing/`, `01-inbox/`, `08-bawaba/`. Those are not knowledge.

### 2. Codemap (when present)

Output: `{PROJECT_ROOT}/.codemap/codemap.md`

Code navigation map. File tree, key functions, module dependencies. Per-project, not vault-wide.

Runs only if `.codemap/codemap.md` exists in the current project (walk up from cwd, max 3 parents). If absent, skip silently. The helm vault intentionally has no `.codemap/`.

## When to run

- Manually via `/map-updater`: updates whichever maps apply.
- On demand after adding knowledge notes, restructuring folders, or large code changes.

The session-start hook (`03-rai/hooks/session-start.py`) loads both maps into context at the start of every session: helm-index always, codemap when present in cwd.

## Process

1. **Helm index pass:**
   - Read current `~/helm/.helm-index/helm-index.md`.
   - Walk the knowledge folders above. Collect every `*.md` that isn't a `_mocs/` MOC.
   - Diff against the index. Surface: new notes to add, deleted notes to remove, moved notes to repoint.
   - Preserve hand-curated indent structure and descriptions. Don't flatten. Don't drop wiki-links unless the target note is gone.
   - Replace the one line under `## Last Updated` with today's date. Never append a changelog: git log holds the history.
   - Keep the file under 20,000 bytes. `session-start.py` skips a larger index without a warning.

2. **Codemap pass (skip if no `.codemap/` in project):**
   - Read current `.codemap/codemap.md`.
   - Scan project structure. Identify key modules, public APIs, entry points.
   - Map dependencies between modules (imports).
   - Update the Structure, Key Functions, Dependencies sections.
   - Keep descriptions one-line. Don't document private helpers.
   - Update the `Updated:` timestamp.

3. **Report:** print a compact summary of what changed in each map, or "no changes" if stable.

## Helm index format

```markdown
# Helm Index

Quick reference for knowledge navigation. Notes are consolidated into topic notes.

---

## 10-knowledge/

### {Domain} ({count} notes)

**{Subtopic}**
- [[Topic Note]] - one-line description
  - [[Child Note]] - one-line description

---

## 11-workflows/

| # | Workflow | When to Use |
|---|----------|-------------|
| 01 | [[01-project\|Project]] | Starting something new end-to-end |

---

## Last Updated
{YYYY-MM-DD}
```

Wiki-links only. No relative paths, no URLs.

## Codemap format

```markdown
# CODEMAP

> Auto-generated navigation map. Updated: {timestamp}

## Entry Points

- `src/main.py` → Application entry

## Structure

{directory tree with one-line descriptions}

## Key Functions

### {Module Name}
- `path:function()` → Description

## Dependencies

{module} → {dependencies}

## Config Files

- `pyproject.toml` → Dependencies, scripts
- `.env` → Environment variables
```

One-line descriptions. Navigation, not documentation. Public API only.

## Rules

1. Helm index runs every invocation. Codemap runs only if `.codemap/` exists in the current project.
2. Never create `.codemap/` in the helm vault itself: helm uses `.helm-index/` instead.
3. Create `.helm-index/` if missing. The folder is the home of `helm-index.md`.
4. Create `.codemap/` only when explicitly initializing a code project, never implicitly.
5. Replace the one dated "Last Updated" / "Updated" line on every run. Never append change notes.
6. Don't fabricate entries. If a note isn't on disk, it's not in the index.
7. Preserve the user's hand-curated structure. Additive updates by default. Ask before deleting wiki-links.
