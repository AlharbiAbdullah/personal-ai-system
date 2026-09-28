<!-- specs/README.md: how work happens in this repo. Living; a replan (plan/ branch) changes it. AGENTS.md, the sdd skill and the hook messages link here instead of restating it. -->
# How {NAME} is built

`specs/` holds the product as plain markdown that any person or agent can read, and the tests prove it. This file is the process. It covers the lifecycle, lanes, file formats and gates, up to the Definition of Done.

| Path | Holds | Changes |
|---|---|---|
| `specs/mission.md` | why, who, scope in and out, success, glossary | only on `plan/` branches |
| `specs/tech-stack.md` | runtime, tooling, distribution, the trunk map, standing rules S-n, never-use, environment | on the branch that adds, removes or swaps a runtime dep, tool or rule (I11). A Trunk entry is added on any branch; removing or changing one is a gate change (I20) |
| `specs/roadmap.md` | phases of `- [ ] slug: title`, Later, Gates | only on `plan/` branches; merge ticks items and marks launches |
| `specs/capabilities/<cap>.md` | what is true now: requirements and scenarios with stable IDs | with every behaviour change, in the same commit as its test |
| `specs/changes/<date>-<slug>/` | one feat change: requirements, plan, validation | frozen at merge |
| `specs/backlog/<date>-<slug>.md` | ideas, spike findings, abandoned changes, launches | deleted when the work starts or a replan drops it |
| `proof/<date>-<slug>/` | one change's proof: the captures a reviewer looks at, indexed by its `README.md` | only by `mise run proof` and merge, on that change's branch; frozen at merge |
| `project_memory/` | decisions (ADRs) and lessons; its README routes each kind of fact | see Formats |

## Lifecycle

```
 SETUP (once, branch plan/project-init)
   constitution: mission.md, tech-stack.md, roadmap.md, capabilities/<entry>.md
   entrypoint crashes found at setup -> [gap] scenarios + roadmap Phase 1
   tooling, gates, this file, AGENTS.md
                   |
  [G1 HUMAN] ! mise run merge            constitution + standard land on {DEFAULT_BRANCH}
                   |
                   v
+============================ THE LOOP: one change at a time ==============================+
| /sdd "<what you want>"                                                                   |
|   classifier (#lanes): first yes wins; a lane only gets heavier                          |
|   mise run change -- <slug> --lane <lane>   refuses while another change is open (I8),   |
|                                             except --hotfix (fix lane, own worktree)     |
|  feat lane                                                                               |
|   TALK      question round(s): Scope, Decisions, Context, Rollback (revert|flag|one-way) |
|             -> scenarios in specs/capabilities/<cap>.md                                  |
|             -> specs/changes/<date>-<slug>/ requirements.md plan.md validation.md        |
|                a group whose Files: are trunk is risk: high; ## Proof: one row per case  |
|  [G2 HUMAN] ! mise run approve     approves the test list and the proof list             |
|   fresh context (/clear)                                                                 |
|   COMPILE   per group: tagged tests -> mise run tdd -- red <ids> (must fail, right       |
|             reason) -> minimal code -> tdd green -> refactor -> verify -> commit on green|
|             risk: high group   -> compile pauses for your look, trunk files first        |
|             spec wrong?        -> scenario + test + code in ONE commit                   |
|             new idea?          -> mise run backlog -- <topic>  (never the roadmap)       |
|   VALIDATE  lenses: conformance, breaker, test honesty; captures the ## Proof rows and   |
|             a confidence line per group (mise run proof); ends with                      |
|             mise run status -- --merge (the full Definition of Done preview)             |
|  [G3 HUMAN] ! mise run merge -- --attest --read-trunk   you read the trunk diff and skim |
|             the leaf against proof; verify + prove-red + DoD + roadmap tick + CHANGELOG  |
|             + squash; prints the next roadmap item, "still right?"                       |
|                                                                                          |
|  fast lanes, no change folder:  fix | chg | chore | refactor   ->  [G3] merge            |
|  spike: mise run backlog -- <topic> --spike   scratch worktree; only the findings land   |
|                                                                                          |
|  LAUNCH  a merged roadmap item (status lists it): /sdd launch <slug>                     |
|          lenses over the whole feature -> fixes as lanes -> your checklist ->            |
|          chg/launch-<slug> takes the flag off -> [G3] merge marks it (launched <date>)   |
+================================================+=========================================+
                                                 | "still right?" = no, 5+ open backlog items,
                                                 | or every 3 merged features (status reminds)
                                                 v
 REPLAN   mise run change -- <date>-replan --lane plan ; /sdd replan
          reorder/merge/split phases, schedule backlog (linked), standing rules, process fixes
          mission.md changes only on plan/ branches (a pivot, or a product-promise constraint)
                                                                           -> [G3] merge
{IF_RELEASE} RELEASE  ! mise run release -- <bump>     bump, tag, build, publish
```

