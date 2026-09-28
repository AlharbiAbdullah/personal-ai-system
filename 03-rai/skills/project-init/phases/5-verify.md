# P5 Verify

**Runs in:** every mode that reached P4. **Writes:** `.agent/project-init/verify.json` (gitignored). P6 builds the front door from it and P7 writes the commit body from it.

Run it, do not trust it. A positive check proves a command works. The negative matrix proves each gate blocks what it should.

## Run

```sh
env -C ~ ~/.claude/skills/project-init/scripts/init.py selftest "$PWD"
```

It runs as one subprocess. The session now runs under the repo's own deny rules and `pre-bash` hook, and those must never mask a result (C19).

**The happy path.** `--start-args '<args>'` names it, as one string. Without the flag, selftest takes the entry script's first README fence. With no fence, it runs the P1 probe again and takes the entry's best passing row: a bare run first, then the guessed `100`, then `--help`. A CLI that runs bare, such as a fresh `uv init` package, gets no made-up argument. The line `happy args .. (none), from the probe's pass row (a bare run)` says which it used, in the words P1 printed for that row: `(guessed args: no README fence)` for tipcalc's `100`. Pass `--start-args` when the chosen args are not the product's real happy path. After a bare `--`, the rest goes to `project.py selftest`.

## Positive checks

Each runs under a timeout in its own process group, which a timeout kills whole. Each keeps only the first and last 64 KB of its output, so a command that floods its output costs no memory. The `timeouts` line prints the three limits:
- 60 s for each check;
- 600 s for `mise install`, which downloads uv, gitleaks and git-cliff on a cold cache;
- for `mise run verify` and `mise run test`, which run the whole test suite: max(600 s, twice the slowest suite run the last `verify.json` recorded). helios's 1523 tests take 150 to 200 s. `--suite-timeout <seconds>` sets it outright. A suite that runs out says so and names the flag.

The checks, in order:
- `mise install`, then `mise run doctor` (0 FAIL), `mise run verify`, `mise run start -- --help`.
- The leak rules over the uncommitted text (I14): `mise x -- gitleaks dir --no-banner --redact -c .gitleaks.toml <path>` for `specs`, `.claude` and `project_memory` each report 0. Scoped paths only: `mise run verify` scans history, which does not hold these files yet, and `gitleaks dir .` would read `.env` and `.venv/`.
- Every other command the generated files name (R2): `mise tasks ls` and `mise run status` for real; `change`, `backlog`, `tdd` and `proof` with `-- --help`, which proves the task wiring and writes nothing.
- An input that is a `[gap]` scenario is expected to crash: its row records the exit and does not fail P5. The strict-xfail test already holds it under test.
- The release dry-runs of a distributable project (pypi or git, from `## Distribution`): `uv version --bump patch --dry-run`, `git cliff --bumped-version` and `uv build -o $TMPDIR`, each through `mise x --`. The build goes to a scratch folder that selftest removes.
- The dry-run of each per-signal skill render wrote, in the folder of its evidence. `db` runs `uv run --locked alembic heads`, which reads the migration scripts and doesn't need a database. `deploy` runs `npx --no-install wrangler deploy --dry-run --outdir <scratch>`. A `run-<name>` skill makes the `start -- --help` row required.
- The happy path (above), as `mise run start -- <args>`, always the last check. P6 quotes it in AGENTS.md and the README.
- A server's health probe (start it, probe it, kill it by PID, never `pkill -f`, N13) is not part of selftest. The happy path is one command that ends within 60 s.
- Each check's record in `verify.json` also holds its `timeout`.

**verify.json** holds `standard`, `at`, `fingerprint` (the sha256 of `mise.toml`, `pyproject.toml`, `uv.lock` and `scripts/project.py`), `checks` (per check: `name`, `key`, `argv`, `cwd`, `required`, `exit`, `green`, `seconds`, the first output line and the tail of a red one), `start` (`args`, `command`, `output`, `green`), `matrix` (`argv`, `exit`, `green`) and `green`. P6 refuses a record that is red, stale or missing a command it quotes.

