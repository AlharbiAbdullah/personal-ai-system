---
name: compile
description: >
  Build step of the pipeline: implement an approved spec test-first, group by group. In a repo
  with .project.toml it follows the repo's .claude/skills/sdd/compile.md, then validate.md, with
  Rai extras (/orchestrator for 3+ disjoint parallel groups, /adversarial-review after
  validate); `/compile launch <slug>` follows the repo's launch.md with the same review extra;
  elsewhere it executes .agent/plan.md. Idempotent: resumes at the first unfinished group, an
  orchestrator wave cut off mid-run, or where a fast lane stopped. USE WHEN the user types
  /compile or asks to implement the approved spec or plan.
---

# Compile

Builds what `/grill` specified. In an SDD repo, progress is derived from test results and git. Elsewhere it lives in the plan's task boxes. Either way a fresh session resumes where the last one stopped.

**Pipeline:** `/grill` → `/spec-improve` (optional) → approval → **`/compile`** (which runs `/adversarial-review`).

**Single-agent mandate:** run inline. Never use the Agent or Workflow tools. The one exception is the lens subagents that the repo's `validate.md` and `launch.md` ask for in Claude Code: they review and never edit.

## 0. Pick the mode

- **SDD mode:** `.project.toml` sits at `git rev-parse --show-toplevel`.
- **Plan mode:** anything else.

## 1. SDD mode

`<default>` below is the `default_branch` of `.project.toml`.

1. **Resume point.** Run `mise run status`.
   - The `scenarios:` line says `no test results`, or its results are `partial` or `stale`: run `mise run test`, then status again. Status judges every group by those results, so without a full, fresh run it names the wrong next group.
   - No open change (`no open change` or `not a lane branch`): status judges only this checkout, and a change may be open on its lane branch anyway. List the lane branches and where each is checked out: `git for-each-ref --format='%(refname:short) %(worktreepath)' refs/heads/feat refs/heads/fix refs/heads/chg refs/heads/chore refs/heads/refactor refs/heads/plan`. Skip worker branches (`--g<n>`).
     - One branch, with no path: `git switch <branch>`, then status again.
     - One branch, with a path: the change is checked out there. Name the path to John with "run `/compile` there", and stop.
     - More than one: name each with its path and ask which one to build. Then act as for one.
     - None: point to `/grill`, which opens one. Stop.
   - A feat change still at `status: draft` (`ready for approve` or `not ready for approve`): "run `! mise run approve` first." Stop.
   - A `dirty:` line on a feat or fast-lane branch, where `git status --porcelain -uall` lists untracked backlog files (`?? specs/backlog/<date>-<slug>.md`): those are ideas parked with `mise run backlog`, not stopped work. Without `-uall`, git shows only `?? specs/backlog/` when no backlog file is tracked yet. Commit each one on this branch, as the backlog row of `sdd/SKILL.md` says: `git add specs/backlog/<file>`, then `git commit -m "spec(backlog): <topic>" -- specs/backlog/<file>`. The pathspec commits that file alone, so work a stopped session left staged stays out of it. Approve also uses the `spec` type for backlog files. No fast lane lands under it, so the park never becomes a fast lane's squash subject, as a `docs` subject would on chore. Run status again. A `dirty:` line that remains is real work.
   - A feat change at `status: approved` with a `dirty:` line: a group may have stopped before its commit. Status judges by test results, so it may already name the group after that one. Go to step 3 first, whose dirty case finishes that group.
   - `<default> moved: run git merge <default>`: a hotfix landed while this change was open. Run that merge on this branch, then `mise run verify`. On a conflict or a red verify, stop and show John what broke. Otherwise run status again and go on down this list.
   - `all groups green`: run the leftover check of step 2 first, since a run cut off after its last merge still owes its teardown. Then go to step 4.
   - A fast lane (fix, chg, chore, refactor) has no groups: go to step 3, which finds where the lane stopped.
   - A plan branch has nothing to compile: follow the close in `.claude/skills/sdd/replan.md`.
   - Otherwise status names the next group: go to step 2.
