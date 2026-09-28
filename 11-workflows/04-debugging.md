# Debugging Workflow

**Triggered by:** "let's debug this" / "{X} is broken" / "why is {behaviour} happening"
**Cadence:** Ad-hoc
**Done when:** original repro no longer triggers the bug, a regression test guards it, full suite green.

Systematic diagnosis and fix. Resist the urge to change random things — follow the steps.

> **SDD repo** (`.project.toml` at the root): steps 1 to 4 hold, and the fix runs the fix lane of [[21-project-init]] Phase C. `/grill "<the bug>"` opens `fix/<slug>`. `/compile` writes the regression test red first, tagged with its scenario ID. The human merges it with `! mise run merge`, so skip the `/git → commit` in step 7. A reusable pattern goes in the repo's `project_memory/lessons.md` on the fix branch, and a systemic follow-up in its backlog (`mise run backlog -- <topic>`), not in the vault.

```
Symptom → Reproduce → Isolate → Diagnose → Fix → Verify → Document
```

---

## Steps

### 1. Describe the Symptom

- [ ] What is the exact error message or unexpected behavior?
- [ ] When did it start? (commit, deploy, config change?)
- [ ] What changed recently? (`git log --oneline -10`)
- [ ] What is the expected behavior vs actual behavior?

### 2. Reproduce

- [ ] Find the exact steps to trigger the bug
- [ ] Reduce to minimum input — smallest case that fails
- [ ] Can you reproduce it consistently?

> **Decision Point**: Can you reproduce it?
> - Yes → continue to isolation
> - No → add logging/observability, wait for next occurrence
> - Intermittent → look for race conditions, timing, state leaks

### 3. Isolate

- [ ] Which layer is the bug in? (UI, API, logic, data, infra)
- [ ] Comment out / bypass components until the bug disappears
- [ ] The last thing you removed is where the bug lives
- [ ] Narrow to the specific function or module

### 4. Diagnose

- [ ] Read the code in the isolated area — carefully
- [ ] Check `git log` for recent changes to that area
- [ ] Form a hypothesis: "The bug is because X"
- [ ] Verify the hypothesis with a targeted test or log statement

> **Decision Point**: Hypothesis confirmed?
> - Yes → continue to fix
> - No → form new hypothesis, repeat step 4
> - Stuck → rubber duck it, or hand to the `debugger` agent / `/think → systematic-debug`

### 5. Fix

- [ ] Write a regression test FIRST — it should fail now (`/testing → tdd` proves the bug)
- [ ] Write the minimal fix — change as little as possible
- [ ] Run the regression test — it should pass now
- [ ] Run the full test suite — nothing else broke

> **Decision Point**: Fix is larger than expected?
> - Small fix → continue
> - Architectural issue → create a separate task, apply a minimal patch now

### 6. Verify

- [ ] Original reproduction steps no longer trigger the bug
- [ ] All existing tests pass
- [ ] Run `/testing → e2e` if the fix touches integration points
- [ ] Manual smoke test of related functionality

### 7. Document

- [ ] `/git → commit` with a message explaining what broke and why
- [ ] If the pattern is reusable, note it for future debugging
- [ ] If the root cause was systemic, create a follow-up task to address the deeper issue

---

## Common Traps

| Trap | Instead |
|------|---------|
| Changing random things to see what happens | Follow isolate → diagnose → hypothesis |
| Fixing the symptom, not the cause | Ask "why?" five times |
| Making the fix too large | Minimal change. Refactor separately |
| Not writing a regression test | Always write the test first |
| Not checking what changed recently | `git log` and `git diff` are your friends |

---

## Connections

- Regression testing: `/testing → tdd`
- End-to-end verification: `/testing → e2e`
- If the fix needs review: [[05-code-review]]
- If the fix is part of a larger task: [[02-task]]
