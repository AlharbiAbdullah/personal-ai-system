# compile: the approved spec, test-first, one group at a time

This is the repo's TDD text. Every behaviour change in any lane follows the loop below. In a feat change it runs over the groups in `plan.md`. In a fix or chg lane it runs once, over that lane's scenario IDs.

## Before the first group

- You are on the change's lane branch. For feat, `requirements.md` says `status: approved`. If it says `draft`, stop: the human runs `! mise run approve` first.
- Read `requirements.md`, `plan.md` and `validation.md`, plus the scenarios for this change in `specs/capabilities/`.
- Read the standing rules in `specs/tech-stack.md`, the newest entries in `project_memory/lessons.md` and the active ADRs for the files you will touch.
- Run `mise run status`. It names the next group: the first one whose IDs lack passing tests. Progress is derived from test results, so there is nothing to tick. A new session resumes the same way.

## The loop, per group

```
 tests tagged with the group's IDs
        |
 mise run tdd -- red <ids>     every ID has >=1 test? every new test fails?
        |                      right reason = AssertionError | NotImplementedError | "DID NOT RAISE"
        |                      wrong reason (ImportError, NameError, SyntaxError, fixture/collection error,
        |                        an exception the test's own code raises)
        |                        -> refuse: "add a stub that raises NotImplementedError"
        |                      records .agent/tdd/<branch>.json, prints trailer lines
 minimal code
        |
 mise run tdd -- green <ids>   needs a red record per ID; all pass
 refactor (tests unedited) -> mise run verify
        |
 git commit -m "fix(cli): usage errors" --trailer "Spec: cli.no-args, cli.help, cli.bad-amount"
                                        --trailer "Red: cli.no-args: assert 1 == 2"
        |
 risk: high group?  -> stop: "review `git diff <group-start>..HEAD` (trunk: <files>), then /sdd compile to continue"
 surprised?         -> append to project_memory/lessons.md in this commit
```

1. **Note the group start:** `git rev-parse HEAD`. For a `risk: high` group, also note the trunk files `mise run status` names on its `next:` line. The pause needs both, and once the group is green, status names the next group instead.
2. **Write the tests.** At least one per scenario ID, tagged with that ID. The tag syntax is in [`specs/README.md#tests-and-commits`](../../../specs/README.md#tests-and-commits). Assert each THEN clause of the scenario literally. Behaviour at the entrypoint is tested by running the real installed command in a subprocess, never an inner function.
3. **Stub what does not exist yet.** A symbol the test needs gets a stub that raises `NotImplementedError`. Without it the test fails for the wrong reason.
4. **See red:** `mise run tdd -- red <ids>`. Every ID must have a test, and every test you wrote or changed must fail for the right reason. An exception that code which exists raises is a right reason too, such as the `ValueError` a fix/ regression test meets. A name the code lacks is not, whether imported or read off its module. Neither is an exception the test's own code raises, such as an `IndexError` from `r.stdout.splitlines()[0]` on empty output: assert on the output instead (`splitlines()[:1] == [...]`). Only an older test on the ID that this branch did not touch may pass, such as the neighbour of a fix/ regression test. On a wrong reason, fix the test or add the stub, then run it again. Keep the `Red:` lines it prints.
5. **Minimal code.** Write only what makes these tests pass. No code for other groups, no speculative options.
6. **See green:** `mise run tdd -- green <ids>`.
7. **Refactor** with the tests unedited, then run `mise run verify` until it is green.
8. **Commit on green, once per group.** Use a conventional subject, a `Spec:` trailer listing the group's IDs, and the `Red:` lines.
9. **Lesson check.** Ask: did anything surprise us? If yes, append an entry to `project_memory/lessons.md` in the same commit: `## <date> | <title>`, `Trigger:`, `Rule:`.
10. **Risk pause.** After a `risk: high` group, stop. Its trunk files, noted at step 1, are the ones the human must read line by line. Say: "review `git diff <group-start>..HEAD`, trunk first: <files>. Then `/sdd compile` to continue."

## Rules while compiling

- **Commit on green only.** Never commit a failing test. The type checker rejects a test that imports a missing symbol, and verify fails anyway. The red evidence lives in the `Red:` trailers, and at merge prove-red proves it again on the old code ([`specs/README.md#definition-of-done`](../../../specs/README.md#definition-of-done)). Keep every `Red:` line `tdd red` prints: prove-red falls back on it when a test cannot reach its body on the old code.
- **Drift.** Reality differs from the spec in a detail, such as an exact message or an exit code. Edit the scenario, its test and the code in ONE commit, and say why in the commit body. Merge lists it as "amended after approval".
- **Stop.** The spec is materially wrong: wrong behaviour, a missing requirement, contradicting decisions, or a dependency nobody decided on. Stop and ask the human. Never replan on your own.
- **Backlog.** A new idea on the way: `mise run backlog -- <topic>`, commit that file alone as the backlog row of `SKILL.md` says, then carry on. Never touch the roadmap.
- **Tests are the contract.** Never weaken, delete or skip a test to get green. A skip or xfail is allowed only for a `[gap]` scenario: strict, with the scenario ID in its reason.
- **Dependencies and choices.** A new runtime dependency or tool edits `specs/tech-stack.md` on this branch. A choice later changes must respect gets one ADR in `project_memory/decisions/`.
- **The env contract.** A commit that adds, moves or retypes an environment read edits its `.env.example` row too: the type, the default, and the file named after `read in`. `mise run doctor` warns about a `read in` file that no longer names the variable.
- **Flag-off guards.** A `[flag-off: <ENV_NAME>]` scenario pins the old behaviour with the flag off. Its test passes on the old code as well as on yours, and prove-red checks that at merge. Leave its ID out of `mise run tdd` (red and green), as with a `Spec-Guard:`; verify runs it. The new behaviour's own tests turn the flag on, as their scenarios' `GIVEN <ENV_NAME>=1` says.
- **Trunk.** Keep trunk edits to the seam: new behaviour goes into leaf modules, and the trunk file gets the one call that reaches them. A trunk file (`## Trunk` in `specs/tech-stack.md`) that no `risk: high` group lists is refused at merge (I18). If the work has to touch one, add it to a `risk: high` group's `Files:` in `plan.md`, in the commit that touches it, and say why in the commit body: merge lists it as amended after approval.
- **Proof.** A group's behaviour may become visible: what a command prints, a page, a terminal session. When `validation.md` has a `## Proof` row for it, capture it after the group's commit: `mise run proof -- <verb> <id> ...` ([`specs/README.md#proof-proofdate-slug`](../../../specs/README.md#proof-proofdate-slug)). Each capture is its own commit, `docs(proof): <id> <kind>`, never part of a code commit. A later code commit makes it stale, so capture again then; validate captures what is still missing.
- **Gates.** When a hook blocks a commit, read its message and fix the cause. Never bypass it.
- **Parallel groups.** A human may split `parallel: yes` groups across workers on `feat/<slug>--g<n>` branches, which merge into `feat/<slug>`. Working alone, run the groups in order.

## The bug variant (fix lane)

- Tag the regression test with the ID of the scenario the code breaks, and see it red first.
- When the spec was silent, add the scenario, plus a guard scenario for the neighbouring behaviour ("SHALL CONTINUE TO"). The guard's test must pass on the old code, so leave its ID out of `mise run tdd` (red and green); verify runs it. Name it in a `Spec-Guard:` trailer. That trailer counts only on a fix/ branch, and never for a scenario you changed: a changed scenario must go red.

## When every group is green

Run `mise run status`: no group is left. Then follow `validate.md`.