## Negative matrix: `mise run selftest`

It works in `git clone --no-local . $TMP/v` with `git init --bare $TMP/origin.git` as origin. The render is not committed until P7. So the clone first copies in the working tree's tracked and untracked files, never ignored ones such as `.env` or `.venv/`. It commits them there on `plan/project-init`. Without that step it would test a repo that has no gates. **Every case must FAIL. A case that passes fails P5** (N26).

| Group | Cases (each must be blocked) |
|---|---|
| Main moves | a commit on main after the first commit, with and without `--no-verify` · `branch -f main` · `update-ref refs/heads/main` · `reset --hard HEAD~1` on main · a fast-forward merge into main |
| Guard rewritten | `reset --hard` or a fast-forward of main to a commit that drops or weakens `.githooks/` · the guard emptied or its x bit cleared in the working tree |
| Forged syncs | a fake `refs/remotes/origin/main`, then `branch -f main` · origin re-pointed at a fake bare repo, then synced · an offline origin sync |
| Unmerged syncs | a sync of an origin main that moved outside merge (no `Merged-By`) |
| Recreated main | main renamed away or deleted, then recreated elsewhere · the same after wiping every ref and reflog |
| Pushes | `origin main` once it exists · `feat/x:main` · a push into the repo itself (`push .`, `push --no-verify .`, `send-pack .`) |
| Content | a staged fake key · a staged `.md` naming a vault or home path (`~/helm`, `$HOME/helm`, `/home/<user>`, `/Users/<user>`) · a partially staged `.py` with a type error only in its staged copy |
| Lane rules | `specs/mission.md` staged on `feat/` · `feat:` touching src without `Spec:` · a test tagged `nope.nope` · a scenario removed without `Spec-Removed:` |
| Skips and subjects | a new `skip` without an ID, in a test, in a root `conftest.py` or named by a string · `update stuff` or `Revert "update stuff"` as a message |

Each refusal of the main guard also prints `check git status`.

**Must PASS in the same clone:** the bootstrap commit, `pack-refs`, `gc`, `pull --ff-only` and `reset --hard origin/main` to a real origin tip, `push -u origin feat/main-menu`, a commit from a worktree.

## pre-bash cases (JSON fed in-process to `project.py hook pre-bash`)

| Must deny | Must allow |
|---|---|
| `mise run merge` | `grep -n PROJECT_MERGE scripts/project.py` |
| `sh -c "PROJECT_MERGE=1 git merge x"` | `git config --get core.hooksPath` |
| `bash ./x.sh` where x.sh sets `PROJECT_MERGE=1` | `grep -- --no-verify specs/README.md` |
| `git -c core.hooksPath=/dev/null commit`, and `core.hookspath` in lower case | `mise run test -- -k merge` |
| `git -c hook.project-main-guard.enabled=false branch -f main x` | |
| `git send-pack origin feat/x:main` | |
| `gh api -X PUT repos/o/r/pulls/1/merge` | |
| `gh api -X DELETE .../protection` | |
| `cp /tmp/h .githooks/pre-commit` | |

## Stop conditions

- **When a positive check fails,** fix the cause in the product text or the render inputs, re-run render (P4), then P5 again. Never edit a gate to make a check pass.
- **When a negative case passes,** stop. A gate that lets it through is broken, and P7 does not run. Report the case and the output.
- **When the same failure repeats,** stop and report both runs. Do not loop.

## tipcalc

```text
positive .... mise install ok | doctor 0 FAIL | verify green (1 passed, 5 xfailed) | start -- --help recorded
              happy args: 100, from the probe's pass row (guessed args: no README fence); a bare run crashes
              happy path: mise run start -- 100 -> "tip: 15.0"
selftest .... every main-move, forged-sync, push, content and lane case blocked; every must-pass case passed
pre-bash .... 10 denied, 4 allowed
```

`start -- --help` still crashes in tipcalc. It is the gap scenario `cli.help`, so its row is recorded, not failed, and P6 quotes only the happy path.

## Next

[6-front-door.md](6-front-door.md).
