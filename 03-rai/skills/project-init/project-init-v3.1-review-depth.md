---
title: "project-init v3.1: review depth, rollback, proof, launch"
status: built
extends: "[[03-rai/skills/project-init/DESIGN|project-init v3 design]]"
source: "John Kim, How I Review AI Code (youtube.com/watch?v=b2QkhmQ0sT0)"
date: 2026-09-26
---

# project-init v3.1: review depth, rollback, proof, launch

v3 proves that the tests are real (prove-red). v3.1 decides **how much of the diff a human reads**. It turns the video's single knob into rules the tool checks:

```
 how much you read  =  f( blast radius , can it be undone , how much proof exists )
                          trunk map        Rollback line      proof bundle
```

Four parts, each extending something v3 already has:

| Part | Extends | What it adds |
|---|---|---|
| A. Trunk map | `risk: high` on plan groups | Risk is derived from the code rather than guessed. Trunk diffs are read, and leaf diffs are skimmed against proof. |
| B. Rollback | talk's round 1, `.env.example` | Every feat says how it is undone: `revert`, `flag`, or `one-way` |
| C. Proof bundle | breaker lens, Run it rows, prove-red | One place for evidence: test, run, before/after, log, http, screenshot, video, terminal recording, attachments |
| D. Launch | roadmap, validate lenses | Merge-ready is not launch-ready. A whole-feature audit runs per roadmap item, then the flag comes off. |

```
                          talk                 compile + validate               merge                launch
                           |                          |                           |                     |
 trunk map  ---------> Files: hit trunk?  ---> risk: high pause --------> trunk diff shown,  ---> audit whole item
                        -> risk: high                                      --read-trunk
 Rollback   ---------> revert|flag|one-way --> flag-off guard scenarios -> guards pass on base -> flag removed (chg)
 proof      ---------> ## Proof rows      ---> mise run proof ...  -----> every row captured,  -> proof.html per change
                        (approved)             auto test proof            summary in squash
```

---

## A. The trunk map

### A.1 Format

`specs/tech-stack.md` gains a section:

```markdown
## Trunk
- src/tipcalc/__init__.py: the entrypoint every command runs through
- src/tipcalc/config.py: settings every module reads
- migrations/**: schema changes reach every row
```

- One line per entry: `- <glob>: <why>`. The why is required. A glob uses gitignore-style matching (`**` crosses directories) and is relative to the repo root.
- A path is **trunk** when any entry matches it. Everything else, tests included, is **leaf**.
- An empty section is valid. A repo with no Trunk section is treated as all leaf, and `doctor` warns.
- The product template's placeholder line fails spec-check, as a line of another shape does, until talk replaces it.

### A.2 Who writes it

- **P1 probe** proposes candidates and writes nothing. It is a static scan of the tracked files, so the list prints even when the sandbox cannot run:
  - every console-script target module in `[project.scripts]`;
  - modules with high fan-in: imported by at least `max(3, min(ceil(25% of the package's modules), 10))` other modules of the same package (an AST import scan, relative imports resolved, no execution). The cap keeps a big package's shared module in: orca's `core/config.py` has 38 importers, under 25% of its package;
  - settings modules that the env contract rows name in `read in`: named like `config` or `settings`, or holding a pydantic-settings class. With no contract yet (an adoption), a `config.py` or `settings.py` counts by name. It must sit at its package's root, or 2 modules outside its own folder must import it. orca's ten per-source configs stay leaf;
  - `migrations/`, `alembic/` and `schema/` folders outside the tests, and top-level folders that hold `*.sql` files. Also any tracked code or schema path that a standing rule S-n names in a code span. A rule's `.env.example`, docs, and paths under `specs/`, `project_memory/`, `proof/` or `docs/` are never candidates: `.env.example` as trunk would put every flag change on trunk.
