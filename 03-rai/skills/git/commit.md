---
name: commit
description: Divide working tree changes into logical commits and push. Always splits, never asks for approval.
disable-model-invocation: true
allowed-tools: Bash(git *), Read, Edit, Write
---

# Commit (logical splits, auto-push)

Group working tree changes into multiple logical commits, in dependency
order, so the user can revert or bisect to any point. Never bulk-commit
with `git add -A` and one message. **No approval gate. Push at the end.**

## Helm vault override (repo root = `~/helm` ONLY)

The helm vault is a brain repo: most working-tree churn is high-frequency Rai
memory/telemetry, not code. There, optimize for **FEW commits**, not maximal
splits. This section OVERRIDES the "always split, even 2-3 changes" rule below.

When the repo root is `~/helm`:

- **Consolidate ALL high-frequency auto-churn into ONE `chore(rai/memory): …`
  commit — do NOT split it by scope.** This means everything under
  `03-rai/memory/**`, `03-rai/semantic-memory/` (pending queue + state),
  `.obsidian/**` (UI layout), `13-archive/historical-sessions/**` (drained
  sessions), session-state JSON, and `*.jsonl` telemetry logs ALL go in a single
  commit. Do NOT emit separate `chore(rai/semantic-memory)`, `chore(obsidian)`,
  `chore(rai/config)`, or `chore(archive)` commits — that per-scope splitting was
  the inflation (~215 auto-commits/week → target ~30). One commit for all of it.
- **Split only genuine human-facing content** into their own logical commits:
  skills, identity, agents, hooks, knowledge/idea/project notes, news/learning
  output, vault docs, templates, and actual code. These are the only `feat`/
  `fix`/`docs`/`refactor` commits worth bisecting.
- **Target a handful of commits per run: ideally 1 churn commit + one per real
  content change. Not 10+.**
- **Never stage `03-rai/semantic-memory/chromadb/`** — gitignored derived vector
  index (purged from history 2026-06-15); it must never re-enter the repo. If it
  appears staged, unstage it.
- **Size limit for unattended runs.** An unattended run never stages a file over
  50 MB, except under `13-archive/historical-sessions/`. A session JSON there over
  90 MB is left unstaged and reported with a critical `notify-send` (GitHub
  rejects files over 100 MB).
- **Never stage paths under `03-rai/skills/news-digest/.runs`.** It is a symlink
  into `~/.local/state`; git refuses them ("beyond a symbolic link").

## Flow

inspect → group → commit → push

## Steps

1. **Inspect**:
   - `git status` (no `-uall`)
   - `git diff` and `git diff --stat`
   - `git log --oneline -10` to learn the repo's commit message style
   - Check `.pre-commit-config.yaml` for `no-commit-to-branch` and other
     blocking hooks
   - Check current branch — if it's `main`/`master` and `no-commit-to-branch`
     is configured, work on a feature branch and fast-forward at the end
2. **Group** (no plan presentation, no approval):
   - Cluster files by feature, scope, or layer (backend foundation, db
     migrations, services, frontend primitives, page redesigns, docs, etc.)
   - Order by dependency: things others depend on land first
   - Each commit must stand alone (ideally compiles + works)
   - Keep ignores/config in their own `chore:` commit
   - Keep docs in their own `docs:` commit
   - Print a one-screen summary of the planned commits as you go, but do
     NOT wait for confirmation — proceed immediately
3. **Commit**:
   - For each group: `git add <specific files>` (never `-A` or `.`)
   - Verify staging with `git status --short`
   - Commit with HEREDOC message in the repo's style (see Format below)
   - Stop and surface errors immediately if a hook fails
4. **Push** (always, no prompt):
   - If a feature branch was used: `git checkout main && git merge --ff-only <branch>` then delete the branch. In an SDD repo (`.project.toml` at the root), skip this bullet and push only the current lane branch, because only the human gates (`! mise run merge`, abandon, release) move `main`.
   - `git push origin main` (or current upstream branch)
   - If push is rejected due to remote changes, `git pull --rebase` then push again
   - Report final commit hashes and the push result

## Grouping heuristics

- **By layer**: ignores/config → db schema → services → routers/agents → frontend primitives → frontend pages → docs
- **By feature scope**: auth, api, ui, search, docs, etc.
- **By dependency**: a shared module (e.g., `http_client.py`) lands before
  files that import it
