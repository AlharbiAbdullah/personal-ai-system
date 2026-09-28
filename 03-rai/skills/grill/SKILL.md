---
name: grill
description: >
  Talk step of the pipeline: pressure-test a feature request, bug report or PRD through
  question rounds BEFORE any code exists, then lock the answers into a spec. In a repo with
  .project.toml it follows the repo's .claude/skills/sdd/talk.md (scenarios + change folder)
  with Rai extras; elsewhere it writes .agent/decisions.md and .agent/plan.md. USE WHEN the
  user types /grill <task> or starts a substantial engineering task whose assumptions need
  interrogating first. Never writes code. The build step is /compile.
---

# Grill

Interrogate the task until its decisions, dependencies, assumptions and failure modes are settled. Then write them where the build step reads them. Grill writes specs, never code.

**Pipeline:** `/grill` → `/spec-improve` (optional) → approval → `/compile` (which runs `/adversarial-review`).

**Single-agent mandate:** run inline. Never use the Agent or Workflow tools.

## 0. Pick the mode

Find the root with `git rev-parse --show-toplevel`.
- **SDD mode:** `.project.toml` sits at that root. The repo's own skill text is the authority. This file only adds the Rai extras.
- **Plan mode:** anything else (helm, a one-off repo, no repo).

## 1. SDD mode

Read `.claude/skills/sdd/SKILL.md` and `specs/README.md` once per session. `<default>` below is the `default_branch` of `.project.toml`.

1. **Open or continue the change.** Follow "Start a change" in `sdd/SKILL.md`: status, classify out loud, slug, `mise run change`. A plan lane runs the check under **plan** below before `mise run change`.
   - **A change is already open.** On its lane branch, status names it (`lane <lane> | change ...` or `lane <lane> | no change folder`). On `<default>`, status says `no open change` even so, and `mise run change` refuses with `I8: a change is open (<branch>)`: treat that refusal the same way.
     - **Reach it** before continuing it from `<default>`: `git switch <branch>`, with the branch the refusal names (when it names more than one, ask which one). When git answers `already used by worktree at '<path>'`, the change is checked out there. Name `<path>` to John with "run `/grill` there", and stop.
     - The request is that change: it names its slug, adds to its spec or answers its open questions. Reach it, then continue it on its lane below. An open feat change at `status: approved` is past grilling: say "run `/compile`" and stop.
     - Any other request that needs a lane waits, as step 1 of "Start a change" says. Ask one question, with option 3 only when the request classifies as fix:
       1. Continue the open change first: reach it and go on with it as the bullet above says. The request waits, unrecorded.
       2. Park the request: `mise run backlog -- <topic>`, then fill What, Why and Notes. On the open lane branch, commit that file alone, as `/compile` does for a parked idea: `git add specs/backlog/<file>`, then `git commit -m "spec(backlog): <topic>" -- specs/backlog/<file>`. On `<default>`, leave it untracked for the next change. Stop.
       3. Hotfix: `mise run change -- <slug> --lane fix --hotfix` opens `fix/<slug>` in a sibling worktree off `<default>`, and the open change stays untouched. Run `mise trust` there, then grill it there as the fix lane below.

       Mark 3 as (Recommended) when users are hit now, and 2 otherwise.
     - A backlog or spike request needs no lane: its bullet below applies.
   - **feat:** go on to step 2.
   - **plan** (replan or pivot): `mise run change` enforces two parts of the Precondition in `sdd/replan.md`: it refuses while another change is open or the tree is dirty. It does not check the third, that the default branch is up to date, so check that first, on `<default>`:
     - No `origin` remote (`git remote get-url origin` fails): the local branch is the only copy, and there is nothing to compare.
     - Otherwise run `git fetch origin <default>`, then `git rev-list --left-right --count <default>...origin/<default>`. `0 0` is up to date. `0 N` is behind: run `git pull --ff-only origin <default>`, a sync the gates allow for merged work. Ahead, diverged, or a refused pull: stop and show John, because only merge moves the default branch. A refused pull has already written origin's files into the tree and the index, so show `git status` with it.

     Then run `mise run change`, and skip the Precondition: running its command again would be refused. Follow `replan.md` from Inputs to Close, with steps 2 and 4 below as extras. Its Close ends the run: steps 3, 5 and 6 are for feat only.
   - **fix, chg, chore, refactor:** these lanes have no change folder. Confirm the lane, the intent and the scenario IDs it touches (chore and refactor touch none) in one round. Write them to `.agent/lane-<slug>.md` (gitignored scratch), so `/compile` in a fresh session starts from them. Then say "run `/compile`", in the hotfix worktree for a hotfix. Stop.
   - **backlog, spike:** as `sdd/SKILL.md` says. Stop.