- **P2 talk** shows the candidates with their reason and asks one question: keep all (Recommended), edit (drop or add), or start empty. The answer is written into `tech-stack.md` on `plan/project-init`. With no candidates the section starts empty, and a headless run keeps all. SCAFFOLD talks before any code exists, so P3 runs the scan once `uv init --package` has committed the entrypoint, and asks the question then.
- **EXTEND** on a v3.0 repo runs the same scan. `render --check` prints a `trunk` item with the candidates, counted as drift, whenever `tech-stack.md` has no Trunk section. P2 then proposes the section on the `plan/` branch.
- **Later edits** happen on any lane branch. Adding an entry is free. Removing or changing one (its glob or its why) counts as a gate-file change: merge shows the Trunk diff and requires `--gate-change`. Shrinking the trunk is the cheapest way to dodge review.

### A.3 What checks it

| Where | Check |
|---|---|
| spec-check, on `plan.md` | A group whose `Files:` match a trunk entry must be `risk: high`. The failure names the file and the entry's why. |
| status and merge (feat) | Each trunk file in the real branch diff must be in the `Files:` of some `risk: high` group. Otherwise FAIL: "the plan said leaf, the diff touched trunk: add it to a risk: high group". That plan edit is listed as amended after approval. |
| merge, every lane | **Trunk step:** the diff restricted to trunk files is printed in full. With a TTY, merge asks "read the trunk diff? y/N". Without one, `--read-trunk` is required, and the squash body records `trunk read by <user.name>`. With no trunk files the step prints `none` and asks nothing. |
| compile | A `risk: high` group pauses as in v3. The pause message now names which of its files are trunk. |

At merge, the trunk is HEAD's entries plus those of the merge-base that the branch removed or changed. So an I20 edit cannot hide the files it drops from I18 and I19 on the same branch. The trunk step sits in step 5 of the Definition of Done, beside the Human checks, since both are asked the same way.

### A.4 Review tiers, as merge and the PR print them

```
review depth  trunk: READ   2 files  +31 -4   src/tipcalc/__init__.py (the entrypoint ...), config.py (...)
              leaf:  SKIM   6 files  +340 -12 against proof: 9 entries, confidence G1 high, G2 medium
```

Design pressure: new behaviour goes into leaf modules. The trunk edit shrinks to the seam, usually one call behind a flag, so the part you must read stays small.

---

## B. Rollback

### B.1 The Rollback line

`requirements.md` gains a required section with exactly one line:

| Line | Meaning | Allowed when |
|---|---|---|
| `revert: <why a revert of the squash is enough>` | Undo = `git revert` of one commit | Any repo whose Distribution is not `service`, and a `service` change that touches no trunk file |
| `flag: <ENV_NAME>` | The new behaviour runs only with the flag on. Its default is off. | Always |
| `one-way: <what cannot be undone>` | A data migration, published interface, sent message, or deleted data | Always. It forces extra checks (B.3). |

A `service` change that touches trunk must say `flag:` or `one-way:`. spec-check refuses `revert:` there, because the Distribution line and the plan's `Files:` are enough to decide.

Talk asks it in round 1 as the fourth topic: **Rollback: if this goes wrong after merge, how is it undone?** The options are the three lines, with the recommendation computed from the Distribution and the trunk hit. So round 1 of a feat holds four questions, one past the usual cap of 3.

The section is the last one of `requirements.md`. Its one line may start with `- `. A change that was approved before v3.1 and lacks the section only gets a warning, so upgraded repos stay green.

### B.2 Flags

