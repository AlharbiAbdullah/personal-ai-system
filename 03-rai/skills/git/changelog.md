---
name: changelog
description: >
  Generate a structured changelog from commits between two tags or dates.
  USE WHEN cutting a release, writing release notes, or summarizing what
  shipped in a time window.
---

# Changelog

Turn a pile of commits into a scannable list of what changed — grouped,
labeled, readable by humans.

## When to use

- Cutting a semver release (v1.2.0 → v1.3.0)
- Writing release notes for an app or library
- Summarizing "what we shipped this month" for stakeholders
- Auditing changes across a date range

## When NOT to use

- Single-PR description → `/git/pr-description`
- Per-commit message → `/git/commit`
- Explaining WHY a specific decision was made → `/architecture/adr-writer`

## Keep a Changelog format

https://keepachangelog.com/ — industry standard. Sections:

```markdown
# Changelog
All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/).
This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.3.0] - 2026-04-22
### Added
- Argon2id password hashing
- New `/api/v2/users/profile` endpoint

### Changed
- Password minimum length raised from 8 to 12

### Deprecated
- `/api/v1/users/me` (use `/api/v2/users/profile`); removal in v2.0.0

### Removed
- Support for Python 3.10 (EOL)

### Fixed
- Race condition in session refresh under high load
- Typo in welcome email subject line

### Security
- CVE-2026-1234: patched XSS in admin panel
```

## Generating from commits

If commits follow Conventional Commits (`feat:`, `fix:`, `chore:`, etc.), you can auto-categorize:

```bash
# List commits between tags
git log v1.2.0..v1.3.0 --oneline

# With author + date
git log v1.2.0..v1.3.0 --pretty=format:"%h %an %ad %s" --date=short

# Only commits matching a prefix
git log v1.2.0..v1.3.0 --oneline --grep="^feat"
git log v1.2.0..v1.3.0 --oneline --grep="^fix"
```

Map Conventional Commit types to Keep-a-Changelog sections:
- `feat:` → **Added**
- `fix:` → **Fixed**
- `chore(deps):` / `refactor:` → usually not in changelog (internal)
- `docs:` → usually not in changelog
- `perf:` → **Changed**
- `BREAKING CHANGE:` → **Changed** + noted prominently
- `security:` or CVE refs → **Security**

## Tools

- **git-cliff** — Rust CLI, generates from Conventional Commits
- **standard-version / changesets** — Node ecosystem
- **conventional-changelog** — industry default; many integrations
- **release-please** — Google's automated release PR tool

Or write by hand if the project is small.

## Process

1. **Identify range** — last tag to HEAD, or two specific tags/dates
2. **List commits** in the range
3. **Group** by type (use prefixes if available, or manually)
4. **Write customer-facing summary per item** — not just the commit message
5. **Separate breaking + security** — these get extra prominence
6. **Date + version** in the heading
7. **Publish**: `CHANGELOG.md` in repo root, copied to GitHub Release notes. In an SDD repo (`.project.toml` at the root), never write the file. `mise run merge` regenerates `CHANGELOG.md` from each squash title, and `! mise run release -- <bump>` writes the version section. The gates refuse a hand-staged `CHANGELOG.md` (I2), so there this skill writes only release-notes text outside the file.

## Writing style

- **Past tense** for what shipped: "Added support for X", not "Add"
- **User-facing impact** over implementation detail: "Faster dashboard" > "Optimized query"
- **Specific versions/numbers**: "Reduced P95 latency from 800ms to 200ms" > "Performance improvements"
- **No internal refactors** unless they matter to users (e.g. new extensibility point)
- **Link to migration docs** for breaking changes

## Per-release vs cumulative

- **Per-release sections**: keep all prior versions in one file
- Never rewrite old entries (they're history)
- Current in-progress work goes in `[Unreleased]` until released

## Anti-patterns

- Dumping raw commit messages — users can't parse it
- Only "Bug fixes and performance improvements" — no signal
- Missing breaking changes — users blindsided by upgrade
- No date / no version number — can't reference historically
- Internal-only changes polluting user-facing changelog
- Marketing copy in technical changelog (save that for the blog post)

## Examples

- "Generate changelog for v1.2.0 to v1.3.0 in Helios"
- "Write release notes from last 2 weeks of commits"
- "Summarize what shipped in Matchbox this month"
- "Auto-categorize these commits into Keep-a-Changelog format"
