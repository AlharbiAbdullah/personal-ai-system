---
name: refactor-clean
description: Clean dead code and loose files after a coding session (auto-delete with git backup)
---

## Purpose

Clean out dead code and loose files after a long coding session. Auto-deletes with git commit backup for easy rollback.

## Before Starting

1. **Create backup commit**
   ```bash
   git add -A
   git commit -m "checkpoint: before refactor-clean"
   ```
2. Note the commit hash for rollback reference

## Tasks

### 1. Find and Remove Dead Code (Python)

Scan for and DELETE:
- Unused variables (assigned but never read)
- Unreachable code blocks (after return/raise)
- Commented-out code blocks (more than 3 lines)
- Empty functions/classes with just `pass`
- Unused function parameters

### 2. Clean Imports

For each Python file:
- Remove unused imports
- Sort imports: stdlib → third-party → local
- Use one import per line for clarity

### 3. Remove Loose Files

Find and DELETE:
- `*.md` files in src/ that aren't README or docs
- `*.bak`, `*.tmp`, `*.pyc` files
- `__pycache__` directories
- Empty `__init__.py` files (unless needed for package)

**Never delete:**
- Files in `tests/` folder
- `README.md`, `CHANGELOG.md`
- Config files (`.env`, `pyproject.toml`, etc.)

### 4. Verify Changes

Run the project's test command. Detect from project files:
- Python with `uv`: `uv run pytest`
- Python with `pip`: `pytest` (or `python -m pytest`)
- Node: `npm test` (or `pnpm test`, `yarn test`)
- Rust: `cargo test`
- Go: `go test ./...`

If no test command can be detected, ask the user.

- If tests pass: proceed to report
- If tests fail: auto-rollback (see Rollback section)

## Rollback (If Tests Fail)

```bash
git revert HEAD --no-edit
```

`git revert` leaves the revert commit in history. If you want to discard the cleanup attempt entirely (no breadcrumb in history), the user can run `git reset --hard HEAD~2` afterwards — that drops both the cleanup commit AND the revert. Default is the safer revert.

Then report what went wrong.

## Output Format

After completion, report:

```
REFACTOR-CLEAN SUMMARY
======================

Backup commit: [hash]

Dead Code Removed:
- [file:line] - [what was removed]

Imports Cleaned:
- [file] - removed [N] unused imports

Files Deleted:
- [filepath] - [reason]

Tests: PASSED / FAILED
Status: COMPLETE / ROLLED BACK

To undo all changes:
git revert [cleanup-commit-hash]
```

## Rules

1. Always create backup commit FIRST
2. Never delete test files
3. Never delete config files
4. Run tests before marking complete
5. Auto-rollback if tests fail
6. Report every deletion with reason