- **The env contract** gets a third kind, `flag`: `APP_FLAG_SAVE_CARD | flag | bool | no | 0 | save-card (change 2026-09-26-save-card)`. Its type is always `bool` and its default is always off. `doctor` checks both.
- **The code** reads the flag at one seam in the trunk. The new behaviour lives in leaf modules the seam calls.
- **Scenarios** for the new behaviour carry `GIVEN APP_FLAG_SAVE_CARD=1`.
- **Flag-off guards:** at least one scenario tagged `[flag-off: APP_FLAG_SAVE_CARD]` pins the old behaviour with the flag off. It is the video's "control experience that must not change". prove-red treats it as a guard: it must **pass** on the base code. This is the feat-lane equivalent of `Spec-Guard:` on fix.
- **spec-check** on a `flag:` change requires the env row of kind `flag` and at least one `[flag-off: <ENV>]` scenario. A `[flag-off]` tag whose ENV is not a flag row fails.
- **Merge's close commit** also writes `specs/backlog/<date>-launch-<slug>.md`: "flip <ENV> on, then remove the flag, its off path and its `[flag-off]` scenarios". The launch in part D consumes it.
- **Flag debt:** `doctor` warns for any flag row whose change merged more than 30 days ago. The date is that of the first commit on the default branch that added the row's line, which is the squash of its change.
- A `[flag-off]` scenario that a branch adds or changes is a flag-off guard on every lane, also when a `fix/` or `chg/` commit names it in `Spec:`. The close commit may add one `<date>-launch-<slug>.md` for a `flag:` change, and no other new file.

### B.3 One-way doors

- The change needs at least one `risk: high` group. spec-check refuses a `one-way:` change with none, and talk puts the one-way work in that group.
- Merge adds a Human check of its own: "I read the one-way part: <what>". It is asked like the others, or covered by `--attest`, and it is not counted against the cap of 3 in `validation.md`.
- The squash body records the one-way line, so `git log` shows every irreversible change.

---

## C. The proof bundle

The human reads proof, not code, for leaf diffs. Proof comes in nine kinds, and each has a capture command that the agent runs headless. Nothing ever opens a window on the desktop.

**One proof per case.** A change never collects every kind. Each case, a scenario or a group, gets the single kind that shows it best (C.3). Test proof is automatic and does not count.

### C.1 Where it lives

Proof is committed on the lane branch, and the pull request shows it. A reviewer who never runs the code still sees the screenshots, recordings and before/after output.

```
proof/<date>-<slug>/                 tracked, one folder per change, any lane; frozen at merge like a change folder
  README.md                          the index: one entry per case, newest last. GitHub renders it with media inline.
  G1-run-no-args.txt                 captured files, named <group or id>-<verb>-<slug>.<ext>
  G2-video-save-flow.webm            the full recording
  G2-video-save-flow.gif             its inline preview (C.2)
  G3-shot-saved-list.png
  G4-tape-interactive.gif
```

- On feat, `<date>-<slug>` is the change folder's name. On the fast lanes it is the author date of the branch's first commit (today while it has none) plus the slug. So every lane has one.
- The folder is written only by `mise run proof`, and by merge's close commit (C.2, test). A hand edit of a captured file breaks its sha256, and pre-commit and merge refuse it. A branch writes only its own folder, so a folder that landed is frozen (I5).
- A capture records the commit it shows, so the tree must match HEAD, `specs/` and `project_memory/` aside.
- **One entry per case.** A new capture for a case (a scenario ID or `G<n>`) replaces its entry, whatever the kind. The old files go (`git rm`) in the capture's own commit, and the tool prints `replaced <kind> captured at <sha>`. So a stale capture leaves nothing behind once it is taken again. Confidence lines are one per group, replaced the same way. A `README.md` edited by hand to hold two entries for one case fails merge and its preview.
- **Ratchet.** A `chg/` or `fix/` branch can ratchet to feat. The ratchet's commit then moves its folder to the change folder's name with `git mv`, so the captures carry over. Rows still need captures made after approve.
- The review depth (A.4) counts the proof folder as neither trunk nor leaf: it is what the leaf is skimmed against.
- File names use the verb (`shot`, `tape`), and entry headings the kind (`screenshot`, `terminal`). A video's steps file is not kept: a `.py` under `proof/` would go through ruff and ty in pre-commit.
- **Size caps:** 5 MB per file, 15 MB per change. A capture over the cap is refused with the flag that shrinks it (`--viewport`, `--seconds`, `--width`). The caps keep a year of changes in the low hundreds of MB, so plain git carries it without LFS.
- **`.gitattributes`** marks `proof/**` media as `binary -diff`, so diffs and blame skip it.
- **Leak scan before write:** every text capture has the home directory replaced by `~`, and gitleaks scans it with the repo's rules. A capture with a secret is refused, and nothing is written. Screenshots and videos show fixtures only, never real accounts or personal data.
- **Commits:** each capture is one commit on the branch, subject `docs(proof): <id> <kind>`, touching only its `proof/` folder. No `Spec:` trailer is needed, because no source changed. A fast lane's squash subject is never such a commit.
- **Test results:** `proof/` joins `specs/` and `.cache/` as paths that never change a test outcome, so a capture does not make `.cache/spec-results.json` stale.
### C.2 Proof kinds

