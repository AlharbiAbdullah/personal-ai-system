---
name: orchestrator
description: >
  Run ONE session as orchestrator + reviewer over N parallel Claude worker
  sessions: one tmux session + one git worktree per task. Plans tasks (in an
  SDD repo: one wave of the approved change's `parallel: yes` groups, never
  a `risk: high` one), spawns workers, monitors and unblocks them, reviews
  output with evidence, merges each worker branch into the integration
  branch (feat/<slug> in an SDD repo, never main) in dependency order,
  tears down, and reports per task. USE WHEN the user says
  /orchestrator, "orchestrate these tasks", "run this as parallel workers",
  "spin up a fleet on this repo", or /compile offers it for 3+ disjoint
  groups. Code projects only, NEVER the helm vault. Never spawns Agent or
  Workflow subagents; workers are tmux sessions.
---

# Orchestrator

One session (this one, Fable at high) drives a fleet of worker sessions
(Opus 5 at high). Each worker has its own tmux session and git worktree. Filesystem is
the bus: briefs in, status files + inbox + DONE markers out. Decisions locked
at `~/helm/.agent/decisions-orchestrator.md`; research at the run of
2026-08-01.

## Hard rules

1. Targets are code projects. NEVER run against `~/helm`.
2. NEVER use the Agent or Workflow tools for worker tasks. Workers are tmux
   sessions: attachable, inspectable, killable.
3. NEVER run `tmux kill-session`/`kill-server` against your own session. If
   `$TMUX` is set, resolve your own session name first and refuse any kill
   that matches it. Worker sessions are always named `wk-<repo>-<task>`,
   and every target names one exactly: `-t "=wk-<repo>-<task>"` for a
   session command (`has-session`, `kill-session`), `-t
   "=wk-<repo>-<task>:"` for a pane command (`send-keys`, `capture-pane`,
   `paste-buffer`). A bare `wk-app-g1` also matches `wk-app-g10` by
   prefix, so with g1 gone, `kill-session -t wk-app-g1` kills g10.
4. NEVER remove a worktree or branch holding uncommitted, untracked, or
   unpushed work. `scripts/orch-teardown.sh` enforces this; always use it.
5. No two concurrent tasks may write the same file. Overlap = same wave is
   forbidden; serialize into different waves instead.
6. NO concurrency cap: one worker per independent task. Only spawn commands
   are staggered, 2-3 at a time and a few seconds apart. That keeps the
   launch burst under the server-side rate limiter.
7. Only the orchestrator merges, and only into the integration branch
   `<int>` (see the table below). Workers never touch the default branch or
   `<int>`, never merge, never push. Landing `<int>` on the default branch
   is a separate step (Phase 5).
8. Never blind-Enter a worker's pane. Unblock with a targeted message.
9. Report status honestly. A worker's DONE claim is verified, never trusted.
10. In an SDD repo (`.project.toml` at the root), workers never write
    `specs/roadmap.md`, `specs/mission.md`, another group's scenarios, or
    anything under `project_memory/`. Nobody in the run executes `mise run
    approve`, `merge`, `abandon` or `release`: those are human gates.
11. A `risk: high` group is never delegated, not even under "full auto".
    `/compile` runs it in the main checkout and pauses after it, so John
    reviews its diff before the next group.

## Branches and run layout

| | SDD repo | Elsewhere |
|---|---|---|
| Integration branch `<int>` | `feat/<slug>`: the open change's branch, `status: approved` | the current branch, where `/compile` has been committing; on the default branch, Phase 0 creates `feat/<slug>` from it |
| `<slug>` | the change slug | the run slug |
| Tasks | one wave of the change's `plan.md` groups (Phase 1): `g<n>` | one wave of the plan file's groups: `g<n>`; or tasks from the user's prompt |
| Worker branch | `feat/<slug>--g<n>`, made by `mise run change -- <slug>--g<n> --parallel` (Phase 2) | `<int>--<task>` |
| Worktree | `../<repo>-<slug>--<task>` | same |
| tmux session | `wk-<repo>-<task>` | same |

