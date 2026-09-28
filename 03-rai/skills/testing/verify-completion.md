---
name: verify-completion
description: >
  Discipline skill: before marking a task done, verify acceptance criteria
  actually hold. USE WHEN finishing a task, especially in AI-assisted work
  where declaring "done" is the easy failure mode.
---

# Verify Completion

AI agents and tired humans both tend to declare tasks done before they
actually work. This skill forces the pause.

## When to use

- Before checking off a task on a board
- Before opening a PR as "ready for review"
- Before telling a stakeholder "it's done"
- Before moving to the next task when multiple are in flight

## When NOT to use

- You've already shipped + measured + confirmed. Done is done.
- Trivial ops that can't fail silently (e.g. `git pull`)

## The rule

"Done" requires evidence. Not opinion, not vibes, not "the code compiles."

Evidence depends on task type:

| Task type | Evidence |
|---|---|
| New feature | Working demo + passing tests |
| Bug fix | Reproduced original bug is now gone + regression test added |
| Refactor | All existing tests still pass + no behavioral change |
| Performance | Benchmark before + after + delta |
| Deploy | Health check returns OK in target env |
| Docs | Another human read it + understood |
| Config change | Target behavior observed in target env |

## Process

### 1. Restate the acceptance criteria
From memory, before looking at code, what does "done" mean?
- If you can't say it crisply, you haven't understood the task.

### 2. Evidence each criterion
For each criterion, produce concrete evidence:
- Test passes
- Screenshot
- Log line
- Benchmark number
- User confirms

### 3. Check for side effects
What might have BROKEN while fixing this?
- Run the full test suite, not just the relevant tests
- Check related modules
- Think about upstream / downstream dependents

### 4. Check your assumptions
Did you assume anything that should be verified?
- "The database is available"
- "The user has permission"
- "This runs on Linux"
- Actually verify where practical.

### 5. Clean up
- Remove debug code
- Revert temporary test data
- Close the dev ngrok tunnel
- Stop the local server
- Commit everything relevant; stash or discard the rest

### 6. Handoff context
If someone else will pick this up:
- What's the state?
- What's tested vs assumed?
- What's the risk if this goes wrong?

## The "in doubt" test

If asked "Are you SURE it's done?" and your honest answer is "pretty sure",
it's NOT done. Either:
- Get evidence to turn "pretty sure" into "yes, confirmed by X"
- Or add a clear caveat to the completion: "done except for Y"

## Anti-patterns

- "The code compiles so it's done" — compilation is necessary, not sufficient
- "Tests pass" without checking if the tests test the right thing
- "I'll fix the edge case in a follow-up" — if it's in scope, it's not done
- "The CI is green" — green CI can still ship broken code (mocks, missing tests)
- "It worked on my machine" — doesn't work anywhere else
- Marking done at EOD without having tried the change — tomorrow you'll forget the context

## Use in multi-step tasks

For tasks with sub-items (like this big reorg):
- Each sub-item gets its own verify-completion pass
- Don't mark the parent done until every child is verified
- Document which children are deferred (not the same as done)

## Examples

- "I think I fixed the bug — verify"
- "PR is ready — check before I request review"
- "Task board says done — is it really?"
- "Did the migration complete correctly?"
