---
title: project-init v3 design
snapshot: 2026-09-23
status: shipped 2026-09-25 (approved by John 2026-09-23)
source: 14-agent design workflow (research, 3 designs, 3 judges, synthesis, critic, patch)
---

# project-init v3: a spec-driven, test-driven build system (patched design)

**Extended by** [[project-init-v3.1-review-depth]]: trunk map, rollback line, proof bundle, launch (built 2026-09-26).

**Evidence tags:**
- `[L]` ran locally during research.
- `[L*]` re-checked in this pass. The scratch folders are listed at the end of section 12.
- `[D]` comes from vendor docs. The Claude Code permission and settings claims were re-read in this pass from the raw docs.
- `[C]` was verified by the critic pass.
- `[U]` is not verified yet. Every `[U]` has a verification step in section 12.

---

## 0. At a glance

### 0.1 The lifecycle

```
 EMPTY FOLDER              EXISTING REPO                 VAULT (Rai only, read-only)
      |                          |                       09-ideas/<x>.md
      +------------+-------------+                       05-projects/{kitchen,active}/<name>/
                   v                                                  |
 /project-init  P0 PREFLIGHT   read-only facts: mode, dirty tree, shared origin,   <------+
                   |           signals, env reads, tools (run, never `command -v`)
                P1 PROBE       existing entrypoints run in a scratch clone, network off
                   |           (no args, --help, abc, env "" and abc)
                P2 TALK        sources first, then question rounds (<=3 per round) until the
                   |           constitution is complete -> specs/mission.md tech-stack.md
                   |           roadmap.md + capabilities/<entry>.md
                P3 SCAFFOLD    empty folder only: uv init --package on main, bootstrap commit
                P4 GENERATE    branch plan/project-init: mise, gates, memory, sdd skill, CI
                P5 VERIFY      every command runs; `mise run selftest` bypass matrix must FAIL
                P6 FRONT DOOR  AGENTS.md + README quickstart, assembled last from commands that ran
                P7 SHIP        commit listed paths only; remote if chosen; punch list
                   |
  [G1 HUMAN] ! mise run merge            constitution + standard land on main
                   |
                   v
+============================ THE LOOP: one change at a time =============================+
| /sdd "<what you want>"          (John: /grill "<...>")                               |
|   classifier (4.1): first yes wins; a lane only gets heavier                             |
|   mise run change -- <slug> --lane <lane>   refuses while another change is open (I8),  |
|                                             except --hotfix (fix lane, own worktree)     |
|  feat lane                                                                               |
|   TALK      question round(s): Scope, Decisions, Context                                 |
|             -> scenarios in specs/capabilities/<cap>.md                                   |
|             -> specs/changes/<date>-<slug>/{requirements,plan,validation}.md              |
|  [G2 HUMAN] ! mise run approve     approving validation.md = approving the test list    |
|   /clear                                                                                 |
|   COMPILE   per group: tagged tests -> mise run tdd -- red <ids> (must fail, right       |
|             reason) -> minimal code -> tdd green -> refactor -> verify -> commit on green|
|             risk: high group   -> compile pauses for your look (D8)                      |
|             spec wrong?        -> scenario + test + code in ONE commit                   |
|             new idea?          -> mise run backlog -- <topic>  (never the roadmap)       |
|   VALIDATE  3 lenses: conformance, breaker, test honesty; ends with                      |
|             mise run status -- --merge (the full DoD preview)                            |
|             [Rai extras: /adversarial-review panel, /visual debug]                       |
|  [G3 HUMAN] ! mise run merge -- --attest    verify + prove-red + DoD + roadmap tick +    |
|             CHANGELOG + squash; prints the next roadmap item, "still right?", /clear     |
|                                                                                          |
|  fast lanes, no change folder:  fix | chg | chore | refactor   ->  [G3] merge           |
|  spike: mise run backlog -- <topic> --spike   scratch worktree; only the findings land   |
+================================================+=========================================+
                                                 | "still right?" = no, 5+ open backlog items,
                                                 | or every 3 merged features (status reminds)
                                                 v
 REPLAN   mise run change -- <date>-replan --lane plan ; /sdd replan
          reorder/merge/split phases, schedule backlog (linked), standing rules, process fixes
          mission.md changes only on plan/ branches (a pivot, or a product-promise constraint)
                                                                           -> [G3] merge
 RELEASE  ! mise run release -- minor      distributable projects only: bump, tag, build, publish
```

- **Human gates.** There are three: `! mise run merge` (G1), `! mise run approve` (G2) and `! mise run merge` (G3).
  - `--attest` is needed only when the change lists Human checks and there is no TTY. Section 5.7 explains why.
  - Section 3.2 says what stops an agent from running a gate, and what only detects it.
- **Everything else is mechanical.**

### 0.2 "We add a new feature: do we update mission? roadmap?"

| Artifact | For a new feature | Written by |
|---|---|---|
| `specs/mission.md` | **No.** Mission changes only on a `plan/` branch, for a pivot or a product-promise constraint. | human + talk |
| `specs/roadmap.md` | **Yes, but only the tool touches it**, at merge. It ticks the item, or inserts it as `(unplanned)` if the feature was never scheduled. | `mise run merge` |
| `specs/tech-stack.md` | Only if the feature adds or removes a runtime dependency, a service or a standing rule. The edit goes on the same branch, and merge enforces this (I11). | agent |
| `specs/capabilities/` | **Always.** New or changed scenarios, each with a stable ID. | talk |
| tests | **Always.** Red first, tagged with the scenario ID, and proven red on the old code at merge. | compile |
| change folder | **Always** for the feat lane. | talk |
| ADR (`project_memory/decisions/`) | Only for a choice that later changes must respect. | agent |
| `project_memory/lessons.md` | Only if something surprised you. | agent / human |
| `CHANGELOG.md` | Always, regenerated at merge. | `mise run merge` |
| `specs/backlog/` | Every out-of-scope idea that came up along the way. | agent / human |

### 0.3 The feature-lifecycle decision table (every change type)

**Legend:**
- **C** = create, **U** = update, **R** = read only, **no** = never touched.
- **tool** = `mise run merge`, `abandon` or `release` writes it. No person or model does.
- **if X** = only when X holds.

| Change type · branch | mission | tech-stack | roadmap | change folder | capabilities (living) | tests | AGENTS.md | ADR | lessons | CHANGELOG | backlog |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **New feature, on roadmap** · `feat/<slug>` | R | U if a dep, service or rule is added/removed | tool ticks | **C** | U: add/modify scenarios | **C** red first, per ID | U if a command changed | C if cross-cutting | C if surprised | tool (`feat`) | C for out-of-scope ideas |
| **New feature, not on roadmap, start now** · `feat/<slug>` | R | same | tool inserts `(unplanned)` + ticks | **C** | same | same | same | same | same | tool | same |
| **Idea, not now** · no branch | no | no | no (next replan) | no | no | no | no | no | no | no | **C** (committed on the current branch; on the default branch it stays untracked until the next change) |
| **Research idea mid-feature** · current branch | no | no | **never** | no | no | no | no | no | no | no | **C** |
| **Spike (you want an answer, not code)** · `mise run backlog -- <topic> --spike` | no | no | no | no | no | throwaway | no | no | C if learned | no | **C** findings report. The scratch worktree `../<repo>-spike-<slug>` is deleted and never merged. |
| **Change behaviour, bounded** (1 capability, 3 or fewer scenarios, no new dep or interface, 1 session) · `chg/<slug>` | no | no | no | no (intent in commit body) | U: scenario edited **in the same commit as its test** (I4) | U: flip the assertion first, see red | U if a command changed | C if it reverses one (old one marked superseded) | C if surprised | tool (`change`) | C if extras come up |
| **Change behaviour, larger** | ratchet: becomes "New feature" | | | | | | | | | | |
| **Remove shipped behaviour, bounded** · `chg/<slug>` | no | U if a dep goes | no | no | U: delete the scenario | delete its linked tests in the same commit, with a `Spec-Removed: <id>` trailer (I4); the count guard allows exactly those | U if a command goes | C | no | tool (`change!`, under Removed) | no |
| **Bug: code breaks an existing scenario** · `fix/<slug>` | no | no | no | no | no (the spec was right) | **C** regression test tagged with the existing ID, red on the old code | no | no | C if the cause generalises | tool (`fix`) | no |
| **Bug: spec silent or wrong** · `fix/<slug>` | no | no | no | no | U: add/modify the scenario + a "SHALL CONTINUE TO" guard scenario | **C** red first; guard IDs pass on the old code (`Spec-Guard:`) | no | C if it reveals a rule | C | tool (`fix`) | no |
| **Hotfix while a feature is open** · `fix/<slug>` via `--hotfix` | as for the two bug rows | | | | | | | | | | After merge, `status` on the open feature says `git merge main`. |
| **Tweak / chore** (copy, style, docs, config) · `chore/<slug>` | no | no | no | no | no | stay green, **unedited** (I7) | U only if AGENTS.md is the thing tweaked | no | no | skipped | no |
| **Dependency bump, swap, add or remove; tool change** · `chore/deps-<slug>` | no | **U** if a runtime dep or tool is added, removed or swapped (I11) | C phase only if the migration is multi-step (at replan) | no | no | unedited; harness-only edits (fixtures, imports, mocks) allowed in commits with a `Test-Harness: <reason>` trailer, shown at merge (I7) | U if commands changed | **C** if a swap or a major version | C if surprised | skipped (users notice → use `chg`) | no |
| **Refactor / perf** · `refactor/<slug>` | no | U if a structure rule changes | no | no | no (a scenario change makes it `chg`) | pass **unedited** (I7, same `Test-Harness:` route); adding tests is allowed | no | C if architectural | C if surprised | `perf` only | no |
| **Cross-cutting constraint** (a11y, security) · `plan/<date>-<slug>`, then `feat/` | U only if it is a product promise | **U** standing rule S-n | U: "apply S-n" phase | C (for the apply phase) | C: **one** cross-cutting capability; never edit every feature | C | no | C | no | tool | no |
| **Replan** (reorder, merge, split) · `plan/<date>-replan` | no | U if a rule changed | **U**; slugs are permanent | no | no | no | U if the process changed | C if a phase is dropped for a reason worth keeping | no | skipped | U: scheduled (linked) or dropped (file deleted, reason in commit) |
| **Pivot** (who, why, scope) · `plan/<date>-pivot` | **U** | U if needed | rewrite; removals scheduled as later changes | no | no (removals ship in the scheduled changes) | no | U pitch line | **C** | no | skipped | re-triage all |
| **Abandon mid-flight** · `! mise run abandon -- "why"` | no | no (never merged) | no (never ticked; next replan decides) | discarded with the branch; tip tagged `abandoned/<slug>` | no | discarded | no | no | C if the finding generalises | no | **C** with reason + tag (tool commits it to main) |
| **Brownfield adoption** · `plan/project-init` | **C** (reverse-engineered + gap talk) | **C** (from lockfiles, config) | **C** (from TODO, issues, PLAN.md + probe findings as Phase 1) | no | **C: entrypoint capability only.** Working behaviour becomes characterization scenarios; crashes become `[gap]` scenarios with strict-xfail tests. Never back-fill the rest. | C: subprocess entrypoint tests | **C** (last) | C: legacy import only | C (v2 lessons carried over) | C from git history | C seed |
| **Release** · `! mise run release -- <bump>` (internal branch `release/vX.Y.Z`) | no | no | no | no | no | green | no | no | no | tool: version section | no |

---

## 1. Thesis

- **A project is a conversation compiled into code.** The conversation leaves committed, agent-agnostic markdown in `specs/`:
  - a thin constitution: mission, tech-stack, roadmap;
  - a living behaviour layer, `capabilities/*.md`, where every scenario has a stable slug ID;
  - one short change folder per feature: requirements, plan, validation;
  - a backlog.
- **The "compile" step is TDD per task group.** Each scenario becomes a test tagged with its ID. The test is seen failing for the right reason, then minimal code makes it pass.
- **Two scripted checks turn drift into a red build:**
  - `spec-check`: every scenario on main has a passing linked test, and no test names an unknown ID.
  - `prove-red`: every new or changed scenario's test fails against the old code.
  - Both work the same for humans, every harness, and CI.
- **One script, `scripts/project.py`, holds every repo check, hook, lifecycle command and status view.**
  - mise is the one manager for tools, env, tasks and setup. uv owns Python.
  - The git hooks are shims into that script, plus one POSIX sh hook that guards main.
  - project-init's own deterministic work (preflight, probe, render, selftest, publish, transcript migration) lives in one vault script, `project-init/scripts/init.py`.
- **Two human gates per feature: `approve` and `merge`.**
  - The fence stops shortcuts: it holds in auto mode and in every harness at the git layer.
  - An audit trail makes deliberate evasion visible (section 3.2).
- **One protocol text per repo:** the generated `.claude/skills/sdd/`.
  - Teammates, pi and OpenCode drive it with `/sdd`.
  - John's vault `/grill` and `/compile` load that same text and add Rai-only extras.

### Design choices and why

| # | Question | Choice | Why (one line) |
|---|---|---|---|
| 1 | Living layer | `capabilities/` edited in place. ADDED, MODIFIED and REMOVED are **derived from `git diff`**, with no delta grammar. | Proof without a fragile parser. |
| 2 | TDD proof | prove-red at merge and in CI, plus the right-reason `tdd red`. No Edit hook by default (D4). | The one proof an agent cannot fake; Bash edits bypass an Edit hook. |
| 3 | Main protection | reference-transaction, plus a copy pinned in git config, with a live-ref check and a creation block `[L*]`. A sync needs `ls-remote` against the committed origin URL, and `Merged-By` on each commit it brings. Also pre-push, `receive.hideRefs`, the Claude layer and a trailer audit. | One chokepoint sees every ref move; the audit catches what gets past it. |
| 4 | Human gates | Prefix deny rules + a `pre-bash` hook with a read-only exemption + `Edit()` denies on gate files + attestation. | Deny holds in auto mode and past leading assignments `[D]`; read-only commands are never blocked (N9). |
| 5 | Memory | `project_memory/` = `lessons.md` (merge=union) + `decisions/<date>-<slug>.md` + `team.md` (team tier). Retire facts/log/decisions.md and the Stop nudge. | Every fact has one home; union-merge team memory is a recorded requirement. |
| 6 | Repo skills | **One** portable skill, `sdd`, with sub-files. Vault `/grill` and `/compile` layer on top of it. | One protocol text. |
| 7 | CHANGELOG | Regenerated per change by merge with `git cliff --with-commit`. Config lives in `pyproject.toml [tool.git-cliff]` with explicit groups and no emoji `[L*]`. | Zero hand edits, no conflict ritual. |
| 8 | Setup | `mise install` does everything via `[hooks] postinstall` `[L]`. | "mise is the one manager." |
| 9 | Secret scan scope | `gitleaks git --staged` in pre-commit; `gitleaks git` (history) in verify and CI with a `.gitleaksignore` baseline. Never `gitleaks dir .`. | `dir` scans gitignored `.venv` and `.env` `[L*]`. |
| 10 | Leak gate | Generic `.gitleaks.toml` rules scoped to `.md` and `.claude/`. The same rules are the render gate for project skills. | One rule set; `k8s/helm/` passes `[L*]`. |
| 11 | Risky groups | Decision D8. Recommended: compile pauses after a `risk: high` group. | The course's model, with no extra gate. |
| 12 | Brownfield crashes (H20) | Sandboxed probe (P1) + `[gap]` scenarios with strict xfail. | The crash is under test from day one. |
| 13 | Lint debt | ruff per-file-ignores baseline, shrink-only. | `mise run verify` stays one whole-repo command locally and in CI. |
| 14 | Hook runtime | `mise x -- uv run --script`: 33-61 ms per call; `mise x` does not fire postinstall `[L*]`. | Follows the uv-script standard; the git layer fails closed. |
| 15 | Progress | **Derived**: a group is done when every scenario ID in it has a passing linked test. | helm's `.agent/decisions.md` has 0 of 39 boxes ticked. |
| 16 | Change folders | Frozen in place, `status: done`. | They are the only home of per-feature why. |
| 17 | Remote creation | Asked inside the talk, only when there is no origin (D2). | Throwaways stay local; the gh token has no `delete_repo`. |
| 18 | Template home | Product templates in `12-system/templates/sdd/`; machinery in `project-init/templates/`. | Vault template rule; ideas/graduate shares them. |
| 19 | Diagrams | ASCII in files rendered into repos (GitHub renders no D2). D2 in vault notes, never Mermaid. | Both locked rules hold. |
| 20 | Lanes | Six: feat, chg, fix, chore, refactor, plan. Spike is a backlog activity; deps is a chore. | Less ceremony, same coverage. |
| 21 | Threat model | Prevent shortcuts, detect evasion (section 3.2). | Local enforcement against an agent with a shell cannot be absolute. |
| 22 | pre-commit content | Staged blobs: ruff through stdin per file; ty on an index export when a file is partially staged `[L*]`. | H22: a broken staged file must fail even when the working copy is clean. |

---

## 2. Repo layout after init (tipcalc, after adoption and feature 1)

**Legend:**
- Writer: T = tool, A = agent, H = human.
- Git: C = committed, ig = gitignored.
- Life:
  - living = edited in place, states today only;
  - frozen = never edited after merge;
  - gen = regenerated by a tool, hash-tracked;
  - append = entries only added.