```
.agent/orchestrator/<run-id>/     run-id = YYYYMMDD-HHMM-<slug>
  plan.md          task table, waves, dependency order, gate decisions
  briefs/<task>.md
  status/<task>.json      written by the status hook (see Setup)
  inbox/<task>.json       worker questions {question, context, blocking}
  reports/<task>.md       worker's completion evidence
  done/<task>.DONE        completion signal, worker-created LAST
  log.jsonl        orchestrator actions, append-only
  report.md        final per-task table + outcomes
```

The run dir is gitignored scratch and is never committed. An SDD repo
already ignores `.agent/`; elsewhere Phase 0 adds it to the repo's exclude
file. The durable record is the merged commits.

## Phase 0: setup (idempotent, once per repo)

1. Preflight: the main checkout is on `<int>`, up to date, with a clean
   tree (`git status --porcelain` lists nothing but `.agent/`).
   Workers branch from its committed tip, so work that is not committed
   never reaches them. In an SDD repo, `mise run status` shows the change
   approved. Elsewhere on the default branch, run `git switch -c
   feat/<slug>` first. Abort with findings if the repo is mid-merge or
   mid-rebase.
2. Merge into the target repo's `.claude/settings.local.json` (create if
   missing, preserve existing keys):
   - `permissions.allow` += `"Bash(tmux:*)"` (the exact blocker a first run hit).
   - Hooks that drive the status files. Each entry runs the same command
     (hook commands already run through a shell):

     ```
     [ -z "$ORCH_TASK" ] && exit 0; exec python3 "$HOME/helm/03-rai/skills/orchestrator/scripts/orch-status-hook.py"
     ```

     Register it under `UserPromptSubmit`, `PreToolUse` (matcher `*`),
     `Stop`, `Notification`, and `SessionEnd`. The guard clause makes it a
     ~2ms no-op for every non-worker session in the repo.
3. Note which gitignored files the project needs at runtime (`.env`,
   local configs). They are copied into each worktree at spawn.
4. Ignore `.agent/` through the exclude file, which every worktree of the
   repo shares. This one line adds it only when `.agent/` is not ignored
   yet, and also works when `.git` is a file:

   ```
   git -C "$REPO" check-ignore -q .agent/ || { x=$(git -C "$REPO" rev-parse --path-format=absolute --git-path info/exclude); mkdir -p "${x%/*}"; echo .agent/ >> "$x"; }
   ```

   Create the run dir skeleton and write `log.jsonl` line
   `{"event":"run_start"}`.

## Phase 1: plan

