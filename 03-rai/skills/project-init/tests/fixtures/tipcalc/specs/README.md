<!-- specs/README.md: how work happens in this repo. Living; a replan (plan/ branch) changes it. AGENTS.md, the sdd skill and the hook messages link here instead of restating it. -->
# How tipcalc is built

`specs/` holds the product as plain markdown that any person or agent can read, and the tests prove it. This file is the process. It covers the lifecycle, lanes, file formats and gates, up to the Definition of Done.

| Path | Holds | Changes |
|---|---|---|
| `specs/mission.md` | why, who, scope in and out, success, glossary | only on `plan/` branches |
| `specs/tech-stack.md` | runtime, tooling, distribution, standing rules S-n, never-use, environment | on the branch that adds, removes or swaps a runtime dep, tool or rule (I11) |
| `specs/roadmap.md` | phases of `- [ ] slug: title`, Later, Gates | only on `plan/` branches; merge ticks items |
| `specs/capabilities/<cap>.md` | what is true now: requirements and scenarios with stable IDs | with every behaviour change, in the same commit as its test |
| `specs/changes/<date>-<slug>/` | one feat change: requirements, plan, validation | frozen at merge |
| `specs/backlog/<date>-<slug>.md` | ideas, spike findings, abandoned changes | deleted when the work starts or a replan drops it |
| `project_memory/` | decisions (ADRs) and lessons; its README routes each kind of fact | see Formats |

## Lifecycle

```
 SETUP (once, branch plan/project-init)
   constitution: mission.md, tech-stack.md, roadmap.md, capabilities/<entry>.md
   entrypoint crashes found at setup -> [gap] scenarios + roadmap Phase 1
   tooling, gates, this file, AGENTS.md
                   |
  [G1 HUMAN] ! mise run merge            constitution + standard land on main
                   |
                   v
+============================ THE LOOP: one change at a time ==============================+
| /sdd "<what you want>"                                                                   |
|   classifier (#lanes): first yes wins; a lane only gets heavier                          |
|   mise run change -- <slug> --lane <lane>   refuses while another change is open (I8),   |
|                                             except --hotfix (fix lane, own worktree)     |
|  feat lane                                                                               |
|   TALK      question round(s): Scope, Decisions, Context                                 |
|             -> scenarios in specs/capabilities/<cap>.md                                  |
|             -> specs/changes/<date>-<slug>/ requirements.md plan.md validation.md        |
|  [G2 HUMAN] ! mise run approve     approving validation.md = approving the test list     |
|   fresh context (/clear)                                                                 |
|   COMPILE   per group: tagged tests -> mise run tdd -- red <ids> (must fail, right       |
|             reason) -> minimal code -> tdd green -> refactor -> verify -> commit on green|
|             risk: high group   -> compile pauses for your look                           |
|             spec wrong?        -> scenario + test + code in ONE commit                   |
|             new idea?          -> mise run backlog -- <topic>  (never the roadmap)       |
|   VALIDATE  lenses: conformance, breaker, test honesty; ends with                        |
|             mise run status -- --merge (the full Definition of Done preview)             |
|  [G3 HUMAN] ! mise run merge -- --attest    verify + prove-red + DoD + roadmap tick +    |
|             CHANGELOG + squash; prints the next roadmap item, "still right?"             |
|                                                                                          |
|  fast lanes, no change folder:  fix | chg | chore | refactor   ->  [G3] merge            |
|  spike: mise run backlog -- <topic> --spike   scratch worktree; only the findings land   |
+================================================+=========================================+
                                                 | "still right?" = no, 5+ open backlog items,
                                                 | or every 3 merged features (status reminds)
                                                 v
 REPLAN   mise run change -- <date>-replan --lane plan ; /sdd replan
          reorder/merge/split phases, schedule backlog (linked), standing rules, process fixes
          mission.md changes only on plan/ branches (a pivot, or a product-promise constraint)
                                                                           -> [G3] merge
```

