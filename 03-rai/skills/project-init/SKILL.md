---
name: project-init
description: >
  Puts a folder or repo on the spec-driven, test-driven standard: a specs/ constitution written
  from a real conversation, mise tasks, git gates that keep main behind `mise run merge`, one
  portable `sdd` skill, team memory, CI when a remote exists, and a punch list for the human.
  USE WHEN the user runs /project-init, or asks to start a project in an empty or new folder,
  set up or adopt an existing repo (AGENTS.md, .claude/, hooks, CI, mise, specs), audit or
  upgrade a repo that already has project-init (drift, a new remote, v2 to v3, v3.0 to v3.1),
  or migrate a legacy memory layout (accumulated_knowledge.json, sessions/, pending/,
  summaries/, chromadb/, project-session hooks). The mode is detected, never asked.
  `/project-init --plan` runs preflight and probe only and writes nothing.
argument-hint: "[--plan]"
---

# project-init v3

One run takes a folder or a repo to the point where `/sdd` can build its first feature. It reads the evidence and probes the code in a sandbox. Then it talks with you until the constitution in `specs/` is complete. It renders the machinery and proves each gate blocks what it should. It stops at the first human gate: `! mise run merge`.

The standard is defined in `templates/specs-README.md`, which P4 renders as `specs/README.md`. The approved design is [DESIGN.md](DESIGN.md), with every hole and finding it closes. Read its section 6 when a phase file is not enough.

**v3.1** adds review depth ([project-init-v3.1-review-depth.md](project-init-v3.1-review-depth.md)). It brings a trunk map in `specs/tech-stack.md` (P1 proposes it, P2 settles it), a Rollback line per feat, a proof bundle and a launch step. EXTEND takes a v3.0 repo there (P8).

## Modes (P0 detects them; the first match is the mode)

