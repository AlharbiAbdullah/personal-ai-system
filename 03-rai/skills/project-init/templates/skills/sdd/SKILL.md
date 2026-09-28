---
name: sdd
description: >
  This repo's spec-driven, test-driven loop. USE WHEN starting any change ("/sdd add split bill"),
  writing specs, compiling an approved spec test-first, validating, launching a merged roadmap item,
  replanning, or asking what is next (/sdd status). Follows specs/README.md. Never runs approve,
  merge, abandon or release.
argument-hint: "<what you want> | talk | compile | validate | launch <roadmap-slug> | replan | status"
---

# sdd

The loop that turns a request into specs, then tests, then code. `specs/README.md` is the authority on lanes, formats and gates. When this skill and that file disagree, the file wins. Read it once per session, before the first change.

## Hard rules

- **Human gates.** Never run `mise run approve`, `merge`, `abandon` or `release`, and never set `PROJECT_MERGE`. When a gate is next, stop. Say what is ready and print the exact command for the human. In Claude Code they type it with the `!` prefix. Elsewhere they use their own terminal.
- **Branches.** Never commit on the default branch. Every change lives on the lane branch that `mise run change` creates.
- **Gates stay on.** Never skip hooks (`--no-verify`), change `core.hooksPath`, or edit `.githooks/` or `scripts/project.py`. When a gate blocks you, read its message and fix the cause.
- **Test first.** No production code without a failing test tagged with its scenario ID.
- **Direction.** `specs/mission.md` and `specs/roadmap.md` change only on `plan/` branches. Merge ticks the roadmap and marks a launch. Ideas go to `mise run backlog -- <topic>`.

## Route by argument

| Argument | Do |
|---|---|
| none, or `status` | Run `mise run status`. Report the branch, the open change, the next group and what blocks merge. With nothing open, offer the next roadmap item, or a launch that status lists. |
| `talk` | Follow `talk.md`: write or finish the spec of the open feat change. |
| `compile` | Follow `compile.md`: build the approved spec test-first, group by group. |
| `validate` | Follow `validate.md`: the review lenses for this lane, then the merge preview. |
| `launch <roadmap-slug>` | Follow `launch.md`: audit the merged item as one feature, then the lane that takes its flag off. |
| `replan` | Follow `replan.md`: roadmap, backlog and process, between changes. |
| a request in words | Start a change (below). |

## Start a change

1. Run `mise run status`. If a change is already open, a request that needs a lane waits: continue the open change, or park the request in the backlog. Only an urgent fix may start alongside it, with `--hotfix`.
2. Classify out loud with the questions in [`specs/README.md#lanes`](../../../specs/README.md#lanes). Ask them in order and stop at the first yes. Quote that question and name the lane. Between two lanes, pick the heavier one.
3. Pick a slug: short, lowercase, kebab-case, permanent. Work that is on the roadmap uses its roadmap slug.
4. Act on the lane:

| Lane | Command | Then |
|---|---|---|
| plan (pivot or replan) | `mise run change -- <date>-<slug> --lane plan` | `replan.md` |
| spike | `mise run backlog -- <topic> --spike` | Answer the question in the scratch worktree it makes. Write the findings into the backlog file, then `git worktree remove` the scratch tree. Its code is never merged. |
| backlog | `mise run backlog -- <topic>` | Fill What, Why and Notes. On a lane branch, commit that file alone: `git add specs/backlog/<file>`, then `git commit -m "spec(backlog): <topic>" -- specs/backlog/<file>`. On the default branch, leave it uncommitted: the next `mise run change` takes it along, new or edited. Stop. |
| feat | `mise run change -- <slug> --lane feat` | `talk.md` |
| fix, chg, chore, refactor | `mise run change -- <slug> --lane <lane>` | the fast-lane recipe below |

For an urgent fix while a change is open, add `--hotfix`. It opens a sibling worktree off the default branch, and the open change stays untouched.

## Fast lanes (no change folder)

The branch is the whole state. Where behaviour moves, run the loop in `compile.md` once, over this lane's scenario IDs: it is the one TDD text.

- **fix.** Run `compile.md` over the ID of the scenario the code breaks. Its bug variant covers a spec that was silent or wrong.
- **chg.** Edit the scenario and flip its test's assertion first, then run `compile.md` over the changed IDs. The scenario, test and code go in one commit, with the intent in the commit body. To remove behaviour, delete the scenario and its tests in one commit with `Spec-Removed: <id>`.
- **chore.** Behaviour stays the same and existing tests stay unedited. A harness-only test edit (fixtures, imports, mocks) goes in its own commit with `Test-Harness: <reason>`. Adding, removing or swapping a runtime dependency or tool also edits `specs/tech-stack.md` on this branch. Dependency work uses the slug `deps-<slug>`.
- **refactor.** Same test rule as chore, and adding tests is fine. If a scenario has to change, the lane was wrong: rerun `mise run change -- <slug> --lane chg`.

**Ratchet.** A lane only gets heavier. When a chg no longer passes Q7 in [`specs/README.md#lanes`](../../../specs/README.md#lanes), run `mise run change -- <slug> --lane feat` and continue in `talk.md`. It upgrades the branch in place. A `launch-<slug>` lane never ratchets: Q7 does not apply to it (`launch.md`).

Commit subjects and trailers: [`specs/README.md#tests-and-commits`](../../../specs/README.md#tests-and-commits).

## How every lane ends

1. `mise run verify` is green.
2. `validate.md` ran the lenses for this lane and ended with `mise run status -- --merge`. A plan lane ends with the close in `replan.md` instead.
3. Hand over with the closing line of `validate.md`, then stop. A hotfix names its branch, and the human types it in the main checkout: `! mise run merge -- --branch fix/<slug>`.
