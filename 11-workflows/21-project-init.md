# Project Init and Build

**Use when:** a repo is on the spec-driven, test-driven standard, or joins it. Setting up a new folder or an existing repo with `/project-init`: a new project, adopting a repo, upgrading or migrating one. Checking a repo against the project-init standard. In a set-up repo: a feature, a fix, a replan, a launch or a release.
**Not for:** 01 project, for the idea, the kitchen and the close of a product. 02 task, for a repo without `.project.toml`: the helm vault, a script, and every repo today. 23 audit, for a repo's architecture or code health. 06 shipping, for the deploy itself. 29 air-gapped delivery, for a sealed target.
**Done when:** the run reached its human gate and the human passed it. Init: G1 merged, `mise run verify` green, punch list read. Feature: G3 merged, next roadmap item printed. Launch: the item's roadmap line ends `(launched <date>)`. Replan: its `plan/` branch merged. Release: the tag exists.

One playbook from an empty folder or an existing repo to a spec-driven, test-driven build. `/project-init` sets the repo up once. After that, every change runs one loop with human gates. The repo's own `specs/README.md` is the rulebook for lanes, formats and gates. This playbook orders the skills around it and never restates its tables.

`main` below means the repo's default branch, `default_branch` in `.project.toml`. Init renames `master` to `main` only when there is no remote. A repo with a remote keeps its default branch, and a `master` rename goes on the punch list.

---

## When to use

| You have | Start at |
|---|---|
| an idea in `09-ideas/`, no repo yet | Phase A: [[01-project]], then Phase B |
| a kitchen folder in `05-projects/kitchen/<name>/` | the exit check in [[01-project]], then Phase B |
| an empty folder, or a repo with no `.project.toml` | Phase B |
| a repo on project-init v2 (`Standard: project-init v2` in `project_memory/README.md`) | Phase B (upgrade) |
| a repo with `.project.toml`, to check it against the project-init standard or fix drift (EXTEND) | Phase B |
| a repo with `.project.toml` | Phase C for a change, F for a launch, D for a replan, E for a release |
| a product whose work is done | the close in [[01-project]] |

Not for the helm vault or a one-off script. Those have no `specs/` and take the plain route in [[02-task]]: `/grill` writes a decisions and plan pair under `.agent/`, and `/compile` carries the plan out. In a code repo that doesn't track `.agent/`, the pair is scratch that `/grill` keeps out of git. In helm, `.agent/` files are tracked records: never exclude or delete them.

---

## The whole flow

```d2
direction: down

vault: "Vault (Rai only)" {
  idea: "09-ideas/<name>.md\n(Tree)"
  kitchen: "05-projects/kitchen/<name>/\nspecs/ + research/"
  idea -> kitchen: "/ideas → graduate"
}

init: "/project-init\nSCAFFOLD · ADOPT · EXTEND · MIGRATE\npreflight, probe, talk, generate, verify"
branch: "branch plan/project-init\nspecs/: mission, tech-stack, roadmap,\ncapabilities/<entry>.md + the standard"
g1: "G1\n! mise run merge" {shape: hexagon}

loop: "Feature loop: one change at a time" {
  talk: "/grill \"<what you want>\"\nlane, scenarios, change folder"
  g2: "G2\n! mise run approve" {shape: hexagon}
  compile: "/clear, then /compile\nred, green, commit per group"
  validate: "validate\nlenses + merge preview"
  g3: "G3\n! mise run merge" {shape: hexagon}
  talk -> g2 -> compile -> validate -> g3
  talk -> compile: "fast lanes skip G2" {style.stroke-dash: 3}
  g3 -> talk: "next roadmap item"
}

launch: "Launch\n/compile launch <slug>\naudit, checklist, flag off"
replan: "Replan\n/grill \"replan\" on plan/<date>-replan\nends at ! mise run merge"
release: "Release\n! mise run release -- <bump>"

vault.kitchen -> init: "talk source 1"
vault.idea -> init: "no kitchen" {style.stroke-dash: 3}
init -> branch -> g1 -> loop.talk
loop.g3 -> launch: "roadmap item merged"
launch -> loop.talk: "fix lanes, then launch-<slug>"
loop.g3 -> replan: "still right? no"
replan -> loop.talk
loop.g3 -> release: "distributable only" {style.stroke-dash: 3}
```