2. **Vault intake** (Rai extra), before the first question. Read only, never write:
   - `~/helm/05-projects/{kitchen,active}/<name>/`, where `<name>` is the repo folder name;
   - the idea note: `grep -l '^spawned:.*<name>' ~/helm/09-ideas/*.md`;
   - `/recall <name> <topic>` hits. They are hints to check against the repo, and the repo wins.

   Anything carried into the repo is sanitized as project-init P2 does it ([Sanitize](../project-init/phases/2-talk.md#sanitize-before-anything-is-written)). No vault paths, wiki-links or personal tooling reach a tracked file.
3. **Talk.** Read `.claude/skills/sdd/talk.md` and follow its sections 1 to 5: evidence, decision rounds, capabilities, the three change files and the checks. Step 4 runs inside its section 2, before its section 4 writes any file. Its section 6 runs at step 6 below.
4. **Extra rounds** (Rai extra), inside the decision rounds: talk's section 2, or the rounds of `replan.md`. After the first round (Scope, Decisions, Context and Rollback in talk) and before anything is written, keep pressure-testing:
   - failure modes and partial failure;
   - hidden coupling to code the change does not name;
   - a success signal nobody can measure;
   - assumptions no test covers;
   - the inputs Review focus should name.

   Each round keeps talk's form: at most 3 questions, each with one (Recommended) option. Talk's cap of 4 rounds gives way while John is answering and asks to go on. What he declines to settle becomes a `[NEEDS CLARIFICATION: ...]` marker.
5. **Before approval** (Rai extra). Run `mise run status`.
   - `not ready for approve`: status prints only the first 5 problems, so read the full lint, `mise run spec-check -- --change <slug>`. Fix every problem it lists except the `[NEEDS CLARIFICATION ...]` markers, then run the lint again.
     - Markers remain: each marker line names a file and its first marker line, with `(+N more)` when there are others. `rg -n 'NEEDS CLARIFICATION' <file>` lists them all. List each open question with its file and line. Say "answer these, then `/grill` again". Stop. The next `/grill` continues the draft (step 1).
     - None remain: run `mise run status` again.
   - `ready for approve`: ask one question.
     1. `/spec-improve`: one Ousterhout and spec-lint pass over the change folder.
     2. `/visual plan`: the change folder rendered to `.agent/visual/<slug>.html` for review.
     3. Neither: approve it as it stands.

     Mark 1 as (Recommended) when the plan has 3 or more groups or a `risk: high` group, and 3 otherwise. Run what he picks by reading that skill's file and following it, up to its own hand-off. Step 6 takes the place of that hand-off, and it stops at the same approval gate.
6. **Hand off.** Follow section 6 of `talk.md` for a feat change in full, naming `/compile` where it says `/sdd compile`. Stop.

## 2. Plan mode (no `.project.toml`)

### 2.1 Stage check

- **The pair** is `.agent/decisions.md` and `.agent/plan.md`, at the repo root. Run the commands below from there.
  - It exists for this task: continue it. The user is adding scope.
  - It exists for another task: leave it untouched. Name this task's pair `.agent/decisions-<slug>.md` and `.agent/plan-<slug>.md`.
  - Never rename, move or overwrite another task's file under `.agent/`.
- **No repo** (`git rev-parse` fails): the pair goes in `.agent/` under the current folder. There is no exclude file, so the rule below does not apply.
- **Scratch or record** (in a git repo).
  - The repo tracks nothing under `.agent/` (`git ls-files .agent` prints nothing): the pair is scratch, never committed. Ignore `.agent/` through the exclude file. This one line adds it only when `.agent/` is not ignored yet, and also works in a linked worktree, where `.git` is a file:

        git check-ignore -q .agent/ || { x=$(git rev-parse --path-format=absolute --git-path info/exclude); mkdir -p "${x%/*}"; echo .agent/ >> "$x"; }

  - The repo already tracks files under `.agent/`: they are records. Helm is this case, because its doctrine ignores nothing and brain files cite `.agent/decisions.md`. Add no exclude there, and never delete or untrack a file.

### 2.2 Evidence before questions

Inspect the files first: `rg` for the touched code paths, `git log` for recent history in a repo, existing tests, manifests and configs. Never ask a question the code already answers. Summarize your understanding in 3 to 6 bullets before the first question.

### 2.3 Rounds: no code, no solutions

- At most 3 questions per round: AskUserQuestion in Claude Code, numbered options elsewhere.
- Each question offers 2 or 3 options. Exactly one is (Recommended), with a one-clause reason. Say what breaks if it is assumed wrong.
- Resolve upstream first: goal, users and success signal, then architecture, data flow, operations and risks, then testing.
- Probe ambiguity, hidden coupling, vague success signals and untested assumptions. Follow-up rounds are fine when answers open new branches.
- Stop and wait for the answers. Draft nothing meanwhile.

### 2.4 Write the decisions file

Once every branch is settled or its risk explicitly accepted, write:

    # Decisions: <task>
    Date: YYYY-MM-DD

    ## Scope
    - In: <what this task covers>
    - Out: <what it leaves alone>
    ## Decisions
    - <decision>. Rejected: <option>, because <reason>.
    ## Context
    - <constraint, pattern to follow, file pointer>
    ## Assumptions accepted
    - <assumption>: <the risk John accepted>

One decision per bullet, each an answer from the rounds. No checkboxes: `/compile` and `/adversarial-review` hold the work to these bullets.

### 2.5 Write the plan file

Write the file directly, never inside an outer code fence:

    # Plan: <title>
    Date: YYYY-MM-DD | Decisions: <path of the decisions file>

    ## Purpose
    <what and why, one short paragraph a newcomer can act on>

    ## Hard constraints
    <carried verbatim from the decisions file, never relaxed silently>

    ## Acceptance criteria
    - Given <state>, when <action>, then <outcome>   (each checked by a named command or test)

    ## G1 <name> | risk: low|high | parallel: yes|no
    Files: <paths; NEW marks a file that does not exist yet>
    - [ ] <task: file path and expected behaviour>
    Verify: <command whose exit code proves this group>

The group header is the SDD `plan.md` header without scenario IDs, so `/compile` and `/orchestrator` read both alike. The task boxes are execution state that `/compile` ticks. The plan has no narration sections (progress, surprises, logs). Reality that contradicts it stops the build and goes to John.

**Plan rules:**
- **Newcomer-executable.** Each task stands alone, with no "as discussed". Every path and symbol exists or is marked NEW.
- **Grounded.** Read the code the plan touches first: callers, module boundaries, tests, duplicated concepts, special cases.
- **Ordered by dependency.** Each group takes under half a day and is proved by its own `Verify:`, never by one big check at the end.
- **Outcomes, not mechanisms,** in acceptance criteria: "p95 under 50 ms", not "use Redis".
- **Flags.** `risk: high` on anything hard to undo: data migrations, security, money, public interfaces. `/compile` pauses after such a group. `parallel: yes` only for groups whose `Files:` are disjoint.
- **Reject in your own draft:** existing complexity kept under new names, and thin wrappers with no abstraction value. Reject too any choice deferred to the implementer that evidence can settle now, and any reopened decision.

### 2.6 Hand off

Ask the question of SDD step 5 (`/spec-improve`, `/visual plan` or neither), with the same (Recommended) rule, and run the pick the same way. Then close by naming both paths: "decisions at `<path>`, plan at `<path>`. Say go, or run `/compile`." For a slugged pair, the command is `/compile <slug>`. Stop.

## Examples

- `/grill add rate limiting to the ingest API`
- `/grill` with a pasted PRD
- `/grill intermittent 500s on upload`: in an SDD repo this classifies as fix, opens `fix/<slug>`, writes `.agent/lane-<slug>.md` and hands over to `/compile`.
- The same request while `feat/<other>` is open: it asks continue, park or hotfix, with hotfix (Recommended) when uploads fail for users now.