- `!` marks a human gate. You type it yourself: in Claude Code with the `!` prefix, anywhere else in your own terminal. Agents never run approve, merge, abandon or release. They stop and ask.
- There are three human gates: `! mise run merge` (G1), `! mise run approve` (G2) and `! mise run merge` (G3).
- `--attest` is needed only when merge has something for a human to confirm (Human checks, or `Test-Harness:` diffs) and there is no TTY (see [Definition of Done](#definition-of-done)). `--read-trunk` is the same for a branch that touches a trunk file.
- `/sdd` is the repo skill in `.claude/skills/sdd/`: `/sdd "<what you want>"`, or `talk`, `compile`, `validate`, `launch <roadmap-slug>`, `replan`, `status`. An agent without skills reads `SKILL.md` there.
- Everything else is mechanical.

## Adding a feature: what changes

| Artifact | For a new feature | Written by |
|---|---|---|
| `specs/mission.md` | **No.** Mission changes only on a `plan/` branch, for a pivot or a product-promise constraint. | human + talk |
| `specs/roadmap.md` | **Yes, but only the tool touches it**, at merge. It ticks the item, or inserts it as `(unplanned)` if the feature was never scheduled. The launch's merge marks it `(launched <date>)` later. | `mise run merge` |
| `specs/tech-stack.md` | Only if the feature adds or removes a runtime dependency, a service or a standing rule. The edit goes on the same branch, and merge enforces this (I11). A new file that every run goes through may get a Trunk entry. | agent |
| `.env.example` | Only for a `flag:` Rollback: the flag's row, off by default. The launch removes it. | talk |
| `specs/capabilities/` | **Always.** New or changed scenarios, each with a stable ID. | talk |
| tests | **Always.** Red first, tagged with the scenario ID, and proven red on the old code at merge. | compile |
| change folder | **Always** for the feat lane. | talk |
| ADR (`project_memory/decisions/`) | Only for a choice that later changes must respect. | agent |
| `project_memory/lessons.md` | Only if something surprised you. | agent or human |
| `CHANGELOG.md` | Always, regenerated at merge. | `mise run merge` |
| `specs/backlog/` | Every out-of-scope idea that came up during the work. For a `flag:` change, the launch item too. | agent or human; `mise run merge` for the launch item |
| `proof/<date>-<slug>/` | **Always** for feat: a capture per `## Proof` row, a confidence line per group, and the test proof. | `mise run proof`; merge writes the test proof |

## Every change type

Legend:
- **C** = create, **U** = update, **R** = read only, **no** = not touched.
- **tool** = `mise run merge`, `abandon` or `release` writes it. No person or model does.
- **if X** = only when X holds.

| Change type: branch | mission | tech-stack | roadmap | change folder | capabilities (living) | tests | AGENTS.md | ADR | lessons | CHANGELOG | backlog |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **New feature, on roadmap**: `feat/<slug>` | R | U if a dep, service or rule is added or removed | tool ticks | **C** | U: add or modify scenarios | **C** red first, per ID | U if a command changed | C if cross-cutting | C if surprised | tool (`feat`) | C for out-of-scope ideas; tool adds the launch item for a `flag:` change |
| **New feature, not on roadmap, start now**: `feat/<slug>` | R | same | tool inserts `(unplanned)` and ticks | **C** | same | same | same | same | same | tool | same |
| **Launch a merged roadmap item**: `/sdd launch <slug>`, then `chg/launch-<slug>` with a flag, `chore/launch-<slug>` without | no | no | tool appends `(launched <date>)` | no | U: the new behaviour's scenarios drop `GIVEN <ENV_NAME>=1`; the `[flag-off]` scenarios go (`Spec-Removed:`) | U: they stop setting the flag; the flag-off tests go with their scenarios | no | no | C if surprised | tool (`change` on chg; skipped on chore) | the launch file holds the findings and the checklist; the launch lane deletes it |
| **Idea, not now**: no branch | no | no | no (next replan) | no | no | no | no | no | no | no | **C** (committed on the current branch; on the default branch it stays untracked until the next change) |
| **Research idea mid-feature**: current branch | no | no | **never** | no | no | no | no | no | no | no | **C** |
| **Spike (you want an answer, not code)**: `mise run backlog -- <topic> --spike` | no | no | no | no | no | throwaway | no | no | C if learned | no | **C** findings report. The scratch worktree `../<repo>-spike-<slug>` is deleted and never merged. |
| **Change behaviour, bounded** (1 capability, 3 or fewer scenarios, no new dep or interface, 1 session): `chg/<slug>` | no | no | no | no (intent in the commit body) | U: scenario edited **in the same commit as its test** (I4) | U: flip the assertion first, see red | U if a command changed | C if it reverses one (the old one marked superseded) | C if surprised | tool (`change`) | C if extras come up |
| **Change behaviour, larger** | ratchet: becomes "New feature" | | | | | | | | | | |
| **Remove existing behaviour, bounded**: `chg/<slug>` | no | U if a dep goes | no | no | U: delete the scenario | delete its linked tests in the same commit, with a `Spec-Removed: <id>` trailer (I4); the count guard allows exactly those | U if a command goes | C | no | tool (`change!`, under Removed) | no |
| **Bug: code breaks an existing scenario**: `fix/<slug>` | no | no | no | no | no (the spec was right) | **C** regression test tagged with the existing ID, red on the old code | no | no | C if the cause generalises | tool (`fix`) | no |
| **Bug: spec silent or wrong**: `fix/<slug>` | no | no | no | no | U: add or modify the scenario, plus a "SHALL CONTINUE TO" guard scenario | **C** red first; guard IDs pass on the old code (`Spec-Guard:`) | no | C if it reveals a rule | C | tool (`fix`) | no |
| **Hotfix while a feature is open**: `fix/<slug>` via `--hotfix` | as for the two bug rows | | | | | | | | | | After merge, `status` on the open feature says `git merge {DEFAULT_BRANCH}`. |
| **Tweak or chore** (copy, style, docs, config): `chore/<slug>` | no | no | no | no | no | pass, **unedited** (I7) | U only if AGENTS.md is the thing tweaked | no | no | skipped | no |
| **Dependency bump, swap, add or remove; tool change**: `chore/deps-<slug>` | no | **U** if a runtime dep or tool is added, removed or swapped (I11) | C phase only if the migration is multi-step (at replan) | no | no | unedited; harness-only edits (fixtures, imports, mocks) allowed in commits with a `Test-Harness: <reason>` trailer, shown at merge (I7) | U if commands changed | **C** if a swap or a major version | C if surprised | skipped (users notice: use `chg`) | no |
| **Refactor or perf**: `refactor/<slug>` | no | U if a structure rule changes | no | no | no (a scenario change makes it `chg`) | pass **unedited** (I7, same `Test-Harness:` route); adding tests is allowed | no | C if architectural | C if surprised | `perf` only | no |
| **Cross-cutting constraint** (a11y, security): `plan/<date>-<slug>`, then `feat/` | U only if it is a product promise | **U** standing rule S-n | U: "apply S-n" phase | C (for the apply phase) | C: **one** cross-cutting capability; never edit every feature | C | no | C | no | tool | no |
| **Replan** (reorder, merge, split): `plan/<date>-replan` | no | U if a rule changed | **U**; slugs are permanent | no | no | no | U if the process changed | C if a phase is dropped for a reason worth keeping | no | skipped | U: scheduled (linked) or dropped (file deleted, reason in the commit) |
| **Pivot** (who, why, scope): `plan/<date>-pivot` | **U** | U if needed | rewrite; removals scheduled as later changes | no | no (removals happen in the scheduled changes) | no | U pitch line | **C** | no | skipped | re-triage all |
| **Abandon mid-flight**: `! mise run abandon -- "why"` | no | no (never merged) | no (never ticked; the next replan decides) | discarded with the branch; tip tagged `abandoned/<slug>` | no | discarded | no | no | C if the finding generalises | no | **C** with reason and tag (the tool commits it to {DEFAULT_BRANCH}) |
| **Adoption of an existing repo**: `plan/project-init` | **C** (reverse-engineered, then gaps talked through) | **C** (from lockfiles, config) | **C** (from TODOs, issues, plans, plus crashes found at setup as Phase 1) | no | **C: entrypoint capability only.** Working behaviour becomes characterization scenarios. Crashes become `[gap]` scenarios with strict-xfail tests. Never back-fill the rest. | C: subprocess entrypoint tests | **C** (last) | C: legacy import only | C (earlier lessons carried over) | C from git history | C seed |
| {IF_RELEASE}**Release**: `! mise run release -- <bump>` (internal branch `release/vX.Y.Z`) | no | no | no | no | no | green | no | no | no | tool: version section | no |

## Lanes

`/sdd` runs this classifier out loud. Ask the questions in order and stop at the first yes.

```
Q1 changes who / why / scope in mission.md?                            -> PLAN (pivot)   plan/<date>-pivot
Q2 only reorders, merges, splits or schedules work, or sets a rule?    -> PLAN (replan)  plan/<date>-replan
Q3 wants an answer, not shipped code?                                  -> backlog --spike (no lane)
Q4 not doing it now?                                                   -> backlog (no branch)
Q5 code violates an existing scenario (a [gap] one does not count), or
   behaviour a reasonable user would not expect where the spec is silent? -> FIX     fix/<slug>  (--hotfix if a change is open)
Q6 observable behaviour unchanged?  -> structure/perf: REFACTOR  |  deps/tools/copy/style/docs/config: CHORE
Q7 one capability, <=3 scenarios, no new dep or interface, one session? -> CHG      chg/<slug>
otherwise                                                               -> FEAT     feat/<slug> + change folder
```

- A `[gap]` scenario is a known violation the roadmap schedules. Fixing it is that roadmap item's feat change, whatever its size. Q5 and Q7 do not apply: the scenario must become an exact contract before approve.
- A launch lane (`chg/launch-<slug>`, `/sdd launch`) is chg whatever its size: it removes a flag's scaffolding and turns on behaviour already specified and proven, so Q7 does not apply.
- A lane only gets heavier. `mise run change -- <slug> --lane feat` upgrades `chg/x` in place to `feat/x` and adds the change folder. A downgrade is refused.
- "Bounded" is judged against the repo, not against how familiar the agent is with it.
- Branch prefixes: `feat/`, `chg/`, `fix/`, `chore/` (dependencies: `chore/deps-<slug>`), `refactor/`, `plan/<date>-<slug>`.

### One change at a time

- **One open change at a time** (I8). `mise run change` refuses while another lane branch is unmerged, or while the tree is dirty. Backlog files on `{DEFAULT_BRANCH}`, new or edited, are exempt: nothing commits there, so they ride into the new branch. A lane-named branch that forks before the adoption (its fork point has no `.project.toml`) is not a change, so I8 skips it. `mise run status` lists it while the default branch lacks it. `git merge {DEFAULT_BRANCH}` into one makes it a change like any other.
- **Hotfix.** `mise run change -- <slug> --lane fix --hotfix` is allowed while a change is open.
  - It runs `git worktree add ../<repo>-fix-<slug> -b fix/<slug> {DEFAULT_BRANCH}`, where `<repo>` is the name of this checkout's folder. The open feature's tree is untouched.
  - A human merges it from the main checkout with `! mise run merge -- --branch fix/<slug>`.
  - Afterwards `mise run status` on the feature branch says `{DEFAULT_BRANCH} moved: run git merge {DEFAULT_BRANCH}`, and prove-red's base follows the new merge-base.
- **Parallel groups.** `--parallel` is for multi-agent runs only. Workers run on `feat/<slug>--g<n>` and merge into `feat/<slug>`, never into {DEFAULT_BRANCH}.

## Formats

IDs are never sequential. Change folders, backlog items and ADRs are `<date>-<slug>`. Scenarios are `<cap>.<slug>`. Branches collide only when both pick the same slug on the same day, and git shows that as a real disagreement.

### Scenarios: `specs/capabilities/<cap>.md`

- **Structure:** `## Requirement: <title>`, then exactly one SHALL sentence, then one or more `### Scenario: <cap>.<slug>` with GIVEN/WHEN/THEN bullets. GIVEN is optional. WHEN and THEN are required.
- **ID:** matches `^[a-z][a-z0-9-]*\.[a-z0-9][a-z0-9-]*$` and is unique in the repo.
- **Content:** no design prose, and no code except literal I/O.
- **Tags after the ID:** a scenario carries at most one. `[flag-off: <ENV_NAME>]` marks a guard that pins the old behaviour with that flag off: its ENV must be a `flag` row of `.env.example` (I22), and prove-red wants its test to pass on the old code, although the branch adds it. `[gap: <roadmap-slug>]` marks known-broken behaviour. Its test is a strict xfail with the ID in the reason, and the slug must exist in the roadmap. Fixing the gap turns the xfail into a strict XPASS, a red build that forces the tag off. That needs a test whose body fails on an assertion about the behaviour, or on the crash that `xfail(raises=<type>)` names. spec-check refuses a gap test that xfails before its body runs (`run=False`, a failing fixture). It also refuses one that calls `pytest.xfail()` or `pytest.fail()`, or whose body raises anything else: a typo's `AttributeError` still fails after the fix. So a change that sets out to fix a gap rewrites that scenario as an exact contract without the tag before approve.
- **Open questions:** `[NEEDS CLARIFICATION: <question>]`. spec-check refuses them on the default branch, in an approved change and in `mission.md`. Before the first merge (G1), when `{DEFAULT_BRANCH}` holds no `.project.toml` yet, it lists each one as a warning instead, and G1's merge refuses while any remain.

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
- **`requirements.md`** (cap 120 lines). Frontmatter: `change` (`<date>-<slug>`), `lane`, `status` (`draft | approved | done`), `roadmap` (the slug), `title` (a conventional commit subject that becomes the squash commit and the CHANGELOG line). Sections: `## Why`, `## Scope` (In, Out), `## Decisions` (each with what was rejected and why), `## Context`, `## Rollback` (below). The capability edits live in `specs/capabilities/`. `mise run status -- --change` prints them as a diff next to this file.
- **`## Rollback`** holds exactly one line, how the change is undone after merge (I21):
  - `revert: <why a revert of the squash is enough>`. spec-check refuses it when the Distribution in `tech-stack.md` is `service` and a `Files:` path in `plan.md` is trunk.
  - `flag: <ENV_NAME>`. The new behaviour runs only with the flag on. It needs its row of kind `flag` in `.env.example` and at least one `[flag-off: <ENV_NAME>]` scenario (I22). Merge's close commit adds the launch item to the backlog (Definition of Done, step 7).
  - `one-way: <what cannot be undone>`: a data migration, a published interface, a sent message, deleted data. It needs a `risk: high` group that holds the one-way work, and merge asks its own Human check, `I read the one-way part: <what>`.
  - A change approved before this rule may lack the section: spec-check only warns.
- **`plan.md`** (cap 100 lines). One header per group, numbered from G1: `## G<n> <name> | <ids> | risk: low|high | parallel: yes|no`, then a `Files:` line of comma-separated paths (a note in parentheses, such as `(NEW)`, is allowed). No checkboxes: a group is done when every ID in it has a passing linked test. `risk: high` makes compile stop after that group and wait for a human look at its diff. A group whose `Files:` match a trunk entry must say `risk: high` (I17), and `mise run status` names its trunk files.
- **`validation.md`** (cap 60 lines):
  - `## Review focus`: at most 5 rows of implied inputs the spec never named. Each row is `- <input> -> <scenario id>` or `- <input> -> none: <reason>` (I13).
  - `## Run it` (optional, feat only): a table `| command | exit | stdout contains | stderr contains |` for what tests cannot reach, such as a real server. Merge runs each row.
  - `## Proof`: a table `| for | kind | shows |` of what a human looks at instead of reading leaf code, at most 6 rows. See [Proof](#proof-proofdate-slug).
  - `## Human checks`: at most 3. Merge asks for each with a TTY, or records your `--attest`.

### Trunk map: `## Trunk` in `specs/tech-stack.md`

The trunk is the code every run goes through: the entrypoint, shared settings, the schema. At merge a human reads the trunk diff line by line and skims the rest, the leaf, against the tests.

```markdown
## Trunk
- src/<pkg>/__init__.py: the entrypoint every command runs through
- src/<pkg>/config.py: settings every module reads
- migrations/**: schema changes reach every row
```

- One line per entry: `- <glob>: <why>`. The why is required. spec-check fails a line of another shape, and the template's placeholder line until talk replaces it.
- Globs are gitignore-style and anchored at the repo root. `**` crosses folders, `*` and `?` stay inside one, and a trailing `/` means the whole folder. `config.py` is the root's own file, never `src/config.py`.
- A path is trunk when any entry matches it. Every other path, tests included, is leaf.
- An empty section is valid. With no section every path is leaf, and `mise run doctor` warns.
- Adding an entry is free on any branch. Removing or changing one is a gate change (I20), because shrinking the trunk is the cheapest way to dodge a review.
- New behaviour goes into leaf modules. The trunk edit shrinks to the seam, usually one call, so the part a human must read stays small.

### Environment contract and flags: `.env.example`

Every variable the app reads is one row, `# NAME | kind | type | required | default | notes`. An empty value means unset, so the default applies.

- `knob`: a plain setting.
- `secret`: an `op://` pointer in `.env`, never the value.
- `flag`: a `bool` whose default is off (`0`, `false`, `no` or `off`). The new behaviour of a `flag:` change runs only with it on. The code reads it at one seam in the trunk, and the new behaviour lives in leaf modules the seam calls. Scenarios for the new behaviour say `GIVEN <ENV_NAME>=1`.

`mise run doctor` checks each value against its row, and each flag's type and default. It warns about flag debt: a flag row that reached `{DEFAULT_BRANCH}` more than 30 days ago. Its launch is due: `/sdd launch <slug>` ends in the lane that flips it on for good and removes the flag, its off path and its `[flag-off]` scenarios.

### Proof: `proof/<date>-<slug>/`

A human reads the trunk diff line by line and skims the leaf against proof. The proof of a change lives in one folder, committed on its branch and shown in the pull request. A reviewer who never runs the code still sees it. On feat the folder is named after the change folder. On the other lanes it is the author date of the branch's first commit and the slug.

`mise run proof -- <verb>` writes it. Each capture is one commit, `docs(proof): <id> <kind>`, that touches only the folder and passes the normal hooks. `<id>` is a scenario ID of the change or `G<n>` of its plan; on the fast lanes it is any scenario ID. A capture records the commit it shows, so the tree must match HEAD (`specs/` and `project_memory/` aside).

| Verb | Kind | Captures |
|---|---|---|
| `run [--before] <id> -- <cmd...>` | run, run --before | the command, its exit code and time, stdout and stderr (4 KB each, head and tail). `--before` runs it on the merge-base's code in a throwaway worktree first: before and after. |
| `log <id> <file> [--grep <re>] [--since <marker>]` | log | an excerpt of a log the run wrote |
| `http <id> <METHOD> <url> [--data <json>]` | http | the request, the status, the headers and the body's head; localhost, 127.0.0.1 and ::1 only |
| `shot <id> <url> [--selector <css>] [--viewport 1280x800] [--dark]` | screenshot | a PNG from headless Chromium (Playwright) |
| `video <id> <url> --steps <file.py> [--seconds 15] [--width 800]` | video | a WebM of `steps(page)` and its GIF preview (ffmpeg) |
| `tape <id> <file.tape>` | terminal | a GIF that vhs renders from the tape; the tape is kept beside it |
| `attach <id> <file> --caption "<text>"` | attach | a png, jpg, gif, svg, webm, mp4, cast, pdf, txt, json or csv made another way |
| `confidence G<n> high\|medium\|low -- "<why>"` | | one line per group, from validate |
| `tests` | test | the `## Tests` section: per scenario ID its tests, how they failed first, the last run. Merge writes it again, with prove-red's verdict. |
| `show` | | `.agent/proof/<date>-<slug>.html`, one page with everything inline; it opens nothing |
| `setup web`, `setup terminal` | | Playwright's parts for a headless Chromium; vhs and ttyd, pinned in `mise.toml` (then `tech-stack.md` names them, I11) |

- **The index.** `README.md` holds one entry per case, newest last: `### <id> · <kind> · <caption>`, then `captured at <sha> · <file> sha256 <hash>`, then the media. GitHub shows images and GIFs inline, and text in fenced blocks. A hand edit of a file breaks its sha256; capture it again.
- **Leak scan and caps (I24).** Text is written with the home folder as `~`, then gitleaks scans it with `.gitleaks.toml`; a hit refuses the capture and writes nothing. A file holds at most 5 MB and a change 15 MB. A refusal names what shrinks it (`--viewport`, `--seconds`, `--width`).
- **One entry per case.** A new capture for a case replaces its entry, whatever the kind: its old files go in the same commit, and the tool prints `replaced <kind> captured at <sha>`. A stale capture taken again leaves nothing behind. A confidence line is replaced the same way. Two entries for one case, from a hand edit, fail merge.
- **Ratchet.** A `chg/` or `fix/` branch can ratchet to feat. Its folder then takes the change folder's name, by `git mv` in the ratchet's commit, so its captures carry over.
- **Headless only.** Nothing opens a window. A verb whose tool is missing refuses with its `setup` command.
- **Stale.** A capture is stale once a later commit changes a file outside `specs/`, `proof/`, `project_memory/` and `CHANGELOG.md`. The preview marks it. A stale capture that fills a `## Proof` row fails at merge: capture it again.

**`## Proof` in `validation.md`.** Talk decides the proof the change owes; approve freezes it with the rest of the file. Each row is `| for | kind | shows |`. `for` is a scenario ID of the change or a `G<n>` of its plan. The kind is run, run --before, log, http, screenshot, video, terminal or attach. **One row per case**: a second row for the same scenario or group fails. A case with no row relies on its test proof alone. The kind follows what the case changes:

| The case changes | Kind |
|---|---|
| what a command prints or exits with | run (`run --before` when the old output matters) |
| a page's look | screenshot |
| a flow across clicks or pages | video |
| an interactive terminal session | terminal |
| an API response | http |
| a background job or service behaviour | log |
| anything captured another way | attach |

A repo whose runtime dependencies hold a known web or TUI framework has a UI. A feat change there with no screenshot, video or terminal row gets a warning from spec-check and approve. A row dropped or changed after approve needs `merge -- --reapprove`, as a Human check does.

### Roadmap, backlog, decisions, lessons

- **`specs/roadmap.md`:** `## Phase <n>: <name>` sections of `- [ ] <slug>: <title>` items, then `## Later` (same item form) and `## Gates` (open questions that block a phase, `- Phase <n>: <question>`). Slugs are permanent. Merge ticks an item, or adds `- [x] <slug>: <title> (unplanned)`.
- **Launches.** A branch whose slug is `launch-<slug>`, on any lane, launches the roadmap item `<slug>`: its merge appends ` (launched <date>)` to the ticked item and ticks nothing. So `launch-` starts no other slug. On `{DEFAULT_BRANCH}` with no change open, `mise run status` lists the ticked items without `(launched`, those with a live flag first (a flag row the change's Rollback names, or whose notes name the item or its change folder): one line with the count and the next `/sdd launch <slug>`, then at most 4 items. An item that shipped before launches existed gets the mark by hand in a replan, or a launch of its own.
- **The launch file `specs/backlog/<date>-launch-<slug>.md`:** merge writes it for a `flag:` change, and `/sdd launch` makes it otherwise. It holds the launch's findings, each with its outcome, and the human's launch checklist. The launch lane deletes it, and its first commit's body keeps the record.
- **`specs/backlog/<date>-<slug>.md`:** frontmatter `status: open | scheduled`, plus `roadmap: <slug>` once scheduled. Sections: What, Why, Notes. Starting scheduled work moves its content into `requirements.md` and deletes the file. A replan that drops one deletes it, with the reason in the commit.
- **`project_memory/decisions/<date>-<slug>.md`** (ADR): frontmatter `status: active | superseded by <date>-<slug>`. An ADR imported from a legacy decisions list also carries `aliases: [<old id>, ...]`, so old references still resolve. Sections: Context, Decision, Rejected, Consequences. Frozen after merge, except `status:`.
- **`project_memory/lessons.md`:** append only (union merge), newest last. Each entry is `## <date> | <title>`, then `Trigger: <what happened>` and `Rule: <what to do next time>`.

### Tests and commits

- **Linkage:** each test lists the scenario IDs it proves, and `mise run test -- --spec <id>` selects them. Each run writes `.cache/spec-results.json` with the outcome per ID (passed, failed, error, xfailed or xpassed), which spec-check and status read. spec-check refuses results from a partial run: a selection, or an ini override other than a strictness switch. It also refuses stale results. If any file outside `specs/` and `proof/` changed since the run, run `mise run test` again.
- **Syntax in this repo:** {TEST_TAG_SYNTAX}
- **Entrypoint tests** run the real installed command in a subprocess, never an inner function.
- **skip and xfail:** a new skip or xfail needs a scenario ID in its reason. An xfail (a test expected to fail) is allowed only for `[gap]` scenarios, and it must be strict: an unexpected pass fails the run. pre-commit reads every staged Python file, because a root `conftest.py` or a plugin skips tests too. It refuses a skip named by a string (`getattr(pytest.mark, ...)`, `add_marker("skip")`): write the marker out.
- **Pending:** a non-gap scenario that has no passing linked test yet. Only a branch with an open change may have pending scenarios, and only ones ADDED or MODIFIED since the merge-base (I3).
- **Commit subjects:** Conventional Commits with the types `feat change fix perf refactor build ci docs test chore spec style revert`, and `!` for a breaking change. The subjects git writes itself pass when the subject inside them is conventional: `Revert "<subject>"`, `Reapply "<subject>"`, `fixup! <subject>`. To revert a commit whose subject is not conventional, write `revert: <summary>`.
- **Trailers:**

| Trailer | Where | Meaning |
|---|---|---|
| `Spec: <ids>` | a `feat/`, `chg/` or `fix/` commit that touches source (a test inside a source root is no source) | the scenarios this commit makes pass |
| `Red: <id>: <reason>` | the same commits; printed by `mise run tdd -- red` | how each test failed before the code. prove-red needs it only when a test fails on the old code before its body runs, even with stubs for the missing names |
| `Spec-Guard: <ids>` | bug fixes on `fix/` | neighbouring scenarios that must pass on the old code too; ignored on other lanes and for a changed scenario |
| `Spec-Removed: <ids>` | the commit that deletes scenarios | their tests are deleted in the same commit |
| `Test-Harness: <reason>` | `chore/` and `refactor/` commits that touch test files | a harness-only edit; merge lists it for the human |
| `Spec-Approved: <hash>`, `Merged-By: mise run merge` | written by approve and merge | the audit trail; never typed by hand |

## Gates

```
pre-commit  <  mise run verify  <  CI           <  mise run merge
  staged       whole repo:         verify          CI checks
  subset of    lint, format,       + prove-red     + Definition of Done extras (run-it rows,
  verify       types, secrets,       on PRs          the proof bundle, human checks, the trunk
               test, spec-check    + audit           diff, gate-file diff, lane rules on the
                                     on push         whole branch)
                                                   + bookkeeping (roadmap, CHANGELOG, squash)
```

- Read `<` as "is a subset of": each rung runs the rung before it, plus more.
- `mise run verify` is the local gate. Green verify is the minimum before anyone calls work done.
- This section is the only place the ladder is written out. AGENTS.md and the hook messages link here.
- **What stops shortcuts.** `{DEFAULT_BRANCH}` moves only through merge, abandon or release, a sync to what origin really holds, or the first commit (I16). A `reference-transaction` hook sees every ref move, and `pre-push` refuses pushes to `{DEFAULT_BRANCH}`. `mise install` sets up the rest of the fence in git's config. `receive.hideRefs` refuses pushes into the repo itself, because those skip every client hook. A pinned copy of the `reference-transaction` guard runs even after `reset --hard` or a merge has rewritten `.githooks/` in the working tree. In Claude Code, deny rules and a `pre-bash` hook keep agents off the human gates, the hook settings and the gate files.
- **A sync takes only merged work.** A sync to origin passes only when every first-parent commit it brings carries `Merged-By: mise run merge`. If origin's `{DEFAULT_BRANCH}` moved some other way, the hook lists the commits, and a human decides.
- **Deleting `{DEFAULT_BRANCH}` passes. Recreating it does not.** A human restores it after checking origin: `! PROJECT_MERGE=1 git branch {DEFAULT_BRANCH} origin/{DEFAULT_BRANCH}`.
- **What detects evasion.** Merge writes `Merged-By: mise run merge` into each commit it puts on `{DEFAULT_BRANCH}`. `mise run status -- --audit`, `mise run doctor`, session start and CI (on push) flag any first-parent commit that lacks it. CI re-runs verify.
- Local enforcement is cooperative. A program written outside the repo can get past the hooks. The audit and CI catch the result afterwards.

### Definition of Done

This is what `! mise run merge` checks, in order. `mise run status -- --merge` runs steps 1 to 6 as a read-only preview; validate ends with it, so you see the checks before typing merge.

1. The tree is clean and the branch is a lane branch (`--branch` names another worktree's branch). For feat, the change is `approved`.
2. `mise run verify` is green, with spec-check strict: nothing is pending and no `[NEEDS CLARIFICATION` remains. So every scenario has a passing linked test, or a strict xfail if it is a gap.
3. prove-red and the count guard pass (see below). Lane rules I7, I11 and I12 pass. For feat, each trunk file the branch diff touches is in the `Files:` of a `risk: high` group (I18). If one is not, the plan said leaf where the diff touched trunk: add the file to a `risk: high` group in `plan.md`. The git config that `mise install` sets is in place (`core.hooksPath`, `receive.hideRefs`, the pinned guard), and the hook files equal the committed blobs. For feat, merge also lists the spec edits made since approve as "amended after approval". The list gives the scenarios and spec files, then the change folder's diff. An approved Human check or Run-it row that is gone, reworded or loosened in `validation.md` needs `--reapprove`. It says you read the diff and approve the new list.
4. Run-it rows execute (`timeout 60` each) and match. Then the proof bundle (I23, I24). Each `## Proof` row of a feat change has its capture. It was made on this branch after approve and is not stale, and its files are of its kind's type and not empty. Each feat group has a confidence line; a `low` one is listed first, marked `!`. Every file in `proof/<date>-<slug>/` matches the sha256 its entry records, within the caps. The step prints the folder and the command that renders the page.
5. Human checks, the change's one-way check (for a `one-way:` Rollback line; not one of the 3 in `validation.md`), code that a `chg/` or `fix/` branch committed before its ratchet to `feat` (so before approve), and `Test-Harness:` diffs:
   - with a TTY, merge asks y/N for each;
   - without a TTY (the `!` path), `--attest` is required, and the squash body records the checks plus `attested by <git user.name>`;
   - with zero human checks, merge runs without a flag.

   The trunk diff is asked the same way (I19). Merge prints the branch diff limited to trunk files, in full. With a TTY it asks `read the trunk diff? y/N`. Without one, `--read-trunk` is required, and the squash body records `Trunk read by <git user.name>` with the files. A branch that touches no trunk file asks nothing.
6. If gate files changed (`.githooks/`, `scripts/project.py`, `.gitleaks.toml`, the CI workflow, `.claude/settings.json`, or the `[tasks]` or `[hooks]` of `mise.toml`), or a `## Trunk` entry was removed or changed (I20), the diff is shown and `--gate-change` is required.
7. A close commit on the branch contains the roadmap tick (or the `(unplanned)` insert), the change's `status: done`, and the regenerated `CHANGELOG.md`. On `feat/`, `chg/` and `fix/` it also writes the `## Tests` section of the proof folder's `README.md`, with prove-red's verdict per ID, and nothing else there. For a `flag:` change it also adds `specs/backlog/<date>-launch-<slug>.md`: flip the flag on, then remove it, its off path and its `[flag-off]` scenarios. On a `launch-<slug>` branch it appends ` (launched <date>)` to the roadmap item `<slug>` instead of a tick, on any lane. The CHANGELOG gains exactly one line, the change's entry under `## [Unreleased]`. Merge skips it on `chore/` and `plan/`, and on `refactor/` adds only a `perf` line. It is the branch's last commit and touches nothing else. spec-check accepts a `Merged-By` commit on a branch only when it is this close commit.
8. Land:
   - **With a remote:** push the branch and open a PR. Its body has the shape of `.github/pull_request_template.md`: What, Review depth, Rollback, Proof, Scenarios, Checklist. The Proof section shows each image and GIF inline through its blob URL at the pushed tip, and text in details blocks. Then wait for its checks (team tier: also for an approving review). `gh pr merge --squash` merges it on GitHub with a generated body that ends in `Merged-By: mise run merge`, without `--delete-branch`, since merge syncs `{DEFAULT_BRANCH}` itself. `git ls-remote origin` must show the PR's merge commit, or a later tip that holds it. `git fetch` brings that tip, and `{DEFAULT_BRANCH}` fast-forwards to it under `PROJECT_MERGE` when each first-parent commit it brings carries the trailer. Then the branch is deleted here, and on origin if origin still has it.
   - **No remote:** a local squash onto `{DEFAULT_BRANCH}`. Any worktree with `{DEFAULT_BRANCH}` checked out is fast-forwarded, and the branch is deleted.
9. It prints the next roadmap item, "still right? If not: /sdd replan", then "/clear".

**The squash subject**, which the CHANGELOG line comes from, is the change's `title:` on feat. On the other lanes it is the branch's first commit of a type the lane lands under, unless `--title '<subject>'` names one. The types are `fix` on fix, `change` on chg, `perf` or `refactor` on refactor, `chore build ci docs style test` on chore, and `spec docs chore` on plan. The preview prints it as `lands as '<subject>'`.

**Review depth.** The preview and merge print how much of the diff a human reads, and the squash body keeps it:

```
review depth  trunk: READ  2 files  +31 -4  src/<pkg>/__init__.py (the entrypoint ...), ...
              leaf:  SKIM  6 files  +340 -12  against proof: 4 entries, confidence G1 high, G2 low
```

Trunk files are read in full. Leaf files, tests included, are skimmed against the tests and the proof. The proof folder counts as neither.

The squash body keeps the scenario IDs, the Rollback line, the Proof block, the prove-red table, the check results and the attestation. The Proof block names the folder, the captures per kind, the test proof and each confidence line. It also copies each `Dismissed:` line from the branch's commits, since the branch is deleted. That is the durable record on `{DEFAULT_BRANCH}`.

**prove-red** runs the tests of new and changed scenarios, and of every gap, against the old code. That is the source roots as they were at the merge-base, checked out with `--no-overlay` so files added since then are gone. The tests inside them stay as the branch has them: a test folder such as `src/<pkg>/tests`, and a `test_*.py` or `conftest.py` beside the code.

| Scenario kind | Expected on the old code | Otherwise |
|---|---|---|
| ADDED, MODIFIED, or (on `fix/` and `chg/` only) named in a `Spec:` trailer | failed, error (collection) or strict xpassed: red. Every test function that is new or changed on the branch is red. So is every new case of a parametrized test. Some reds stop before any assertion runs, on a missing name or a fixture error. Others stop on an exception the old code raises. Such a test runs again with stubs for the names the old code lacks. There it must fail on an assertion or a `NotImplementedError`. An exception raised by code that exists counts too, such as the `ValueError` a `fix/` regression test meets. One the test's own code raises does not, such as an `IndexError` from `splitlines()[0]` on empty output. If the stubs cannot get the body to run either, the ID needs its `Red:` trailer | passed or xfailed, also a pass with the stubs: FAIL `<id> pins nothing new` |
| Guard (`Spec-Guard:` on `fix/` for a scenario not changed, or a characterization scenario from setup) | passed | failed: FAIL "guard broke"; a collection error is a warning |
| Flag-off guard (`[flag-off: <ENV>]`, added or modified, any lane) | passed | failed: FAIL "flag-off guard broke: the old behaviour changed with the flag off"; a collection error is a warning |
| Gap (`[gap: <slug>]`), changed on the branch or not | xfailed (strict) | passed or xpassed: FAIL "gap test does not reproduce the gap" |
| Count guard | tests collected at HEAD >= tests collected at the base, minus tests linked only to REMOVED IDs. The base count runs in a worktree at the base: its own tests and pytest config, on its own code | FAIL "tests disappeared" |

A human-only escape hatch exists: `! mise run merge -- --allow <id> --reason "<why>"`, printed into the squash body.

## Invariants

| # | Rule | Checked by |
|---|---|---|
| I1 | `mission.md` and `roadmap.md` are staged only on `plan/` branches. Merge also writes the roadmap. | pre-commit, spec-check |
| I2 | `CHANGELOG.md` is staged only by merge or release. | pre-commit, spec-check |
| I3 | On the default branch each scenario has a passing linked test. A gap has a strict xfail whose reason contains its ID, and its slug is in the roadmap. No orphan tags, and no skip or xfail on a linked test except for a gap. On a branch with an open change, ADDED and MODIFIED scenarios may be pending. | spec-check (verify, CI) |
| I4 | A commit that adds or modifies a scenario stages a test tagged with it. Removing a scenario deletes its tests in the same commit, with a `Spec-Removed:` trailer. | pre-commit, commit-msg |
| I5 | A change folder with `status: done` is frozen. A branch writes only its own proof folder, so a proof folder is frozen once it lands. | pre-commit, spec-check |
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
| I17 | A `plan.md` group whose `Files:` match a trunk entry says `risk: high`. | spec-check, approve |
| I18 | Every trunk file in a feat branch diff is in the `Files:` of a `risk: high` group. | `status -- --merge`, merge |
| I19 | A human confirmed reading the trunk diff before it lands. | merge (the prompt, or `--read-trunk`) |
| I20 | Removing or changing a Trunk entry needs `--gate-change`. | merge |
| I21 | Every feat change has exactly one valid Rollback line. A `service` change that touches trunk cannot say `revert:`, and a `one-way:` change has a `risk: high` group. | spec-check, approve |
| I22 | A `flag:` change has its `flag` row in `.env.example` and a `[flag-off]` guard scenario, which passes on the old code. | spec-check, prove-red |
| I23 | Every `## Proof` row of a feat change is captured on its branch after approve, current and not empty, and each group has a confidence line. | merge, `status -- --merge` |
| I24 | Every proof file matches the sha256 its entry records, stays within 5 MB per file and 15 MB per change, and passes the leak scan. | `mise run proof`, pre-commit, merge |

## Size caps

spec-check warns when a file passes its cap. Split it or cut it. Never raise the cap to fit.

| File | Cap |
|---|---|
| `AGENTS.md` | 40 lines |
| `specs/capabilities/<cap>.md` | 300 lines; split the capability beyond that |
| `requirements.md` | 120 lines |
| `plan.md` | 100 lines |
| `validation.md` | 60 lines; Review focus 5 rows, Proof 6 rows, Human checks 3 |
| `project_memory/README.md` | 1 KB |

The other files under `specs/` and `project_memory/` have no line cap.