**SDD repo.** The approved `plan.md` is the plan; do not re-split it.
1. The tasks are one wave, as step 2 of
   [`compile`](../compile/SKILL.md#1-sdd-mode) defines it. It starts at
   the group `mise run status` names next and stops before the first
   `parallel: no` or `risk: high` group, minus groups already done. Each
   group becomes task `g<n>`. With fewer than 2, there is nothing to run
   in parallel: spawn nothing and end as the last list of Phase 7 says.
   Groups after the wave wait for `/compile`, which runs them in plan order.
2. Brief per group: Problem = the group's scenario IDs with their full
   scenario text, plus the Why and Decisions of `requirements.md`. Files to
   modify = its `Files:` line plus its own scenarios. Acceptance = every ID
   has a tagged test that went red, then green, and `mise run verify` is
   green. Verification = `mise run tdd -- green <ids>` and `mise run verify`.

**Elsewhere.**
1. From a plan file (`.agent/plan.md` or `.agent/plan-<slug>.md`): one wave
   by the same rule over its unticked groups, each task `g<n>`. From the
   user's prompt: break it into tasks. For each task draft a brief
   (template below). The **Files to modify** list is the ownership
   boundary.
2. Independence test: any two tasks sharing a file go in different waves.
   Order waves by dependency: contracts > core logic > consumers > tests > docs.

Then, both modes:
3. Write `plan.md`: task table (task, goal, files, wave, est. timeout),
   wave order, merge order.
4. **PLAN GATE** (default ON): show the table, wait for OK. Skipped only if
   the user said "full auto" at invocation.

### Brief template (`briefs/<task>.md`)

```
# <task-id>: <title>
## Problem
<what and why, with concrete evidence: paths, line refs, current behavior>
## Deliverable
<one paragraph, observable outcome>
## Files to modify
<explicit list; touching files outside it needs an inbox question first>
## Hard constraints
<DO NOT list: no push, no merge, no deps without asking, project rules.
SDD repo: follow .claude/skills/sdd/compile.md for this group's IDs only;
never edit roadmap, mission, other groups' scenarios or project_memory/;
a lesson or ADR goes in the report and the orchestrator commits it>
## Acceptance criteria
<numbered, each mechanically checkable>
## Verification
<exact commands whose exit codes prove the criteria>
```

## Phase 2: spawn (per task, staggered 2-3 at a time)

```bash
REPO=/path/to/repo; SLUG=<slug>; INT=<int>; TASK=g1; RUN=.agent/orchestrator/<run-id>
WT=$(dirname $REPO)/$(basename $REPO)-$SLUG--$TASK
# SDD repo: I8's --parallel exception makes feat/<slug>--g<n> off feat/<slug>'s committed tip
(cd $REPO && mise run change -- $SLUG--$TASK --parallel) && git -C $REPO worktree add "$WT" "$INT--$TASK"
# elsewhere:
git -C $REPO worktree add "$WT" -b "$INT--$TASK" "$INT"
cp -r $REPO/.claude "$WT/" 2>/dev/null  # settings.local.json is untracked: worktrees don't inherit it
cp $REPO/.env "$WT/" 2>/dev/null        # + whatever Phase 0 noted
(cd "$WT" && mise trust)                # SDD repo: a new path is untrusted to mise
S="wk-$(basename $REPO)-$TASK"
tmux new-session -d -s "$S" -c "$WT" -x 220 -y 50
tmux send-keys -t "=$S:" \
  "ORCH_TASK=$TASK ORCH_RUN_DIR=$REPO/$RUN claude --model claude-opus-5 --effort high --dangerously-skip-permissions" Enter
sleep 15
tmux capture-pane -t "=$S:" -p | tail -25   # verify boot
```

In an SDD repo, `change --parallel` refuses a group that is not `parallel: yes`
in the approved `plan.md`, and a worker branch that exists already. Surface a
refusal on the group; never fall back to `git worktree add -b`.

With no tmux server running yet (`tmux ls` fails), the first `new-session`
starts one. John's tmux.conf has tmux-continuum restore on, so his
saved sessions come back into that server. They are his: leave them
running, and name them in the report.

**Resume.** A worker branch `<int>--<task>` that exists already is left
over from an earlier run of this wave, one that stopped before its
teardown. `/compile` step 2 sends you here when it finds one and that
run's dir has no `report.md`.
- Phase 0 runs as usual, except the end of its step 4: make no new run
  dir. Reuse the run dir `/compile` read, the last of `ls -d
  .agent/orchestrator/????????-????-<slug>/` (elsewhere: of `ls -d
  .agent/orchestrator/*/`), with its briefs and `log.jsonl`. Append
  `{"event":"resume"}` to that log. Workers launched before the stop
  write their status, inbox and DONE files there.
- No such run dir: the branches are not an orchestrator run's, since a
  human may split the groups by hand. Name each branch with its
  worktree path to John and stop.
- Run no `change --parallel` and no `worktree add -b` for those
  branches. The tasks are those branches: skip Phase 1's wave rule and
  the PLAN GATE, which passed before any worker branch existed.

Then per task, the first match wins:
1. Its group is done on `<int>`. In an SDD repo, none of its IDs is in
   the list `mise run spec-check` prints. With a plan file, its boxes are
   ticked. It merged already: run the test suite as Phase 5 does after a
   merge. Only its own merge is skipped. Phase 5's "After the last wave"
   still runs once every task has merged, before Phase 6 tears it down.
2. `done/<task>.DONE` exists: go to Phase 4.
3. Otherwise the worker still owns it. Reuse its worktree as it stands,
   with its commits and edits: the path `git worktree list` shows for the
   branch (a listed path that is gone: `git worktree prune` first). Only
   when none is listed, add one without `-b`, `git worktree add "$WT"
   "$INT--$TASK"`, then the copies and `mise trust` above. A live session
   (`tmux has-session -t "=wk-<repo>-<task>"`) is the worker still at it:
   go to Phase 3. With no session, start one in the worktree as above.
   Send the worker prompt with one more line: "Your earlier commits and
   edits on this branch are work so far. Continue from them."

Boot dialogs, in order of appearance, each detected via capture-pane:
- Folder trust ("Do you trust the files"): send `Enter` (accept).
- Bypass-permissions warning: select accept (send `Down` then `Enter`),
  re-capture to confirm the REPL prompt is up.

Prompt delivery (the three proven idioms, never deviate), with `P` the
exact pane target `=wk-<repo>-<task>:`:
- Single line: `tmux send-keys -t P -l 'TEXT'` then `sleep 1` then
  `tmux send-keys -t P Enter` (twice if a menu may be up).
- Multi-line: `tmux load-buffer -b b -` from stdin, `tmux paste-buffer -p -d -b b -t P`,
  then separate Enter.
- Verify submission: `tmux capture-pane -t P -p -S -30 | grep '❯'`.

Worker prompt (adapt, keep every clause):

```
Read <RUN>/briefs/<TASK>.md now. Work ONLY inside this worktree, only on the
files the brief lists. Full autonomy: never wait for approval, never ask the
user. If genuinely blocked, write {"question","context","blocking":true} to
<RUN>/inbox/<TASK>.json with the Write tool and continue anything unblocked.
Commit completed work with conventional messages. Never push, never merge,
never touch the default branch or <int>. When ALL acceptance criteria pass: write
<RUN>/reports/<TASK>.md (files changed, commands run, full verification
output), then as the LAST action run: touch <RUN>/done/<TASK>.DONE. Do not
create it earlier.
```

In an SDD repo, add: "Follow .claude/skills/sdd/compile.md for the IDs in
your brief only. `mise run status` names the change's next group, which
may be another worker's: ignore it and build the group in your brief.
Never edit specs/roadmap.md, specs/mission.md, another group's scenarios
or project_memory/; put a lesson in your report instead."

Before reusing any session for a new task: `rm -f` its stale DONE marker.

## Phase 3: monitor

Signal priority: status files (hook-written) > DONE markers > inbox >
capture-pane (fallback only).

Status semantics: `working` (prompt submitted / tool running), `idle` (turn
ended), `waiting` (notification fired: needs input), `exited`.

Cadence, adaptive: ~30s when any worker is stuck or waiting, ~120s normal,
~300s when all idle. Poll in-turn: never background the watcher, because
turn-exit reaps it. Loop `scripts/orch-poll.sh <run-dir> <repo>` + `sleep`,
each Bash call under 10 minutes, and repeat calls while workers run. Show
the user the poll table whenever a task changes state (running status,
not silence).

Interventions:
- **Inbox question**: answer with a decision, into the pane (idioms above).
  Log the Q and A to `log.jsonl`.
- **Stall** (status file untouched 3+ normal intervals AND pane looks idle):
  send a targeted diagnostic: "Status check: what are you blocked on, one
  paragraph. If nothing, continue the brief." Never a bare Enter.
- **capture-pane fallback rules**: strip ANSI
  (`sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g'`). A visible spinner ALWAYS overrides
  an apparently idle prompt. A queued-message block above the spinner is
  still working (a known false-negative trap). A "paste again to expand" line
  is a collapsed-paste display artifact, not a stall.
- **Rate limited**: normal state, not an error. Wait it out, then send:
  "That failure was TEMPORARY rate limiting, not a bug. Run the exact same
  command again." (Exact wording matters: otherwise the worker invents a
  workaround.)
