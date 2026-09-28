---
name: code-archaeology
description: >
  Structured exploration of an unfamiliar or legacy codebase via git. USE
  WHEN inheriting code, onboarding to a new repo, or debugging code no
  one owns. Uses git history + structural scans to build a mental model.
---

# Code Archaeology

Dig up a codebase. Build a mental model through evidence, not guessing.

## When to use

- Onboarding to a new codebase (yours or someone else's)
- Inheriting an abandoned or legacy repo
- Debugging unfamiliar code written months/years ago
- Preparing a major refactor — need to understand current shape first
- Due diligence before acquisition / open-sourcing

## When NOT to use

- Familiar code you know well
- Code you wrote last week
- Pure architectural design → `/architecture/system-design`

## Workflow

### 1. Orient (5 min)
```bash
# Top-level layout
ls -la
tree -L 2 -I 'node_modules|__pycache__|.venv|dist'

# README, CONTRIBUTING, docs/
find . -maxdepth 2 -iname "readme*" -o -iname "contributing*" -o -iname "architecture*"
```

Read the README first. Always.

### 2. Entry points (5 min)
Where does execution start?
- `main.py` / `index.ts` / `cmd/*/main.go`
- `pyproject.toml` / `package.json` / `Cargo.toml` — check `[project.scripts]`, `"bin":`, etc.
- `Dockerfile` / `docker-compose.yml` — ENTRYPOINT + CMD
- `Makefile` / `justfile` / `tasks.py` — common commands

### 3. Call graph (15 min)
Starting from entry points, trace major flows.
- **Run the app** if possible — follow logs
- **Read top-level functions** — don't dive deep yet
- **Map the major modules** — what does each folder do?

### 4. Git history (15 min)
Git tells you what's important, what's fragile, what's recent.

```bash
# Most changed files (bus factor + hotspot signal)
git log --format="" --name-only | grep -v "^$" | sort | uniq -c | sort -rn | head -20

# Recent activity (last 3 months)
git log --since="3 months ago" --oneline

# Who knows what (code ownership)
git shortlog -sne

# File blame — who wrote this function?
git blame path/to/file.py

# Commits touching a specific file
git log --follow -- path/to/file.py

# When was this function introduced?
git log -S "def my_function" --source --all
```

### 5. Test coverage as map (10 min)
What's tested = what's load-bearing.
```bash
# Test files give you module shape
find . -name "test_*.py" -o -name "*.test.ts" -o -name "*_test.go"

# What does the test suite even do?
pytest --collect-only
# or
npm test -- --listTests
```

### 6. Config + secrets shape (5 min)
- `.env.example` / `config.example.yml` — what the app needs to run
- `settings.py` / `config.ts` — runtime config structure
- Environment variables in Dockerfile / docker-compose

### 7. External dependencies (10 min)
Who are we calling + who's calling us?
- Outgoing: parse the code for HTTP calls, DB queries, message queues, SDKs
- Incoming: API route handlers, message consumers, cron jobs

Draw this on paper or Excalidraw.

### 8. Gotchas + folklore (10 min)
Every legacy codebase has "don't touch X" lore.
- `// NOTE:` / `// XXX:` / `// HACK:` comments
- TODO list with dates or initials
- Large try/catch blocks (mask failures)
- Disabled tests
- Git commits with "fix urgent" / "hotfix" / "revert" in messages

## Output

```
# Code Archaeology: [Repo Name]
Date: YYYY-MM-DD | Analyst: [Name]

## TL;DR
- Purpose: [one sentence]
- Entry point: [file + function]
- Key modules: [list]
- Main flow: [one sentence]

## Structure
[directory tree + annotations on what each folder does]

## Entry points + flows
[diagrams + sequence of main execution paths]

## Key modules
| Module | Purpose | Knowledge owner | Risk |
|---|---|---|---|
| auth/ | JWT + session | @alice (last commit 2024) | Medium |
| ingest/ | Kafka consumer | @bob | High (complex state) |

## Hotspot files (most changed)
[list from git log]

## External dependencies
- Outgoing: [list]
- Incoming: [list]

## Gotchas + folklore
- [Thing 1] — evidence: [where]
- [Thing 2] — evidence: [where]

## Questions for the team
- [Question 1]
- [Question 2]

## First contribution ideas
- [Easy ticket to build context]
- [Next-level task after that]
```

## Tools

- **tokei / scc / cloc** — code statistics
- **git log / git blame** — history
- **ctags / universal-ctags** — symbol navigation
- **ast-grep / tree-sitter** — structural search
- **codeql** — semantic search (heavy)
- **gource** — visualize history over time (fun, occasionally useful)

## Anti-patterns

- Reading top-to-bottom of every file — wastes time
- Trying to understand everything before writing any code
- Ignoring git history — it's the most underused context source
- Believing what comments say without checking — comments lie
- Starting by refactoring — learn before changing
- No notes — you'll re-derive the same knowledge next month

## Examples

- "Code archaeology on the legacy Helios codebase"
- "Build a mental model of this repo"
- "Where should I start on this unfamiliar project?"
- "Who owns each module in this codebase?"