| Kind | Command (agent-runnable) | Captures | Fits |
|---|---|---|---|
| test | automatic: `mise run proof -- tests`, and merge's close commit on feat, chg and fix | per scenario ID: test node, red reason (the `tdd red` record, else the `Red:` trailer), the last run, and prove-red's verdict at merge | every lane that has scenario IDs |
| run | `mise run proof -- run <id> [--before] -- <cmd...>` | command, exit code, stdout and stderr (4 KB each, head and tail), duration. `--before` runs the same command on the merge-base code in a throwaway worktree and stores the pair. | CLI output, scripts, `curl` for HTTP, `duckdb`/`sqlite3` for data, `grep` over logs |
| log | `mise run proof -- log <id> <file> [--grep <re>] [--since <marker>]` | an excerpt of a runtime log written during the run | services, jobs, pipelines |
| http | `mise run proof -- http <id> <METHOD> <url> [--data <json>]` | request line, status, headers, and the body head. Refused unless the host is localhost or 127.0.0.1. | APIs |
| screenshot | `mise run proof -- shot <id> <url> [--selector <css>] [--viewport 1280x800] [--dark]` | a full-page PNG from headless Chromium via Playwright | web UI |
| video | `mise run proof -- video <id> <url> --steps <file.py> [--seconds 15]` | a WebM from Playwright's `record_video`, driven by a short steps file of page actions. Also a GIF preview (ffmpeg, 800 px wide). GitHub plays only uploaded videos inline. | web flows: click, type, save |
| terminal | `mise run proof -- tape <id> <file.tape>` | a GIF of a real terminal session rendered by vhs from a `.tape` script; the tape is committed beside it, so anyone can re-render it | interactive CLI, TUI |
| attach | `mise run proof -- attach <id> <file> --caption "<text>"` | any existing file: png, jpg, gif, svg, webm, mp4, cast, pdf, txt, json, csv | anything captured another way (an asciinema cast, a chart the test wrote, a PDF export) |
| confidence | `mise run proof -- confidence <G#> high\|medium\|low -- "<why>"` | one line per group, written by validate | every feat group |

`<id>` is a scenario ID or a group `G<n>`. Every entry records the commit it was captured at, and a sha256 for files.

Capture tools are external and optional per repo:
- **Playwright** runs via `uv run --no-project --with playwright==1.63.0`. It drives the system's `/usr/bin/chromium` when there is one (or `PROJECT_PROOF_CHROMIUM`), else its own Chromium. `mise run proof -- setup web` installs Playwright's ffmpeg, which its video recorder needs, and its Chromium only when the system has none.
- **vhs** is pinned in `mise.toml` (`aqua:charmbracelet/vhs`) only when `setup terminal` is run.
- **ffmpeg** makes the video previews. `setup web` checks for it.
- A kind whose tool is missing refuses with the setup command, never a partial capture.
- P1 probe names the surface from the declared runtime dependencies: a web UI, a terminal UI, console scripts only, or none. The framework lists are project.py's `WEB_UI_FRAMEWORKS` and `TUI_FRAMEWORKS`, which init.py reads from its source and never copies. P7's punch list names `mise run proof -- setup web` or `setup terminal` for the first two. P5 runs `mise run proof -- --help` with the other task checks.