2. **Parallel check** (Rai extra), before every feat group.
   - **Leftover worker branches** come first: `git for-each-ref --format='%(refname:short) %(worktreepath)' 'refs/heads/feat/<slug>--*'`. Any line means some groups run, or ran, on branches of their own, and some of that work may not be merged yet. Never ask the orchestrator question, and never build those groups here. Read this change's newest run dir, the last of `ls -d .agent/orchestrator/????????-????-<slug>/`:
     - It has no `report.md`: an `/orchestrator` wave was cut off before its teardown. Read `~/helm/03-rai/skills/orchestrator/SKILL.md` and run it again over those branches, resuming as its Phase 2 says, through its Phase 7 report. Then go back to step 1.
     - It has a `report.md`: that run ended with those tasks left on purpose (a timeout, a refused teardown, a worker that failed twice). Show John its table and stop.
     - There is none: no orchestrator run made these branches. A human split the groups by hand, as `compile.md` allows. Name each branch with its worktree path to John and stop.
   - The wave is the run of `plan.md` groups that starts at the group status names next and stops before the first group marked `parallel: no` or `risk: high`. Leave out any group that is already done. `mise run spec-check` runs the suite and lists every ID still lacking a passing test; a done group has none of its IDs there.
   - The next group is itself `parallel: no` or `risk: high`: the wave is empty. Build that group in step 3.
   - The wave holds 3 or more groups and their `Files:` lines are disjoint: ask, at most once per wave.
     1. `/orchestrator` on this wave: workers on `feat/<slug>--g<n>`, merged into `feat/<slug>`. (Recommended when each group is more than a few minutes of work.)
     2. Run them here, in order. This answer holds for the rest of the wave.

     On 1, read `~/helm/03-rai/skills/orchestrator/SKILL.md` and run this wave by its SDD mode, through its Phase 7 report. The orchestrator stops there and prints no hand-back line. This skill then goes on at step 1, in the same session.
   - Otherwise, or on 2: step 3.

   A `risk: high` group is never delegated, not even under "full auto". It runs here, and `compile.md` pauses after it so John reviews its diff.
