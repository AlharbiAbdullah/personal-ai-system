# Code Review Workflow

**Use when:** reviewing a diff before it merges, at every merge. His own change or Rai's, in any repo: a self-review before merge.
**Not for:** 23 audit, for a whole repo or an architecture rather than one diff. 04 debugging, for a bug the review turns up.
**Done when:** every checklist gate passes and the diff is merged clean.

> **His self-review, with one machine pass.** This playbook is the human self-review checklist and the order to run it in. The machine pass over the diff is the built-in `/code-review`. Invoke it at step 3, and don't re-implement it here.

Self-review gate before merging. Every merge passes through this checklist.

```
Diff → Architecture → Logic → Security → Tests → Clean → Merge
```

---

## Steps

### 1. Read the Full Diff

- [ ] `git diff main..HEAD`: read every changed line
- [ ] No surprises: every change is intentional
- [ ] No debug code left behind (console.log, print, TODO hacks)
- [ ] No commented-out code (delete it, git has history)
- [ ] No unrelated changes bundled in

### 2. Architecture Check

- [ ] Second reader for steps 2 to 5: hand the diff and the checklists of steps 2 to 5 to the `reviewer` agent. It returns findings with location, severity, issue and fix, and a PASS or FAIL per step. It cannot edit files.
- [ ] Rai re-checks each reviewer finding against the code before acting on it.
- [ ] Changes are in the correct layer (don't mix concerns)
- [ ] No circular dependencies introduced
- [ ] Single Responsibility Principle: each module does one thing
- [ ] Consistent with existing patterns in the codebase
- [ ] No unnecessary abstractions (YAGNI)

> **Decision Point**: Architectural issue found?
> - Minor → fix now
> - Major → create a separate refactoring task, don't block this merge

### 3. Logic Check

- [ ] Edge cases handled (empty input, null, boundary values)
- [ ] Error handling is appropriate (not swallowing errors silently)
- [ ] Functions are small and focused (if >50 lines, consider splitting)
- [ ] Variable/function names are clear and accurate
- [ ] No premature optimization
- [ ] Run the built-in `/code-review` for the machine pass over the diff

### 4. Security Check

- [ ] Run `/security → security-review` when auth, input handling or data access changed
- [ ] No secrets in code (API keys, passwords, tokens)
- [ ] User input is validated and sanitized
- [ ] Auth checks are in place where needed
- [ ] No SQL injection, XSS, or command injection vectors
- [ ] An internet-facing change to auth, input handling or an API goes to the `pentester` agent. It needs a written scope John approved: the target, the tests allowed, the time window. It returns findings with severity, evidence and a fix each. It tests only inside the scope and changes no code.
- [ ] Rai re-checks each pentester finding before a fix.

> **Decision Point**: Security issue found?
> - Always fix before merging. No exceptions.

### 5. Test Check

- [ ] Every new behavior has a test
- [ ] Tests are meaningful (not just testing that code runs)
- [ ] Tests cover edge cases, not just the happy path
- [ ] No flaky tests introduced
- [ ] Test names describe the behavior being verified

### 6. Clean Up

- [ ] Run `/git → refactor-clean`: dead code, unused imports
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
| Am I adding complexity for a hypothetical future? | YAGNI: build for now |
| Does every line earn its place? | Less code = fewer bugs |

---

## Connections

- Machine diff pass: the built-in `/code-review`
- The self-review checklist as a skill: `/testing → code-review`
- Security details: `/security → security-review`
- Cleanup: `/git → refactor-clean`
- Agents: the `reviewer` agent (steps 2 to 5), the `pentester` agent (step 4, internet-facing changes only)
- Part of the task flow: [[02-task]]
- Debugging if review catches a bug: [[04-debugging]]
