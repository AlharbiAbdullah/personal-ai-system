# CODING FORMAT

Single source of truth for all coding-related rules. Loaded at session start.

---


### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them. Don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it. Don't delete it.

When your changes create orphans:
- Remove imports, variables, functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## Codebase Navigation

Before exploring any codebase:
1. Check for `.codemap/codemap.md`.
2. If it exists, read it first.
3. If missing, run `/map-updater`.

After creating or deleting files, update `.codemap/codemap.md` silently.

Also read the project's `AGENTS.md` before writing any code.

---

## Code Behavior

Before writing:
1. Read `.codemap/codemap.md` and project `AGENTS.md`.
2. Find existing patterns. Reuse before creating.
3. State filepath and reasoning before creating files.

Never:
- Install dependencies without explaining.
- Create duplicate functionality.
- Skip types or error handling (outside the impossible-scenario exception in §2).

For architecture or data-systems guidance: route through `/utilities` (contains `solution-architect` and `data-architect` sub-skills).

---

## Code Limits

- Files: max 500 lines.
- Functions: max 50 lines.
- Classes: max 100 lines.
- Line length: 100 chars (ruff).
- Tests live next to code they test.

---

## Naming Standards

| What | Convention | Example |
|------|-----------|---------|
| Framework / ecosystem files | As-is | `AGENTS.md`, `SKILL.md`, `Rai/`, `Excalidraw/`, JS/TS camelCase (`useApi.ts`) |
| Repos, directories | kebab-case | `data-orchestrator` |
| Docs, configs, non-code files | kebab-case | `auth-flow.md`, `app-config.yaml` |
| Code files (.py, .js, .ts) | snake_case | `data_loader.py` |
| Python functions, variables | snake_case | `get_user_data` |
| Python classes | PascalCase | `DataLoader` |
| Constants, env vars | SCREAMING_SNAKE_CASE | `MAX_RETRIES`, `DB_HOST` |
| Git branches | kebab-case | `feature/add-auth-flow` |
| SQL, dbt models | snake_case | `dim_customer` |
| Docker images, services | kebab-case | `data-api` |

---

## Search Commands

Use `rg` (ripgrep) instead of `grep` and `find`:

```bash
# Search content
rg "pattern"

# Find files
rg --files -g "*.py"
```

---

## Code Safety

- Never commit or push until explicitly told.
- Check git remote before any push.
- Verify file paths and module names before use.
- One change at a time when debugging.
- Test your code. No feature is complete without tests.
- Don't modify user-authored content (notes, docs) without asking.

---

## Git Hygiene

**NEVER mention Claude, Anthropic, or AI in any git activity.** No `Co-Authored-By`, no AI references in commit messages, PR descriptions, branch names, comments, or any GitHub-visible content.

---

## Code Output Formatting

- Code blocks with language tags.
- Short is better.
- Match the existing file's style.