3. **Compile.** Three records show where the last session stopped:
   - the branch's commits: `git log --no-merges --format='%h %s%n%(trailers:key=Spec,key=Spec-Removed)' <default>..HEAD`;
   - the red record: `.agent/tdd/<branch>.json` (for example `.agent/tdd/fix/<slug>.json`), keyed by scenario ID. `tdd red` writes an ID's `red` and leaves its `green` null; `tdd green` fills the `green`;
   - edits not committed yet: `git status --porcelain -uall`, which step 1 has cleared of parked backlog files.

   Then, by lane:
   - feat: read `.claude/skills/sdd/compile.md` once per session.
     - Dirty case (from step 1): the stopped group holds the IDs that have a `red` entry and appear in no commit's `Spec:` trailer. Finish that group first: go on at `compile.md` step 5, or at its step 7 when every `green` is filled. Its commit takes the `Spec:` and `Red:` lines that `mise run tdd -- green <ids>` prints, run again in a fresh session. Then go back to step 1. No such ID, and status names a group: the edits are its work so far. Build that group here, keeping them, and skip step 2 for it. No such ID and no group left: show the edits to John and stop.
     - Run the `compile.md` loop for the one group status names next. When that group commits green, go back to step 1, so the resume point and the wave are checked again before every group. The risk pause ends the run instead.
   - fix, chg, chore, refactor: read `.agent/lane-<slug>.md` first when `/grill` left one: the lane, scenario IDs and intent confirmed there. The branch is the whole state, so find where the lane stopped from the three records before running anything.

     For fix and chg, the lane IDs are the ones it runs `mise run tdd` over (a fix's guard IDs stay out):
     1. A commit on the branch lists every lane ID in its `Spec:` trailer, or in `Spec-Removed:` for a removal. The recipe is done: never run `tdd red` again, because a committed test passes and `tdd red` refuses a passing test. With uncommitted edits, show them to John and stop. Otherwise run `mise run verify`: green goes to step 4, red stops and shows what broke.
     2. Every lane ID has a `red` entry and no commit lists it yet: red is seen. Go on at `compile.md` step 5 (minimal code), or at its step 7 when every ID's `green` is filled too. The commit takes the `Spec:` and `Red:` lines that `tdd green` prints. In a fresh session, run `mise run tdd -- green <ids>` again to print them.
     3. Neither: follow that lane's recipe under "Fast lanes" in `.claude/skills/sdd/SKILL.md` from its start, keeping uncommitted edits as work so far. It runs `compile.md` wherever behaviour moves.

     For chore and refactor (no IDs): with a lane commit on the branch and a clean tree, compare `git diff <default>...HEAD` with the intent in the lane file. It covers the intent: run `mise run verify`, then step 4. Otherwise go on with that lane's recipe from the part still missing.
   - Where the text says `/sdd compile` (the risk pause), John types `/compile`.
4. **Validate.** When every group is green, or the fast-lane recipe is done and `mise run verify` is green, read `.claude/skills/sdd/validate.md`. Run its lenses for this lane and give every finding its outcome. Hold its Close until step 5 is done.
5. **Adversarial review** (Rai extra).
   - feat: read `~/helm/03-rai/skills/adversarial-review/SKILL.md` and run the panel up to its report. Its findings take validate's outcomes. The Close runs once, at step 6.
   - Other lanes: offer it. (Recommended: skip, unless the diff touches money, security or stored data.)
   - Without `OPENROUTER_API_KEY`, skip it and say so.
6. **Close.** Run validate's Close: the lesson check, the proof captures, `mise run status -- --merge`, the report and the hand-over line. In a linked worktree, such as a hotfix's, `git rev-parse --path-format=absolute --git-dir --git-common-dir` prints two different paths. There the hand-over names the branch, as `sdd/SKILL.md` says: `! mise run merge -- --branch <branch>`, plus any flags the preview names, typed in the main checkout. That checkout is the first path `git worktree list` prints. Merge then removes this worktree. A plain merge typed here leaves it checked out on `<default>`. Stop. Never run `approve`, `merge`, `abandon` or `release`.

When a breaker finding is hard to see, `/visual debug` replays the failing run step by step.

**Launch.** `/compile launch <slug>`, on the default branch with no change open: read `.claude/skills/sdd/launch.md` and follow it. Rai extra: after its four lenses, run the `/adversarial-review` panel over the same audited diff, as in step 5; its findings take launch's outcomes. The fix lanes and the launch lane it opens are ordinary lanes: `/compile` builds each one from step 1.

## 2. Plan mode (`.agent/plan.md`)

1. **Resume point.**
   - The plan is the file `/grill` named: `.agent/plan.md`, or `.agent/plan-<slug>.md` when the user passes a slug. Its header names its decisions file.
   - No such file: list the candidates, the `.agent/plan-*.md` files that still have an unticked box (`grep -l '^- \[ \]' .agent/plan-*.md`), each with its `# Plan:` title and `Date:`. Say "run `/compile <slug>`" for the one to build, and stop. No candidate either: point to `/grill` and stop.
   - Every box ticked: re-run each `Verify:` and acceptance criterion, report, offer `/adversarial-review`, stop.
   - Otherwise read the decisions file once, then go to step 2.
2. **Parallel check,** before every group. Skip it in helm, where the orchestrator never runs, and outside a git repo. Elsewhere, run the leftover check of SDD step 2 first, over `refs/heads/<branch>--*` for the current branch, with the last of `ls -d .agent/orchestrator/*/` as the run dir. Then apply the wave rule of SDD step 2 to the plan file: the next group is the first one with an unticked task. On a wave of 3 or more groups with disjoint `Files:`, ask the same question.
   - Option 1 needs a clean tree with the groups done so far committed, because workers branch from the committed tip.
   - On 1, run the orchestrator as SDD step 2 says, through its Phase 7 report. It ticks each group's boxes once that group merges green. This skill then goes on at step 1, in the same session.
3. **One group:** the first with an unticked task.
   1. Read the code paths in `Files:` before editing.
   2. Where behaviour changes, write the test first by [`testing/tdd.md`](../testing/tdd.md).
   3. Implement the tasks as written: the files, the architecture, the decisions.
   4. Run the group's `Verify:`. Never advance on red.
   5. Tick the group's boxes in the plan file.
   6. Commit on green, one conventional commit per group, when John asked for commits in this session.
   7. After a `risk: high` group, stop. John reviews its diff and says continue.
   8. Go back to step 1 for the next group.
4. **While building:**
   - A detail differs from the plan, such as a name or a path. Fix the plan line, keep going, and name it in the final report.
   - The plan is materially wrong: wrong behaviour, a missing requirement, contradicting decisions, or a dependency nobody decided on. Stop, say exactly what broke, and let John decide. Never replan on your own.
   - A choice the plan left open: take the simplest option that honours the decisions file, and name it in the report.
   - The Ousterhout lens carries into code: deep modules, hidden sequencing and policy, fewer concepts, complexity pulled downward.
5. **Done.** Every box is ticked and every acceptance criterion is green by its command. Report what shipped, the evidence, and each choice made in flight. When an orchestrator wave created `feat/<slug>` off the default branch, name that branch in the report: landing it is John's call. Offer `/adversarial-review`. Stop.

Stopping early is safe: the unticked boxes are the resume point. Say what blocks.

## Examples

- `/compile` after `! mise run approve` and `/clear`
- `/compile` in a fresh session: resumes at the first group without passing tests
- `/compile` on `fix/<slug>` in a fresh session, with the fix commit already on the branch: verify, then validate
- `/compile` after `/grill` in a one-off repo: executes `.agent/plan.md`
- `/compile rate-limit` in helm: executes `.agent/plan-rate-limit.md`