- `!` marks a human gate. You type it yourself: in Claude Code with the `!` prefix, anywhere else in your own terminal. Agents never run approve, merge, abandon or release. They stop and ask.
- There are three human gates: `! mise run merge` (G1), `! mise run approve` (G2) and `! mise run merge` (G3).
- `--attest` is needed only when merge has something for a human to confirm (Human checks, or `Test-Harness:` diffs) and there is no TTY (see [Definition of Done](#definition-of-done)).
- `/sdd` is the repo skill in `.claude/skills/sdd/`: `/sdd "<what you want>"`, or `talk`, `compile`, `validate`, `replan`, `status`. An agent without skills reads `SKILL.md` there.
- Everything else is mechanical.

## Adding a feature: what changes

| Artifact | For a new feature | Written by |
|---|---|---|
| `specs/mission.md` | **No.** Mission changes only on a `plan/` branch, for a pivot or a product-promise constraint. | human + talk |
| `specs/roadmap.md` | **Yes, but only the tool touches it**, at merge. It ticks the item, or inserts it as `(unplanned)` if the feature was never scheduled. | `mise run merge` |
| `specs/tech-stack.md` | Only if the feature adds or removes a runtime dependency, a service or a standing rule. The edit goes on the same branch, and merge enforces this (I11). | agent |
| `specs/capabilities/` | **Always.** New or changed scenarios, each with a stable ID. | talk |
| tests | **Always.** Red first, tagged with the scenario ID, and proven red on the old code at merge. | compile |
| change folder | **Always** for the feat lane. | talk |
| ADR (`project_memory/decisions/`) | Only for a choice that later changes must respect. | agent |
| `project_memory/lessons.md` | Only if something surprised you. | agent or human |
| `CHANGELOG.md` | Always, regenerated at merge. | `mise run merge` |
| `specs/backlog/` | Every out-of-scope idea that came up during the work. | agent or human |

## Every change type

Legend:
- **C** = create, **U** = update, **R** = read only, **no** = not touched.
- **tool** = `mise run merge`, `abandon` or `release` writes it. No person or model does.
- **if X** = only when X holds.

| Change type: branch | mission | tech-stack | roadmap | change folder | capabilities (living) | tests | AGENTS.md | ADR | lessons | CHANGELOG | backlog |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **New feature, on roadmap**: `feat/<slug>` | R | U if a dep, service or rule is added or removed | tool ticks | **C** | U: add or modify scenarios | **C** red first, per ID | U if a command changed | C if cross-cutting | C if surprised | tool (`feat`) | C for out-of-scope ideas |
| **New feature, not on roadmap, start now**: `feat/<slug>` | R | same | tool inserts `(unplanned)` and ticks | **C** | same | same | same | same | same | tool | same |
| **Idea, not now**: no branch | no | no | no (next replan) | no | no | no | no | no | no | no | **C** (committed on the current branch; on the default branch it stays untracked until the next change) |
| **Research idea mid-feature**: current branch | no | no | **never** | no | no | no | no | no | no | no | **C** |
| **Spike (you want an answer, not code)**: `mise run backlog -- <topic> --spike` | no | no | no | no | no | throwaway | no | no | C if learned | no | **C** findings report. The scratch worktree `../<repo>-spike-<slug>` is deleted and never merged. |
| **Change behaviour, bounded** (1 capability, 3 or fewer scenarios, no new dep or interface, 1 session): `chg/<slug>` | no | no | no | no (intent in the commit body) | U: scenario edited **in the same commit as its test** (I4) | U: flip the assertion first, see red | U if a command changed | C if it reverses one (the old one marked superseded) | C if surprised | tool (`change`) | C if extras come up |
| **Change behaviour, larger** | ratchet: becomes "New feature" | | | | | | | | | | |
| **Remove existing behaviour, bounded**: `chg/<slug>` | no | U if a dep goes | no | no | U: delete the scenario | delete its linked tests in the same commit, with a `Spec-Removed: <id>` trailer (I4); the count guard allows exactly those | U if a command goes | C | no | tool (`change!`, under Removed) | no |
| **Bug: code breaks an existing scenario**: `fix/<slug>` | no | no | no | no | no (the spec was right) | **C** regression test tagged with the existing ID, red on the old code | no | no | C if the cause generalises | tool (`fix`) | no |
| **Bug: spec silent or wrong**: `fix/<slug>` | no | no | no | no | U: add or modify the scenario, plus a "SHALL CONTINUE TO" guard scenario | **C** red first; guard IDs pass on the old code (`Spec-Guard:`) | no | C if it reveals a rule | C | tool (`fix`) | no |
| **Hotfix while a feature is open**: `fix/<slug>` via `--hotfix` | as for the two bug rows | | | | | | | | | | After merge, `status` on the open feature says `git merge main`. |
| **Tweak or chore** (copy, style, docs, config): `chore/<slug>` | no | no | no | no | no | pass, **unedited** (I7) | U only if AGENTS.md is the thing tweaked | no | no | skipped | no |
| **Dependency bump, swap, add or remove; tool change**: `chore/deps-<slug>` | no | **U** if a runtime dep or tool is added, removed or swapped (I11) | C phase only if the migration is multi-step (at replan) | no | no | unedited; harness-only edits (fixtures, imports, mocks) allowed in commits with a `Test-Harness: <reason>` trailer, shown at merge (I7) | U if commands changed | **C** if a swap or a major version | C if surprised | skipped (users notice: use `chg`) | no |
| **Refactor or perf**: `refactor/<slug>` | no | U if a structure rule changes | no | no | no (a scenario change makes it `chg`) | pass **unedited** (I7, same `Test-Harness:` route); adding tests is allowed | no | C if architectural | C if surprised | `perf` only | no |
| **Cross-cutting constraint** (a11y, security): `plan/<date>-<slug>`, then `feat/` | U only if it is a product promise | **U** standing rule S-n | U: "apply S-n" phase | C (for the apply phase) | C: **one** cross-cutting capability; never edit every feature | C | no | C | no | tool | no |
| **Replan** (reorder, merge, split): `plan/<date>-replan` | no | U if a rule changed | **U**; slugs are permanent | no | no | no | U if the process changed | C if a phase is dropped for a reason worth keeping | no | skipped | U: scheduled (linked) or dropped (file deleted, reason in the commit) |
| **Pivot** (who, why, scope): `plan/<date>-pivot` | **U** | U if needed | rewrite; removals scheduled as later changes | no | no (removals happen in the scheduled changes) | no | U pitch line | **C** | no | skipped | re-triage all |
| **Abandon mid-flight**: `! mise run abandon -- "why"` | no | no (never merged) | no (never ticked; the next replan decides) | discarded with the branch; tip tagged `abandoned/<slug>` | no | discarded | no | no | C if the finding generalises | no | **C** with reason and tag (the tool commits it to main) |
| **Adoption of an existing repo**: `plan/project-init` | **C** (reverse-engineered, then gaps talked through) | **C** (from lockfiles, config) | **C** (from TODOs, issues, plans, plus crashes found at setup as Phase 1) | no | **C: entrypoint capability only.** Working behaviour becomes characterization scenarios. Crashes become `[gap]` scenarios with strict-xfail tests. Never back-fill the rest. | C: subprocess entrypoint tests | **C** (last) | C: legacy import only | C (earlier lessons carried over) | C from git history | C seed |

## Lanes

`/sdd` runs this classifier out loud. Ask the questions in order and stop at the first yes.

```
Q1 changes who / why / scope in mission.md?                            -> PLAN (pivot)   plan/<date>-pivot
Q2 only reorders, merges, splits or schedules work, or sets a rule?    -> PLAN (replan)  plan/<date>-replan
Q3 wants an answer, not shipped code?                                  -> backlog --spike (no lane)
Q4 not doing it now?                                                   -> backlog (no branch)
Q5 code violates an existing scenario, or behaviour a reasonable user
   would not expect where the spec is silent?                          -> FIX       fix/<slug>  (--hotfix if a change is open)
Q6 observable behaviour unchanged?  -> structure/perf: REFACTOR  |  deps/tools/copy/style/docs/config: CHORE
Q7 one capability, <=3 scenarios, no new dep or interface, one session? -> CHG      chg/<slug>
otherwise                                                               -> FEAT     feat/<slug> + change folder
```

- A lane only gets heavier. `mise run change -- <slug> --lane feat` upgrades `chg/x` in place to `feat/x` and adds the change folder. A downgrade is refused.
- "Bounded" is judged against the repo, not against how familiar the agent is with it.
- Branch prefixes: `feat/`, `chg/`, `fix/`, `chore/` (dependencies: `chore/deps-<slug>`), `refactor/`, `plan/<date>-<slug>`.

### One change at a time

- **One open change at a time** (I8). `mise run change` refuses while another lane branch is unmerged, or while the tree is dirty. Untracked backlog files are exempt.
- **Hotfix.** `mise run change -- <slug> --lane fix --hotfix` is allowed while a change is open.
  - It runs `git worktree add ../<repo>-fix-<slug> -b fix/<slug> main`, where `<repo>` is the name of this checkout's folder. The open feature's tree is untouched.
  - A human merges it with `! mise run merge -- --branch fix/<slug>`.
  - Afterwards `mise run status` on the feature branch says `main moved: run git merge main`, and prove-red's base follows the new merge-base.
- **Parallel groups.** `--parallel` is for multi-agent runs only. Workers run on `feat/<slug>--g<n>` and merge into `feat/<slug>`, never into main.

## Formats

IDs are never sequential. Change folders, backlog items and ADRs are `<date>-<slug>`. Scenarios are `<cap>.<slug>`. Branches collide only when both pick the same slug on the same day, and git shows that as a real disagreement.

### Scenarios: `specs/capabilities/<cap>.md`

- **Structure:** `## Requirement: <title>`, then exactly one SHALL sentence, then one or more `### Scenario: <cap>.<slug>` with GIVEN/WHEN/THEN bullets. GIVEN is optional. WHEN and THEN are required.
- **ID:** matches `^[a-z][a-z0-9-]*\.[a-z0-9][a-z0-9-]*$` and is unique in the repo.
- **Content:** no design prose, and no code except literal I/O.
- **Tags after the ID:** `[gap: <roadmap-slug>]` marks known-broken behaviour. Its test is a strict xfail with the ID in the reason, and the slug must exist in the roadmap. Fixing the gap turns the xfail into a strict XPASS, a red build that forces the tag off. So a change that sets out to fix a gap rewrites that scenario as an exact contract without the tag before approve.
- **Open questions:** `[NEEDS CLARIFICATION: <question>]`. spec-check refuses them on the default branch, in an approved change and in `mission.md`.

An illustration for a made-up `hello` command. spec-check reads scenarios only from `specs/capabilities/*.md`, so these IDs never count.

```markdown
# Capability: example

## Requirement: Greeting
The CLI SHALL greet the name given as the first argument.

### Scenario: example.greets-name
- GIVEN no config file exists
- WHEN the user runs `hello World`
- THEN stdout is `Hello, World` and the exit code is 0

## Requirement: No crash on bad input
The CLI SHALL never end with a traceback.

### Scenario: example.no-args [gap: input-hardening]
- WHEN the user runs `hello` with no arguments
- THEN stderr holds no traceback and the exit code is not 0
```

### Change folder: `specs/changes/<date>-<slug>/` (feat lane only)

```
            mise run change            ! mise run approve              ! mise run merge
 (none) ------------------> draft ---------------------> approved ---------------------> done (frozen)
                              |                              |
                              +---------- ! mise run abandon -+--> branch tagged abandoned/<slug>, deleted;
                                                                   backlog report committed by the tool
```

- `status:` changes only through the tool commands (I6). The fast lanes have no folder: their branch is the whole state.
- **`requirements.md`** (cap 120 lines). Frontmatter: `change` (`<date>-<slug>`), `lane`, `status` (`draft | approved | done`), `roadmap` (the slug), `title` (a conventional commit subject that becomes the squash commit and the CHANGELOG line). Sections: `## Why`, `## Scope` (In, Out), `## Decisions` (each with what was rejected and why), `## Context`. The capability edits live in `specs/capabilities/`. `mise run status -- --change` prints them as a diff next to this file.
- **`plan.md`** (cap 100 lines). One header per group, numbered from G1: `## G<n> <name> | <ids> | risk: low|high | parallel: yes|no`, then a `Files:` line. No checkboxes: a group is done when every ID in it has a passing linked test. `risk: high` makes compile stop after that group and wait for a human look at its diff.
- **`validation.md`** (cap 60 lines):
  - `## Review focus`: at most 5 rows of implied inputs the spec never named. Each row is `- <input> -> <scenario id>` or `- <input> -> none: <reason>` (I13).
  - `## Run it` (optional, feat only): a table `| command | exit | stdout contains | stderr contains |` for what tests cannot reach, such as a real server. Merge runs each row.
  - `## Human checks`: at most 3. Merge asks for each with a TTY, or records your `--attest`.

### Roadmap, backlog, decisions, lessons

- **`specs/roadmap.md`:** `## Phase <n>: <name>` sections of `- [ ] <slug>: <title>` items, then `## Later` (same item form) and `## Gates` (open questions that block a phase, `- Phase <n>: <question>`). Slugs are permanent. Merge ticks an item, or adds `- [x] <slug>: <title> (unplanned)`.
- **`specs/backlog/<date>-<slug>.md`:** frontmatter `status: open | scheduled`, plus `roadmap: <slug>` once scheduled. Sections: What, Why, Notes. Starting scheduled work moves its content into `requirements.md` and deletes the file. A replan that drops one deletes it, with the reason in the commit.
- **`project_memory/decisions/<date>-<slug>.md`** (ADR): frontmatter `status: active | superseded by <date>-<slug>`. An ADR imported from a legacy decisions list also carries `aliases: [<old id>, ...]`, so old references still resolve. Sections: Context, Decision, Rejected, Consequences. Frozen after merge, except `status:`.
- **`project_memory/lessons.md`:** append only (union merge), newest last. Each entry is `## <date> | <title>`, then `Trigger: <what happened>` and `Rule: <what to do next time>`.

### Tests and commits

- **Linkage:** each test lists the scenario IDs it proves, and `mise run test -- --spec <id>` selects them. Each run writes `.cache/spec-results.json` with the outcome per ID (passed, failed, error, xfailed or xpassed), which spec-check and status read.
- **Syntax in this repo:** `@pytest.mark.spec("<id>", ...)` tags a test, and a gap test also carries `@pytest.mark.xfail(strict=True, reason="<id>: <why>")`.
- **Entrypoint tests** run the real installed command in a subprocess, never an inner function.
- **skip and xfail:** a new skip or xfail needs a scenario ID in its reason. An xfail (a test expected to fail) is allowed only for `[gap]` scenarios, and it must be strict: an unexpected pass fails the run.
- **Pending:** a non-gap scenario that has no passing linked test yet. Only a branch with an open change may have pending scenarios, and only ones ADDED or MODIFIED since the merge-base (I3).
- **Commit subjects:** Conventional Commits with the types `feat change fix perf refactor build ci docs test chore spec style revert`, and `!` for a breaking change.
- **Trailers:**

| Trailer | Where | Meaning |
|---|---|---|
| `Spec: <ids>` | a `feat/`, `chg/` or `fix/` commit that touches source | the scenarios this commit makes pass |
| `Red: <id>: <reason>` | the same commits; printed by `mise run tdd -- red` | how each test failed before the code |
| `Spec-Guard: <ids>` | bug fixes | neighbouring scenarios that must pass on the old code too |
| `Spec-Removed: <ids>` | the commit that deletes scenarios | their tests are deleted in the same commit |
| `Test-Harness: <reason>` | `chore/` and `refactor/` commits that touch test files | a harness-only edit; merge lists it for the human |
| `Spec-Approved: <hash>`, `Merged-By: mise run merge` | written by approve and merge | the audit trail; never typed by hand |

## Gates

```
pre-commit  <  mise run verify  <  CI           <  mise run merge
  staged       whole repo:         verify          CI checks
  subset of    lint, format,       + prove-red     + Definition of Done extras (run-it rows,
  verify       types, secrets,       on PRs          human checks, gate-file diff, lane rules
               test, spec-check    + audit           on the whole branch)
                                     on push       + bookkeeping (roadmap, CHANGELOG, squash)
```

- Read `<` as "is a subset of": each rung runs the rung before it, plus more.
- `mise run verify` is the local gate. Green verify is the minimum before anyone calls work done.
- This section is the only place the ladder is written out. AGENTS.md and the hook messages link here.
- **What stops shortcuts.** `main` moves only through merge, abandon or release, a sync to what origin really holds, or the first commit (I16). A `reference-transaction` hook sees every ref move, and `pre-push` refuses pushes to `main`. In Claude Code, deny rules and a `pre-bash` hook keep agents off the human gates, the hook settings and the gate files.
- **What detects evasion.** Merge writes `Merged-By: mise run merge` into each commit it puts on `main`. `mise run status -- --audit`, `mise run doctor`, session start and CI (on push) flag any first-parent commit that lacks it. CI re-runs verify.
- Local enforcement is cooperative. A program written outside the repo can get past the hooks. The audit and CI catch the result afterwards.

### Definition of Done

This is what `! mise run merge` checks, in order. `mise run status -- --merge` runs steps 1 to 6 as a read-only preview; validate ends with it, so you see the checks before typing merge.

1. The tree is clean and the branch is a lane branch (`--branch` names another worktree's branch). For feat, the change is `approved`.
2. `mise run verify` is green, with spec-check strict: nothing is pending and no `[NEEDS CLARIFICATION` remains. So every scenario has a passing linked test, or a strict xfail if it is a gap.
3. prove-red and the count guard pass (see below). Lane rules I7, I11 and I12 pass. `core.hooksPath` is `.githooks`, and the hook files equal the committed blobs.
4. Run-it rows execute (`timeout 60` each) and match.
5. Human checks and `Test-Harness:` diffs:
   - with a TTY, merge asks y/N for each;
   - without a TTY (the `!` path), `--attest` is required, and the squash body records the checks plus `attested by <git user.name>`;
   - with zero human checks, merge runs without a flag.
6. If gate files changed (`.githooks/`, `scripts/project.py`, `.gitleaks.toml`, the CI workflow, `.claude/settings.json`, or the `[tasks]` or `[hooks]` of `mise.toml`), the diff is shown and `--gate-change` is required.
7. A close commit on the branch contains the roadmap tick (or the `(unplanned)` insert), the change's `status: done`, and the regenerated `CHANGELOG.md`.
8. Land:
   - **With a remote:** push the branch and open a PR, then wait for its checks (team tier: also for an approving review). Squash-merge with a generated body that ends in `Merged-By: mise run merge`, then `git pull --ff-only`.
   - **No remote:** a local squash onto `main`. Any worktree with `main` checked out is fast-forwarded, and the branch is deleted.
9. It prints the next roadmap item, "still right? If not: /sdd replan", then "/clear".

The squash body keeps the scenario IDs, the prove-red table, the check results and the attestation. That is the durable record on `main`.

**prove-red** runs the tests of new and changed scenarios against the old code. That is the source roots as they were at the merge-base, checked out with `--no-overlay` so files added since then are gone.

| Scenario kind | Expected on the old code | Otherwise |
|---|---|---|
| ADDED, MODIFIED, or named in a `Spec:` trailer | failed, error (collection) or strict xpassed: red | passed or xfailed: FAIL `<id> pins nothing new` |
| Guard (`Spec-Guard:`, or a characterization scenario from setup) | passed | failed: FAIL "guard broke"; a collection error is a warning |
| Gap (`[gap: <slug>]`) | xfailed (strict) | passed or xpassed: FAIL "gap test does not reproduce the gap" |
| Count guard | tests collected at HEAD >= tests at base, minus tests linked only to REMOVED IDs | FAIL "tests disappeared" |

A human-only escape hatch exists: `! mise run merge -- --allow <id> --reason "<why>"`, printed into the squash body.

## Invariants

| # | Rule | Checked by |
|---|---|---|
| I1 | `mission.md` and `roadmap.md` are staged only on `plan/` branches. Merge also writes the roadmap. | pre-commit, spec-check |
| I2 | `CHANGELOG.md` is staged only by merge or release. | pre-commit, spec-check |
| I3 | On the default branch each scenario has a passing linked test. A gap has a strict xfail whose reason contains its ID, and its slug is in the roadmap. No orphan tags, and no skip or xfail on a linked test except for a gap. On a branch with an open change, ADDED and MODIFIED scenarios may be pending. | spec-check (verify, CI) |
| I4 | A commit that adds or modifies a scenario stages a test tagged with it. Removing a scenario deletes its tests in the same commit, with a `Spec-Removed:` trailer. | pre-commit, commit-msg |
| I5 | A change folder with `status: done` is frozen. | pre-commit, spec-check |
| I6 | `status:` moves draft, approved, done only via approve and merge. | merge (`Spec-Approved:` hash) |
| I7 | On `refactor/` and `chore/`, existing test files are not edited, except in `Test-Harness:` commits. | merge, CI |
| I8 | One open change at a time, except `--hotfix` and `--parallel`. | `mise run change` |
| I9 | prove-red expectations hold for each scenario kind. | prove-red (merge, CI on PRs) |
| I10 | Tests never disappear, except those linked only to removed scenarios. | prove-red count guard |
| I11 | Adding, removing or swapping a runtime dependency or tool changes `tech-stack.md` on the same branch. | spec-check, merge |
| I12 | feat lane: the approve commit comes before the first commit that touches source. | merge |
| I13 | Each Review focus row points at an existing scenario ID, or says `none: <reason>`. | approve |
| I14 | No personal paths or wiki-links in tracked docs or skills. | gitleaks rules (pre-commit, verify, CI) |
| I15 | Every mise task named in AGENTS.md, README.md or this file exists. | spec-check, doctor |
| I16 | The default branch moves only via merge, abandon or release, a confirmed origin sync, or the first commit. Only merge, abandon or release push it, apart from the first push to a remote that does not have it yet. | reference-transaction, pre-push, audit |

## Size caps

spec-check warns when a file passes its cap. Split it or cut it. Never raise the cap to fit.

| File | Cap |
|---|---|
| `AGENTS.md` | 40 lines |
| `specs/capabilities/<cap>.md` | 300 lines; split the capability beyond that |
| `requirements.md` | 120 lines |
| `plan.md` | 100 lines |
| `validation.md` | 60 lines; Review focus 5 rows, Human checks 3 |
| `project_memory/README.md` | 1 KB |

The other files under `specs/` and `project_memory/` have no line cap.