A `!` command is a human gate. You type it yourself: in Claude Code with the `!` prefix, anywhere else in your own terminal. Rai prints the command and stops. It never runs approve, merge, abandon or release, and never sets `PROJECT_MERGE`.

---

## Domain methods

A method workflow runs inside this loop and never copies its mechanics. [[27-data-pipeline]] and [[31-ai-system-build]] supply the talk questions, the plan groups and the proof rows. Each lists its slots in its own file.

---

## Phase A: before init (the kitchen, optional)

The idea, the kitchen and the choice between a kitchen and a straight init live in [[01-project]] steps 1 to 8. The kitchen has the shape of a repo's `specs/`, so `/project-init` copies it instead of asking again.

- [ ] Look for a kitchen: `ls ~/helm/05-projects/kitchen/<name>/specs/`. One that passes the exit check in [[01-project]] goes straight to Phase B.

---

## Phase B: /project-init

- [ ] An existing repo joins the standard only on his go, given for each repo.
- [ ] For a new product, `mkdir ~/projects/<name>` first. Then `cd` into the folder or repo. Never copy kitchen files in by hand: the init talk reads, copies and cleans them.
- [ ] On an existing repo, `/project-init --plan` first is safe: preflight and probe only, a report, no writes.
- [ ] Run `/project-init`. It detects the mode and never asks for it. The Modes table in the `/project-init` skill is the authority. The short form, in its detection order (the first match is the mode):

| Mode | When | What it adds |
|---|---|---|
| EXTEND | `.project.toml` exists | an audit: unchanged generated files upgrade silently, a customized one shows its diff and asks |
| EXTEND + v2 migrate | the stamp `Standard: project-init v2` in `project_memory/README.md` | one migration prompt listing each v2 file's fate (apply all is Recommended), then the talk fills the gaps |
| MIGRATE | the legacy JSON memory layout (`accumulated_knowledge.json`, `sessions/`, ...) | transcripts go to a local quarantine, are redacted, then archived under `13-archive/historical-sessions/<repo>/`; nothing from them is committed to the repo. The knowledge JSON becomes one backlog report, and the JSON, the v1 hooks and the `.gitignore` block go (`init.py migrate-v1`) |
| SCAFFOLD | an empty folder: no code, no commits | `uv init --package`, the first commit `chore: scaffold <name>` on `main` |
| ADOPT | everything else: existing code on no standard | the probe runs every entrypoint in a scratch clone with no network; each crash becomes a `[gap]` scenario and roadmap Phase 1 |

> **Decision Point**: preflight stops.
> - A dirty tree, an upstream both ahead and behind, or an origin shared with another checkout. Shared means the same URL, or a renamed repo's old URL with the same root commit. Code with no `.git`, or a `.git` with no commits but an `origin`.
> - A repo with no stack pack: v3 ships the Python pack only, so a node repo stops before the talk. This stop prints first. Stopping is Recommended. The other option takes only `specs/` and memory, with no gates, on `plan/project-init`.
> - Each stop is one prompt with 2 or 3 options and one (Recommended). Answer it. Never force past it.