### C.3 The contract: `## Proof` in `validation.md`

Talk decides which proof the change owes, next to Review focus and Human checks. Approve freezes it, so approving `validation.md` approves the proof list, the same way it approves the tests.

```markdown
## Proof   (what a human looks at instead of reading leaf code; test proof is automatic)
| for | kind | shows |
| cli.save-card | run --before | `tipcalc save 12` prints `saved 1 card`; before: exit 2 |
| G2 | video | open /cards, click Save, the card appears in Saved |
| G3 | screenshot | the Saved list in dark mode |
```

- Capped at 6 rows; a seventh warns, as the other caps of `validation.md` do. Each row names a scenario ID or group of this change, and a kind other than test and confidence.
- **One row per case.** A second row for the same scenario or group fails. A case with no row relies on its test proof alone.
- Talk picks the kind from what the case changes:

| The case changes | Kind |
|---|---|
| what a command prints or exits with | run (`--before` when the old output matters, always on fix) |
| a page's look | screenshot |
| a flow across clicks or pages | video |
| an interactive terminal session | terminal |
| an API response | http |
| a background job or service behaviour | log |
| anything captured another way | attach |
- The repo has a UI when its declared runtime dependencies include a known web or TUI framework. The list holds Django, Flask, Streamlit, Gradio, Dash, NiceGUI, Reflex, Panel, FastHTML, Flet, Textual, urwid, prompt-toolkit and a few more. An HTTP API framework such as FastAPI does not count: its proof is http. A feat with no screenshot, video or terminal row then gets a warning from spec-check and approve. The human sees the gap before approving.
- A dropped or loosened row after approve needs `--reapprove`, the same rule as Human checks and Run it.

Fast lanes have no `validation.md`. Their `proof/` folder has the automatic test proof, written by validate. On `fix/`, validate always captures `run --before` of the reproduction: the bug on the old code, and the fix on the new.

### C.4 Staleness

An entry is **stale** when a later commit on the branch changed a file outside `specs/`, `proof/`, `project_memory/` and `CHANGELOG.md` (only merge writes it). The preview marks it stale, and the human decides whether it still shows the truth. It is not a failure. A stale entry that fills a `## Proof` row is a failure, because recapturing is one command.

### C.5 What merge checks (a new DoD step, after Run it)

The step runs in merge's cheap pass, so a missing capture refuses before verify and prove-red run. It prints after Run it.

1. Each `## Proof` row has a matching entry, captured on this branch after approve, not stale, with a non-empty file of the kind's media type.
2. Each feat group has a confidence line. A `low` line is listed first with an attention marker. It is not a failure, because the human reads it.
3. Every file in the folder matches the sha256 its README entry recorded, and the caps from C.1 hold.
4. The step prints the folder path and `proof.html`. It never opens them.

The preview (`status -- --merge`) runs the same checks read-only.

### C.6 The durable record and the pull request

- The `proof/<date>-<slug>/` folder lands on the default branch with the squash, so the record is the folder itself.
- The squash body gains a Proof block: counts per kind, each confidence line, and the folder path.
- **With a remote**, merge writes the PR body from section E. It embeds each image and GIF through its blob URL at the pushed tip (`https://github.com/<owner>/<repo>/blob/<tip>/proof/<...>/<file>?raw=true`), so the review page shows the proof inline. That works on a private repo for anyone with access. A WebM appears as a link beside its GIF preview. The PR's Files tab also renders `proof/<...>/README.md` with its media. Owner and repo come from origin's URL; an origin with no host (a local path) gets relative links.
- The PR body ends with the squash body, folded in a `<details>` block. The squash commit itself keeps the plain record. A PR that is already open keeps the body it was opened with.

### C.7 Viewing