- **Crashed/exited session**: relaunch claude in the same pane, with
  `--resume` if a session id is known. Otherwise start fresh and re-prompt,
  pointing at the brief and existing commits. Plan state lives on disk;
  nothing is lost.
- **Timeout** (per-task, from plan.md): capture the pane tail and mark the
  task failed-timeout in the report. Do NOT tear down its worktree; surface it.

## Phase 4: review (orchestrator = the only reviewer)

Trigger: DONE marker appears. Never trust it:
1. Run the brief's Verification commands yourself, in that worktree. Exit
   codes and output are the evidence.
2. `git -C <wt> diff <int>...HEAD` and read the FULL diff against the
   brief: correctness and acceptance criteria only, not style. Check no
   files outside the ownership list changed. In an SDD repo, also check
   that the diff touches no roadmap, mission or `project_memory/` file and
   no scenario outside the group's IDs.
3. Read `reports/<task>.md`; claims without matching evidence count as
   failures.
4. Reject: `rm` the DONE marker, send findings to the worker's pane as a
   numbered list, return to monitoring. Accept: mark reviewed in `log.jsonl`.

## Phase 5: merge (one branch at a time, dependency order)

**MERGE GATE** (default ON): before the first merge of each wave, show what
will merge (branch, commits, diffstat, verification result) and wait for OK.
Skipped only under "full auto".