**What the talk asks.** It reads every source before the first question: the kitchen `specs/`, a legacy kitchen (`PRD.md`, `ROADMAP.md`, `BUILD-LOG.md`) or `active/<name>/`, the idea, the repo docs, GitHub issues, lockfiles, the language standard. Then:
- Thin sources open with one free-text prompt: "Tell me about it: who is it for, what hurts today, what does done look like?"
- Decision rounds follow: at most 3 questions per round, 2 or 3 options each, one (Recommended), at most 4 rounds.
- Always settled: the mission one-liner and the distribution.
- The trunk question: the probe proposes the paths every run goes through (entrypoints, shared settings, schema), each with its why. 1. Keep all (Recommended). 2. Edit. 3. Start empty. The answer is the `## Trunk` section of `specs/tech-stack.md`: at every merge, you read the trunk diff and skim the rest.
- The remote question comes only when there is no `origin`. 1. Private GitHub repo, Recommended unless the talk showed a throwaway. 2. Local only, Recommended for a throwaway. The new repo is named after the folder, not the Python package, and the README quickstart then opens with its clone line.
- Anything still open becomes a `[NEEDS CLARIFICATION: ...]` marker. G1 refuses while one remains, so answer them before merging.

**What it leaves.** Branch `plan/project-init` with one commit `chore(init): project-init v3`, holding:
- the constitution in `specs/` (`mission.md`, `tech-stack.md`, `roadmap.md`, `capabilities/<entry>.md`) and `specs/README.md`;
- mise tasks, the git gates, the `sdd` skill and `project_memory/`;
- `AGENTS.md` and the README quickstart, assembled last from commands that ran green;
- CI, when a remote exists.

A tracked `.agent/` is read in the talk and untracked on the branch (D7). A repo with no `.python-version` gets the Python version that builds it, pinned before any `uv add`.

It ends with a punch list of what only a human can do.

- [ ] **G1.** Review the branch: `git diff main...plan/project-init -- specs/ AGENTS.md`. Then type `! mise run merge`. If Claude Code denies the `!` form, run it in a terminal you open yourself. Rai never opens one.
- [ ] Work the punch list, such as `git config --global init.defaultBranch main`, the 1Password items behind the `op://` secrets in `.env.example`, and `mise run proof -- setup web` or `setup terminal` when the probe found a web or terminal UI.
- [ ] `/clear` before the first feature.
- [ ] Vault, after G1:
  - Move `kitchen/<name>/research/` to `05-projects/active/<name>/research/` if it holds anything worth keeping.
  - Delete `kitchen/<name>/`. The repo's `specs/` is now the one copy of mission and roadmap, and a second copy drifts.
  - `active/<name>/` holds non-code work only: research, meeting notes. Never mission, roadmap or architecture.
  - An older `active/<name>/` with vision, roadmap or architecture files was a talk source. Check that the merged `specs/` holds what they say, then delete them. A later `/project-init` audit flags any that remain.
  - Add the project to `05-projects/projects-moc.md` and point the idea's `spawned:` link at its new home.
  - These vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Phase C: the feature loop

One change at a time. `mise run change` refuses a second one while one is open, apart from a hotfix.