```
tipcalc/
├── AGENTS.md                      agent contract: 3 pointers, commands, 5 rules, 3 memory lines      T (last) | C | gen+H
├── README.md                      pitch + the ONLY quickstart (tool-owned region)                        T+H | C | living
├── CHANGELOG.md                   Keep a Changelog, written by merge/release only                      T | C | gen
├── .project.toml                  standard, default_branch, origin_url, audit_since, [paths],
│                                  [signals]+evidence, server_protection, ruff_baseline,
│                                  [generated] sha256 per file                                           T | C | gen
├── mise.toml                      [tools] uv gitleaks git-cliff · [env] · [hooks] postinstall · [tasks] T then H | C | living
├── mise.lock                      tool versions + sha256 + provenance (linux-x64)                     T | C | gen
├── mise.local.toml                per-developer overrides                                              H | ig
├── .python-version                interpreter pin, read by uv only (mise ignores it by default [L])   uv | C
├── pyproject.toml                 description = mission one-liner; ruff S+ANN; pytest spec marker;
│                                  [tool.git-cliff]; ruff baseline block if brownfield                   T/A | C | living
├── uv.lock                        every command uses --locked                                          uv | C | gen
├── .env.example                   typed env contract (knob | secret); empty = unset; op:// pointers    A/H | C | living
├── .env                           local knob values + op:// pointers only                             H | ig
├── .gitignore .editorconfig .gitattributes   stack ignores + standard lines; lessons.md merge=union  T | C
├── .gitleaks.toml                 default rules + personal paths + wiki-link (generic, no username)   T | C | gen
├── .gitleaksignore                only if history already had findings at adoption (fingerprints)     T | C
├── .githooks/pre-commit|commit-msg|pre-push   2-line shims -> scripts/project.py hook <name>          T | C | gen
├── .githooks/reference-transaction            POSIX sh: main moves only via sanctioned paths [L*]     T | C | gen
├── scripts/project.py             ONE PEP 723 script, stdlib only (see 6.P4); also the hook launcher  T | C | gen
├── .github/workflows/ci.yml       job `verify` (+ prove-red on PRs, audit on push); only with a remote T | C | gen
├── .claude/settings.json          2 hooks (SessionStart, PreToolUse:Bash) + allow/deny                 T | C | gen
├── .claude/settings.local.json    personal permissions                                                 H | ig
├── .claude/skills/sdd/            SKILL.md talk.md compile.md validate.md replan.md (portable loop)   T | C | gen
├── .agents/skills/sdd -> ../../.claude/skills/sdd   only if M6 shows pi/OpenCode need it [U]          T | C | gen
├── specs/README.md                THE process: lifecycle, tables 0.2 + 0.3, classifier, formats,
│                                  gate ladder, Definition of Done, size caps                          T, then plan/ edits | C | living
├── specs/mission.md               why, who, what, scope in/out, success, glossary                      H+A | C | living (plan/ only)
├── specs/tech-stack.md            runtime, tooling, standing rules S-n, never-use, distribution,
│                                  environment (points at .env.example)                                 H+A | C | living
├── specs/roadmap.md               phases of slugs `- [ ] slug: title`, Later, Gates                   H+A, T ticks | C | living
├── specs/capabilities/cli.md      Requirement (one SHALL) + Scenario `cli.<slug>` GIVEN/WHEN/THEN       A, H reviews | C | living
├── specs/capabilities/config.md   same, for env knobs                                                  A | C | living
├── specs/changes/2026-09-24-entrypoint-hardening/
│   ├── requirements.md            frontmatter (lane, status, title, roadmap) + Why/Scope/Decisions/Context  A | C | frozen at merge
│   ├── plan.md                    groups: scenario IDs, files, risk, parallel                         A | C | frozen at merge
│   └── validation.md              Review focus (<=5), Run it (optional), Human checks (<=3)           A | C | frozen at merge
├── specs/backlog/2026-09-24-percent-flag.md   idea/report; status open|scheduled                       A/H | C | living
├── project_memory/README.md       routing table (section 8), <=1 KB                                   T | C | gen
├── project_memory/lessons.md      `## date | title` + Trigger + Rule                                  A/H | C | append (merge=union)
├── project_memory/decisions/2026-09-24-usage-errors-exit-2.md   ADR; only `status:` edited later       A/H | C | frozen
├── project_memory/team.md         roster + authority (TEAM TIER ONLY, D9)                             H | C | living
├── tests/conftest.py              spec(*ids) marker, --spec selector, writes .cache/spec-results.json   T | C | gen
├── tests/test_cli.py              subprocess tests of the real console script                          A | C | living
├── src/tipcalc/…                  code                                                                 A | C | living
├── .cache/                        spec-results.json, tool caches                                      T | ig
└── .agent/                        scratch only: tdd red records, orchestrator runs, visual plans       T/A | ig
```

**Retired from v2:**
- Files: `Makefile`, `scripts/doctor.sh`, `scripts/verify.sh`, `scripts/git-hooks/`, `ONBOARDING.md`, `docs/spec.md`, `.mcp.json` (GitHub MCP).
- `.github/CODEOWNERS` and `pull_request_template.md` while the repo is solo (D9).
- Memory files: `project_memory/{facts,log,decisions}.md`.
- Hooks and skills: `.claude/hooks/project-*.py` (all three), and `.claude/skills/{run,verify,release}` as defaults.

---

## 3. Lifecycle: gates, commands, enforcement (diagram in 0.1)

### 3.1 Change state machine

```
            mise run change            ! mise run approve              ! mise run merge
 (none) ------------------> draft ---------------------> approved ---------------------> done (frozen)
                              |                              |
                              +---------- ! mise run abandon -+--> branch tagged abandoned/<slug>, deleted;
                                                                   backlog report committed to main by the tool
