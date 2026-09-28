# P1 Probe

**Runs in:** ADOPT, EXTEND, MIGRATE, and `--plan`. SCAFFOLD runs it only after P3's scaffold commit, for the trunk block ([3-scaffold.md](3-scaffold.md)). **Writes:** nothing in the repo. Everything happens in a scratch clone of the committed state.

The probe exists because an adopted repo can pass every gate while its entrypoint crashes (H20). It runs the real console scripts before anyone writes a spec about them.

It also lists the **trunk candidates**: the paths whose diffs a human should read rather than skim (v3.1). P2 turns them into the `## Trunk` section of `specs/tech-stack.md`. And it names the **UI surface**, which decides the proof the repo's changes owe and the capture tools P7 puts on the punch list.

## Run

```sh
env -C ~ ~/.claude/skills/project-init/scripts/init.py probe "$PWD"
```

What it does:

```text
git clone --no-local -q . $TMP/probe           committed state only; the repo is untouched
cd $TMP/probe && uv sync                       a lock is created in the clone if the repo has none
  no .python-version: uv sync --python <v>     each P0 candidate in turn; the first that builds
per console script, per env read:
  unshare -rn                                  no network; without user namespaces: "probe skipped"
  env -i PATH=<clone venv>:<tool bins> HOME=$TMP/home UV_CACHE_DIR=<real cache> LANG=C.UTF-8
  timeout 10 <script> {no args | --help | abc | happy-path args from README fences, else 100}
  env probes: VAR="" and VAR=abc, with the happy-path args (or no args)
entry points with api|deploy|pipeline|db signals: --help only
crash = "Traceback (most recent call last)" in stderr
```

## Check

- `git status --porcelain` in the repo is identical before and after the probe.
- Every console script from `[project.scripts]` and every env read from P0 has a row.
- The report ends with the `surface` line and the `trunk` block, even when the sandbox could not run: both come from a static read.
- The happy path comes from a README fence when one exists. With none, the no-args row stands in when it passes. Only when a bare run fails too does the guessed `100` row stand in, marked `(guessed args: no README fence)`: tipcalc's case.

## Stop conditions

- The repo has no `.python-version`: the clone is synced with each P0 candidate in turn, and the report names the version that built (`python ...... no .python-version: 3.12 built the clone; P4 pins it`). Pass it to P4 as `init.py prepare --python <v>`. P1 still writes nothing to the repo.
- `uv sync` fails in the clean clone for every candidate: do not stop. Report it; it becomes the first Phase 1 roadmap item in P2, because the repo does not build from its own commits. The entrypoints stay unprobed. Each failure is named by uv's first `×` or `error:` line and its `... was included because ...` hint, never by uv's closing `hint: Build failures usually ...` line.
- No root `pyproject.toml`: `unprobed: no stack pack for <stack>`. P0 has already stopped such a repo.
- No user namespaces (`unshare -rn` fails): print `probe skipped`. P2 works from static evidence, and the P7 commit body names the skip.
- A probe that hangs is killed by `timeout 10` and counts as a crash with reason `timeout`.

## What P2 does with the result

| Probe row | Becomes |
|---|---|
| exit 0 with the expected output | a characterization scenario (it must keep passing: a guard at the G1 merge) |
| a traceback, or a timeout | a `[gap: <phase-1-slug>]` scenario with a strict-xfail test, and `<phase-1-slug>` becomes the first roadmap item |
| a trunk candidate | a proposed `## Trunk` line in `specs/tech-stack.md`: P2 asks keep all, edit, or start empty |

## Output (tipcalc)

```text
probe ....... (scratch clone, network off)
              tipcalc 100 -> "tip: 15.0" exit 0 (guessed args: no README fence)
              tipcalc -> IndexError traceback | tipcalc --help -> ValueError | tipcalc abc -> ValueError
              TIPCALC_DEFAULT_PERCENT="" -> ValueError | TIPCALC_DEFAULT_PERCENT=abc -> ValueError
              1 pass, 5 crashes; no README fence names a happy path, so 100 stood in for one; repo untouched
surface ..... console scripts only: tipcalc; proof by run, which needs no setup
trunk ....... 1 candidate for ## Trunk in specs/tech-stack.md (a static scan: no code ran)
              - src/tipcalc/__init__.py: the entrypoint of the tipcalc command (tipcalc:main)
```

