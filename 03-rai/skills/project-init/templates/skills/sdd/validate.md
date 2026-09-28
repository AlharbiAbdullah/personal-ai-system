# validate: review the branch before the human merges it

Validate looks for what the tests missed, then previews the Definition of Done. It never merges.

## Lenses by lane

| Lane | Lenses |
|---|---|
| feat | 1 conformance, 2 breaker, 3 test honesty |
| chg, fix | 2 breaker |
| chore, refactor | none: `mise run verify` plus the unedited-tests rule (I7) |
| plan | none: `mise run verify` |

**Inputs for every lens:** `requirements.md` and `validation.md` for feat, the scenario diff from `mise run status -- --change`, the branch diff `git diff <default>...HEAD`, and the test files.

**How to run them.** In Claude Code, run each lens as its own subagent with the same inputs, told only its lens. In other harnesses, run them one after another. Each lens reports findings as `file:line`, what is wrong, and the evidence.

### 1. Conformance

For each scenario in the change, compare the scenario text, its test and the code:
- **missing:** no code path produces the THEN;
- **partial:** some inputs produce it, others do not;
- **contradicts:** the code or the test does something else than the text says;
- **unrequested:** the code does something no scenario asks for.

### 2. Breaker

Attack the real entrypoint, not inner functions. Run each input for real and record the command, exit code and output.
- Every Review focus row in `validation.md`.
- Inputs you invent: empty, whitespace, huge, zero, negative, non-ASCII, the wrong type, a missing or empty env value, repeated flags, an interrupted run.
- For each changed line, ask: if this broke, would a test fail? When unsure, break it on purpose, run the tests, then restore it.

### 3. Test honesty

- **Tautologies:** the test asserts what it set up itself.
- **Mocks of the unit under test**, or of the entrypoint the scenario names.
- **Weakened assertions:** `in` where the scenario gives an exact value, "exit code is not 0" where it says 2.
- **Wrong target:** an inner function called where the scenario names the command.
- **Wrong tag:** a test tagged with an ID whose THEN it does not check. The requirement's SHALL above that scenario does not count.

## Every finding gets one outcome

1. **In scope:** a new or amended scenario, its test (red first with `mise run tdd -- red`) and the code, all in ONE commit. A new scenario's ID also goes into a group of the change's `plan.md`, in the same commit. Otherwise spec-check warns that a changed ID is in no group.
   - The branch already has the behaviour: an earlier group wrote it, but no scenario or test pins it. `tdd red` answers `passes already`, since it runs the test on this branch's code. The red shows only on the base. Commit the scenario and its test with `Spec:` and no `Red:` line, since they are green here. Then run `mise run prove-red`. It runs the committed test on the merge-base's code, where it must fail. When it passes there too, the base had the behaviour already: the next case applies.
   - The behaviour is not new on this branch: the base has it too. An example is a surviving mutant (`bill < 0` to `bill <= 0`) on a line the change did not write. A new scenario would pass on the base, and prove-red fails an ADDED scenario that pins nothing new. When an existing scenario's THEN already covers that input, add the test under that scenario's ID. prove-red checks only ADDED and MODIFIED IDs, and verify runs every test. A requirement's SHALL alone is not such a scenario: lens 3 flags that tag as wrong. With no such scenario, the finding is out of scope (outcome 2): `mise run backlog -- <topic>`. The item says the base already has the behaviour. A scenario for it passes on the base, so prove-red fails it on a feat or chg branch. It lands in one of two ways: on a `fix/` branch beside a regression test, as a `Spec-Guard:` scenario, or with the human's `--allow <id> --reason "<why>"` on `! mise run merge`. A later change that alters the behaviour pins its new form the usual way.
2. **Out of scope:** `mise run backlog -- <topic>`, committed alone as the backlog row of `SKILL.md` says.
3. **Dismissed:** one `Dismissed: <file:line or finding>: <reason>` line per finding, in the body of the commit that closes validate. If nothing else changed, make that an empty commit: `git commit -m "test(<slug>): validate" -m "Dismissed: ..." --allow-empty`. The squash merge deletes the branch, so merge copies every `Dismissed:` line of its commits into the squash body.

## Close

1. **Lesson check.** Did anything surprise us? If yes, append to `project_memory/lessons.md` and commit it.
2. **Proof** ([`specs/README.md#proof-proofdate-slug`](../../../specs/README.md#proof-proofdate-slug)):
   - Capture every `## Proof` row of `validation.md` that has no current capture, in the kind the row names: `mise run proof -- <verb> <id> ...`. The preview below names the missing and the stale ones.
   - On `fix/`, capture the reproduction with `mise run proof -- run --before <id> -- <cmd...>`: the bug on the old code, the fix on the new.
   - For feat, one confidence line per group: `mise run proof -- confidence G<n> high|medium|low -- "<why>"`, the why in one line. High: every path the group adds has a test, and its proof shows it. Low: you are unsure, and the why says of what. A low line is what the human reads first.
   - Then `mise run proof -- tests` (the test proof per scenario ID) and `mise run proof -- show`. Keep the path it prints for the handover.
3. Run `mise run status -- --merge`, the read-only preview of the Definition of Done. Fix every failure an agent may fix. Four steps are the human's to read, so leave them as they stand. They are Human checks, the trunk diff, a gate-file diff, and an approved check dropped or reworded since approve ("amended after approval").
4. Report the lenses run, each finding with its outcome, the preview, and the page `mise run proof -- show` printed (`.agent/proof/<date>-<slug>.html`), which the human opens before merging.
5. Hand over with the command on the preview's last line:
   - `ready: a human runs ...`: "run `! mise run merge`";
   - `ready for a human: ...`: that command with its flags, after the human reads what the line names. `--attest` covers Human checks and `Test-Harness:` diffs, `--read-trunk` the trunk diff (the preview's `trunk` step prints it, with the `review depth` block below the steps), `--gate-change` a gate-file diff or a Trunk entry removed or changed, and `--reapprove` an approved check dropped or reworded since approve. In their own terminal, `mise run merge` asks for each Human check and for the trunk diff, so `--attest` and `--read-trunk` are not needed there.
   - Outside feat, the preview's `lane` step ends `lands as '<subject>'`: the squash subject, which the CHANGELOG line comes from. When that subject is a parked idea (`spec(backlog): ...`) instead of the branch's own work, add `--title '<type>(<scope>): <subject>'` to the command, with a type the lane lands under (`specs/README.md#definition-of-done`). A plan lane can pick such a subject, since `spec` is one of its types.
   - In a hotfix worktree, the human types it in the main checkout, with `--branch fix/<slug>` when the line lacks it, as the end of `SKILL.md` says.

Then stop.