- **By risk**: smaller, riskier changes get isolated commits so they can
  be reverted without losing the rest

## Commit message format

**Always descriptive. Never generic.** A future reader (or future you,
six months from now) should know exactly what shipped without opening
the diff.

Match the repo's existing style first (read `git log`). Default to
Conventional Commits:

```
<type>(<scope>): <imperative subject under 70 chars>

<body — required for non-trivial commits. explain WHAT changed and WHY.
list the key files or modules affected. wrap at 100 chars.>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`, `build`, `ci`

### Subject line rules

- Imperative mood (`add`, `fix`, `rename`, `drop`), not past tense
- Specific, not vague: name the actual thing
- Under 70 characters
- No trailing period
- Include scope in parentheses when there is a clear one

### Body rules

- **Required** for any commit touching more than one file or anything
  non-obvious
- Explain WHY the change exists (the motivation, constraint, or bug)
- Name the key files, modules, or behaviors affected
- If it fixes a bug, describe the bug
- If it changes behavior, describe the old and new behavior
- Skip the body only for truly trivial commits (typo fix, gitignore
  addition, single-line tweak with self-evident intent)

### Banned subjects

Never ship commits with messages like these. They are useless for
revert and bisect:

- `update`, `update files`, `update code`
- `fix`, `fix bug`, `fix stuff`, `fixes`
- `wip`, `progress`, `changes`
- `misc`, `cleanup`, `tweaks`, `minor changes`
- `commit`, `save`
- Anything that does not name what changed

### Good vs bad examples

Bad:
```
update order service
```

Good:
```
refactor(api): route outbound calls through an async HTTP client

OrderService now calls services.http.Client.get instead of the sync
requests session. Keeps the event loop unblocked and lets the client
reuse connections. Same change applied to the inventory service.
```

Bad:
```
fix bug
```

Good:
```
fix(search): skip the index lookup for queries under 3 chars

Single keystrokes were triggering full index scans and adding latency.
Gated the lookup on MIN_QUERY_CHARS in search_service.query.
```

Always pass the message via HEREDOC so multi-line bodies survive:

```bash
git commit -m "$(cat <<'EOF'
feat(scope): specific descriptive subject line

Body explaining what changed and why. Name the files or modules.
Multiple lines welcome when the change is non-trivial.
EOF
)"
```

## Rules

- **Always split. Never bulk commit.** Even 2-3 changes get split if
  they're logically separate.
- **Specific file staging only.** Never `git add -A`, `git add .`, or
  `git add <directory>` unless that directory truly is one logical unit.
- **Never skip hooks.** No `--no-verify`. If a hook fails, fix the root
  cause and re-stage.
- **Never amend after pushing.** Create a new commit instead.
- **Always push at the end.** No prompt, no confirmation. The skill ends
  with a push.
- **No AI attribution.** No "Generated with Claude", no "Co-Authored-By:
  Claude", no AI mentions in commit messages, branch names, or PR text.
- **Pre-commit blocks main?** Use a feature branch and fast-forward main
  at the end. Fast-forward merges don't trigger commit hooks. An SDD repo
  (`.project.toml`) is the exception: its hooks refuse any move of `main`
  outside the human gates (merge, abandon, release).
- **Pull before push** if remote has new commits. Rebase, don't merge.
- **Sensitive files**: skip `.env`, credentials, large binaries unless
  the user explicitly asks. Warn if found in the working tree.

## Example flow

```
Working tree: 47 files changed.
Plan (proceeding without approval):
  1. chore: ignore build output and add dockerignore
  2. feat(backend): centralized async HTTP client
  3. feat(db): orders schema v2 (raw + staging + marts)
  4. feat(search): indexer, query parser and ranking
  5. feat(pipeline): nightly import with a CLI dispatcher
  6. feat(frontend): shared UI primitives and theme tokens
  7. feat(landing): new light theme
  8. feat(cart): sidebar, checkout modal and i18n polish
  9. feat(maps): store locator with floating panels
 10. feat(admin): dashboard layouts and view registry
 11. feat(reports): two-tab redesign and route restructuring
 12. docs: codemap, AGENTS.md, TODO, project memory
```

Then commits go in sequence, each with focused staging and a
descriptive subject + body. Push happens automatically at the end.
