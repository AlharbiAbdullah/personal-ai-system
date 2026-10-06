---
name: migration-playbook
description: >
  Plan and execute a framework / runtime / major version migration. USE WHEN
  the team is upgrading across a breaking boundary: React 18→19, Python
  3.9→3.12, Node 16→20, Next pages→app router, Django 3→5, etc.
---

# Migration Playbook

A migration is not a rewrite. It's a choreographed move through breaking
changes with tests at every checkpoint.

## When to use

- Major version upgrade of a framework, language, or runtime
- Swapping an ORM, test runner, bundler, or other load-bearing dep
- Legacy system strangler-fig — replacing piece by piece
- **SDD repo** (`.project.toml` at the root): a bump or swap runs as the `chore/deps-<slug>` lane. `specs/tech-stack.md` changes on the same branch (I11), and a swap or a major version gets an ADR in `project_memory/decisions/`. A multi-step migration becomes a roadmap phase at the next replan, one change per milestone. Tests stay unedited apart from `Test-Harness:` commits (I7).

## When NOT to use

- Minor version bump → just do it with tests
- Rewrites from scratch: `/architecture/system-design`, with the requirements from `/writing → prds`. In an SDD repo a rewrite is a pivot: `/grill "pivot: <what changes>"`.
- Refactoring within the current framework → `/git/refactor-clean`

## Process

### 1. Inventory the breaking changes
- Read the migration guide end-to-end
- List every breaking change that applies to this codebase
- Tag each: `auto-fixable` / `manual-trivial` / `manual-complex` / `requires-redesign`

### 2. Estimate effort
- Count affected files per breaking change
- Bucket by effort tag
- Total = sum of estimates + 30% buffer

### 3. Pre-flight checks
- Does CI pass cleanly TODAY on the current version? (migrate from a clean base)
- Test coverage on the parts that will change — supplement if <60%
- Can you deploy both versions side-by-side? (feature flags, blue-green)

### 4. Pick a strategy
- **In-place big-bang**: branch, migrate everything, test, merge. Only for small codebases.
- **Strangler fig**: new version runs alongside old; features move over one at a time.
- **Module-by-module**: migrate one package/module at a time within one repo.
- **Shim layer**: write adapters so old code keeps working while new code uses new version.

### 5. Checkpoint plan
Break the migration into milestones. Each milestone ends with:
- CI green
- Deployable / revertable
- A demo-able piece of working software

Example for React 18 → 19:
- M1: codemod pass + fix typescript errors
- M2: replace deprecated APIs (auto-migration-tool output)
- M3: migrate class components to function components in affected tree
- M4: update test-library + fix test failures
- M5: full production deploy + monitor
- M6: cleanup shims

### 6. Execute
- Work in isolation per module where possible
- Keep a running log of "surprises encountered" — feeds lessons learned
- Run tests continuously, not just at end of milestone
- Deploy to staging after each milestone
- Communicate status weekly to the team

### 7. Post-migration
- Remove all shims + compat layers
- Update CI to pin to new version explicitly
- Document the migration in an ADR
- Share lessons learned

## Risk mitigations

- **Performance regressions** — baseline perf before, compare after
- **Hidden breaking changes** — integration tests > unit tests here
- **Deprecated transitive deps** — audit the dep graph, not just top-level
- **Rollback plan** — you should be able to revert at any milestone

## Anti-patterns

- Migrating without a working test suite — you won't know what broke
- Skipping the inventory step — effort estimates become fiction
- Big-bang migration on a large codebase — weeks of broken main branch
- Mixing migration with feature work — attribute problems becomes impossible
- No communication cadence — team thinks you disappeared

## Examples

- "Plan a Python 3.9 → 3.12 migration for a pipeline repo"
- "Upgrade Next.js from pages router to app router for Dataforge"
- "Migrate a legacy Airflow pipeline repo to Dagster"
- "Move a React codebase from Create-React-App to Vite"
