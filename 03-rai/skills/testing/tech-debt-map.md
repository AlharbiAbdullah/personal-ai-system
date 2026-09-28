---
name: tech-debt-map
description: >
  Map a codebase's technical debt: coupling hotspots, coverage gaps,
  architectural drift, documentation debt. USE WHEN inheriting a codebase
  or planning a cleanup sprint. Diagnoses; doesn't fix.
---

# Tech Debt Map

Produce a structured debt map. Ranked. Actionable. Separate from refactoring
(which fixes) — this diagnoses and prioritizes.

## When to use

- Inheriting a codebase and planning cleanup
- Quarterly engineering health review
- Before sizing a rewrite vs. refactor decision
- When velocity is mysteriously slowing

## When NOT to use

- Clean, well-maintained codebase — focus energy elsewhere
- Just before a ship deadline — bad timing, wait till after launch

## What to measure

### 1. Coupling hotspots
Files with highest fan-in/out. A change there ripples everywhere.

```bash
# Simple heuristic: files imported most often
find . -name "*.py" -exec grep -l "from .mymodule" {} \; | wc -l

# Or use a tool: madge (JS), pydeps (Python), cargo tree (Rust)
```

### 2. Test coverage gaps
Which modules have <50% coverage? Weighted by criticality (billing > helpers).

```bash
# Python
pytest --cov=src --cov-report=term-missing

# Node
jest --coverage
```

### 3. Architectural drift
Places where the code has diverged from the design / convention:
- Deep nesting where the pattern is supposed to be flat
- Direct DB access from UI layer in a "clean architecture" codebase
- God-classes or god-functions (>500 lines, >20 methods)
- Circular imports

### 4. Documentation debt
- Functions without docstrings where required
- Out-of-date docs (compare last-edit vs code last-edit)
- Undocumented config values / env vars
- Missing ADRs for load-bearing decisions

### 5. Deprecated API usage
- Calling functions marked deprecated
- Using removed framework features
- Polyfill code for browsers/runtimes we don't support anymore

### 6. Performance cliffs
- Unbounded queries (no LIMIT, no pagination)
- N+1 patterns
- Sync in async paths, or vice versa
- In-memory computation where streaming would fit

### 7. Code age + ownership signal
- Files untouched >1 year (might be stable; might be forgotten)
- Files with single owner who's gone (bus factor 0)
- Files with 20+ contributors (consensus erosion)

## Process

1. **Pick 2–3 dimensions** from the list above. Full audits get unwieldy.
2. **Measure with tools** where possible; otherwise sample (random 10 files).
3. **Rank** by (impact × likelihood of pain) / fix-effort.
4. **Classify**:
   - **Bleed-now**: causing pain every week. Fix soon.
   - **Bleed-soon**: will cause pain in 3–6 months. Plan.
   - **Background**: ugly but stable. Live with it or clean opportunistically.
   - **Acceptable**: flagged but not worth fixing.
5. **Report** in a structured doc.

## Output template

```
# Tech Debt Map: [Project]
Date: YYYY-MM-DD | Analyst: [Name]

## TL;DR
- Top 3 bleed-now items: [list]
- Estimated cleanup effort: [weeks]
- Expected velocity gain post-cleanup: [qualitative]

## 1. Coupling hotspots
| File | Fan-in | Fan-out | Rank |
|---|---|---|---|
| core/auth.py | 34 | 8 | Bleed-now |
| ...

## 2. Coverage gaps
| Module | Coverage | Criticality | Rank |
|---|---|---|---|
| billing/ | 28% | HIGH | Bleed-now |
| ...

## 3. Architectural drift
- [Description] — [location] — [severity]

## 4. Documentation debt
- ...

## 5. Deprecated API usage
- ...

## 6. Performance cliffs
- ...

## 7. Ownership risk
- ...

## Prioritized backlog
1. [Bleed-now] Fix auth.py coupling — est 2 weeks — owner TBD
2. [Bleed-now] Bring billing coverage to 70% — est 1 week
3. [Bleed-soon] Replace deprecated ORM calls — est 3 days
...

## Accepted debt (NOT fixing)
- [Item] — why we're keeping it
```

## Anti-patterns

- Treating debt map as a to-do list — it's a PRIORITIZED to-do list
- Measuring everything — overwhelms; pick 2–3 dimensions
- No "accepted debt" section — every codebase has stuff that's ugly but fine
- Counting LOC as a quality metric — it's not
- Equal weight to all debt — billing-path debt >> helper debt
- Debt map without effort estimates — can't prioritize

## Relationship to other skills

- Measure vs fix: this skill MEASURES. Fixing happens via `/git/refactor-clean` or normal dev work.
- Dependency-specific debt → `/testing/dependency-audit`
- Architectural pattern debt → `/architecture/patterns` (for target) + `/architecture/migration-playbook` (for fix)

## Examples

- "Map tech debt in the Matchbox codebase"
- "What should we clean up before the Taskflow v2 launch?"
- "Which files are most at risk of breaking when we add feature X?"
- "Coverage gap analysis for OpenKit"