`mise run proof -- show` renders `.agent/proof/<date>-<slug>.html` (untracked) from the folder's README: the review-tier header from A.4, confidence lines, the test proof, then entries grouped by scenario. Images appear inline, videos in `<video controls>`, terminal recordings as GIFs, and run and http entries as before/after text panes. It has no external requests: each image and video is inline as a `data:` URI. It prints the path and never launches a browser.

---

## D. Launch

Merge-ready is the first 80%. Launch is the last 20%: a whole-feature audit, then the flag comes off.

### D.1 `/sdd launch <roadmap-slug>`

Agent-runnable, on the default branch with no change open. The audit itself opens no lane: each fix it needs is a lane of its own, and the launch ends with the lane `launch-<slug>`. The text is `.claude/skills/sdd/launch.md`.

1. It collects the squash commits whose change names this roadmap slug. A feat change names it in its folder's `roadmap:` field, found by the squash body's `Change: <folder>`. A fast lane names it in `Branch: <lane>/<slug>`. The audited diff is the first such commit's parent up to HEAD, limited to the files those commits touched.
2. The launch file is `specs/backlog/<date>-launch-<slug>.md`, named by the roadmap slug. Merge writes it for a `flag:` change (B.2), and `mise run backlog -- launch-<slug>` makes it otherwise.
3. It runs the launch lenses, each as its own fresh subagent with the same inputs, told only its lens:
   - **performance:** hot paths, N+1s, unbounded reads, startup cost;
   - **security:** input trust, secrets, injection, file and network reach;
   - **conformance:** the feature against the scenarios, mission and roadmap wording as a whole, not per change;
   - **simplicity:** dead code, duplicate helpers, names, and leftovers from broad strokes (the video's cleanup pass).
   - In the vault, `/compile launch <slug>` follows the same text and adds `/adversarial-review` over the same diff.
4. Every finding gets a v3 outcome: a backlog item, a fix, chg or refactor lane started now, one at a time, or a `Dismissed:` line. Each is written under `## Findings` in the launch file. A run after a lane's merge resumes at the next open finding.
5. It writes a launch checklist for the human into the launch file. The human uses the feature end to end, opens each change's proof (`proof/<date>-<slug>/README.md`, or validate's `proof.html`), and lists what felt wrong. Taste is the human's.
6. The launch file is written on the default branch, where nothing commits. So `mise run change` lets a backlog file there, new or edited, ride into the next lane branch, which commits it alone.
7. **The launch lane** comes last, once every finding has its outcome and the checklist is ticked:
   - **With a flag:** `chg/launch-<slug>`. One commit flips the default and deletes the flag row, the off path and the `[flag-off]` scenarios with `Spec-Removed:`. The new behaviour's scenarios drop `GIVEN <ENV>=1`, so they are MODIFIED and prove-red wants them red on the old code, where the flag is off. The lane stays chg whatever its scenario count, since Q7 does not apply. It removes the flag's scaffolding and turns on behaviour already specified and proven.
   - **Without a flag:** `chore/launch-<slug>`, one commit. It is empty (`--allow-empty`) when the launch file was never committed.
   - Either way, that commit deletes the launch file, and its body holds the launch record: the range, each finding with its outcome, the checklist. The squash keeps the body of its subject commit, so the record lands.

### D.2 Roadmap mark

- A branch whose slug is `launch-<slug>` launches the roadmap item `<slug>`, on any lane. Merge's close commit appends ` (launched <date>)` to that item and ticks nothing. The item must be ticked and not launched yet, or step 7 fails with the reason. `ROADMAP_ITEM_RE` still reads the marked line as the same ticked item. So no other slug starts with `launch-`.
- The close commit of a launch branch may change the roadmap only that way: one line, the mark appended where it stands (spec-check, `close_commit_problem`). Outside feat, no other close commit touches the roadmap.
- `mise run status` on the default branch with no change open lists the ticked items without `(launched`, those with a live flag first. A flag row of `.env.example` is live for an item in two cases. A change of the item names it in its Rollback line, or the row's notes name the item or one of its change folders. One line gives the count and the next `/sdd launch <slug>`, and at most 4 items follow. With every item launched, or none ticked, it prints nothing.
- Items ticked before v3.1 are listed too. A replan marks them by hand, since the roadmap changes on plan/ branches.

