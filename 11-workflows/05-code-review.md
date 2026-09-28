# Code Review Workflow

**Triggered by:** "review this diff" / "self-review before merge"
**Cadence:** Every merge
**Done when:** every checklist gate passes and the diff is merged clean.

> **Sequencing layer, not the engine.** This playbook is the human self-review
> checklist + the order to run it in. The machine diff-analysis pass is the
> `/testing → code-review` skill — invoke it at step 3/4, don't re-implement it here.

Self-review gate before merging. Every merge passes through this checklist.

```
Diff → Architecture → Logic → Security → Tests → Clean → Merge
```

---

## Steps

### 1. Read the Full Diff

- [ ] `git diff main..HEAD` — read every changed line
- [ ] No surprises — every change is intentional
- [ ] No debug code left behind (console.log, print, TODO hacks)
- [ ] No commented-out code (delete it, git has history)
- [ ] No unrelated changes bundled in

### 2. Architecture Check

- [ ] Changes are in the correct layer (don't mix concerns)
- [ ] No circular dependencies introduced
- [ ] Single Responsibility Principle — each module does one thing
- [ ] Consistent with existing patterns in the codebase
- [ ] No unnecessary abstractions (YAGNI)

> **Decision Point**: Architectural issue found?
> - Minor → fix now
> - Major → create a separate refactoring task, don't block this merge

### 3. Logic Check

- [ ] Edge cases handled (empty input, null, boundary values)
- [ ] Error handling is appropriate (not swallowing errors silently)
- [ ] Functions are small and focused (if >30 lines, consider splitting)
- [ ] Variable/function names are clear and accurate
- [ ] No premature optimization
- [ ] Run `/testing → code-review` for the machine pass over the diff

### 4. Security Check

- [ ] Run `/security → security-review`
- [ ] No secrets in code (API keys, passwords, tokens)
- [ ] User input is validated and sanitized
- [ ] Auth checks are in place where needed
- [ ] No SQL injection, XSS, or command injection vectors

> **Decision Point**: Security issue found?
> - Always fix before merging — no exceptions

### 5. Test Check

- [ ] Every new behavior has a test
- [ ] Tests are meaningful (not just testing that code runs)
- [ ] Tests cover edge cases, not just the happy path
- [ ] No flaky tests introduced
- [ ] Test names describe the behavior being verified

### 6. Clean Up

- [ ] Run `/git → refactor-clean` — dead code, unused imports
- [ ] Consistent formatting with the rest of the codebase
- [ ] No unnecessary files added

### 7. Merge

- [ ] All checks pass
- [ ] `/git → commit` with a clear, descriptive message
- [ ] Merge to main. In an SDD repo (`.project.toml` at the root), skip the commit above and this merge. There `/compile` commits on the lane branch, and the human's `! mise run merge` merges it into `main` ([[21-project-init]] Phase C).
- [ ] Verify tests pass on main after merge

---

## Review Mindset

| Ask yourself | Why |
|-------------|-----|
| Would I understand this code in 6 months? | Clarity over cleverness |
| What's the blast radius if this breaks? | Calibrate review depth |
| Am I adding complexity for a hypothetical future? | YAGNI — build for now |
| Does every line earn its place? | Less code = fewer bugs |

---

## Connections

- Machine diff pass: `/testing → code-review`
- Security details: `/security → security-review`
- Cleanup: `/git → refactor-clean`
- Part of the task flow: [[02-task]]
- Debugging if review catches a bug: [[04-debugging]]