```

- `status:` lives in the `requirements.md` frontmatter and changes only through the tool commands (I6).
- The fast lanes have no folder: their branch is the whole state.

### 3.2 Threat model and gate layers

**Threat model.** The fence targets a cooperative but fallible agent: one that takes shortcuts under pressure ("commit to main", `--no-verify`, "just merge it", editing a hook to get past it). It does not claim to stop an agent that sets out to deceive, because an agent with a shell can write and run any program. For that case the design relies on detection:
- every commit that `project.py` lands on the default branch carries a `Merged-By: mise run merge` trailer;
- session-start, `mise run doctor` and CI (on push to main) flag any first-parent commit since `audit_since` that lacks the trailer;
- CI re-runs verify on main.

| Threat | Prevention | Detection / backstop |
|---|---|---|
| Commit, merge, reset, `branch -f`, `update-ref` or `--no-verify` onto main | `reference-transaction` sees every ref move. Its pinned copy runs even after `reset --hard` or a merge rewrote `.githooks/` `[L*]` | trailer audit |
| Forged sync: fake `refs/remotes/origin/main`, origin re-pointed at a fake repo, or origin's main moved outside merge | The hook allows a sync only when the new tip equals `git ls-remote origin` and origin's URL equals `origin_url` from **main's committed** `.project.toml`, read past replace refs. Each first-parent commit it brings must carry `Merged-By: mise run merge` `[L*]` | trailer audit |
| Delete main, then recreate it elsewhere | Creation is blocked unless the repo is empty: no ref, no reflog, and no commit in the object store but the new one `[L*]`. Deletion alone is recoverable (origin, reflog) | session-start "default branch missing" |
| Push to `origin/main`, including `feat/x:main` | pre-push allows it only under `PROJECT_MERGE`, or while the remote lacks the branch and the local default branch goes up as it is. `receive.hideRefs` refuses a push into the repo itself, which skips every client hook. Server ruleset on public/Pro repos | CI audit on push; a local sync refuses commits without `Merged-By` |
| Agent runs approve, merge, abandon or release, or sets `PROJECT_MERGE` | Prefix deny rules (they match past any leading assignment and inside nested subcommands, and hold in auto mode `[D]`) + `pre-bash`, which also covers `sh -c`, `eval`, and script files inside the repo or temp dirs | `Merged-By` trailer + "attested by" line in the squash body |
| Agent merges its own PR through gh | deny `gh pr merge*`; `pre-bash` denies `gh api` writes (`-X`/`--method` other than GET, or `-f`/`-F`/`--field`/`--raw-field`/`--input`) and `gh repo edit/delete/rename/archive`, `gh ruleset` | GitHub PR record |
| Agent disables hooks (`-c core.hooksPath`, `-c hook.*`, `GIT_CONFIG_*`, `--no-verify`, editing `.git/config`) | `pre-bash`; `.git` is a protected path, so tool writes and redirects there prompt `[D]`. The pinned guard still runs when `core.hooksPath` is overridden `[L*]` | session-start, doctor and merge check the gate config (`core.hooksPath`, `receive.hideRefs`, the pinned guard) and compare `.githooks/*` with the committed blobs |
| Agent edits gate files (`.githooks/`, `project.py`) with Write, Edit, `sed -i`, `tee` or a redirect | `Edit(/.githooks/**)`, `Edit(/scripts/project.py)` deny. Edit rules cover every built-in edit tool and Bash `sed`/`tee`/redirect targets `[D]` | merge refuses changed gate files without `--gate-change`; merge refuses when hook files differ from committed |
| Untested scenario, or a test that pins nothing | `spec-check` (verify), `prove-red` (merge) | CI runs both |
| Secret or vault path in a commit | gitleaks staged scan (pre-commit) | history scan (verify, CI) |
| Unapproved spec reaches code | merge checks the approve commit precedes the first `src/` commit (I12) | "amended after approval" line |

**Honest limit, what still gets through prevention:**
- a program the agent writes outside the repo and temp dirs;
- an obfuscated command (for example a base64-decoded payload);
- a human deleting `.githooks/`;
- a push that skips pre-push (`push --no-verify`, `send-pack`) to a repo without a server ruleset. A local sync of it is then refused, unless its commits forge the `Merged-By` trailer;
- wiping every ref, reflog and commit. The next commit is a first commit again, as after `git init`;
- a skip whose marker name is computed at run time (a call, `exec`). pre-commit cannot read it. spec-check sees the skipped test;
- a variable the agent writes into `.env`, which mise loads into its tasks and `mise x`. `PROJECT_MERGE` there lets any move of main through, and `HOME` picks the git config the guard trusts;
- a sync from a fake origin that the agent sets up on purpose. The guard's `ls-remote`, like merge's confirm and fetch, drops `git -c`, `GIT_CONFIG_*`, `XDG_CONFIG_HOME` and `GIT_SSH*`. It takes `url.<base>.insteadOf` and `core.sshCommand` only from `~/.gitconfig` and the system config, with the files they include. Five routes still reach a fake repo:
  - an edit of `~/.gitconfig` or `~/.ssh/config` with the Write or Edit tool, which `pre-bash` never sees;
  - a write, by any tool, to a file `~/.gitconfig` includes under a name `pre-bash` does not know as git config;
  - a `HOME` that names another `.gitconfig`, set in pi or OpenCode (no `pre-bash`) or inside a program such as a test run;
  - a fake `ssh` or `git-upload-pack` first on `PATH`;
  - the repo's own transport settings (`http.proxy`, `http.sslVerify`) in front of a server the agent runs.

  A forged main that carries the trailer passes the audit. It shows once origin's real main moves on: `git pull --ff-only` fails, and the next merge refuses to sync over commits origin lacks.

Each leaves a trace the audit, CI or spec-check catch after the fact. The guard reads the user's git config only from `~/.gitconfig` and `~/.config/git/config`, and the files they include. Some users keep that config elsewhere (`GIT_CONFIG_GLOBAL`, another `XDG_CONFIG_HOME`), or reach origin through a `GIT_SSH_COMMAND` in the shell. They see a sync refused with "cannot reach origin" until origin's rules or `core.sshCommand` are in one of those files. The refusal says so, and names the by-hand sync as the other way out. In pi and OpenCode, the Claude layer (deny rules, `pre-bash`) is absent `[U]`; the git layer and the audit still hold. Optional OS-level hardening, Claude Code's sandbox with write-deny on gate files, is Risk 1 `[U]`.

### 3.3 The gate ladder (one definition, H33)

```
pre-commit  ⊂  mise run verify  ⊂  CI  ⊂  mise run merge
  staged       whole repo:        verify      CI checks
  subset of    lint, format,      + prove-red + DoD extras (run-it rows, human checks,
  verify       types, secrets,    on PRs      gate-file diff, lane rules on the whole branch)
               test, spec-check   + audit     + bookkeeping (roadmap, CHANGELOG, squash)
                                  on push
```

- Each rung runs the rung before it, plus more.
- `specs/README.md#gates` is the only place this is written out. AGENTS.md and the hook messages link to it.

### 3.4 A feature, typed out (tipcalc, feature 1)

```
/sdd "harden the entrypoint"            -> classifier: on roadmap, new behaviour -> feat
  mise run change -- entrypoint-hardening   -> branch feat/entrypoint-hardening + change folder (draft)
  talk: Scope, Decisions, Context       -> edits capabilities/cli.md + config.md,
        writes requirements/plan/validation, runs `mise run status` -> "ready for approve"
! mise run approve                     -> lint ok, commit "spec(entrypoint-hardening): approve"
/clear
/sdd compile  (John: /compile)     -> G1 usage errors: red 3/3 -> green -> commit
                                          G2 env knob:     red 2/2 -> green -> commit
/sdd validate                          -> 3 lenses; 1 finding (negative bill) -> scenario+test+code, 1 commit
                                          ends with: mise run status -- --merge (DoD preview, 1 human check listed)
! mise run merge -- --attest           -> verify ok, prove-red 6/6 red on base, roadmap ticked,
                                          CHANGELOG regenerated, squash to main, next item printed
/clear
```

---

## 4. Classifier, lanes and invariants (full table in 0.3)

### 4.1 Lane classifier

It lives in `specs/README.md#lanes`, and `/sdd` runs it out loud.
- Ask the questions in order; the first yes wins.
- A lane only gets heavier. `mise run change -- <slug> --lane feat` upgrades `chg/x` in place to `feat/x` and adds the folder. A downgrade is refused.
- "Bounded" is judged against the repo, not against how familiar the agent is with it.

```
Q1 changes who / why / scope in mission.md?                            -> PLAN (pivot)   plan/<date>-pivot
Q2 only reorders, merges, splits or schedules work, or sets a rule?    -> PLAN (replan)  plan/<date>-replan
Q3 wants an answer, not shipped code?                                  -> backlog --spike (no lane)
Q4 not doing it now?                                                   -> backlog (no branch)
Q5 code violates an existing scenario, or behaviour a reasonable user
   would not expect where the spec is silent?                          -> FIX       fix/<slug>  (--hotfix if a change is open)
Q6 observable behaviour unchanged?  -> structure/perf: REFACTOR · deps/tools/copy/style/docs/config: CHORE
Q7 one capability, <=3 scenarios, no new dep or interface, one session? -> CHG      chg/<slug>
otherwise                                                               -> FEAT     feat/<slug> + change folder
```

### 4.2 Concurrency rules

- **One open change at a time** (I8). `change` refuses while another lane branch is unmerged, or while the tree is dirty. Untracked backlog files are exempt.
- **Hotfix.** `mise run change -- <slug> --lane fix --hotfix` is allowed while a change is open.
  - It runs `git worktree add ../<repo>-fix-<slug> -b fix/<slug> <default>`; the open feature's tree is untouched.
  - The human lands it with `! mise run merge -- --branch fix/<slug>`.
  - Afterwards `mise run status` on the feature branch says `main moved: run git merge main`, and prove-red's base follows the new merge-base.
- **Parallel groups.** `--parallel` is for the orchestrator only. Workers run on `feat/<slug>--g<n>` and merge into `feat/<slug>`, never into main.

### 4.3 Invariants, each with the tool that enforces it

| # | Invariant | Enforced by |
|---|---|---|
| I1 | `specs/mission.md` and `specs/roadmap.md` are staged only on `plan/` branches. The roadmap is also written by merge under `PROJECT_MERGE`. | pre-commit (staged) + spec-check (branch diff) |
| I2 | `CHANGELOG.md` is staged only by merge or release. | pre-commit + spec-check |
| I3 | On the default branch, every scenario has at least one passing linked test. A `[gap: <roadmap-slug>]` scenario needs an `xfail(strict=True)` test whose reason names its ID, and the slug must exist in the roadmap. No orphan tags; no skip/xfail on linked tests except gaps. On a branch with an open change, ADDED/MODIFIED scenarios may be pending. | `spec-check` (verify, CI) |
| I4 | A commit that ADDS or MODIFIES a scenario also stages a test naming the ID. A commit that REMOVES a scenario deletes every test naming it and carries `Spec-Removed: <id>`. | pre-commit + commit-msg |
| I5 | A change folder with `status: done` is frozen. | pre-commit + spec-check |
| I6 | `status:` moves draft→approved→done only via approve and merge. | merge verifies the approve commit carries `Spec-Approved:` with the spec hash |
| I7 | On `refactor/` and `chore/`, existing test files are unchanged, except in commits carrying `Test-Harness: <reason>`. Merge lists those diffs as human checks. | merge + CI |
| I8 | One open change at a time, except `--hotfix` and `--parallel`. | `project.py change` |
| I9 | prove-red expectations hold for each scenario kind (table in 5.5). | `prove-red` (merge; CI on PRs) |
| I10 | Tests collected at HEAD ≥ tests collected at base minus tests linked only to REMOVED IDs. | `prove-red` |
| I11 | A runtime dependency or tool added, removed or swapped means `specs/tech-stack.md` changed on the same branch. | spec-check (branch diff) + merge |
| I12 | feat lane: the approve commit precedes the first commit touching `src` roots. | merge |
| I13 | Every Review focus row maps to an existing scenario ID, or says `none: <reason>`. | approve |
| I14 | No vault paths or wiki-links in tracked docs or rendered skills. | gitleaks rules (pre-commit staged, CI history, init render gate) |
| I15 | Every `mise run X` in AGENTS.md, README.md or specs/README.md is a real task. | `spec-check` + doctor |
| I16 | The default branch moves only via merge, abandon or release, the first commit of an empty repo, or a confirmed origin sync. Each commit in a sync has the `Merged-By` trailer. It is pushed only by them or at bootstrap. | reference-transaction and its pinned copy + pre-push + `receive.hideRefs` + trailer audit |

---

## 5. TDD mechanics

### 5.1 Scenario grammar (enforced by `spec-check`)

- **File:** `specs/capabilities/<cap>.md`.
- **Structure:** `## Requirement: <title>`, then exactly one SHALL sentence, then one or more `### Scenario: <cap>.<slug>` with GIVEN/WHEN/THEN bullets.
- **ID:** matches `^[a-z][a-z0-9-]*\.[a-z0-9][a-z0-9-]*$` and is unique in the repo. Slugs, never numbers, so parallel branches cannot collide.
- **Content:** no design prose; no code except literal I/O.
- **Size cap:** 300 lines; split the capability beyond that.

Example (`capabilities/cli.md` after adoption):

```markdown
# Capability: cli

## Requirement: Tip output
The CLI SHALL print the tip for the bill given as the first argument.

### Scenario: cli.tip-default
- GIVEN TIPCALC_DEFAULT_PERCENT is unset
- WHEN the user runs `tipcalc 100`
- THEN stdout is `tip: 15.0` and the exit code is 0

## Requirement: No crash on bad input
The CLI SHALL never end with a Python traceback.

### Scenario: cli.no-args [gap: entrypoint-hardening]
- WHEN the user runs `tipcalc` with no arguments
- THEN stderr holds no traceback and the exit code is not 0
```

### 5.2 Change folder (templates in `12-system/templates/sdd/`)

**`requirements.md`** (cap 120 lines):

```markdown
---
change: 2026-09-24-entrypoint-hardening
lane: feat
status: draft                                   # draft | approved | done
roadmap: entrypoint-hardening
title: "fix(cli): clear errors instead of tracebacks"   # becomes the squash commit + CHANGELOG line
---
## Why
`tipcalc`, `tipcalc abc`, `tipcalc --help` and an empty TIPCALC_DEFAULT_PERCENT all end in a traceback.
## Scope
In: argument and env validation. Out: new flags (backlog: percent-flag).
## Decisions
- Usage errors exit 2 with one `error:` line (argparse convention). Rejected: exit 1, it collides with runtime failure.
- An empty env knob means unset, so the default applies. Rejected: failing on empty, it punishes a copied `.env`.
## Context
- argparse in `main()`; env via a pydantic-settings model with `env_ignore_empty=True` in `src/tipcalc/config.py` (tech-stack S-1).
```

> v3.1: `requirements.md` ends with a `## Rollback` section of one line (`revert:`, `flag:` or `one-way:`), which this sample predates. See [[project-init-v3.1-review-depth]] B.1.

The capability edits live in `capabilities/*.md`. `mise run status -- --change` prints them as a diff next to this file: one review view, no copy.

**`plan.md`** (cap 100 lines, no checkboxes, progress is derived):

```markdown
## G1 usage errors | cli.no-args cli.help cli.bad-amount | risk: low | parallel: no
Files: src/tipcalc/__init__.py, tests/test_cli.py
## G2 env knob | config.percent-empty config.percent-invalid | risk: low | parallel: no
Files: src/tipcalc/config.py (NEW), tests/test_config.py (NEW)
```

`risk: high` on a group means compile stops after that group and waits for the human (D8, option 1).

> v3.1: a group whose `Files:` match a `## Trunk` entry of `tech-stack.md` must be `risk: high` (I17). See [[project-init-v3.1-review-depth]] A.3.

**`validation.md`** (cap 60 lines; `verify-completion.md`'s evidence table, cut down):

```markdown
## Review focus   (implied inputs the spec never named; each -> a scenario, or "none: <reason>")
- no args -> cli.no-args
- --help -> cli.help
- non-numeric bill -> cli.bad-amount
- negative bill -> cli.negative-amount
- env knob empty / non-numeric -> config.percent-empty, config.percent-invalid
## Run it   (optional, feat only: what tests cannot reach, e.g. a real server; merge executes each row)
| command | exit | stdout contains | stderr contains |
## Human checks   (<=3; merge asks with a TTY, or records your --attest)
- The error messages read clearly to a first-time user.
```

> v3.1: `validation.md` also holds `## Proof`, one row per case, which this sample predates. See [[project-init-v3.1-review-depth]] C.3.

### 5.3 Test linkage

`tests/conftest.py` `[L*]`:
- registers the `spec(*ids)` marker;
- adds `--spec <id>` selection;
- writes `.cache/spec-results.json`. Per ID it records nodes and outcome: `passed | failed | error | xfailed | xpassed`, plus collection errors.

Entrypoint tests always spawn the real console script, which `uv run` puts on PATH `[L]`:

```python
@pytest.mark.spec("cli.no-args")
def test_no_args_prints_usage() -> None:
    r = subprocess.run(["tipcalc"], capture_output=True, text=True, check=False)
    assert r.returncode == 2
    assert r.stderr.startswith("usage: tipcalc")
```

`pyproject.toml` gets the block below, and ruff S603/S607 is ignored under `tests/**`:

```toml
[tool.pytest.ini_options]
addopts = "-q --strict-markers -p no:cacheprovider"
markers = ["spec(*ids): scenario ids this test proves"]
```

### 5.4 The compile loop per group

```
 tests tagged with the group's IDs
        |
 mise run tdd -- red <ids>     every ID has >=1 test? all fail?
        |                      right reason = AssertionError | NotImplementedError | "DID NOT RAISE"
        |                      wrong reason (ImportError, NameError, SyntaxError, fixture/collection error)
        |                        -> refuse: "add a stub that raises NotImplementedError"
        |                      records .agent/tdd/<branch>.json, prints trailer lines
 minimal code
        |
 mise run tdd -- green <ids>   needs a red record per ID; all pass
 refactor (tests unedited) -> mise run verify
        |
 git commit -m "fix(cli): usage errors" --trailer "Spec: cli.no-args, cli.help, cli.bad-amount"
                                        --trailer "Red: cli.no-args: assert 1 == 2"
        |
 risk: high group?  -> stop: "review `git diff <group-start>..HEAD`, then /sdd compile to continue"
 surprised?         -> append to project_memory/lessons.md in this commit
```

- **Commit on green only.** ty rejects a red test that imports a missing symbol `[L*]`, and verify would fail anyway.
- **Red evidence** lives in the trailers (breadcrumbs) and is re-proven by `prove-red` (the proof).
- **Bug variant:** a regression test tagged with the violated ID, red first. If the spec was silent, add the scenario plus a guard scenario for the neighbouring behaviour, and declare the guard with `Spec-Guard:`.
- **Drift rule:** if reality differs from the spec, the scenario, the test and the code change in ONE commit. The merge output shows it as "amended after approval".
- **Stop rule:** if the spec is materially wrong (not a detail), compile stops and asks. It never replans on its own.

### 5.5 prove-red (lane-aware)

```
base   = merge-base(HEAD, <default>)                 (CI: origin/<base_ref>)
diff   = scenario blocks in specs/capabilities/ at base vs HEAD -> ADDED, MODIFIED, REMOVED
ids    = ADDED + MODIFIED + IDs named in `Spec:` trailers of fix/chg commits
guards = `Spec-Guard:` IDs; on plan/project-init every ADDED non-gap scenario is a characterization guard
map    = id -> test nodes, from the HEAD run's .cache/spec-results.json
tmp    = git worktree add --detach $TMP HEAD
         git -C $TMP checkout --no-overlay <base> -- <src roots>   (files added since base are removed [C])
         git -C $TMP checkout --no-overlay HEAD -- <tests in them>  (src/<pkg>/tests, a test_*.py or conftest.py beside the code: HEAD's)
         uv sync --locked; pytest --continue-on-collection-errors --spec <ids + guards + gaps>
count  = pytest --collect-only -q in a second worktree at base (old tests, old code)
```

| Scenario kind | Expected on the old code | Otherwise |
|---|---|---|
| ADDED / MODIFIED / `Spec:` trailer ID | `failed`, `error` (collection) or strict `xpassed` = red | `passed` or `xfailed`: FAIL "<id> pins nothing new" |
| Guard (`Spec-Guard:`, or an init characterization scenario) | `passed` | `failed`: FAIL "guard broke"; collection error: inconclusive (warning) |
| Gap (`[gap: slug]`) | `xfailed` (strict) | `passed`/`xpassed`: FAIL "gap test does not reproduce the gap" |
| Count guard | collected(HEAD) ≥ collected(base) minus tests linked only to REMOVED IDs | FAIL "tests disappeared" |

Notes:
- `--no-overlay` is mandatory. The overlay default leaves files added at HEAD in the "old code" tree, so new-module tests would pass `[C]`.
- `--continue-on-collection-errors` is mandatory. Without it, one bad file stops the whole run `[L*]`.
- The G1 merge of `plan/project-init` passes: characterization scenarios pass on base as guards, and gaps xfail on base.
- The human-only escape hatch is `merge -- --allow <id> --reason "<why>"`, printed into the squash body (Risk 2).
- Targets are under 20 s warm on tipcalc and under 5 s for pre-commit. M3 and M4 measure both.

### 5.6 Anti-cheat

- **Test deletion:** deleting a linked test leaves its scenario untested, so `spec-check` fails unless the scenario is REMOVED in the same commit with `Spec-Removed:` (I4). The count guard backs this up.
- **Skip/xfail:** pre-commit rejects a new `skip` or `xfail` whose reason lacks a scenario ID. xfail is allowed only for `[gap]` scenarios, with `strict=True`.
- **No-behaviour lanes** cannot touch existing test files except through `Test-Harness:` commits, which merge lists for the human (I7).
- **Validate lens 3 (test honesty)** hunts tautologies, mocks of the unit under test, and weakened assertions.

### 5.7 Definition of Done = what `! mise run merge` checks, in order

`mise run status -- --merge` runs steps 1 to 6 as a read-only preview. validate ends with it, so the human sees the checks before typing merge.

> v3.1 adds steps this list and its sample output predate. They are the trunk plan check (I18), the proof bundle (I23, I24), the trunk read (`--read-trunk`, I19), the review depth and the launch mark. The repo's `specs/README.md` has the current list. See [[project-init-v3.1-review-depth]] A.3, C.5 and D.2.

1. The tree is clean; the branch is a lane branch (`--branch` names another worktree's branch). For feat, the change is `approved`.
2. `mise run verify` is green, with `spec-check` strict: nothing pending, no `[NEEDS CLARIFICATION`.
3. prove-red and the count guard pass. Lane rules I7, I11 and I12 pass. The git config `hook install` sets is in place (`core.hooksPath`, `receive.hideRefs`, the pinned guard), and the hook files equal the committed blobs.
4. Run-it rows execute (`timeout 60` each) and match.
5. Human checks and `Test-Harness:` diffs:
   - with a TTY, merge asks y/N for each;
   - without a TTY (the `!` path), `--attest` is required, and the squash body records the checks plus "attested by <git user.name>";
   - with no human checks, no flag is needed.
6. If gate files changed (`.githooks/`, `scripts/project.py`, `.gitleaks.toml`, `ci.yml`, `.claude/settings.json`, the `[tasks]` or `[hooks]` of `mise.toml`), the diff is shown and `--gate-change` is required.
7. A close commit on the branch, under `PROJECT_MERGE`, holds:
   - the roadmap tick, or the `(unplanned)` insert;
   - change `status: done`;
   - `git cliff --with-commit "<title>" -o CHANGELOG.md` `[L*]`.
8. Land:
   - **Remote (D1 option 1):** push the branch, run `gh pr create`, then wait on `gh pr checks`. The required checks and the generated CI's jobs gate the merge, and the rest only warn. In the team tier, merge also waits for `reviewDecision=APPROVED`. Then `gh pr merge --squash --match-head-commit <tip>` with a generated body carrying `Merged-By: mise run merge`, and no `--delete-branch`: gh would then switch to main and pull it outside `PROJECT_MERGE`, which the guard refuses at G1. Merge syncs main itself. `git ls-remote origin` must name the pull request's merge commit, or a later tip that holds it (another merge landed in between). `git fetch` brings that tip, and main fast-forwards to it under `PROJECT_MERGE` when each first-parent commit it brings carries the trailer. Both git calls run as the guard runs its own (3.2). Then the branch is deleted here, and on origin if origin still has it. A pull request that merged on an earlier run whose sync failed goes straight to the sync `[L]`.
   - **No remote:** squash via `git merge-tree --write-tree` + `git commit-tree` + `git update-ref` under `PROJECT_MERGE`. Any worktree that has main checked out is fast-forwarded, and the branch is deleted.
   - **D1 option 2:** the local squash, then `git push origin main` under `PROJECT_MERGE`; pre-push allows it.
9. It prints the next roadmap item, "still right? If not: /sdd replan", then "/clear".

Sample:

```
merge feat/entrypoint-hardening
  tree clean ........ ok      verify ........... ok (lint types secrets test spec-check)
  prove-red ......... ok 6/6 red on base (4 assertion, 2 collection)   guards 1/1 pass
  test count ........ 1 -> 8  spec before code .. ok   amended after approval .. 1 scenario (cli.negative-amount)
  deps -> tech-stack  ok (pydantic-settings added, tech-stack.md changed)
  hooks ............. ok (core.hooksPath=.githooks, 4 files match HEAD)
  human checks ...... 1/1 attested by John Doe
  roadmap ........... ticked entrypoint-hardening (Phase 1: done)   CHANGELOG .. 1 line under Fixed
  merged ............ main (local squash, Merged-By trailer)  branch deleted
  next .............. percent-flag "--percent overrides the default". Still right? If not: /sdd replan
  now ............... /clear
```

The squash body keeps the IDs, the prove-red table, the check results and the attestation. It also copies each `Dismissed:` line of the branch's commits (validate's dismissals), since the squash deletes the branch. That is the durable record on main.

### 5.8 Why "all gates green on code that crashes" (H20) cannot recur

1. **The P1 probe runs the real entrypoints at adoption.** Any traceback becomes a `[gap]` scenario with a strict-xfail test plus roadmap Phase 1. Fixing the crash turns the xfail into a strict XPASS, a red build that forces the scenario to flip.
2. **Every feat must fill Review focus** (I13).
3. **Tests drive the real console script**, never an inner function.
4. **prove-red rejects tests that already pass on the old code.** `--no-overlay` makes the old code genuinely old.
5. **The breaker lens hits the real entrypoint** with Review-focus inputs and with inputs it invents.

What remains: an input nobody named and the breaker did not invent. That is hunted, not guaranteed.

---

## 6. project-init v3: phases

**Shape of the skill:**
- `SKILL.md` is a router of 200 lines or fewer and states no block count.
- `phases/0-preflight.md` … `phases/9-migrate.md`.
- `scripts/init.py` (PEP 723, Rai-only) holds the deterministic work: `preflight`, `probe`, `render [--check]`, `selftest`, `publish`, `migrate-transcripts`.
- **Every machinery file is written by `init.py render`, never by the Write tool.** That makes writes hash-aware (N18), absolute-path and `install -D` based (N17). It also keeps the repo's own gate-file denies from blocking EXTEND.
- `templates/` holds machinery only; product templates live in `12-system/templates/sdd/`.
- `tests/` is pytest for `project.py`, `init.py` and the hooks.

**Rules that replace v2's rule 4:**
- **R1.** Never ask about the standard. Ask about the product: its gaps, as many rounds as the constitution needs (P2).
- **R2.** Every command in a generated file ran green here, or ran its declared `--dry-run` form.
- **R3.** Every write is hash-aware: an unchanged render is updated; a customized file gets a diff and a question.

### P0 Preflight (read-only: no writes, no execution of project code)

**Mode:**
- `.project.toml` present: **EXTEND**.
- v2 stamp `Standard: project-init v2`: **EXTEND + v2 migrate**.
- Any of `accumulated_knowledge.json`, `sessions/`, `summaries/`, `pending/`, `chromadb/`, `project-session-*.py`: **MIGRATE**.
- No `.git` and no code: **SCAFFOLD**.
- Otherwise: **ADOPT**.
- A lone `.claude/` never counts (N24).

**Stops.** Each is a 2-3 option prompt with one (Recommended):
- A dirty tree. Untracked lockfiles are exempt (D3).
- An upstream that is both ahead and behind.
- An `origin` whose root commit differs from HEAD's, or that another local repo also uses (the helios-demo case).

**Facts collected:**
- Default branch; `origin` only; dead remotes are flagged (N25).
- Human authors over 6 months, which sets solo or team (D9).
- `gh auth status`, plan, visibility.
- Tools checked by **running** `<tool> --version`, never `command -v`.
- Env reads found by an AST scan for `os.environ` and `os.getenv`.

**Signals (H4)** come only from parsed evidence, stored with the path in `.project.toml`:

| Signal | Evidence |
|---|---|
| cli | `[project.scripts]` |
| api | fastapi, flask, django or litestar deps |
| db | sqlalchemy, psycopg, asyncpg or redis deps, `alembic.ini`, `migrations/` |
| ui | react, svelte or next deps |
| deploy | Dockerfile, compose, fly.toml, wrangler.toml, `k8s/` |
| pipeline | airflow, dagster, prefect or dbt deps, `dags/` |

**Fixes:** H4, N14, N24, N25.

### P1 Probe (ADOPT, EXTEND, MIGRATE; never writes to the repo)

```
git clone --no-local -q . $TMP/probe           committed state only; the repo is untouched
cd $TMP/probe && uv sync                       a lock is created in the clone if the repo has none
per console script, per env read:
  unshare -rn                                  no network [L*]; without user namespaces: "probe skipped"
  env -i PATH=<clone venv>:<tool bins> HOME=$TMP/home UV_CACHE_DIR=<real cache> LANG=C.UTF-8
  timeout 10 <script> {no args | --help | abc | happy-path args from README fences}
  env probes: VAR="" and VAR=abc, with the happy-path args (or no args)
entry points with api|deploy|pipeline|db signals: --help only
crash = "Traceback (most recent call last)" in stderr
```

tipcalc output (P0 + P1):

```
mode ........ ADOPT            git ..... master, 1 commit, no origin, untracked: uv.lock (lockfile: will commit)
stack ....... python/uv, cli (tipcalc = tipcalc:main)       signals .. cli; no db/api/ui/deploy/pipeline
tools ....... mise 2026.9.12, uv 0.12.10, gh 2.101.0 (Free); gitleaks not runnable (pinned in P4)
probe ....... (scratch clone, network off)
              tipcalc 100 -> "tip: 15.0" exit 0
              tipcalc -> IndexError traceback | tipcalc --help -> ValueError | tipcalc abc -> ValueError
              TIPCALC_DEFAULT_PERCENT="" -> ValueError | TIPCALC_DEFAULT_PERCENT=abc -> ValueError
vault ....... no kitchen/active/idea named tipcalc
```

> v3.1: the probe report now ends with a `surface` line and a `trunk` block (the candidates for `## Trunk`). `phases/1-probe.md` has the current tipcalc sample. P7's punch list then names the proof setup a UI needs. See [[project-init-v3.1-review-depth]] A.2 and C.2.

The residual side-effect surface (Unix sockets, files outside the clone) is Risk 15.

**Fixes:** the probe side of H20; C22 (P0 is now genuinely read-only).

### P2 Talk: intake and constitution

**Sources, in order** (the vault is read only because this runs as Rai):
1. `05-projects/kitchen/<name>/specs/*` (graduate shape: copy, then sanitize).
2. Legacy `kitchen/<name>/{PRD,ROADMAP,BUILD-LOG}.md` and `active/<name>/*`.
3. The idea whose `spawned:` matches, or `09-ideas/<name>.md`.
4. Repo docs: README, `docs/{PRD,SPEC,ARCHITECTURE}.md`, `MISSION.md`, `PLAN.md`, `TODO.md`, `.agent/*.md`, v2 `docs/spec.md` and `facts.md`.
5. `gh issue list --limit 50` when a remote exists.
6. Lockfiles and config.
7. The locked language standard, plus only the team-safe principles from `02-ana/identity/tech-stack.md`.

**Constitution checklist.** The talk ends only when every item is filled or marked:
- **mission:** who it is for, the problem, why now, scope in and out, the success signal, the one-liner;
- **tech-stack:** runtime, distribution, standing rules;
- **roadmap:** at least 2 phases of feature-sized items, the first one concrete.

**Pre-fill.** Every field is filled from its source first. Probe crashes become `[gap]` scenarios and the Phase 1 item.

**The conversation:**
- **Thin sources** (greenfield SCAFFOLD with no kitchen, like Run A): open with a free-text prompt: "Tell me about it: who is it for, what hurts today, what does done look like?" The agent translates the answer into the checklist, then runs decision rounds for what is still open.
- **Decision rounds:** at most 3 questions per round, each with 2-3 options and one (Recommended). Use AskUserQuestion in Claude Code; in other harnesses, numbered options in chat.
- **Cap:** 4 rounds. Anything still open becomes `[NEEDS CLARIFICATION: …]`, and G1 merge refuses while any remain (spec-check).
- **Remote question:** asked only when there is no origin (D2).
- **Headless runs:** gaps become markers directly.

tipcalc (sources are thin but the code answers most fields) gets one round:
1. Mission one-liner.
2. Distribution: none / PyPI.
3. Private GitHub / local only.

> v3.1: the constitution checklist adds the Trunk section of `tech-stack.md`, so tipcalc gets a second round: keep its 1 trunk candidate, edit, or start empty. See [[project-init-v3.1-review-depth]] A.2.

**Sanitize:**
- `[[x]]` becomes `x`.
- Vault paths, personal tooling and 1Password item names are dropped.
- Provenance goes in frontmatter with no path (`source: vault-kitchen 2026-09-23`).
- The gitleaks rules then block anything the sanitizer missed (I14).

**Writes:** mission, tech-stack, roadmap, `capabilities/<entry>.md` (characterization + gaps), `specs/README.md`, `specs/backlog/`.

tipcalc standing rules:
- S-1: external input is parsed by pydantic at the boundary; env via pydantic-settings with `env_ignore_empty=True`.
- S-2: secrets are `op://` pointers only.
- S-3: scripts are uv PEP 723.

**Fixes:** H5, H6, H29, H41 (constitution side); C11 (greenfield conversation).

### P3 Scaffold (SCAFFOLD only)

- Run `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=init.defaultBranch GIT_CONFIG_VALUE_0=main uv init --package --name <n> --description "<mission one-liner>" .` This gives `main` plus uv's Python `.gitignore` `[L]`.
- Then `uv add --dev ruff ty pytest && uv lock`.
- Then the bootstrap commit `chore: scaffold <n>` on main (the first commit; no hooks are active yet).
- Non-Python stacks use a stack pack in `templates/stacks/`, with the same task names.
- **ADOPT with no remote:** `git branch -m master main`. **With a remote:** the rename goes on the punch list; a shared default branch is never renamed here.

**Fixes:** H1, H6, H10, and the root cause of H15.

### P4 Generate (on `plan/project-init`, via `init.py render`)

**Toolchain.** `mise.toml`, rendered for tipcalc:

```toml
min_version = "2026.9.0"

[settings]
lockfile = true
task.run_auto_install = true

[tools]                                   # no python: uv owns it (.python-version + uv.lock)
uv = "0.12.10"
gitleaks = "8.30.1"
"aqua:orhun/git-cliff" = "2.14.1"

[env]
_.file = ".env"                           # knobs + op:// pointers; a missing file is ignored [L]
_.python.venv = { path = ".venv", create = false }

[hooks]
postinstall = "uv sync --locked && uv run --script scripts/project.py hook install"   # `mise install` = whole setup [L]

[tasks.start]      { description = "Run the app; args after --",                 run = "uv run --locked tipcalc" }
[tasks.fmt]        { description = "Format and autofix",                          run = ["uv run --locked ruff format .", "uv run --locked ruff check --fix ."] }
[tasks.test]       { description = "Tests; args after --, e.g. -- --spec cli.no-args", run = "uv run --locked pytest" }
[tasks.verify]     { description = "The local gate; CI runs it too (specs/README.md#gates)", depends = ["lint", "types", "secrets", "spec-check"], run = "echo verify: green" }
[tasks.lint]       { hide = true, description = "Lint + format check",           run = ["uv run --locked ruff check .", "uv run --locked ruff format --check ."] }
[tasks.types]      { hide = true, description = "Type check",                    run = "uv run --locked ty check" }
[tasks.secrets]    { hide = true, description = "Secret + leak scan of history", run = "gitleaks git --redact --no-banner ." }
[tasks.spec-check] { hide = true, description = "Scenario <-> test trace + lane rules", depends = ["test"], run = "uv run --script scripts/project.py check" }
# visible, each run = "uv run --script scripts/project.py <name>": status, change, backlog, tdd, doctor
# human (description starts "HUMAN:"): approve, merge, abandon (+ release when distributable)
# hidden: prove-red, selftest
```

- **Inline tables are for display only.** The shipped file uses one `[tasks.X]` table per task, each with a description.
- **tipcalc task count:** `mise tasks ls` shows 12 (start, fmt, test, verify, status, change, backlog, tdd, doctor, approve, merge, abandon). 6 are hidden but still runnable `[L*]`. `release` is omitted because distribution is none. v3.1 adds the visible `proof` task ([[project-init-v3.1-review-depth]] C.2).
- **After writing:** `mise trust` (an untrusted config breaks every shim, including Claude's own `uv` `[L]`), then `mise lock --platform linux-x64`, then `mise install`.
  - Team tier: doctor detects a teammate's platform missing from `mise.lock` and prints the `mise lock --platform <os-arch>` command. It lands through a chore change `[U]`.
- **`uv` is always called with `--locked`, never `--frozen`** (`--frozen` exits 0 while silently skipping new deps `[L]`).

**Typed env contract** (`.env.example`):

```
# NAME | kind | type | required | default | notes          (an empty value means unset: the default applies)
# TIPCALC_DEFAULT_PERCENT | knob | float 0..100 | no | 15 | tip percent when none is given
#TIPCALC_DEFAULT_PERCENT=15
```

- Knobs stay commented out.
- A secret row reads `# NAME | secret | str | yes | - | op:// pointer; read in <files>`, with `#NAME=op://<vault>/<item>/<field>` under it. The contract lists only the variables the project reads: it has no example row.
- An empty knob equals unset in the app (pydantic-settings `env_ignore_empty=True`: `""` gives the default 15.0; `abc` raises `ValidationError` `[L*]`) and in doctor ("empty: default 15 applies").
- doctor fails on a non-empty value of the wrong type. For a secret, it fails when the value is not an `op://` pointer, or when the secret is required and unset. An optional secret (`required no`) left unset is ok.
- Secret-bearing projects render `start` as `op run --env-file .env -- uv run --locked <n>` `[U]`.

**Gates:**
- `.githooks/pre-commit`, `commit-msg` and `pre-push` are two-line shims: `exec mise x -- uv run --script scripts/project.py hook <name> "$@"`. If mise is missing, `exec` fails and the hook blocks: the git layer fails closed.
- **pre-commit** is the staged subset of verify. It works on `git diff --cached --name-only --diff-filter=ACMR -z`, which works before the first commit `[L]`:
  1. Lane rules I1, I2, I4, I5 on the staged diff. During a merge commit, the lane rules skip a path whose staged content is git's merge result or MERGE_HEAD's copy. That content came from the merged branch.
     I4 and the unknown-id check read a file as a test the way commit-msg does. A test is under a test root, or it is a `test_*.py` or `conftest.py` beside the code in a `src` root. I7 counts the same files as existing tests.
  2. Staged content, not the working tree (H22):
     - for each staged `.py`: `git show :<path> | ruff check --force-exclude --stdin-filename <path> -` and the same with `ruff format --check` `[L*]`;
     - `ty check <files>` in place when no staged file has unstaged edits; otherwise on an index export (`git checkout-index` of tracked `.py` + config into `$TMP`) with `ty check --python .venv/bin/python` `[L*]`.
  3. `gitleaks git --pre-commit --staged --redact --no-banner .` with the `.gitleaks.toml` leak rules `[L*]`. If `gitleaks version` fails: exit 1 "run: mise install". No bypass variable.
  4. The skip/xfail rule, on every staged `.py`: a root `conftest.py` or a plugin skips tests too. A skip named by a string (`getattr(pytest.mark, ...)`, `add_marker("skip")`) is refused, because its reason cannot be read.
  5. Target: under 5 s (measured in M4).
- **commit-msg:**
  - Conventional types: `feat change fix perf refactor build ci docs test chore spec style revert`, with `!` for breaking.
  - The subjects git writes pass when the subject inside them is conventional: `Revert "<s>"`, `Reapply "<s>"`, `fixup! <s>`, `squash! <s>`, `amend! <s>`. To revert a commit whose subject is not conventional, write `revert: <summary>`.
  - On `feat/`, `chg/` and `fix/`, a commit touching `src` roots needs `Spec:` or `Spec-Removed:`. Tests inside them are not source: a test root such as `src/<pkg>/tests`, or a `test_*.py` or `conftest.py` beside the code.
  - `Spec:` and `Spec-Guard:` IDs must exist in the index. `Spec-Removed:` IDs must exist at HEAD and be absent from the index.
  - `Test-Harness:` needs a reason.
- **pre-push:** refuses updates to `refs/heads/<default>`, with two exceptions. (a) Bootstrap (N10): the remote lacks that branch, and the local default branch goes up as it is. (b) `PROJECT_MERGE` is set: merge's own push (D1 option 2). It does not run verify; merge and CI do.
  - It guards the branch in the `D=` line of the reference-transaction hook, in the working tree and in the pinned copy. It also guards the one `.project.toml` names. An edit to `.project.toml` can add a name, never remove the rendered one.
- **`hook install`** (mise's postinstall; doctor and merge check the result) sets three things in the local git config, each once `[L*]`:
  - `core.hooksPath=.githooks`;
  - `receive.hideRefs=refs/heads/<default>`. A push into the repo itself (`git push . x:main`) runs receive-pack inside `.git`, where no client hook runs;
  - `hook.project-main-guard` for the `reference-transaction` event: it runs the guard from a pinned blob, the default branch's committed copy (the working tree's before the bootstrap commit). It steps aside while `.githooks/reference-transaction` is that blob and executable. So a `reset --hard` or merge that rewrites `.githooks/` before it moves main still meets the guard.
- **reference-transaction** `[L*]` (every case in the M4 matrix below runs in `mise run selftest`):

```sh
#!/bin/sh
# main moves only via project.py (PROJECT_MERGE), a sync to what origin really holds, or the first commit.
[ "$1" = prepared ] || exit 0
D=main; Z=0000000000000000000000000000000000000000                      # D rendered from .project.toml
T=$(command -v timeout || command -v gtimeout)                  # coreutils; without it, ls-remote runs untimed
refuse() {
  echo "blocked: $1" >&2
  echo "  git may have changed the index and files for this move already: check git status" >&2; exit 1
}
empty_repo() {  # no ref, no reflog, and no commit in the object store but the new one
  [ -z "$(git rev-list -n 1 --all --reflog 2>/dev/null)" ] || return 1
  git cat-file --batch-all-objects --batch-check='%(objecttype) %(objectname)' | grep '^commit ' | grep -qv " $new\$" && return 1
  return 0
}
while read -r old new ref; do
  [ "$ref" = "refs/heads/$D" ] || continue
  cur=$(git rev-parse -q --verify "refs/heads/$D")
  [ "$cur" = "$new" ] && continue
  [ "$new" = "$Z" ] && continue                                     # delete, rename, pack-refs, gc: recoverable
  [ -z "$cur" ] && empty_repo && continue                           # first commit of an empty repo
  [ -n "$PROJECT_MERGE" ] && continue                                                   # project.py merge/abandon/release
  want=$(git --no-replace-objects show "refs/heads/$D:.project.toml" 2>/dev/null | sed -n 's/^origin_url = "\(.*\)"$/\1/p')  # replace refs cannot forge it
  if [ -n "$want" ] && [ "$want" = "$(git remote get-url origin 2>/dev/null)" ]; then
    remote=$(${T:+$T 10} git ls-remote origin "refs/heads/$D" 2>/dev/null | cut -f1)
    [ -z "$remote" ] && refuse "cannot reach origin to confirm $D"   # recovery: retry online, core.sshCommand in ~/.gitconfig, or the by-hand sync
    if [ "$new" = "$remote" ]; then                                 # a sync to what origin holds, if merge landed it all
      log=$(git --no-replace-objects log --first-parent --format='%h %(trailers:key=Merged-By,valueonly,separator=%x2C,unfold)' "$new" --not "$cur" --) || log="?"
      bad=$(printf '%s\n' "$log" | grep -v '^[0-9a-f]* mise run merge$' | grep . | cut -d' ' -f1 | head -n 5 | tr '\n' ' ')
      [ -z "$bad" ] && continue
      refuse "origin's $D holds commits that did not land through 'mise run merge' (no Merged-By trailer): $bad"
    fi
  fi
  [ -z "$cur" ] && refuse "$D is missing here, and only a human recreates it (specs/README.md#gates)"
  refuse "$D moves only via 'mise run merge' (specs/README.md#gates)"
done
exit 0
```

- Every delete passes (`branch -D`, `branch -m`, `pack-refs`, `gc`): a deleted main is recoverable from origin and the reflog. Recreating it is blocked unless the repo is empty `[L*]`. A human restores it after checking origin: `PROJECT_MERGE=1 git branch main origin/main`.
- The guard ends each refusal with the `check git status` line. `pull` and `reset --hard` rewrite the index and files before the ref moves, so a refused sync can leave them changed.
- `timeout` (or `gtimeout`) bounds `ls-remote` to 10 s where coreutils exists. Without it the sync still works, untimed.
- **`.gitleaks.toml`** `[L*]`:
  - `[extend] useDefault = true`.
  - `personal-path` regex `((?:~[A-Za-z0-9._-]*|\$HOME|\$\{HOME\})/helm\b|(^|[^/\w])helm/0[0-9]-)`: the vault under any home spelling, and a vault folder not after `/` or a word character, so `k8s/helm/01-base` passes.
  - `personal-home-path` regex `(?:^|[^\w.-])/((?:home|Users)/[A-Za-z][A-Za-z0-9._-]*)(?:/|\b)` with `secretGroup = 1`. gitleaks' default global allowlist passes a secret that starts with `/home/` or `/Users/`, so the reported secret drops the leading slash. A URL or relative path (`https://x/home/a`, `src/home/`) does not match.
  - Both are scoped to `(\.md$|^\.claude/|^\.agents/|^AGENTS\.md$)`.
  - `wiki-link`, scope `\.md$`. A line with only a dotted TOML array-of-tables header (`[[tool.uv.index]]`) is allowlisted for it.
  - The allowlist includes the config itself.
  - At adoption, if the history scan finds anything, write `.gitleaksignore` with the fingerprints and put "rotate these" on the punch list.
- **Brownfield lint debt (N3):** a ruff `per-file-ignores` block built from `ruff check --output-format json`, marked `# project-init baseline: shrink only`. doctor fails if it grows; the debt becomes a backlog item. For ty, see Risk 8.
- **CI** (only when a remote exists):

```yaml
name: ci
on:
  push: { branches: [main] }       # rendered from the detected default; EXTEND re-checks
  pull_request: {}
jobs:
  verify:
    name: verify
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4   # P4 resolves the current major via gh api
        with: { fetch-depth: 0 }
      - uses: jdx/mise-action@v4     # tools pinned by mise.lock
      - run: mise run verify         # `uv run --locked` syncs the venv itself; no postinstall needed [D]
      - if: github.event_name == 'pull_request'
        run: mise run prove-red -- --base "origin/${{ github.base_ref }}"
      - if: github.event_name == 'push'
        run: mise run status -- --audit   # annotation for main commits that skipped merge
```

  If a repo already has CI (helios: `backend`, `frontend`), it is kept, and `sdd.yml` is added, with workflow and job both named `sdd`.

**Memory:**
- `project_memory/README.md` (the routing table);
- `lessons.md` (seeded or carried over);
- `decisions/`;
- `team.md` in the team tier only (D9);
- `.gitattributes`: `project_memory/lessons.md merge=union`.

**Claude environment** (`.claude/settings.json`):

```json
{
  "hooks": {
    "SessionStart": [{"hooks": [{"type": "command", "command": "mise x -- uv run --script \"$CLAUDE_PROJECT_DIR/scripts/project.py\" hook session-start || echo 'project hooks are OFF on this machine: install mise, then run: mise install'"}]}],
    "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "mise x -- uv run --script \"$CLAUDE_PROJECT_DIR/scripts/project.py\" hook pre-bash"}]}]
  },
  "permissions": {
    "allow": ["Bash(mise run start *)", "Bash(mise run fmt)", "Bash(mise run test *)", "Bash(mise run verify)",
              "Bash(mise run status *)", "Bash(mise run change *)", "Bash(mise run backlog *)", "Bash(mise run tdd *)",
              "Bash(mise run doctor)", "Bash(mise run lint)", "Bash(mise run types)", "Bash(mise run spec-check)",
              "Bash(mise run prove-red *)", "Bash(mise run selftest)", "Bash(mise tasks *)", "Bash(uv run --locked *)",
              "Bash(git status *)", "Bash(git diff *)", "Bash(git log *)", "Bash(git show *)", "Bash(git switch *)",
              "Bash(git add *)", "Bash(git commit -m *)", "Bash(git merge *)", "Bash(git fetch *)", "Bash(git pull --ff-only *)",
              "Bash(git worktree *)", "Bash(gh pr view *)", "Bash(gh pr checks *)", "Bash(gh run view *)", "Bash(gh issue list *)"],
    "deny":  ["Bash(mise run approve*)", "Bash(mise run merge*)", "Bash(mise run abandon*)", "Bash(mise run release*)",
              "Bash(gh pr merge*)", "Bash(git push --force*)", "Bash(git push -f*)",
              "Edit(/.githooks/**)", "Edit(/scripts/project.py)"]
  }
}
```

- **Deny rules:**
  - They are prefix forms only. They match past any leading assignment and inside nested subcommands, and deny wins over allow in every mode `[D]`.
  - `Edit(/…)` is anchored at the project root. It covers every built-in edit tool, including Write, plus Bash `sed`/`tee`/redirect targets `[D]`.
  - No substring denies live here: they blocked read-only commands (N9 regression).
- **`project.py` as launcher.** It reads the hook's stdin `cwd`. If that directory's git toplevel is a different worktree with its own `scripts/project.py`, it re-execs that file with the same stdin, because `$CLAUDE_PROJECT_DIR` stays at the session root inside worktrees `[D]`.
- **`pre-bash`:**
  1. **Read-only exemption.** If every subcommand is a known read (`cat`, `less`, `head`, `tail`, `grep`, `rg`, `ls`, `wc`, `stat`, `file`, `diff`, `sed -n` without `-i`, `find` without `-exec`/`-delete`, and git `log`/`show`/`diff`/`status`/`rev-parse`/`ls-files`/`ls-remote`/`config --get`/`branch --list`), with no `>`, `>>` or `tee`, the command is allowed.
  2. **Otherwise deny** when the text contains any of:
     - `PROJECT_MERGE`;
     - `mise (run |r |tasks run )?(approve|merge|abandon|release)\b` or `project\.py (approve|merge|abandon|release)\b`;
     - `--no-verify`, or `git commit -n`;
     - `core.hooksPath` in any case (git config keys are case-insensitive), a `hook.` config key (`-c hook.<name>.enabled=false`), `GIT_CONFIG_(COUNT|KEY_|VALUE_|PARAMETERS)`;
     - `git send-pack`, which pushes without pre-push;
     - `.githooks/`, `.git/hooks`, `.git/config`;
     - `gh api` writes, `gh pr merge`, `gh repo (edit|delete|rename|archive)`, `gh ruleset`.
  3. **Script indirection.** When a subcommand runs `sh`, `bash`, `zsh`, `source`, `.`, `python`, `python3`, `uv run` or `node` on a file inside the repo or a temp dir, `pre-bash` reads that file (up to 256 KB) and applies the same patterns.
  4. **Failure mode.** If mise is missing, the hook command fails non-blocking (fail open), and SessionStart says so loudly (Risk 1).
- **Settings reload.** Claude Code reloads a `settings.json` written mid-session `[D]`. From P5 on, project-init's own session runs under these rules, which is why P5's matrix and P7's remote steps run inside `init.py` or `project.py` subprocesses.
- **No `.mcp.json`:** `gh` already has `repo,workflow` `[L]`.
- **Personal additions** go in `settings.local.json`; list keys merge `[D]`.

**Project skill.**
- `.claude/skills/sdd/` is rendered from `project-init/templates/skills/sdd/` (section 7).
- If the M6 check shows pi or OpenCode need it, `.agents/skills/sdd` is rendered as a symlink to it. Both binaries reference `.agents/skills` and `.claude/skills` (string evidence only) `[L*]` `[U]`.
- Per-signal skills are generated only with file evidence, and each is verified by dry-run:
  - `run-<name>`: services only, with failure modes;
  - `db`: `alembic current`;
  - `deploy`: `wrangler deploy --dry-run`.
- The name `run` is never used, because it would replace the bundled `/run` `[D]`.
- **Render gate:** the rendered skill must pass the same gitleaks leak rules (I14), not a raw grep. That keeps `k8s/helm/` valid.

**Release shapes** (from the `## Distribution` line in tech-stack.md):

| Distribution | `! mise run release -- <bump>` | P5 verifies with |
|---|---|---|
| pypi | internal branch `release/vX.Y.Z`: `uv version --bump`, `git cliff --bump -o CHANGELOG.md` `[L*]`, merge → tag → `uv build` → `op run -- uv publish` | `uv version --bump patch --dry-run`, `git cliff --bumped-version` `[L]`, `uv build -o $TMPDIR` |
| git (installed from repo) | same, without publish; `gh release create` when a remote exists | the same dry-runs |
| service | tag + changelog; the `deploy` skill deploys | the deploy tool's dry-run |
| none | no release task; CHANGELOG still maintained per merge | n/a |

**git-cliff config** lives in `pyproject.toml` `[tool.git-cliff]`, which git-cliff reads directly `[L*]`:
- the Keep a Changelog header;
- groups: Added (`feat`), Changed (`change`), Removed (any `type!:`), Fixed (`fix`), Performance (`perf`);
- `spec`, `chore`, `ci`, `docs`, `test`, `style`, `build`, `refactor` are skipped;
- no emoji;
- `features_always_bump_minor = true`.

**`project.py` subcommands** (one PEP 723 script, stdlib only, `requires-python >=3.12`, ruff/ty-clean; N7, N11):

| Group | Subcommands |
|---|---|
| Specs | `check [--change <slug>]`, `status [--change] [--merge] [--audit]` |
| Lifecycle | `change <slug> [--lane] [--hotfix] [--parallel]`, `backlog <topic> [--spike]`, `approve`, `merge [--branch] [--attest] [--gate-change] [--allow <id> --reason]`, `abandon <why>` |
| TDD | `tdd red\|green <ids>`, `prove-red [--base]` |
| Machine | `doctor`, `selftest`, `release <bump> [--dry-run]` |
| Hooks | `hook pre-commit\|commit-msg\|pre-push\|session-start\|pre-bash` (plus the launcher re-exec) |

**Fixes:** H3, H12, H13, H14, H15/H24, H16, H17, H18, H19, H21, H22, H23, H33, H34, H35, H36, H37, H38; N2, N3, N4, N5, N7, N9, N10, N11, N12, N19, N20, N22.

### P5 Verify

**Positive checks.** Every command runs under `timeout 60`:
- `mise install`, `mise run doctor` (0 FAIL), `mise run verify`, `mise run start -- --help`;
- each AGENTS.md command, and the dry-run release/deploy/db commands;
- builds go to `$TMPDIR`;
- a server is health-probed, then killed by PID, never with `pkill -f` (N13).
- v3.1: `mise run proof -- --help` joins the task checks ([[project-init-v3.1-review-depth]] C.2).

**Negative matrix: `mise run selftest`.** It runs as one subprocess, so the session's permission rules never mask a result (C20).
- It works in `git clone --no-local . $TMP/v` with `git init --bare $TMP/origin.git`. Every case must FAIL; a case that passes fails P5 (N26):
  - commit on main after the first commit; `--no-verify` commit on main;
  - `branch -f main`, `update-ref refs/heads/main`, `reset --hard HEAD~1` on main, fast-forward merge into main;
  - forged `refs/remotes/origin/main` then `branch -f main`;
  - origin re-pointed at a fake bare repo then synced;
  - rename main away then recreate it at another commit;
  - offline origin sync;
  - push to `origin main` once it exists; push `feat/x:main`;
  - staged fake key; a staged `.md` containing `~/helm/…`, `$HOME/helm/…`, `/home/<user>` or `/Users/<user>`;
  - a partially staged `.py` whose staged copy has a type error and whose working copy is clean;
  - `specs/mission.md` staged on `feat/`;
  - a new `skip` without an ID, in a test file, in a root `conftest.py`, or named by a string; `update stuff` or `Revert "update stuff"` as a commit message;
  - `feat:` touching src without `Spec:`; a test tagged `nope.nope`;
  - removing a scenario without `Spec-Removed:`;
  - deleting main, then recreating it, also after wiping every ref and reflog;
  - a sync of an origin main that moved outside merge (no `Merged-By`);
  - `reset --hard` or a fast-forward of main to a commit that drops or weakens `.githooks/`;
  - a push into the repo itself: `push .`, `push --no-verify .`, `send-pack .`.
- Each refusal of the main guard must also print `check git status`.
- **pre-bash cases** are fed as JSON to `project.py hook pre-bash` in-process. Must deny:
  - `mise run merge`;
  - `sh -c "PROJECT_MERGE=1 git merge x"`;
  - `bash ./x.sh` where x.sh contains `PROJECT_MERGE=1`;
  - `git -c core.hooksPath=/dev/null commit`, `git -c core.hookspath=/dev/null commit`, `git -c hook.project-main-guard.enabled=false branch -f main x`;
  - `git send-pack origin feat/x:main`;
  - `gh api -X PUT repos/o/r/pulls/1/merge`;
  - `gh api -X DELETE …/protection`;
  - `cp /tmp/h .githooks/pre-commit`.
- **Must also PASS:**
  - bootstrap commit, `pack-refs`, `gc`;
  - `pull --ff-only` and `reset --hard origin/main` to a real origin tip;
  - `push -u origin feat/main-menu`;
  - a commit from a worktree via `cd ../wt`;
  - pre-bash allows `grep -n PROJECT_MERGE scripts/project.py`, `git config --get core.hooksPath`, `grep -- --no-verify specs/README.md`, `mise run test -- -k merge`.

**Fixes:** N12, N13, N26; C20.

### P6 Front door, assembled last

**AGENTS.md** (at most 40 lines, BMAD admission test: nothing derivable from the repo):

```markdown
# tipcalc
Why and scope: `specs/mission.md`. Stack and standing rules: `specs/tech-stack.md`. Next work: `specs/roadmap.md`.
The process (lanes, formats, gates, Definition of Done): `specs/README.md`.

## Commands
All commands are mise tasks (`mise tasks ls`). Once per machine: `mise install`.
Before you call anything done: `mise run verify`. CI runs verify plus prove-red, and merging adds the
Definition of Done (`specs/README.md#gates`). Run the app: `mise run start -- 100`.

## How work happens
1. Every change starts with `/sdd "<what you want>"` (no skills in your agent? read `.claude/skills/sdd/SKILL.md`). It picks the lane.
2. approve, merge, abandon and release are human gates. Never run them; stop and ask.
3. No production code without a failing test tagged with its scenario id (`@pytest.mark.spec("cli.no-args")`). Commit on green.
4. A behaviour change edits its scenario in `specs/capabilities/` in the same commit as its test and code.
5. Out-of-scope ideas: `mise run backlog -- <topic>`. Never edit `specs/roadmap.md` or `specs/mission.md` outside a `plan/` branch.

## Memory
- Something surprised you: append to `project_memory/lessons.md` now.
- A choice future changes must respect: one file in `project_memory/decisions/`.
- Secrets: `op://` pointers only, never values.
```

**README.** The existing README is audited: every fenced command is checked against mise tasks or repo binaries, and stale ones are listed. The tool-owned quickstart region is replaced, with the diff shown:

```
curl https://mise.run | sh      # once per machine
mise install                    # tools, dependencies, git hooks
mise run verify                 # green = ready
mise run start -- 100           # tip: 15.0
```

> v3.1: AGENTS.md gains two items under How work happens: the trunk diff and proof at merge, and the launch. The quickstart region gains one line on the trunk diff and the proof folder. The samples above predate them. See [[project-init-v3.1-review-depth]] C and D.

There is no CLAUDE.md or CLAUDE.local.md; either one would switch off native AGENTS.md loading `[D]`.

**Fixes:** H7, H8, H9, H11, H26, H30, H31; C7.

### P7 Ship and punch list

- **Staging:** `git add -- <[generated] paths + constitution + lockfiles>`, never `-A` (N14).
- **Commit:** `chore(init): project-init v3`. The body is written after P5 and holds real results (N21).
- **Remote** (D2 = GitHub), via `init.py publish`:
  1. `gh repo create <n> --private --source . --remote origin -d "<one-liner>"` (no `--push`);
  2. `git push -u origin main` (pre-push allows it: the remote lacks main);
  3. `git push -u origin plan/project-init`;
  4. `gh repo edit --default-branch main --delete-branch-on-merge --enable-squash-merge`;
  5. write `origin_url` into `.project.toml` on the branch.

  The default branch is `main` explicitly, not whatever HEAD was (C5).
- **Final prompt:** "review, then `! mise run merge`" (G1), then "/clear before the first `/sdd`".
- **Punch list** (human-only):
  - `git config --global init.defaultBranch main`;
  - 1Password items named in the env contract;
  - server rules state, recorded once in `.project.toml` (`unavailable: Free private`) and never retried;
  - secrets to rotate, if `.gitleaksignore` was written;
  - a remote default-branch rename.

**Fixes:** H2, H3, N1, N14, N21, N22, N23; C5.

### EXTEND (audit + upgrade)

**Hash-aware regeneration** through `init.py render`. An unchanged file is upgraded silently; a customized file gets a diff and a question (N18).

**Checks:**
- placeholders `\{[A-Z_]+\}` and "Add your description here";
- CI push branch against the default branch; CI job names against required checks;
- CODEOWNERS against team.md (team tier);
- every gate calls a mise task; the doc-command check (I15);
- the ruff baseline only shrinks; the `project.py` version;
- `core.hooksPath` is set; hook files match their committed blobs; the trailer audit since `audit_since`;
- `.agent/` tracked in git triggers D7;
- 2+ human authors triggers an offer of the team tier (D9);
- **a remote that appeared since the last run triggers the remote steps:** `origin_url`, CI, repo settings, and server rules after the first green CI run using the observed job names (N23, N2).

**Rai-only checks:**
- `05-projects/active/<name>/` holding vision, roadmap or architecture raises "direction lives in the vault; migrate to specs/".
- A fact kept in both places is compared (the orca 518 vs 537 case).

**Fixes:** N15, N18, N23.

### MIGRATE

**v1 JSON (helios):**
1. **Transcripts** (N1, C4), via `init.py migrate-transcripts`:
   1. Move `sessions/`, `pending/` and `summaries/` into a local quarantine `~/.local/state/project-init/quarantine/<repo>-<date>/` (mode 700, outside every repo and Syncthing folder) **before** the `.gitignore` block is touched.
   2. Run `gitleaks dir <quarantine> -f json`. Replace every reported `Secret` string in place with `REDACTED:<rule-id>`. A rescan must exit 0 `[L*]`.
   3. Only then copy the redacted set to `~/helm/13-archive/historical-sessions/<repo>/` (git-tracked in helm; helm's own commit flow and security validator run on it).
   4. The rotation list (rule + file, never values) goes to the punch list. The quarantine is deleted after John confirms.
   5. Nothing from these folders is ever staged in the project repo.
2. `accumulated_knowledge.json` (field `date`, falling back to `decided`) is rendered once into `specs/backlog/<date>-legacy-knowledge.md`, bannered "snapshot <mtime>, unreviewed". It feeds P2 intake and is then `git rm`'d (N16).
3. Legacy hooks are removed from whichever settings file registers them, including `settings.local.json`.
4. The staged gitleaks scan runs on the migration commit.

**v2 → v3 (tipcalc).** One prompt shows each v2 file's fate; option 1, apply all, is Recommended.
- `.mise.toml` → `mise.toml` (git mv; the python pin is dropped).
- `facts.md` → tech-stack.md and the mission glossary.
- `decisions.md` D-NNN → `decisions/<date>-<slug>.md` with `aliases: [D-007]`.
- `lessons.md` is kept. `log.md` is deleted (D5).
- These are deleted: Makefile, doctor.sh, verify.sh, `scripts/git-hooks/`, ONBOARDING, `docs/spec.md` (its content feeds intake), `.claude/hooks/*`, `.claude/skills/{run,verify,release}`, `.mcp.json`, and CODEOWNERS/PR template when solo (D9).
- `extend-exclude = [".claude"]` is removed from pyproject.

**Committed `.agent/` (open-kit, orca):** per D7.

---

## 7. Skill changes

### 7.1 In every repo: one generated skill, `sdd` (portable, vault-path-free)

```yaml
---
name: sdd
description: >
  This repo's spec-driven, test-driven loop. USE WHEN starting any change ("/sdd add split bill"),
  writing specs, compiling an approved spec test-first, validating, replanning, or asking what is next
  (/sdd status). Follows specs/README.md. Never runs approve, merge, abandon or release.
argument-hint: "<what you want> | talk | compile | validate | replan | status"
---
```

| File | Job | Built from |
|---|---|---|
| `SKILL.md` | Router. Classifies out loud **by linking `specs/README.md#lanes`** (it never restates the table), runs `mise run change`, and routes: feat to talk; fast lanes to their recipe (red first where behaviour moves); ideas and spikes to `backlog`; roadmap work to `replan`. | course `/change` + superpowers ratchet |
| `talk.md` | Constitution and feature spec. Evidence first; a free-text opener when sources are thin; decision rounds of at most 3 questions (AskUserQuestion in Claude Code, numbered options elsewhere), 2-3 options with one Recommended; writes capabilities + the 3 files; Review focus; over/under-specification checks; size caps; ends with `mise run status` and "run `! mise run approve`". Starting a scheduled item moves its backlog file's content into requirements.md and deletes the file. | grill method + course feature-spec + think/spec-driven checks + execplan-create quality rules |
| `compile.md` | **The canonical TDD text** (vault `testing/tdd.md` points here). Resumes at the first group whose IDs lack passing tests; the loop in 5.4; drift, stop, backlog and risk-pause rules; one commit per group on green; lesson prompt. | goal + rewritten tdd.md |
| `validate.md` | Lenses by lane. **feat:** (1) conformance (missing / partial / contradicts / unrequested), (2) breaker (hostile inputs on the real entrypoint, plus "if this broke, would a test fail?"), (3) test honesty. **chg / fix:** breaker only. **chore / refactor:** none (verify + I7). Claude Code runs lenses as subagents; other harnesses run them in sequence. Each finding becomes scenario + test + code, a backlog item, or a dismissal with its reason in the commit body. Ends with `mise run status -- --merge` and "run `! mise run merge`". | course lesson 9 + spec-kit converge + BMAD verification gap |
| `replan.md` | Precondition: clean break. Inputs: roadmap, open backlog, lessons since the last replan, open `[gap]`s, deferred findings. Edits the roadmap (slugs permanent), schedules or drops backlog items, amends tech-stack, improves the process (edits `specs/README.md` or these files; EXTEND then sees a customized hash). | course lesson 8 |

Rules:
- The render gate is the gitleaks leak rule set (I14).
- The vault must never define a top-level skill named `sdd`, because a personal skill beats a project skill `[D]`.

### 7.2 In the vault (D6)

| Skill / file | Verdict | Change | Milestone |
|---|---|---|---|
| `project-init/` | **Rewrite (v3)** | Sections 6 and 12, plus `scripts/init.py`. | M1-M7 |
| `grill/` | **Keep, reshape; absorbs execplan-create** | **In a repo with `.project.toml`:** read `.claude/skills/sdd/talk.md` and follow it, adding the Rai extras (vault intake, extra rounds, an offer of `/spec-improve` and `/visual plan` before G2). **Elsewhere** (helm, one-offs): write `.agent/decisions.md` + `.agent/plan.md` (gitignored scratch) using execplan-create's plan rules, with no narration sections and no checkbox decisions. Fix grill:18. | M8 |
| `execplan-create/` | **Retire** | Its quality rules move into grill and the `plan.md` template. | M8 |
| `goal/` → **`compile/`** | **Rename + reshape** | In SDD repos, follow `sdd/compile.md` then `validate.md`, adding Rai extras (`/orchestrator` for 3+ disjoint groups, `/adversarial-review` after validate). Elsewhere, execute `.agent/plan.md`. Frees the built-in `/goal`. | M8 |
| `execplan-improve/` → **`spec-improve/`** | **Rename + reshape** | One Ousterhout + spec-lint pass over a change folder or `.agent/plan.md`. `skip` means "no edits, stop at approval"; it never chains into implementation. Delete the vault path at :29. | M8 |
| `adversarial-review/` | **Keep** | Inputs: change folder + capability diff + `git diff <default>...HEAD`. Out-of-scope findings go to the backlog. Fix :75 and MANIFEST:54. | M8 |
| `orchestrator/` | **Keep, reshape** | Briefs from `plan.md` groups with `parallel: yes`. Workers on `feat/<slug>--g<n>` merge into `feat/<slug>`, never main. Workers never write roadmap, mission, other groups' capabilities, or `project_memory`. Run dir: gitignored `.agent/orchestrator/` (fix :55, :232). `feature/` → `feat/`. | M8 |
| `testing/tdd.md` | **Reduce to a pointer** | "Read `project-init/templates/skills/sdd/compile.md`. Outside an SDD repo, skip the spec-ID and `mise run tdd` steps." One TDD text, no drift (C6). Add frontmatter. | M8 |
| `testing/verify-completion.md`, `pragmatic.md`, `unit-test.md` | **Keep** | Seed `validation.md`; spikes; brownfield characterization. | none |
| `think/spec-driven.md` | **Retire** | Folded into `sdd/talk.md` and `specs/README.md`; remove its row in `think/SKILL.md`. | M8 |
| `visual/plan.md` | **Keep, reshape input** | Renders a change folder for G2 into `.agent/visual/<slug>.html`. Fix stale refs :18, :30, :58. | M8 |
| `MANIFEST.md` | **Fix** | Pipeline rows, :54, :107, `.agent/` = gitignored scratch. | M8 |
| `03-rai/AGENTS.md` | **Add 1 routing line** | "SDD repos: talk = /grill, build = /compile; both follow the repo's `.claude/skills/sdd`." (`coding-format.md` is already over its 4 KB budget.) | M8 |
| `12-system/templates/sdd/` | **New** | mission, tech-stack, roadmap, capability, requirements, plan, validation, backlog, decision, lesson. | M1 |
| `ideas/graduate.md` | **Reshape** | Scaffolds `05-projects/kitchen/<name>/specs/{mission,tech-stack,roadmap}.md` + `backlog/` + `research/` from `12-system/templates/sdd/`. | M9 (separate approval) |
| `12-system/templates/PRD.md` | **Pointer** | Points at `12-system/templates/sdd/`. | M9 |
| `11-workflows/01-project.md`, `02-task.md`, `03-kitchen.md` | **Rewrite as pointers** | 01 and 02 link to the repo process template (`project-init/templates/specs-README.md`) instead of restating the loop or lane table (C6). 01 keeps one **D2** diagram of the vault-side flow (idea → kitchen → project-init → repo loop), which exists nowhere else. 03: "zero open questions" becomes "open questions are roadmap Gates". | M9 |
| `03-rai/AGENTS.md` memory routing rule, `distill_session.py`, `turn-capture.py` | **Edit** | Section 8 (H27). | M10 (separate approval) |
| `pai-brain` synced plugin | **Per D10** | Default: remove only `project_init` and `tdd`. | M11 |

**Count:**
- Vault: 2 retired (execplan-create, think/spec-driven), 2 renamed, 0 new skills.
- Per repo: 1 skill, replacing v2's 3 defaults.

---

## 8. Memory

```
                        +-------------------- the repo (team truth) --------------------+
 why / who / scope ---> | specs/mission.md                                              |
 stack, rules S-n ----> | specs/tech-stack.md  (+ .env.example types)                   |
 what is true now ----> | specs/capabilities/*.md  +  tagged tests (proved by CI)        |
 next / maybe --------> | specs/roadmap.md  /  specs/backlog/                            |
 per-change why ------> | specs/changes/<date>-<slug>/requirements.md (frozen)           |
 cross-change choice -> | project_memory/decisions/<date>-<slug>.md (ADR)                |
 what bit us ---------> | project_memory/lessons.md (append, merge=union)                |
 how to work ---------> | specs/README.md (process) + AGENTS.md (5-rule contract)        |
 commands ------------> | mise.toml                                                      |
 who may merge -------> | project_memory/team.md (team tier) -> generated CODEOWNERS     |
 where I stopped -----> | derived: mise run status (branch, change, next group, dirty)   |
                        +----------------------------------------------------------------+
 John's habits, cross-project lessons, one pointer per project  --->  Rai vault memory
```

- **Living versus records.**
  - Living docs (mission, tech-stack, roadmap, capabilities, AGENTS, README) state today only and hold no rejected rows.
  - Records (ADRs, frozen change folders, lessons) keep the why and the rejected option; that is their purpose.
- **SessionStart** (`project.py hook session-start`) prints a derived block, tail-capped at 3 KB so the newest entries survive (N6):

```
[tipcalc] feat/entrypoint-hardening | change entrypoint-hardening (approved) | hooks on | mise trusted
next: G2 config.percent-empty config.percent-invalid (no passing tests; results 14:02) | dirty: 1
audit: ok (main: 3 commits since adoption, all via merge)
lessons (newest 5): 2026-09-24 run `mise install` after editing [project.scripts] (console script stale) ...
decisions (active, newest 3): 2026-09-24 usage errors exit 2
```

  - It resolves the repo from the hook input `cwd` through the launcher.
  - It never prints AGENTS.md, which loads natively.
  - It says loudly when hooks are off, mise is untrusted, gitleaks is not runnable, or the audit flags a commit.
- **No Stop hook and no log.md** (H25, H32, N8, D5).
  - Stop fires every turn, and SessionEnd cannot make Claude act `[D]`.
  - Progress is derived from test outcomes plus git, which catches Bash, subagent and external edits alike.
  - Lessons are prompted where they happen: compile after each group, and validate before the merge preview.
- **H27 routing rule** (the text added to `03-rai/AGENTS.md` in M10):
  > "Repo truth lives in the repo. In a repo with `.project.toml`, project facts (requirements, decisions, commands, lessons) are written to `specs/` or `project_memory/`, never only to Rai memory. Rai memory keeps John-level patterns, cross-project lessons with a link, and one pointer per project. On conflict the repo wins; /recall hits about a repo are hints to verify."
  - Both writers of Rai memory get the same filter for sessions whose cwd holds `.project.toml`:
    - the batch distiller `distill_session.py`;
    - the live observer `turn-capture.py`, whose daily-log bullets for such turns are limited to personal patterns, cross-project lessons with a link, and a one-line project pointer (C9).
  - This is a Memory v3 behaviour change, so it is its own separately approved milestone (M10).
  - The repo never references the vault; the gitleaks rules block it.
- **H28:** no sequential IDs anywhere. ADRs, change folders and backlog items are `<date>-<slug>`; scenarios are `<cap>.<slug>`. Two branches collide only by choosing the same slug on the same day, a genuine disagreement that git shows.

---

## 9. Ledger

### 9.1 Holes H1-H41

| ID | How addressed |
|---|---|
| H1 | P3: `GIT_CONFIG_* uv init --package --description` gives `main` + uv's .gitignore `[L]`. |
| H2 | D2 asked in the talk; P7 creates the repo without `--push`, pushes `main` first, then the branch, then sets the default branch explicitly; EXTEND completes remote steps whenever an origin appears. |
| H3 | Lockfile committed at init (D3); `--locked` everywhere turns a missing lock into a red build. |
| H4 | Signals from parsed manifests and marker files, evidence stored; no prose grep. |
| H5 | P2 reads vault kitchen/active/idea + repo docs + issues; asks gaps only. |
| H6 | Description = mission one-liner; doctor and EXTEND fail on the uv placeholder. |
| H7 | AGENTS.md written in P6, after P5 ran every command; doc-command check (I15). |
| H8 | AGENTS.md is team-only; Rai extras live in vault grill/compile + 1 routing line in `03-rai/AGENTS.md`; leak rules block vault paths. |
| H9 | Admission test, 40 lines or fewer, no memory protocol copy. |
| H10 | uv's template or a stack template + standard lines (`.env`, `.env.*`, `!.env.example`, `.agent/`, `.cache/`, `mise.local.toml`, `dist/`). |
| H11 | README fenced commands audited; tool-owned quickstart region replaced with the diff shown. |
| H12 | reference-transaction works with no remote and no server `[L*]`; merge path per D1; server rules where the plan allows. |
| H13 | CODEOWNERS only in the team tier, generated from team.md (D9). |
| H14 | All rules in `project.py` + one sh hook, generated in P4, activated by `mise install`. |
| H15/H24 | CI branch rendered from the detected default; master→main rename when there is no remote; EXTEND re-checks. |
| H16 | No python in `[tools]`; uv owns the interpreter; doctor asserts `mise ls --current` has no python. |
| H17 | Typed contract. **Empty = unset = default**, in the app (pydantic-settings `env_ignore_empty=True` `[L*]`) and in doctor. doctor fails only on a wrongly typed non-empty knob, an unset required secret, or a secret that is not an `op://` pointer. Scenarios: `config.percent-empty` and `config.percent-invalid`. |
| H18 | gitleaks pinned in mise; checked by running `gitleaks version`. |
| H19 | Tasks: start, fmt, test, verify, status, change, backlog, tdd, doctor (+ human approve, merge, abandon, release; hidden lint, types, secrets, spec-check, prove-red, selftest). |
| H20 | Section 5.8; prove-red uses `--no-overlay` `[C]`. |
| H21 | `uv sync --locked` in postinstall; `uv run --locked` in tasks; mise-action honours mise.lock; never `--frozen`. |
| H22 | pre-commit checks staged content: ruff through stdin per staged file, ty on an index export when a file is partially staged `[L*]`; whole repo in verify and CI. |
| H23 | pre-commit exits 1 if gitleaks cannot run; no bypass variable; CI scans history. |
| H25 | Stop nudge retired; state derived from git + test results. |
| H26 | Process lives only in `specs/README.md` (rendered from one template); AGENTS.md has a 5-rule contract; `sdd/SKILL.md`, hook messages, vault `11-workflows/` and `testing/tdd.md` link instead of restating. |
| H27 | Routing rule + filters in both `distill_session.py` and `turn-capture.py` (M10). |
| H28 | Date-slug ADR files; slug IDs; lessons union-merged. |
| H29 | `docs/spec.md` retired; `specs/` is the primary artifact. |
| H30 | One quickstart (README); AGENTS.md points to `mise tasks ls`. |
| H31 | ONBOARDING retired; team tier uses the built-in `/team-onboarding`; no clone line without a remote. |
| H32 | No Stop hook. |
| H33 | One gate ladder (3.3): pre-commit ⊂ verify ⊂ CI ⊂ merge, written once in `specs/README.md#gates`; AGENTS.md wording matches it. |
| H34 | No GitHub MCP; gh CLI. |
| H35 | allow/deny seed covering every agent task; personal rules in `settings.local.json`. |
| H36 | Release shapes by Distribution; git-cliff pinned with a pyproject config `[L*]`; dry-run verification only. |
| H37 | No `run` skill (it would replace bundled `/run`); `run-<name>` only for services, with failure modes. |
| H38 | One `sdd` skill; per-signal skills only with file evidence. |
| H39 | The SKILL.md router states no block count. |
| H40 | D10 (default: remove only `project_init` and `tdd` from the pai-brain upload); flag the drifted `~/projects/personal-ai-system/03-rai/skills/project-init/`. |
| H41 | Section 12 runs A-D, then the M11 rollout (remote trial, orca/open-kit `--plan`, helios clone, then helios). |

### 9.2 Audit findings N1-N27

| ID | How addressed |
|---|---|
| N1 | Transcripts go to a local quarantine, are redacted by gitleaks findings, and must rescan clean before they reach the git-tracked helm archive; never staged in the project repo. |
| N2 | Required checks = observed job names after the first green run; public/Pro only; `enforce_admins` in the team tier only. |
| N3 | ruff per-file-ignores baseline, shrink-only; staged pre-commit; debt backlog item. |
| N4 | Pinned, run-checked, no bypass variable, CI history scan with a baseline. |
| N5 | Section 3.2: creation block, origin confirmation, gh write denies, Edit denies on gate files, script scanning, hooksPath checks, trailer audit `[L*]`. |
| N6 | SessionStart keeps the newest entries (tail cap). |
| N7 | No vendored `.py` hooks under `.claude/`; `project.py` is lint- and type-clean. |
| N8 | Nudge retired. |
| N9 | No git-verb parser; substring denies moved from permission rules into `pre-bash` with a read-only exemption; the P5 matrix proves legitimate commands pass. |
| N10 | Creation allowed for the first commit; pre-push allows a push while the remote lacks the default branch. |
| N11 | Hooks run on uv-managed Python ≥3.12 via PEP 723; the git hooks are sh, so any machine whose system python3 is older works. |
| N12 | Side-effect commands verified by dry-run only. |
| N13 | Timeouts, health probe, kill by PID, builds to `$TMPDIR`. |
| N14 | P0 stops on a dirty or diverged tree or a shared origin; explicit pathspec staging. |
| N15 | EXTEND audit list with manifest hashes. |
| N16 | `date`/`decided` fallback; legacy knowledge becomes a frozen triage report, not active memory. |
| N17 | `init.py render`: absolute template paths, `install -D`, a single copy. |
| N18 | Hash-aware writes. |
| N19 | Makefile retired; `mise install` installs tools, then postinstall syncs; init runs `mise trust`. |
| N20 | mise-action + a per-stack postinstall (`npm ci` for node). |
| N21 | No entry zero; the ship commit body is written after P5. |
| N22 | Recorded once as unavailable; local layers enforce. |
| N23 | Local merge path defined; EXTEND auto-completes when a remote appears. |
| N24 | Mode from manifest, v2 stamp or the full legacy list; a bare `.claude/` is ignored. |
| N25 | Only `origin` counts; dead remotes flagged. |
| N26 | `mise run selftest` in a scratch clone with a bare origin; a check that does not fail is a failure. |
| N27 | The built-in `/verify` claim, "detected then confirmed", and the README Rule 2 contradiction are removed in the rewrite. |

### 9.3 Critic findings C1-C43

| ID | Finding | Resolution |
|---|---|---|
| C1 | H22 only half fixed (working tree, not staged content) | Fixed: ruff on staged blobs via stdin; ty on an index export when a file is partially staged `[L*]`. |
| C2 | N5 bypasses: fake origin ref, `gh api` merge, Write tool, script indirection, `.git/config` | Fixed: `ls-remote` + committed `origin_url` + creation block `[L*]`; `gh api` write deny; `Edit()` denies cover Write, `sed`, `tee` and redirects `[D]`; script-file scanning; `.git` protected path `[D]` + hooksPath checks. Remaining evasion is named in 3.2 and caught by the trailer audit. |
| C3 | N9 reintroduced by substring deny rules | Fixed: permission denies are prefix-only; substring checks live in `pre-bash` with a read-only exemption; P5 proves the read-only cases pass. |
| C4 | N1 moved transcripts into git-tracked helm | Fixed: quarantine → redaction → clean rescan → archive. The residual (gitleaks is pattern-based) is Risk 16. |
| C5 | H2: `gh repo create --push` pushes HEAD, not main | Fixed: no `--push`; main pushed first; `--default-branch main` set explicitly. |
| C6 | H26 again across vault and repo | Fixed: `testing/tdd.md` and `11-workflows/01-02` become pointers; `compile.md` and `specs-README.md` are the only texts. |
| C7 | H33 AGENTS.md misstates the gates | Fixed: the gate ladder (3.3), with AGENTS.md wording to match. |
| C8 | H17 empty-knob policy conflict | Fixed: empty = unset = default everywhere `[L*]`. |
| C9 | H27 `turn-capture.py` ungated | Fixed: M10 gates both writers. |
| C10 | prove-red overlay checkout keeps new files | Fixed: `--no-overlay` `[C]`; M3 has a new-file fixture. |
| C11 | Greenfield constitution from 3 form answers | Fixed: P2 checklist, free-text opener, up to 4 rounds, `[NEEDS CLARIFICATION]` blocks G1. |
| C12 | Risky groups changed without asking | Fixed: D8, recommending the course's pause model. |
| C13 | No hotfix-mid-feature route; deps swap needing test edits | Fixed: `--hotfix` worktree lane (4.2); `Test-Harness:` trailer route (I7). |
| C14 | D2 rule missing for vault notes | Fixed: section 1 choice 19; `11-workflows/01` carries a D2 diagram; M9 verifies no Mermaid and a d2 fence. |
| C15 | Solo/team tiering applied silently | Fixed: D9. |
| C16 | G1 prove-red fails on characterization; xfail outcome undefined | Fixed: init characterization scenarios are guards; outcome table in 5.5. |
| C17 | I4 and commit-msg contradict scenario removal | Fixed: `Spec-Removed:` trailer and rules (I4, commit-msg). |
| C18 | "Real fence" claim disproved | Fixed: 3.2 states the threat model and the limit. |
| C19 | P5 negative matrix masked by same-session deny rules | Fixed: `mise run selftest` subprocess; pre-bash tested in-process; settings reload is a documented fact `[D]`. |
| C20 | Human checks become `--yes` under `!` | Fixed: TTY prompts when present; otherwise `--attest`, recorded with the git user in the squash body; preview via `status --merge`. **Partly rejected:** attestation cannot prove a human read the checks; it makes the claim explicit and auditable. |
| C21 | P0 "read-only" vs the probe | Fixed: the probe is P1, in a scratch clone with no network `[L*]`; P0 runs no project code. |
| C22 | Mission "only on pivot" vs cross-cutting | Fixed: one rule, "only on `plan/` branches (pivot or product promise)", enforced by I1. |
| C23 | Render-gate grep vs `k8s/helm/` | Fixed: the render gate uses the gitleaks leak rules. |
| C24 | D1 option 2 vs pre-push | Fixed: pre-push allows default-branch pushes under `PROJECT_MERGE`. |
| C25 | `$CLAUDE_PROJECT_DIR` vs worktree cwd | Fixed: the launcher re-execs the worktree's own `project.py`. |
| C26 | Deny rule semantics unverified | Verified `[D]` this pass: deny matches past any leading assignment, `*` may lead, deny and ask apply in auto mode and to nested subcommands. The docs also say deny rules are not a security boundary, which 3.2 reflects. |
| C27 | git-cliff flags, config, emoji | Verified `[L*]`: `--with-commit`, `--bump -o`, `--bumped-version`, `[tool.git-cliff]` in pyproject, custom groups with no emoji. |
| C28 | reference-transaction behaviour | Verified `[L*]`: 17 cases, including the forged ref and fake origin. |
| C29 | `gitleaks dir` scans gitignored files | Verified `[L*]` (`.env` and `.venv/` reported). |
| C30 | `gh repo create --push` semantics | No longer relied on (C5). |
| C31 | pi/OpenCode skills, hooks, AskUserQuestion | Both binaries reference `.agents/skills` and `.claude/skills` (string evidence) `[L*]`; M6 live check with a symlink fallback. `talk.md` is harness-neutral. Hooks and deny rules in other harnesses are `[U]`, so the git layer is the stated floor (3.2, Risk 14). |
| C32 | mise-action runs postinstall | No longer needed: `uv run --locked` syncs the venv `[D]`; M9 remote trial confirms. |
| C33 | `mise x` cost and postinstall; timing targets | Measured `[L*]`: 33-61 ms per hook call, no postinstall on `mise x`. pre-commit and prove-red times are marked targets and measured in M3/M4. |
| C34 | Settings written mid-session | Verified `[D]`: Claude Code reloads settings files, so C19's subprocess design is required. |
| C35 | `Edit(.githooks/**)` path semantics | Verified `[D]`: `/path` anchors at the project root; rules are written `Edit(/.githooks/**)`. |
| C36 | `mise lock` for macos-arm64 | Removed: linux-x64 only; teammate platforms added on demand `[U]`. |
| C37 | Whole pai-brain disable | Fixed: D10, targeted by default. |
| C38 | Ceremony too heavy | **Partly accepted:** lanes cut from 8+ to 6 (spike and deps folded); 12 visible tasks instead of 17; validate lenses 2-3 only for feat, breaker only for chg/fix. **Rejected:** dropping prove-red or the count guard; they are the only mechanical proof of TDD and are one script call at merge. |
| C39 | M8 bundles vault-wide and memory changes | Fixed: M8 is pipeline skills only; M9 (vault-side adjacent) and M10 (memory) are separately approved. |
| C40 | `Read(./.env)` deny | Removed. |
| C41 | Mac-teammate reasoning | Removed; N11 is stated neutrally. |
| C42 | Process narration in the design | Removed (judge scores, "fatal flaw"). |
| C43 | Two canonical TDD texts | Covered by C6: `compile.md` template is canonical; `testing/tdd.md` is a pointer. |

---

## 10. Open decisions for John

**D1. Merge path when solo (H12)**
1. A branch per change. `mise run merge` opens a PR, waits for CI and squash-merges when an origin exists; it squash-merges locally when not. (Recommended: CI before merge and a PR record without extra typing, and Free private repos cannot enforce server rules anyway.)
2. Always a local squash-merge; merge then pushes main itself, which pre-push allows under `PROJECT_MERGE`. Fastest, but loses the CI-before-merge wait.
3. v2 PR-only everywhere, with a mandatory remote.

**D2. Creating the GitHub remote (H2)**
1. Ask inside the talk, only when there is no origin; the default option is a private GitHub repo. (Recommended: throwaways like tipcalc stay local, and your gh token has no `delete_repo` scope.)
2. Always create a private repo when gh is logged in, with `--local` to opt out.
3. Never create one; put the command on the punch list.

**D3. Untracked lockfile (H3)**
1. Commit `uv.lock` and `mise.lock` in the init commit after `uv lock --check`. (Recommended: every `--locked` gate fails without it.)
2. Punch-list item only.

**D4. How hard to enforce TDD**
1. prove-red at merge and in CI, plus the right-reason `tdd red` and `Spec:`/`Red:` trailers. (Recommended: the only proof an agent cannot fake, with no friction while editing.)
2. Option 1, plus a compile-scoped Edit hook that denies `src/` edits until `tdd red` is recorded for the current group. More friction, and Bash edits bypass it.
3. Advisory only.

**D5. Session log**
1. Retire `log.md`. (Recommended: progress is derived; git and CHANGELOG hold the history; the Stop nudge that fed it fires every turn.)
2. Keep it, written only by merge, one line per change.

**D6. The vault ExecPlan pipeline**
1. grill absorbs execplan-create, goal becomes compile, execplan-improve becomes spec-improve, think/spec-driven folds into the templates. (Recommended: one pipeline; it frees the built-in `/goal` and uses your word "compile".)
2. Keep all five names and change only their behaviour.

**D7. Committed `.agent/` in open-kit and orca**
1. Read the files as P2 intake, then `git rm`. (Recommended: git history is the archive, per vault doctrine.)
2. Move them to `docs/history/agent/` with a "frozen, not maintained" README.

**D8. Risky task groups (the course's "one group at a time for risky areas")**
1. `risk: high` on a group makes compile stop after that group. You review the group's diff and say continue; no extra gate command. (Recommended: the course's model, without a second approve/merge cycle.)
2. A `risk: high` group must be its own change, with its own approve and merge.
3. No special handling.

**D9. Solo vs team tier (reverses the v2 "everything by default" ruling for four files)**
1. Tier by evidence. Solo repos get no CODEOWNERS, PR template, team.md or ONBOARDING; EXTEND offers the team tier when a second human author appears in 6 months of history. (Recommended: those files are no-ops when solo (H13, H31) and drift.)
2. Everything by default, as v2 decided.

**D10. H40 cleanup scope**
1. Remove only `project_init` and `tdd` from the pai-brain upload (re-upload on claude.ai without them `[U]`). (Recommended: smallest blast radius; other pai-brain skills may still serve claude.ai chats.)
2. Disable the whole `pai-brain@synced` plugin after a skill-by-skill check that each one has a vault successor.
3. Leave it as is.

---

## 11. Risks: where this is wrong if an assumption fails

1. **Local enforcement is cooperative.**
   - On Free private repos a human can remove `.githooks/`.
   - An agent can evade prevention with programs outside the repo and temp dirs, or with obfuscated commands (3.2).
   - The trailer audit and CI catch the effect after the fact.
   - Optional hardening is Claude Code's OS-level sandbox with write-deny on `.githooks/` and `scripts/project.py` `[U]`. It must not deny `.git/config`, because `git push -u` writes it.
2. **prove-red noise.** Integration tests that need services, moved modules, or changed fixtures can fail on the old code for unrelated reasons, or raise inconclusive guards. The escape is `merge -- --allow <id> --reason "<why>"`: human-only, printed into the squash body.
3. **`!` bash mode `[U]`.** If typing `! mise run merge` in Claude Code hits deny rules or `pre-bash`, human gates run in a terminal you open yourself. Nothing launches one, per the never-steal-focus rule. M6 tests this first.
4. **Ceremony tax.** A feat change is 3 files plus 2 gates, capped at 120/100/60 lines; most work lands in fast lanes. If feat still feels heavy, widen the chg threshold (for example to 5 scenarios) before cutting anything else.
5. **Living capabilities can rot as prose.** Only the conformance lens compares scenario text against assertions. Keep scenarios to GIVEN/WHEN/THEN with no design prose, and watch for the 6-to-9-month drift others reported.
6. **mise is a hard dependency.** Teammates must install it. `mise x` auto-trusts, which is a trust decision made when hooks run. `mise.lock` covers linux-x64 only; other platforms are added on demand `[U]`; Windows is `[U]`.
7. **Only pytest is proven.** Trace and prove-red are verified for pytest `[L*]`. Other stacks need a JUnit-based adapter; until one exists, `spec-check` falls back to static tag presence (weaker).
8. **ty has no documented per-file ignore** equivalent to the ruff baseline `[U]`. On a debt-heavy repo the fallback is `[tool.ty.src] exclude` for legacy dirs plus a backlog item.
9. **`op run --env-file .env` resolving `op://` pointers is `[U]`.**
10. **Squash merges drop per-group commits and trailers from main.** The squash body keeps IDs, the prove-red table and the attestation; GitHub keeps the PR. With no remote, branch history is gone after merge.
11. **Name collision.** A future built-in or personal skill named `sdd` would shadow the repo skill. Rename it in one EXTEND pass; the manifest makes that mechanical.
12. **Brownfield honesty.** On helios, most behaviour stays unspecified for a long time. "Specs equal the system" holds only for the entrypoint and for code changed since adoption.
13. **AGENTS.md native loading has gaps** `[D]`: the first session after an upgrade, telemetry off, third-party providers, or a CLAUDE.md in a parent directory. The SessionStart block is the guaranteed floor.
14. **Other harnesses** (pi, OpenCode) lack the Claude layer, and possibly skill discovery `[U]`. There, the git layer, merge checks, CI and the audit are the whole fence, and AGENTS.md rule 2 is advisory.
15. **Probe residue.** The P1 sandbox cuts network but not Unix sockets (Docker, D-Bus) or writes outside the clone. Entry points with api/deploy/pipeline/db signals get `--help` only.
16. **Transcript redaction is pattern-based.** gitleaks finds known secret shapes. Anything unusual in helios's transcripts survives redaction into the helm archive; the quarantine stays until John confirms.
17. **Main syncs need the network.** The hook confirms origin with `ls-remote`. Offline, `pull` and `reset` to `origin/main` are blocked with a clear message until you are back online.

---

## 12. Implementation plan

**Working rules for the build:**
- Paths are under `~/helm/03-rai/skills/` unless stated otherwise.
- Each milestone is one reviewable commit on the helm branch `project-init-v3`, made through an isolated worktree because of live memory churn. Nothing merges to helm main until M7 passes.
- `$S` is the session scratchpad. Human commands in the verification runs are typed by the test harness, standing in for John.

### M1. Product templates and the process document
**Files:**
- NEW `~/helm/12-system/templates/sdd/{mission,tech-stack,roadmap,capability,requirements,plan,validation,backlog,decision,lesson}.md`.
- NEW `project-init/templates/specs-README.md`: ASCII lifecycle, tables 0.2 and 0.3, classifier, formats, gate ladder, DoD, caps.

**Verify:**
- `vale` `Rai.*` is clean on the new files.
- `grep -c '—'` returns 0.
- Rendering by hand for tipcalc into `$S/fix/specs/` yields the section 5 examples. That tree is M2's first fixture.

### M2. `project.py` core: `check`, `status`, conftest plugin
**Files:** NEW `project-init/templates/scripts/project.py` (`check`, `status`), `templates/tests/conftest.py`, `project-init/tests/test_check.py` + `tests/fixtures/`.

**Verify:** `cd project-init && uv run --with pytest pytest tests -q` passes:

| Case | Expected |
|---|---|
| (a) scenario with no test on main | exit 1, `cli.no-args: no linked test` |
| (b) test tagged `nope.nope` | exit 1, `unknown id` |
| (c) `skip` on a linked test | exit 1 |
| (d) `[gap: entrypoint-hardening]` + strict xfail | exit 0 |
| (d') the same gap when the test XPASSes | exit 1 |
| (d'') gap slug missing from roadmap | exit 1 |
| (e) pending scenario on a branch with an open change | exit 0; the same on main, exit 1 |
| (f) Review focus row pointing at a missing ID | exit 1 |
| (g) 121-line requirements.md | warning, exit 0 |
| (h) `[NEEDS CLARIFICATION` in an approved change or in `specs/mission.md` | exit 1 |
| (i) AGENTS.md naming `mise run nope` | exit 1 |
| (j) branch diff stages `specs/mission.md` on `feat/x` | exit 1 (I1 in verify) |

### M3. TDD tooling: `tdd red|green`, `prove-red`, count guard, I7, I11
**Files:** EDIT `project.py`; NEW `project-init/tests/test_prove_red.py` + `tests/fixtures/make_tipcalc.sh` (clones tipcalc `master`, removes origin, renames to main, runs `uv lock`, adds pytest).

**Verify:**

| Case | Expected |
|---|---|
| Base case: `test_cli.py` (tip-default, no-args), `test_parse.py` importing `parse_amount`, fixed src | `cli.no-args red (assert 1 == 2)`, `cli.bad-amount red (collection error)`, `cli.tip-default` passes as a `Spec-Guard`, exit 0 |
| Fix adds NEW `src/tipcalc/config.py` and `test_config.py` imports it | `config.*` red by collection error on base (proves `--no-overlay`) |
| `plan/project-init` fixture with `cli.tip-default` (characterization) + 5 gaps | guard passes, gaps xfail on base, exit 0 |
| test_no_args mutated to assert `returncode == 1` | exit 1, `cli.no-args passes on the old code` |
| test_tip_default deleted, scenario kept | spec-check exit 1 |
| scenario + test deleted in one commit with `Spec-Removed:` | count guard 3→2 allowed, exit 0 |
| `tdd red cli.bad-amount` before any stub exists | refuses: `ImportError is the wrong red: add a stub that raises NotImplementedError` |
| `tdd red cli.bad-amount` with the stub | exit 0, prints `Red: cli.bad-amount: NotImplementedError` |
| `refactor/x` editing `tests/test_cli.py` without `Test-Harness:` | I7 exit 1; with the trailer, listed for the human |
| pyproject gains `pydantic-settings` without a tech-stack edit | I11 exit 1 |
| prove-red wall time | measured; target under 20 s warm |

### M4. Git gates
**Files:** NEW `project-init/templates/githooks/{pre-commit,commit-msg,pre-push,reference-transaction}`, `templates/gitleaks.toml`; EDIT `project.py` (`hook pre-commit|commit-msg|pre-push`, `selftest`).

**Verify:** `mise run selftest` in `$S/gates` + `$S/origin.git`. Rows marked `[L*]` already passed in this pass (scratch `v3patch/rt`):

| Case | Expected |
|---|---|
| first commit in a fresh repo | 0 `[L*]` |
| commit on main | blocked, `blocked: main moves only via 'mise run merge'` `[L*]` |
| `--no-verify` commit on main | blocked |
| `branch -f main feat/x`; `update-ref refs/heads/main` | blocked `[L*]` |
| `update-ref refs/remotes/origin/main feat/x` then `branch -f main origin/main` | blocked `[L*]` |
| origin re-pointed at a fake bare repo holding feat/x as main, fetch, `branch -f main origin/main` | blocked `[L*]` |
| origin unreachable, `branch -f main feat/x` | blocked `[L*]` |
| `branch -m main old` then `branch main feat/x` | rename passes, recreation blocked `[L*]` |
| `pack-refs --all`, `gc` | 0 `[L*]` |
| real origin advanced: `pull --ff-only`, `reset --hard origin/main` | 0 `[L*]` |
| ff merge into main with `PROJECT_MERGE=1` | 0 `[L*]` |
| push main to an empty origin | 0 `[L*]`; again once origin has main: 1; with `PROJECT_MERGE=1`: 0 |
| push `feat/x:main` | 1 |
| push `-u origin feat/main-menu` | 0 |
| staged fake AWS key | 1 |
| PATH without gitleaks | 1, `run: mise install` |
| `.md` containing `~/helm/05-projects/x` | 1; `k8s/helm/01-base` gives 0 `[L*]` |
| partially staged `.py`: staged copy has a ruff or ty error, working copy clean | 1 (ruff stdin and ty-on-index behaviour `[L*]` in `v3patch/stg`) |
| `specs/mission.md` staged on `feat/x` | 1 |
| new bare `@pytest.mark.skip` | 1 |
| message `update stuff` | 1 |
| `feat(cli): x` touching src without `Spec:` | 1 |
| scenario deleted, tests kept or no `Spec-Removed:` | 1 |
| delete main, detached commit, then `branch main HEAD`; every ref and reflog wiped, then `update-ref refs/heads/main <old>` | blocked, `main is missing here` |
| origin's main moved outside merge (`send-pack`), then `pull --ff-only` or `reset --hard origin/main` | blocked, lists the commits without `Merged-By` |
| main reset or fast-forwarded to a commit without `.githooks/` or with a weakened guard; guard emptied or its x bit cleared in the working tree | blocked by the pinned guard |
| push into the repo itself: `push .`, `push --no-verify .`, `send-pack .` | 1 (pre-push; `receive.hideRefs`) |
| any refusal of the main guard | prints `check git status` |
| `.md` containing `/home/someone`, `/Users/someone` or `$HOME/helm/05-projects/x` | 1 |
| new skip in a root `conftest.py`; a skip named by a string (`getattr(pytest.mark, "sk" + "ip")`) | 1 |
| subject `Revert "update stuff"`; `Revert "docs: x"`, `Reapply "docs: x"`, `fixup! docs: x` | 1; 0 |
| an origin sync on a machine without `timeout` | 0 (pytest) |
| pre-commit on tipcalc | measured; target under 5 s |

### M5. Lifecycle commands
**Files:** EDIT `project.py` (`change`, `backlog`, `approve`, `merge`, `abandon`, `doctor`, `status --merge --audit`, `release --dry-run`); NEW `tests/test_lifecycle.py`.

**Verify on the fixture (no remote):**
- **change:**
  - on a dirty tree: exit 1, listing the files;
  - clean: `feat/split-bill` + 3 template files, `status: draft`;
  - a second `change` while open: exit 1 (I8);
  - `--lane fix --hotfix`: a sibling worktree on `fix/<slug>` off main, exit 0;
  - `--parallel`: exit 0.
- **approve:** with lint errors, exit 1; clean, commit `spec(split-bill): approve` with `Spec-Approved: sha256:…`.
- **merge:**
  - with pending IDs: exit 1, listing them;
  - with a human check, no TTY and no `--attest`: exit 1, listing the check;
  - with `--attest` after green: one squash commit on main whose body lists the IDs, the prove-red table, the attestation and `Merged-By: mise run merge`; roadmap `[x]`; `status: done`; one CHANGELOG line under Unreleased; branch deleted; output ends with the next item, "still right?" and "/clear";
  - `--branch fix/<slug>` from the main checkout lands the hotfix; `status` on the open feature then says `main moved: run git merge main`;
  - on a branch editing `.githooks/pre-commit`: refused without `--gate-change`;
  - with `core.hooksPath` unset: refused.
- **status --audit** after a forced `PROJECT_MERGE=1` commit without the trailer: WARN naming the sha.
- **abandon -- "not worth it"**: tag `abandoned/split-bill`, branch gone, `specs/backlog/<date>-split-bill.md` on main with the trailer.
- **doctor:**
  - `.env` with `TIPCALC_DEFAULT_PERCENT=`: ok, `empty: default 15 applies`;
  - `=abc`: FAIL `not a float`;
  - a secret without `op://`: FAIL.
- **release --dry-run** with distribution none: `no release for distribution: none`.

### M6. Machinery templates, the `sdd` skill, the Claude environment
**Files:**
- NEW `project-init/templates/{mise.python.toml,ci.yml,settings.json,AGENTS.md,README-quickstart.md,env.example,gitignore-extra,gitattributes,project_memory/README.md,pyproject-additions.toml}` (incl. `[tool.git-cliff]`).
- NEW `templates/skills/sdd/{SKILL,talk,compile,validate,replan}.md`.
- EDIT `project.py` (`hook session-start|pre-bash`, launcher re-exec).

**Verify** (render into `$S/render` from the tipcalc fixture):
- `mise install` runs postinstall: `.venv` exists, `core.hooksPath` = `.githooks`.
- `mise run verify` is green.
- `mise tasks ls` lists 12 tasks with descriptions; the hidden 6 still run `[L*]`.
- The gitleaks leak rules over `.claude AGENTS.md specs` report 0.
- `git cliff --unreleased` shows Added/Changed/Fixed groups with no emoji `[L*]`.
- pre-bash cases (as in P5): the deny set denies and the read-only set allows.
- session-start with 12 lesson fixtures prints 3 KB or less, including the newest 5.
- The launcher, from a worktree whose `project.py` differs, runs the worktree's copy.
- **Live checks, in real sessions:**
  1. `! mise run status` works. If `! mise run approve` is denied, write "run human gates in a terminal" into `specs/README.md#gates` (Risk 3).
  2. Start pi and OpenCode in the rendered repo: does `sdd` appear? If not, render the `.agents/skills/sdd` symlink and re-check. Do project hooks or deny rules apply there? Record the answer in Risk 14.

### M7. project-init SKILL.md v3, `init.py`, and deleting v2
**Files:**
- REWRITE `project-init/SKILL.md` (router, 200 lines or fewer).
- NEW `project-init/phases/{0-preflight,1-probe,2-talk,3-scaffold,4-generate,5-verify,6-front-door,7-ship,8-extend,9-migrate}.md`.
- NEW `project-init/scripts/init.py` (preflight, probe, render, selftest, publish, migrate-transcripts) + `project-init/tests/test_init.py`.
- DELETE `project-init/scripts/project-{branch-guard,memory-inject,memory-nudge}.py`, `templates/{facts,log,decisions,ONBOARDING,project-skill,doctor.sh}`, `templates/git-hooks/`.
- REWRITE `templates/{team.md,pull_request_template.md}` for the team tier.

**Verify with four runs.**

**Run A: SCAFFOLD, empty folder.** `mkdir $S/hello && cd $S/hello`, then `/project-init`. Scripted conversation: a free-text answer ("a CLI that greets a name, for me, done = prints Hello, <name>"), then one round (distribution none, local only, and the (Recommended) option for roadmap Phase 2, which no source names in an empty folder).
- `main` has 1 commit `chore: scaffold hello`; the current branch is `plan/project-init` with 1 commit.
- `specs/{README,mission,tech-stack,roadmap}.md` + `capabilities/cli.md` (`cli.runs`) exist; the constitution checklist is complete.
- `mise run verify` is green, 1 passed. doctor 0 FAIL. `mise run selftest` all as specified.
- AGENTS.md is 40 lines or fewer; pyproject description = the one-liner.
- After `! mise run merge`: prove-red reports `cli.runs` as a passing guard; main has 2 commits; tree clean.

**Run B: ADOPT, pre-v2 tipcalc.** `git clone --no-local ~/projects/tipcalc $S/tc-adopt`, `git checkout master`, `git remote remove origin`, `uv lock` (uv.lock untracked). Scripted answers: "tiny CLI that prints the tip for a bill", none, local only.
- P0 + P1 print the 6.P0/P1 block: 5 probe crashes, 1 pass; the repo tree is unchanged after P1.
- `master` → `main`; `plan/project-init` holds 1 commit including `uv.lock`; description no longer the placeholder.
- `capabilities/cli.md` + `config.md`: `cli.tip-default` (passing) + 5 `[gap: entrypoint-hardening]` scenarios; roadmap Phase 1 `entrypoint-hardening`.
- `mise run test` gives `1 passed, 5 xfailed`; verify green; `extend-exclude` holds only the two tool-owned copies (`scripts/project.py`, `tests/conftest.py`), with no v2 `.claude` entry; `ruff check .` clean.
- After `! mise run merge`: main = `df806ec` + `chore(init): project-init v3`, with the `Merged-By` trailer.

**Run C: EXTEND v2 → v3.** Clone tipcalc, `git checkout master && git merge --ff-only chore/project-init`, remove origin.
- Exactly one migration prompt.
- After applying it, the file set equals Run B's plus four more: `project_memory/decisions/*` with `aliases:`, the v3 `ci.yml`, `CHANGELOG.md` and the v2 tests. It lacks `decisions/.gitkeep`, which render seeds only into an empty `decisions/`. The `ci.yml` replaces the v2 one, remote or not. The v2 lessons are preserved, and a retiring lesson follows each one `migrate-v2` named. `phases/9-migrate.md` "Check (Run C)" holds the same list.
- The v2 files listed in MIGRATE are gone; CI push branch `main`; verify green.

**Run D: idempotence.** Re-run on Run B's output: `EXTEND: 0 changes`. Hand-edit AGENTS.md and re-run: it shows the diff and asks; nothing is overwritten.

### M8. Reshape the pipeline skills, then ship one real feature
**Files:**
- REWRITE `grill/SKILL.md`.
- `git mv goal compile` + rewrite; `git mv execplan-improve spec-improve` + rewrite.
- DELETE `execplan-create/` and `think/spec-driven.md`; EDIT `think/SKILL.md`.
- REWRITE `testing/tdd.md` as a pointer.
- EDIT `adversarial-review/SKILL.md`, `orchestrator/SKILL.md` + `scripts/orch-teardown.sh`, `visual/plan.md`, `MANIFEST.md`.
- EDIT `~/helm/03-rai/AGENTS.md`: the one skill-routing line only.

**Verify the text changes:**
- `grep -rn 'execplan-pending\|execplan-create\|skills/goal' ~/helm/03-rai` gives 0 live hits.
- A new session lists `grill`, `compile`, `spec-improve`, with no `goal` or `execplan-create`.
- vale `Rai.*` is clean.

**Verify end to end in Run B's output:**
1. `/grill entrypoint-hardening` writes the change folder, turns the 5 gaps into exact contracts, and adds `cli.negative-amount`. `mise run status` says `ready for approve`.
2. `! mise run approve`, then `/clear`.
3. `/compile` finishes G1 and G2 green; pydantic-settings is added with `env_ignore_empty=True`, and tech-stack.md is updated.
4. validate reports 3 lenses and ends with `mise run status -- --merge`.
5. `! mise run merge -- --attest` shows prove-red 6/6 red on base (4 assertion, 2 collection), lands one squash commit `fix(cli): clear errors instead of tracebacks`, ticks Phase 1, and adds a CHANGELOG line under Fixed.

Then the binary behaves like this:
- `tipcalc` exits 2 with `usage: tipcalc …`;
- `tipcalc abc` exits 2 with `error: bill must be a number`;
- `TIPCALC_DEFAULT_PERCENT= tipcalc 100` prints `tip: 15.0`;
- `TIPCALC_DEFAULT_PERCENT=abc tipcalc 100` exits 2 with one `error:` line;
- `mise run test` shows 0 xfailed.

### M9. Vault-side adjacent notes (separate approval)
**Files:**
- REWRITE `~/helm/11-workflows/{01-project,02-task,03-kitchen}.md` as pointers (01 keeps one D2 diagram of the vault-side flow).
- EDIT `ideas/graduate.md`.
- EDIT `~/helm/12-system/templates/PRD.md` to a pointer.

**Verify:**
- `grep -c '```mermaid'` = 0 and `grep -c '```d2'` ≥ 1 in 01-project.md.
- 02-task.md contains no lane table, only the link.
- A dry `/ideas graduate` on a scratch Tree note scaffolds `kitchen/<name>/specs/`.

### M10. Memory routing (separate approval; Memory v3 behaviour change)
**Files:**
- EDIT `~/helm/03-rai/AGENTS.md` (the routing rule).
- EDIT `~/helm/03-rai/hooks/scripts/distill_session.py` and the turn-capture observer (`turn-capture.py`): for cwd with `.project.toml`, keep personal patterns, cross-project lessons with a link, and a one-line pointer.

**Verify:**
- A replayed tipcalc session transcript through both paths yields no project requirement, command or decision text in the daily log or the distilled output, and exactly one pointer line.
- `/rai eval` shows no regression on the golden set.

### M11. Rollout and cleanup (each item approved separately)
1. **Remote trial.** Repeat Run B with D2 = GitHub (repo `tipcalc-v3-trial`, private). Expected:
   - GitHub default branch `main`;
   - `merge` goes through a PR; CI job `verify` green, prove-red runs on the PR, the audit step runs on push;
   - protection recorded as `unavailable (Free private)`;
   - you delete the repo by hand afterwards (the token lacks `delete_repo`).
2. **H40 per D10.** Expected: `pai-brain:project_init` and `pai-brain:tdd` gone from the skill list (option 1). Flag the personal-ai-system copy.
3. You run `git config --global init.defaultBranch main`.
4. `/project-init --plan` (P0 + P1, no repo writes) on orca and open-kit produces reports and the D7 choice.
5. **helios MIGRATE on a `git clone --no-local` copy.** Expected:
   - transcripts land in the quarantine before any `.gitignore` edit; the redaction rescan exits 0;
   - only then do they appear under `13-archive/historical-sessions/helios/`;
   - `git log -p | grep -c 'sessions/.*\.jsonl'` = 0 for the new project commits;
   - legacy knowledge becomes one backlog triage report;
   - the ruff baseline absorbs the 3,778 findings and `mise run verify` is green;
   - the existing CI is kept and `sdd.yml` added; protection 403 recorded.

   Real helios follows only after you read the clone report.
6. **helios-demo.** Preflight must stop with the shared-origin prompt: "1. treat as its own repo and re-point origin; 2. stop (Recommended: its origin belongs to helios)".

---

**Key files:**
- `~/helm/03-rai/skills/project-init/SKILL.md` (current v2, to be rewritten)
- `~/helm/03-rai/skills/project-init/scripts/project-branch-guard.py` (to be retired)
- `~/helm/03-rai/AGENTS.md` (routing line in M8, memory rule in M10)
- `~/helm/03-rai/hooks/scripts/distill_session.py` (M10)
- `~/helm/12-system/templates/` (new `sdd/` subfolder)

**Evidence from this pass** (all under `$S/`):
- `v3patch/rt/reference-transaction` + `v3patch/rt/w`: the final hook and its 17-case matrix. Forged origin ref, fake origin URL, recreation and offline cases are blocked; pack-refs, gc, first commit, real-origin sync and `PROJECT_MERGE` pass; without the pack-refs line, pack-refs is blocked.
- `v3patch/stg`: a staged broken file with a clean working copy; ruff via `--stdin-filename` exits 1, working-tree ruff exits 0; ty on an index export exits 1, ty on the working tree exits 0.
- `v3patch/cliff`: git-cliff 2.14.1 `--with-commit`, `--bump -o`, `--bumped-version` (v0.2.0), and `[tool.git-cliff]` read from pyproject with custom groups and no emoji.
- `v3patch/leak`: `gitleaks dir` reports gitignored `.env` and `.venv/`; the JSON report carries `Secret`; replacing it and rescanning exits 0.
- `v3patch/mx`: `mise x -- uv run --script` at 33-61 ms; postinstall fires on `mise install`, not on `mise x`; `hide = true` tasks are unlisted but runnable.
- `docs/permissions.md`, `docs/settings.md`: deny rules match past leading assignments and nested subcommands and precede allow in every mode; `Edit()` rules cover all edit tools and `sed`/`tee`/redirect targets; `/path` anchors at the project root; settings files reload mid-session.
- Also checked this pass: `unshare -rn` blocks TCP unprivileged on this box; pydantic-settings 2.15.0 `env_ignore_empty=True` maps `""` to the default and `abc` to `ValidationError`; the opencode 1.18.32 and pi 0.87.1 binaries contain the strings `.agents/skills` and `.claude/skills`.