One pass and 5 crashes: `cli.tip-default` plus 5 gap scenarios under the roadmap slug `entrypoint-hardening`. One trunk candidate: tipcalc is a single module.

## The UI surface

From the runtime dependencies in `pyproject.toml` (`[project] dependencies` and its extras), read statically. The framework lists are the ones project.py warns with at approve (`WEB_UI_FRAMEWORKS` and `TUI_FRAMEWORKS` in this skill's `templates/scripts/project.py`), read from its source, never copied. An HTTP API framework such as FastAPI is no UI: its proof is `http`.

| Surface | Evidence | P7's punch list |
|---|---|---|
| web | a web UI framework, e.g. streamlit, django, flask, gradio | `mise run proof -- setup web` (Playwright's parts for a headless Chromium) |
| terminal | a TUI framework, e.g. textual, urwid, prompt-toolkit | `mise run proof -- setup terminal` (vhs and ttyd, pinned in `mise.toml`) |
| cli | console scripts only | nothing: `run` captures need no tool |
| none | neither | nothing: `run`, `http` and `log` need no tool |

A web framework wins over a TUI one. `probe --json` has it under `surface`, as `{"kind", "evidence", "setup"}`.

## Trunk candidates

The `trunk` block comes from a static scan of the files git tracks: the AST and the file list, never an import or a run. So it prints even when the probe itself was skipped or unprobed. Each row is already a `## Trunk` line, `- <glob>: <why>`, with its glob relative to the repo root:

| Candidate | Evidence | Its why, e.g. |
|---|---|---|
| entrypoint | the module a `[project.scripts]` entry runs | `the entrypoint of the tipcalc command (tipcalc:main)` |
| fan-in | a module that at least `max(3, min(ceil(25%), 10))` of its package's modules import: 10 importers are always enough, so a big package's shared module counts. Imports are resolved from the AST, relative ones included. Tests and code outside the package never count as importers. A folder without `__init__.py` inside a package belongs to it, and the root `src/` is never a package, even with a stray `__init__.py`. | `imported by 4 of 7 other modules in shop` |
| settings | with an env contract, each file its `read in` notes name that is named like a settings module (`config`, `settings`) or holds a pydantic-settings class. With no contract yet (an adoption), a `config.py` or `settings.py` counts by name. It must sit at its package's root, or 2 modules outside its own folder must import it. A per-source config that only its own folder reads stays leaf. | `settings read from the env: SHOP_DB_URL` |
| schema | a `migrations/`, `alembic/` or `schema/` folder anywhere outside the tests, and a top-level folder that holds `*.sql` files, each as `<folder>/**` | `migrations: schema changes reach every row` |
| standing rule | a code or schema path that a standing rule S-n of `specs/tech-stack.md` names in a code span, when the repo tracks it (EXTEND): a Python, SQL or schema file, or a folder that holds one. Never `.env.example`, a doc, or a path under `specs/`, `project_memory/`, `proof/` or `docs/` | `named by standing rule S-1` |

Rows come by kind, then by path. A path found twice is one row with both reasons, and a path inside a folder row is left out. `probe --json` has them under `trunk`, as `{"glob", "why"}` objects.

## Services

Service-shaped signals (api, db, deploy, pipeline) limit the probe to `--help`, and a repo with no console script runs nothing at all. Either way the probe learns little about a service, and it says so:

```text
service ..... little signal for a service: the api, deploy signals limit it to --help, which never reaches the running service
              P2: suggest the service's health check as the Run-it row of the first feat change (validation.md `## Run it`), e.g. `| curl -fsS http://localhost:<port>/health | 0 | | |`
```

orca's only console script is a stub that prints usage. P2 carries the suggestion into the first feat change: merge runs its Run-it rows, which tests cannot reach.

## Residual risk

The sandbox cuts the network, not Unix sockets (Docker, D-Bus) or writes outside the clone (Risk 15). That is why service-shaped entry points only get `--help`.

## Next

By mode, as in the `SKILL.md` mode table:
- ADOPT: [2-talk.md](2-talk.md).
- MIGRATE and EXTEND + v2 migrate: [9-migrate.md](9-migrate.md) first. Its transcript step and migration prompt come before P2.
- EXTEND: [8-extend.md](8-extend.md). It sends you to P2 only for the gaps it lists, such as a crash here that has no scenario yet.
- `--plan`: print the P0 and P1 reports, the surface and the trunk candidates included, and stop.