Per branch, in plan order, with the main checkout on `<int>`:
```bash
git -C $REPO merge --no-ff $INT--$TASK   # refuse to start if the tree is dirty
<run the project's test suite>           # SDD: mise run verify; green before the next branch
```
With tasks from a plan file, tick that group's boxes in the main
checkout's plan file once its merge is green. After each merge, rebase
remaining unmerged branches: in each worktree `git rebase <int>`. On
conflict (merge or rebase): abort the operation, hand the conflict back to
THAT worker's still-open session ("<int> moved, rebase onto it and resolve
the conflict in your worktree, re-run verification, re-touch DONE"),
re-verify on its DONE. Escalate to John
only after the worker fails twice. The orchestrator never resolves
conflicts itself.

After the last wave:
- **SDD repo:** commit the lessons and ADRs from the worker reports
  (`project_memory/lessons.md`, `project_memory/decisions/`) on
  `feat/<slug>`, in one commit. Leave out any that `feat/<slug>`
  already holds: a resumed run may have made this commit before it
  stopped. Landing on main is the human's `! mise run merge`, never this
  run's.
- **Elsewhere, standalone, on a `feat/<slug>` this run created:** a final
  MERGE GATE shows it against the default branch. On OK, merge it, or open
  a PR when the repo is PR-only. On a branch that existed before the run,
  stop: landing it is John's call.

Then teardown (Phase 6) and the report (Phase 7), which ends the run.

## Phase 6: teardown (only after a task's branch is merged and green)

```bash
~/helm/03-rai/skills/orchestrator/scripts/orch-teardown.sh <repo> <worktree> <int>--<task> <tmux-session>
```
The script refuses on uncommitted/untracked/unpushed work, and on a branch
not merged into the repo checkout's HEAD (the integration branch). It also
refuses to kill the caller's own tmux session. A refusal is surfaced to
John, not overridden.

## Phase 7: report

Write `report.md` in the run dir: one row per task (task, goal, worktree,
branch, status, commits, verification result, merge result). Add a short
outcomes narrative: deviations, rejected DONEs, conflicts, anything alive.
Print the table. The run dir stays uncommitted scratch.

The run stops here. What comes next depends on who started it:
- **Started by `/compile`** (either mode): print no hand-back line.
  `/compile` goes on at its step 1 in this same session: the next group,
  or validate.
- **Started on its own, over an SDD change or a plan file:** hand back
  "run `/compile`". It resumes at the next group without passing tests
  (SDD) or the first unticked group (plan file).
- **Started on its own, over tasks from the prompt:** the report is the end.

## Examples

- `/compile` in an SDD repo with 3 disjoint `parallel: yes` groups offers
  this skill. The plan gate shows g1-g3 as one wave, merged into
  `feat/<slug>`. After the report, `/compile` goes on in the same session.
- `/compile` in a fresh session after that run died mid-wave. It finds
  the `feat/<slug>--g<n>` branches and resumes this run over them (Phase
  2, Resume) instead of asking again.
- `/orchestrator ship these 4 fixes in ~/projects/<repo>: <list>` : plan gate,
  4 briefs, 1-2 waves, merge gate per wave, final gate for main.
- `/orchestrator full auto: migrate the 3 collectors to the new client` :
  all gates skipped, report at the end.
- `/orchestrator status` mid-run: print the poll table + inbox summary.
- `/orchestrator abort t3` : capture t3's pane tail, kill its session,
  teardown (guard still applies), mark aborted in the report.