---

## E. Pull request and squash body

`pull_request_template.md` and the generated body both follow this shape. The rule is that the summary is shorter than the diff.

```markdown
## What        (at most 3 lines)
## Review depth
trunk: READ  <files, each with its why>      leaf: SKIM  <n files> against proof
## Rollback    revert | flag: ENV | one-way: <what>
## Proof       confidence G1 high, G2 medium: <why>
<one row per ## Proof entry: the image or GIF inline, the run output in a details block>
full index: proof/<date>-<slug>/README.md
## Scenarios   <IDs>
## Checklist   (v3's, plus: the Trunk section is current; a flag has its [flag-off] guard;
                the Proof rows are captured and current)
```

---

## F. Invariants added

| ID | Invariant | Enforced by |
|---|---|---|
| I17 | A plan group that touches trunk is `risk: high` | spec-check |
| I18 | Every trunk file in a feat diff is in a `risk: high` group | status, merge |
| I19 | A human confirmed reading the trunk diff before it lands | merge (`--read-trunk` or TTY) |
| I20 | Removing or changing a Trunk entry needs `--gate-change` | merge |
| I21 | Every feat has exactly one valid Rollback line; `service` + trunk excludes `revert` | spec-check |
| I22 | A `flag:` change has a `flag` env row and a `[flag-off]` guard that passes on base | spec-check, prove-red |
| I23 | Every `## Proof` row is captured, current and non-empty, and each feat group has a confidence line | merge, `status -- --merge` |
| I24 | Proof files match their recorded sha256, stay within the caps, and pass the leak scan | proof, pre-commit, merge |

---

## G. Implementation plan (test-first, each on its own commit series in the skill's tests)

| M | Scope | Files |
|---|---|---|
| M12 | Trunk map: parse, spec-check I17, status and merge I18-I20, `--read-trunk`, review-tier print | `templates/scripts/project.py`, `specs-README.md`, `tests/test_check.py`, `tests/test_lifecycle.py` |
| M13 | Probe candidates and the talk question, EXTEND upgrade proposal | `phases/1-probe.md`, `phases/2-talk.md`, `phases/8-extend.md`, `scripts/init.py`, `tests/test_init.py` |
| M14 | Rollback: section lint I21, the `flag` env kind, the `[flag-off]` tag, prove-red guard I22, close-commit launch backlog, doctor flag debt | `project.py`, `tests/test_prove_red.py`, `tests/test_check.py` |
| M15 | Proof: the `proof` task and its verbs (C.2, plus `tests` and `setup`). The leak scan and caps. `## Proof` lint, the merge step I23-I24, the squash block, the PR body embeds. | `project.py`, `mise.python.toml`, `gitattributes`, `settings.json`, `pull_request_template.md`, the `validation.md` templates, `tests/test_proof.py` (new) |
| M16 | Launch: `sdd/launch.md`, status listing, roadmap mark | `templates/skills/sdd/launch.md` (new), `SKILL.md`, `project.py` |
| M17 | Text: the sdd skill (talk, compile, validate), the PR template, the specs README, the AGENTS.md template. The vault's `12-system/templates/sdd/`: Trunk, Rollback, Proof sections. Playbook `11-workflows/21-project-init.md`. | templates, `12-system/templates/sdd/`, `11-workflows/` |
| M18 | Acceptance: tipcalc empty-folder run through one flagged feat with web-free proof (run --before, tape), one trunk-touching fix, and a launch. Then EXTEND on a v3.0 repo copy. | scratch acceptance, reports in `~/.cache/project-init-v3-reports/` |

Screenshot and video capture are verified on a tiny local HTTP fixture served on localhost inside the test, with Chromium headless. Tests that need Playwright or vhs skip with the setup command in their reason when the tool is absent. They are marked, so a machine without the tools still runs the full core suite.