| Mode | Detected by | Phases |
|---|---|---|
| EXTEND | `.project.toml` exists | 0, 1, 8; then 2 (gaps only), 4-7 for what changed |
| EXTEND + v2 migrate | `Standard: project-init v2` stamp in `project_memory/README.md` or `AGENTS.md` | 0, 1, 9 (v2 part), 2, 3 (rename only), 4-7 |
| MIGRATE | any of `accumulated_knowledge.json`, `sessions/`, `summaries/`, `pending/`, `chromadb/` under `project_memory/` (a root-level `sessions/` or `pending/` is the project's own code), or `.claude/hooks/project-session-*.py` | 0, 1, 9 (v1 part), 2, 3 (rename only), 4-7 |
| SCAFFOLD | no code, and no `.git` or a `.git` with no commits | 0, 2, 3, 4-7 |
| ADOPT | everything else | 0, 1, 2, 3 (rename only), 4-7; a tracked `.agent/` is read in 2 and untracked in 4 (D7) |
| `--plan` | the argument | 0 and 1, then the report; no writes anywhere |

A `.claude/` folder on its own never changes the mode.

A repo with code but no stack pack stops in P0, in every mode but SCAFFOLD: v3 ships the Python pack only (a root `pyproject.toml`). The stop offers `specs/` and memory only, with no gates ([phases/0-preflight.md](phases/0-preflight.md)).

## Flow

```text
 P0 preflight   read-only facts, stops, signals            init.py preflight
 P1 probe       entrypoints in a scratch clone, no network; init.py probe
                UI surface and trunk candidates from a static scan
 P2 talk        vault + repo intake, question rounds,       agent (Write tool), sdd talk text
                constitution + entry capability in specs/
 P3 scaffold    SCAFFOLD: uv init + bootstrap commit, then  agent (Bash), init.py probe
                the Trunk question from the new entrypoint
                others: master -> main when no remote
 P4 generate    branch plan/project-init; D7; the pin,      init.py prepare, init.py render,
                the dev group; machinery                    then mise install
 P5 verify      every command runs; every bypass FAILS      init.py selftest
 P6 front door  AGENTS.md + README quickstart, last          init.py render --front-door
 P7 ship        pathspec commit, remote if chosen, punch     init.py publish
                list
      |
 [G1 HUMAN]  ! mise run merge      (project-init stops here and never runs it)
      |
      v
 the repo loop: /sdd "<what you want>"   (Rai: /grill to talk, /compile to build, per D6)
```

## Phase files

Read the phase file before you run the phase. Each one says what to run, what to check, when to stop, and what it writes.

| Phase | File | Job |
|---|---|---|
| P0 | [phases/0-preflight.md](phases/0-preflight.md) | Mode, git state, stops, signals, tools, env reads |
| P1 | [phases/1-probe.md](phases/1-probe.md) | Run the real entrypoints, find crashes, name the UI surface, list trunk candidates |
| P2 | [phases/2-talk.md](phases/2-talk.md) | Intake (vault + repo), sanitize, question rounds, constitution |
| P3 | [phases/3-scaffold.md](phases/3-scaffold.md) | First commit for an empty folder; default-branch rename |
| P4 | [phases/4-generate.md](phases/4-generate.md) | Render the machinery on `plan/project-init` |
| P5 | [phases/5-verify.md](phases/5-verify.md) | Positive checks + the negative matrix |
| P6 | [phases/6-front-door.md](phases/6-front-door.md) | AGENTS.md and README quickstart from commands that ran |
| P7 | [phases/7-ship.md](phases/7-ship.md) | Commit, optional GitHub remote, punch list |
| EXTEND | [phases/8-extend.md](phases/8-extend.md) | Hash-aware audit and upgrade |
| MIGRATE | [phases/9-migrate.md](phases/9-migrate.md) | v1 JSON layout, v2 to v3, committed `.agent/` |

## Rules

- **R1.** Never ask about the standard. Ask about the product: its gaps, round after round until the constitution is complete (P2, at most 4 rounds).
- **R2.** Every command in a generated file ran green here, or ran its declared `--dry-run` form.
- **R3.** Every write is hash-aware. An unchanged render is updated. A customized file gets a diff and a question.

Hard limits that follow from the design:

- **Human gates.** Never run `mise run approve`, `merge`, `abandon` or `release`, and never set `PROJECT_MERGE`. G1 is typed by the human.
- **Machinery goes through `init.py render`.** Never write a machinery file with the Write or Edit tool. The Write tool is for product text only: `specs/mission.md`, `tech-stack.md`, `roadmap.md`, `capabilities/`, `backlog/`, entrypoint tests, ADRs in `project_memory/decisions/`, and in a v2 migration the retiring lessons appended to `project_memory/lessons.md` (P9).
- **P0 and P1 write nothing** to the repo. P1 works in a scratch clone.
- **Stage by explicit path.** Never `git add -A` or `git add .`.
- **The repo never names the vault.** No vault paths, wiki-links, personal tooling or 1Password item names in tracked files. The gitleaks leak rules block what the sanitizer misses (I14).
- **The vault is read-only** for this skill. The one write is the redacted transcript archive in P9.
- **No `CLAUDE.md` or `CLAUDE.local.md`** in the repo: either one switches off native AGENTS.md loading.
- **Diagrams in repo files are ASCII.** GitHub renders no D2, and Mermaid is retired.
- **Kill by PID, never `pkill -f`.** Builds go to `$TMPDIR`. Never `gitleaks dir .` on a repo (it scans `.env` and `.venv/`).

## scripts/init.py

All deterministic work runs through one PEP 723 script, stdlib only, Rai-side. It is never copied into a repo. The phase files are its specification: when the two disagree, fix both in the same commit. `init.py <command> --help` lists every flag.

Every call is one line, typed from the repo root:

```sh
env -C ~ ~/.claude/skills/project-init/scripts/init.py <command> "$PWD" [flags]
```

`env -C ~` starts the script outside the repo, and `"$PWD"` names the repo. `uv` is usually a mise shim, and a shim refuses to run in a folder whose `mise.toml` is not trusted yet. That happens to an EXTEND repo on a new machine, and to any repo between render and `mise trust` in P4.

| `<command> [flags]` | Phase | Job |
|---|---|---|
| `preflight` | P0 | Read-only facts, mode, stops, signals, vault matches. Exit 1 on a stop. |
| `probe` | P1 | Scratch-clone probe of every console script and env read. Then the UI surface and the trunk candidates, from a static scan. Never writes the repo. |
| `prepare [--python X.Y] [--dry-run]` | P4 | Before render, on `plan/project-init`. With no `.python-version`, it pins the first version that builds, before any `uv add` or `uv sync`. `--python` is the one P1 reported. Then `uv add --dev` of ruff, ty, pytest and the project's own test extras and groups, `uv lock` and `uv sync --locked`. |
| `render [--check] [--remote github] [--values <json>]` | P4, P8 | Renders machinery hash-aware and records `[generated]` hashes in `.project.toml`. `--remote github` adds the CI file for a remote P7 will create. `--values` fills a placeholder render could not derive. `--check` writes nothing. It lists each file as ok, missing, upgrade or customized, with the diff of a customized one, and each CI push-branch drift (H15). A customized front-door file is diffed against the version P6 wrote. One whose template changed since P6 is listed as upgrade, or as customized when it is kept. It also names git gates that are off in this clone, and audits past a local-folder origin that a writing render refuses. A `specs/tech-stack.md` with no `## Trunk` section is a `trunk` item with its candidates (the v3.1 upgrade). A customized file blocks the write until it is answered: `--keep-file <path>` keeps yours, `--force-file <path>` takes the render. `--agents-symlink` adds `.agents/skills/sdd`. |
| `render --front-door` | P6 | AGENTS.md and the README quickstart region, only from commands P5 recorded green. |
| `selftest [--start-args '<args>'] [--suite-timeout <s>]` | P5 | Positive checks under `timeout 60`, the happy path last, then the repo's own `project.py selftest` in one subprocess: the negative matrix of the gate cases in `specs/README.md#gates`. `mise run verify` and `test` run the whole suite, so they get max(600 s, twice the last run), or `--suite-timeout`. Writes `.agent/project-init/verify.json`. |
| `publish [--remote github] [--repo <name>] [--dry-run]` | P7 | The ship commit `chore(init): project-init v3` on `plan/project-init` (EXTEND: `... v3 upgrade` on its own branch): named paths plus `git add -u`, never `-A`, and a body written from `verify.json`. It refuses until P6 ran and `verify.json` is green and fresh. A re-run amends a late change into the same commit. `--remote github` adds the remote steps. It creates the private repo, named after the folder or `--repo`, and pushes main. It records the origin and the server rules state, and gives the README quickstart its clone line. Then it pushes the branch and sets the repo options. It refuses while `.agent/` is tracked (D7). Each is recorded in `.agent/project-init/publish.json`, so a re-run continues at the one that failed. `--dry-run` prints the staging, the files it leaves out, the commit and the remote steps, and runs nothing. |
| `migrate-v2 [--apply]` | P9, P4 | EXTEND + v2 migrate. Without `--apply`: the one migration prompt, each v2 item with its fate and each lesson the migration contradicts; writes nothing. With `--apply`, on `plan/project-init` after the yes and P2: `git mv .mise.toml mise.toml`, the v2 hooks unregistered, then the deletions staged, and `.claude` out of the ruff `extend-exclude`. It refuses until every D-NNN has its ADR. |
| `migrate-transcripts [--resume]` | P9 | Quarantine, redact, rescan, then copy to the helm session archive. `--resume` finishes a quarantine a run left unfinished. |
| `migrate-v1 [--apply]` | P9, P4 | MIGRATE. Without `--apply`: the v1 prompt, each item with its fate; writes nothing. With `--apply`, on `plan/project-init` after the transcript step: the legacy knowledge report in `specs/backlog/`, the project-session hooks unregistered, `git rm` of `accumulated_knowledge.json` and the hooks, and the legacy `.gitignore` block removed. It refuses while a store is still in the repo. |

From P4 on, the session runs under the repo's own `.claude/settings.json`. It names two hooks. SessionStart (`project.py hook session-start`) prints the derived block. It shows the branch and change, the next group, the audit and the newest lessons and ADRs, and says loudly when the hooks are off. PreToolUse:Bash (`project.py hook pre-bash`) denies command text that names `.githooks/`, `core.hooksPath`, `PROJECT_MERGE` or `gh repo edit`, among others. That is expected: gate work runs inside `init.py` and `mise run` subprocesses, which those rules do not mask. Their writes are absolute-path, `install -D` and hash-aware (N17, N18).

## Approved decisions (John, 2026-09-23)

| # | Decision (the Recommended option) | Applied in |
|---|---|---|
| D1 | A branch per change. Merge opens a PR and waits for CI when an origin exists, and squash-merges locally when not. | `project.py merge`; P7 |
| D2 | The remote is asked in the talk only when there is no origin. The default answer is a private GitHub repo. | P2 question, P7 publish |
| D3 | `uv.lock` and `mise.lock` are committed in the init commit after `uv lock --check`. | P0 exemption, P4, P7 |
| D4 | TDD is enforced by prove-red at merge and in CI, plus right-reason `tdd red` and `Spec:`/`Red:` trailers. No Edit hook. | rendered `project.py`, sdd `compile.md` |
| D5 | `log.md` is retired. Progress is derived from tests and git. | P4 memory, P9 |
| D6 | grill absorbs execplan-create, goal becomes compile, execplan-improve becomes spec-improve, and think/spec-driven folds into the templates. | vault skills, M8 |
| D7 | A committed `.agent/` is read as P2 intake, then `git rm`'d. | P0 reports it, P2, P4 (ADOPT), P8, P9; publish refuses while it is tracked |
| D8 | A `risk: high` plan group pauses compile for the human's look. No extra gate. | sdd `compile.md` |
| D9 | Tier by evidence. P0 sets the tier from 6 months of human authors with a commit of their own (web-UI uploads and bots do not count). Solo repos skip CODEOWNERS, the PR template, team.md and ONBOARDING. EXTEND offers the team tier when a second author appears. | P0, P4, P8 |
| D10 | The old claude.ai skills upload that carried a v1 `project_init` is removed entirely: disabled in Claude Code, deleted on claude.ai. | rollout, M11 |

## Where things live

- `templates/`: machinery only (`scripts/project.py`, `tests/conftest.py`, `mise.python.toml`, `ci.yml`, `settings.json`, `AGENTS.md`, `README-quickstart.md`, `specs-README.md`, `skills/sdd/`, `project_memory/`, env, git and ignore files).
- Product templates (mission, tech-stack, roadmap, capability, backlog, change folder, decision, lesson): `~/helm/12-system/templates/sdd/`. P2 fills them, and the filled files carry no vault path into the repo.
- `tests/`: pytest for `project.py`, `init.py` and the hooks. Run `uv run --with pytest pytest tests -q` from this folder.

## Future work

- **A node stack pack** (`templates/stacks/node/`). open-kit needs it. Until it ships, P0 stops a node repo. The pack needs node's own P0 detectors, probe, mise tasks, test tags and `project.py` adapters.

## The finished run (tipcalc, ADOPT)

```text
mode ........ ADOPT   master -> main (no remote)   branch plan/project-init
probe ....... tipcalc 100 -> "tip: 15.0"; 5 inputs end in a traceback -> 5 [gap] scenarios
talk ........ 2 rounds: one-liner, distribution none, local only; trunk: keep its 1 candidate
generated ... specs/ (constitution, cli.md, config.md), mise tasks, gates, sdd skill, memory
verified .... mise run verify green (1 passed, 5 xfailed); selftest: every bypass blocked
shipped ..... chore(init): project-init v3 on plan/project-init, uv.lock included
next ........ review, then `! mise run merge`; then /clear before the first /sdd
punch list .. git config --global init.defaultBranch main
```