- [ ] `mise run status`: the branch, the open change, the next roadmap item. A change already open? Finish it, or park the new request with `mise run backlog -- <topic>`.
- [ ] **Talk.** `/grill "<what you want>"`. Teammates and other harnesses use `/sdd "<what you want>"`: the same talk text. It classifies the lane out loud (the repo's `specs/README.md#lanes`, first yes wins) and runs `mise run change -- <slug> --lane <lane>`. For a feat it writes:
  - the scenarios in `specs/capabilities/`;
  - the change folder `specs/changes/<date>-<slug>/`: `requirements.md`, `plan.md`, `validation.md`.

  Round 1 of a feat asks four questions: Scope, Decisions, Context and Rollback. Rollback is how the change is undone after merge: `revert: <why>`, `flag: <ENV_NAME>` (the new behaviour behind a flag, off by default) or `one-way: <what>`. A plan group whose files are trunk is `risk: high`. `validation.md` gains `## Proof`: one row per case, in the one kind that shows it best (run, screenshot, video, terminal, http, log, attach).

  It ends with `mise run status` saying "ready for approve".
- [ ] Optional, before G2: `/spec-improve` (one Ousterhout and spec-lint pass over the change folder) and `/visual → plan` (the change folder as an HTML page under `.agent/visual/`; open it yourself).
- [ ] **G2.** Read `validation.md` (Review focus, Proof, Human checks), the Rollback line and the scenario diff (`mise run status -- --change`). Then type `! mise run approve`. Approving `validation.md` approves the test list and the proof list.
- [ ] `/clear`.
- [ ] **Build.** `/compile`. Per plan group: tagged tests, `mise run tdd -- red <ids>` (must fail for the right reason), minimal code, `tdd green`, refactor, `mise run verify`, one commit on green.
  - A `risk: high` group pauses compile. Review `git diff <group-start>..HEAD`, its trunk files first, then `/compile` again to continue.
  - A group whose change shows (output, a page, a terminal session) gets its `## Proof` row captured after its commit: `mise run proof -- <verb> <id> ...`, one commit per capture.
  - 3 or more disjoint groups marked `parallel: yes`: `/compile` offers `/orchestrator`. Workers merge into `feat/<slug>`, never into `main`. Its tmux workers need his explicit permission rule first: without one, the classifier blocks them.
- [ ] **Validate.** `/compile` runs the lenses for the lane after the last group, each as the `reviewer` agent. The lenses: conformance, breaker and test honesty for feat, breaker only for chg and fix. It captures every `## Proof` row still missing, a confidence line per group and the test proof, and renders `.agent/proof/<date>-<slug>.html` (`mise run proof -- show`). It ends with `mise run status -- --merge`, the full Definition of Done preview. Rai extra: `/fusion → review`, a panel of other models on the branch diff. Its out-of-scope findings go to the backlog.
- [ ] **G3.** Open the proof page first, low confidence lines at the top. Then type the command on the last line of the merge preview (`mise run status -- --merge`). Plain `! mise run merge` needs no flag. `--read-trunk` says you read the trunk diff, which the preview prints in full: read it line by line, and skim the rest against the proof. `--attest` confirms Human checks or `Test-Harness:` diffs, because the `!` path has no TTY: in your own terminal, `mise run merge` asks each check, and the trunk diff, y/N instead. `--gate-change` accepts a gate-file diff or a Trunk entry removed or changed. `--reapprove` accepts an approved Human check, Run-it row or Proof row that changed since G2. Merge runs verify and prove-red, checks the proof, ticks the roadmap, regenerates `CHANGELOG.md`, squashes onto `main` and prints the next item with "still right?". With a remote, the PR body shows the proof inline. A `flag:` change also leaves the launch item in the backlog.
- [ ] `/clear`. Next item: back to the top of this phase. "Still right?" is no: Phase D. A roadmap item whose work has all merged is launched in Phase F.

**Other lanes:**
- **fix, chg, chore, refactor:** no change folder and no G2. The talk opens the lane branch. `/compile` runs red first where behaviour moves, then the lane's lenses (breaker for fix and chg, none for chore and refactor). G3 merges. A fix lane's diagnosis follows [[04-debugging]] steps 1 to 4 before the talk.
- **Spike** (you want an answer, not code): `mise run backlog -- <topic> --spike`. It gives a scratch worktree; only the findings land, as a backlog file.
- **Hotfix while a feature is open:** `mise run change -- <slug> --lane fix --hotfix` opens a sibling worktree off `main`. Land it with `! mise run merge -- --branch fix/<slug>`, then `git merge main` on the feature branch.
- **Abandon:** `! mise run abandon -- "<why>"`. The branch is tagged `abandoned/<slug>` and a backlog report lands on `main`.

> **Decision Point**: the spec turns out wrong mid-build.
> - A detail: scenario, test and code change in one commit. Merge shows it as "amended after approval".
> - Materially wrong: compile stops and asks, and never replans on its own. You choose one of two.
>   1. The correction goes in as scenario, test and code in one commit. Merge lists it as amended after approval. (Recommended: the finished groups are kept, and G3 lists every amended scenario before the merge.)
>   2. `! mise run abandon -- "<why>"`, then a new talk.

> **Decision Point**: a new idea comes up mid-feature.
> - `mise run backlog -- <topic>`. Never edit the roadmap from a feature branch.
> - A chg that grows past Q7 in the repo's `specs/README.md#lanes`: `mise run change -- <slug> --lane feat` upgrades it in place. Lanes only get heavier.

---

## Phase D: replan between features

**When:**
- merge asked "still right?" and the answer is no;
- `mise run status` reminds you: 5 or more open backlog items, or 3 features merged since the last replan;
- a feature showed that the roadmap, a standing rule or the process is wrong;
- the product pivots.

- [ ] Clean break: no open change (merge or abandon it first), a clean tree, `main` up to date.
- [ ] `/grill "replan the roadmap"`. When who, why or scope changes, `/grill "pivot: <what changes>"`. It classifies the plan lane, runs `mise run change -- <date>-replan --lane plan` (`<date>-pivot` for a pivot) and follows the repo's `.claude/skills/sdd/replan.md`, adding vault intake and extra rounds. Teammates and other harnesses: `/sdd replan`, the same text without the Rai extras.
- [ ] The talk summarizes the roadmap, the open backlog, lessons since the last replan and open gaps, then asks decision rounds. `replan.md` lists what a replan may change. In short: it changes what comes next, never what is merged, and writes no code, tests or scenarios. `mission.md` changes only in a pivot, or for a constraint that is a product promise.
- [ ] `mise run verify`, then `mise run status -- --merge`, then type the command on its last line, as at G3. When it would land a parked idea (`lands as 'spec(backlog): ...'`), add `--title 'spec(replan): <what changed>'`.
- [ ] `/clear`. The first item of the new roadmap starts Phase C.

> **Decision Point**: the process fix is for this repo only, or for every repo?
> - This repo: edit `specs/README.md` or `.claude/skills/sdd/` on the replan branch. The next `/project-init` audit shows the file as customized and asks.
> - Every repo: fix the template under `03-rai/skills/project-init/templates/` in the vault. Then re-run `/project-init` in each repo, and EXTEND upgrades the unchanged copies.

---

## Phase E: release

Only for a distributable product. The `## Distribution` line in `specs/tech-stack.md` decides. `none` has no release task: `CHANGELOG.md` still grows with every merge.

- [ ] No open change, and `mise run verify` green on `main`.
- [ ] Pick the bump: `patch`, `minor` or `major`. `mise x -- git cliff --bumped-version` prints what the merged commits imply.
- [ ] Type `! mise run release -- <bump>`. On an internal `release/vX.Y.Z` branch it bumps the version (pypi and git) and writes the version section of `CHANGELOG.md`, merges that branch into `main`, then tags. Then:
  - `pypi`: builds and publishes, with the token from 1Password.
  - `git`: no publish; `gh release create` when a remote exists.
  - `service`: tag and changelog only. The deploy is the next step.
- [ ] `service` only: deploy with the repo's `deploy` skill. Init generates one only for a wrangler config.
  - A compose service, or any target with no `deploy` skill: deploy with [[06-shipping]] step 4.
  - A sealed or offline target: hand the deploy to [[29-air-gapped-delivery]].
  - Before the deploy, write the rollback: [[06-shipping]] step 7.
  - After it, verify live: [[06-shipping]] step 5.
  - Something wrong: a minor fault is a hotfix (Phase C), a major one runs the rollback.
- [ ] An offline bundle stays `service` in `## Distribution`: there is no separate bundle value.

- [ ] Never bump a version, tag or edit `CHANGELOG.md` by hand: `! mise run release` does all three. The gates refuse a hand-staged `CHANGELOG.md` (I2).

---

## Phase F: launch a merged roadmap item

Merge-ready is not launch-ready. Each change passed its own review; the launch reviews the roadmap item as one feature, then its flag comes off. The repo's `.claude/skills/sdd/launch.md` is the procedure.

**When:** `mise run status` on `main`, with no change open, lists the merged items not launched yet, those with a live flag first, and names the next `/sdd launch <slug>`. `mise run doctor` also warns about a flag older than 30 days.

- [ ] On `main`, no open change: `/compile launch <slug>`. Teammates and other harnesses use `/sdd launch <slug>`: the same text without the Rai extra.
  - It collects the item's squash commits and diffs them as one, then runs four lenses as fresh `reviewer` agents: performance, security, conformance and simplicity. Rai extra: `/fusion → review` over the same diff.
  - Every finding gets an outcome: fix it now in a lane of its own, park it in the backlog, or dismiss it with a reason. The launch file `specs/backlog/<date>-launch-<slug>.md` records each one.
- [ ] Each fix lane runs Phase C from the build step and ends at its own G3. After each merge, `/compile launch <slug>` again resumes at the next open finding.
- [ ] **Your checklist.** The launch file holds one for you. Use the feature end to end, with its flag on where one guards it. Open each change's proof, and write down what felt wrong. What you list gets an outcome the same way.
- [ ] **The launch lane.** Once every finding is closed and the checklist ticked, the agent opens it. A flag guards the item: `chg/launch-<slug>`, where the flag, its off path and its `[flag-off]` scenarios go. No flag: `chore/launch-<slug>`, one commit. Either way the launch file goes, and its commit body keeps the record.
- [ ] G3 as usual. Merge appends `(launched <date>)` to the roadmap item, and `mise run status` stops listing it.

> **Decision Point**: status lists items that shipped before v3.1.
> - They were never launched by this process. Mark them in the next replan (Phase D): add ` (launched <date>)` to each line. (Recommended when they have no flag and nothing to audit.)
> - Or launch each one: the audit runs on its old changes too.

---

## What gets updated when

The full answer lives in each repo, rendered from `03-rai/skills/project-init/templates/specs-README.md`:
- `specs/README.md#adding-a-feature-what-changes`: the artifacts of a new feature.
- `specs/README.md#every-change-type`: every change type against every file.

The one-line answer: **new feature: mission no, roadmap ticked by the tool at merge, capabilities and tests always, proof in `proof/` for every feat. Its launch marks the roadmap item `(launched <date>)`.**

---

## Stop conditions

- **A human gate is next** (G1, G2, G3, abandon, release): Rai says what is ready, prints the exact command and stops.
- **A gate blocks** (a hook, verify, prove-red): read its message and fix the cause. Never `--no-verify`, never change `core.hooksPath`, never edit `.githooks/` or `scripts/project.py`.
- **prove-red fails for a reason unrelated to the change** (a service the old code needs, a moved module): only the human may type `! mise run merge -- --allow <id> --reason "<why>"`. The reason lands in the squash body.
- **A `risk: high` group finished:** wait for the human's look at its diff.
- **The `!` prefix is denied in Claude Code:** the human runs the gate in a terminal they open. Rai never opens one.
- **MIGRATE:** the quarantine is deleted only after John confirms the archived transcripts.

---

## Sync

- Code repos: `main` moves only through `! mise run merge`, abandon, release or a sync from origin. `/compile` commits on lane branches. Never `/git → commit` onto `main`.
- Vault edits (kitchen, `active/`, the MOC, the idea) follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- The idea, the kitchen and the close: [[01-project]]
- A repo without `.project.toml`: [[02-task]]
- A fix lane's diagnosis: [[04-debugging]] steps 1 to 4
- A service deploy, its rollback and live checks: [[06-shipping]] steps 4, 5 and 7
- A sealed target: [[29-air-gapped-delivery]]
- Domain methods: [[27-data-pipeline]], [[31-ai-system-build]]
- Skills: `/project-init`, `/grill`, `/spec-improve`, `/visual → plan`, `/compile`, `/fusion → review`, `/orchestrator`
- The rulebook in each repo: `specs/README.md`, rendered from `03-rai/skills/project-init/templates/specs-README.md`
