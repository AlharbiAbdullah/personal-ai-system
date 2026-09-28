# P4 Generate

**Runs in:** every mode except `--plan`. EXTEND renders only what P8 listed. **Writes:** machinery through `init.py render`, entrypoint tests through the Write tool. P7 makes the commit.

## Run, in order

```sh
git switch -c plan/project-init                   # from the default branch; specs/ comes along untracked
git rm -r -q --cached .agent                      # D7, only when P0 reported a tracked .agent/: P2 read it; the files stay on disk
env -C ~ ~/.claude/skills/project-init/scripts/init.py migrate-v2 "$PWD" --apply   # EXTEND + v2 migrate: the moves the P9 prompt approved
env -C ~ ~/.claude/skills/project-init/scripts/init.py migrate-v1 "$PWD" --apply   # MIGRATE (v1): the moves the P9 prompt approved (9-migrate.md)
env -C ~ ~/.claude/skills/project-init/scripts/init.py prepare "$PWD" [--python <v>]   # the pin, the dev group, uv lock, uv sync --locked
env -C ~ ~/.claude/skills/project-init/scripts/init.py render "$PWD" [--remote github]   # --remote only for a GitHub answer in P2
mise trust && mise lock --platform linux-x64 && mise install   # at once: an untrusted mise.toml breaks every shim
# write the entrypoint tests (below)
mise run test
```

EXTEND of a v3 repo opens its branch with `mise run change` instead ([8-extend.md](8-extend.md)).

## What prepare does

`init.py prepare` runs before render, because render's ruff and ty baselines run from the venv it makes. It refuses on the default branch. `--dry-run` prints the four steps and runs none.

1. **The Python pin.** A repo with no `.python-version` gets one before any `uv add` or `uv sync`. `--python <v>` is the version P1 reported built. Without it, prepare tries P0's candidates with `uv sync` in a scratch clone of the committed state, and pins the first that builds. The repo's own `.venv` is never touched. If none builds, prepare stops and writes nothing. The pin ships in P7 with the lockfiles.
2. **The dev group.** `uv sync`, and so `mise install`, CI and prove-red, installs the dev group only, with the groups it includes (`include-group`), or uv's `default-groups` when the project sets them. prepare runs `uv add --dev` with what those lack:
   - the project's own test dependencies, as the project wrote them: the `dev`, `test`, `tests` and `testing` extras of `[project.optional-dependencies]`, and the `test`, `tests` and `testing` groups of `[dependency-groups]`. An extra that names the project itself, such as `app[cov]`, is followed one level;
   - the standard's ruff, ty and pytest.

   helios keeps `pytest-asyncio` and `pytest-cov` in its `dev` extra. Without them in the dev group, 290 of its tests failed.
3. **The lock (D3):** `uv lock --check`, else `uv lock`. P7 commits it.
4. **The venv:** `uv sync --locked`. When it fails, prepare stops and prints uv's cause: the repo does not build here.

## What render writes

render records the sha256 of each file it writes under `[generated]` in `.project.toml` (R3). A seed is different. render writes it only when it is missing, and after that the project owns it. `[seeded]` lists it for the P7 pathspec, and no later render compares it or asks about it. The seeds are `lessons.md`, `decisions/.gitkeep`, `team.md`, `.gitleaksignore` and the lint-debt backlog item.

| Area | Files |
|---|---|
| Toolchain | `mise.toml` (tools uv, gitleaks, git-cliff; no python; `[hooks] postinstall`; one `[tasks.X]` table per task) |
| Manifest | `.project.toml`. Keys: `standard`, `default_branch`, `origin_url`, `audit_since`, `tier`. `origin_url` is set when an origin exists, never to a local folder path, and P7 adds it for a remote it creates. `migrated_from` is set once a render met the v2 stamp, and P6 reads it. `server_protection`: `none: no GitHub remote`. For a GitHub origin that exists already (orca, helios), render asks `gh api repos/<owner>/<repo>/branches/<default>/protection` (never with `--offline`). A 403 that says "Upgrade to GitHub Pro" records `unavailable: Free private`, and no later run asks again. Any other answer leaves `pending: ...` until P7 or EXTEND records the real state. `ruff_baseline`, `ty_baseline` and `gitleaks_baseline`: what the adoption scans found (below). `agents_symlink`, with the flag. Tables: `[paths]` (below), `[signals]` with their evidence, `[values]`, `[generated]`, `[seeded]`, `[kept]` (a customized file whose render was declined), and `[front_door_templates]`, which P6 writes. |
| Python | `pyproject.toml` additions. The first line under `## One-liner` in `specs/mission.md` becomes `description`. `--values DESCRIPTION` stands in only while the mission has none. The rest: ruff `S` and `ANN` with the tool-owned copies `scripts/project.py` and the spec plugin excluded, `[tool.ruff.format] exclude = ["*.md"]`, the pytest `spec` marker and flags, `[tool.git-cliff]`, the brownfield ruff baseline. `S101`, `S603` and `S607` are off for the tests, with one `per-file-ignores` row per `[paths] tests` root (helios's `backend/tests/**`). Loose tests get one row per folder (`src/tipcalc/test_*.py`, `./test_*.py` at the root). A test made after render may have no row yet: a new test folder, or a first `test_*.py` beside the code in a folder. For a `test_*.py` file, pre-commit's `S101` refusal says to re-render. For a helper or `conftest.py` in a new test folder, it prints the folder row to add by hand. A row a later render adds goes above the baseline block. ruff formats the Python fences in Markdown too, and the docs keep their code as written: helios's `ruff format` rewrote 13 Markdown files. A project on pytest 9's native `[tool.pytest]` table gets the pytest keys there, as lists. A string `addopts` or `markers` in that table becomes a list too, since pytest 9 refuses a string there and refuses both tables at once. |
| Env | `.env.example`, the typed contract with one row per env read (knobs commented out, secrets as `op://` pointers). The reads come from an AST scan for `os.environ`, `os.getenv` and pydantic-settings fields. A read's key may be a module constant, in the same module or imported from another (`HOST_ENV = "ORCA_MCP_HOST"`). `required` comes from the code, for a secret as for a knob: no default and no `Optional`. orca's `str \| None = None` secrets are not required. Some reads have an empty default (`""` or none) and fall back to a literal or a module constant. Such a read records that value as its default. The forms are `os.environ.get(NAME, "") or DEFAULT_HOST`, and the same through one variable: `value or DEFAULT_HOST`, `if not raw: return DEFAULT_PORT`. A row the file already holds is kept as the project wrote it, and a read with no row gets one. The names the code scan does not see carry over as rows too. They come from the project's own plain `.env.example` lines, compose interpolation (`${NAME}`) and a Makefile's `NAME ?=` or `$${NAME}`. Such a row is not required, of type `str`, with no default and a blank value, since the old file may hold a real secret. A name that says it holds a secret is a secret row, any other a knob. Adoption never drops a name. Its notes name the files that read it, `read in <files>`, with no line numbers, and doctor warns when one of them no longer names the variable. It looks for the name as a whole word. Only a file with a pydantic-settings class may spell it in lower case. That class is based on `BaseSettings`, or on a base of the project's own whose name ends in `Settings`. doctor reads an empty value as unset, as the contract says (H17). It still warns when an open `[gap]` scenario names that variable, because the gap says the app does not honour the contract yet. Render never deletes a row, not even one whose read the scan no longer sees. |
| Git | `.gitignore` lines, `.editorconfig`, `.gitattributes` (`project_memory/lessons.md merge=union`) |
| Gates | `.githooks/{pre-commit,commit-msg,pre-push}` shims, `.githooks/reference-transaction`, `scripts/project.py`, `.gitleaks.toml`, and the `.gitleaksignore` seed only when the history scan finds anything (below) |
| Tests | The spec plugin (the `spec(*ids)` marker, `--spec`, `.cache/spec-results.json`), from `templates/tests/conftest.py`. pytest loads a `conftest.py` only for the tests under its folder. So the plugin has to be in a folder above every test pytest collects. Those are the test roots, and any loose `test_*.py` beside the code or at the root. It goes in `tests/conftest.py` when `tests/` holds them all and that file is free. Free means absent, or the plugin a render wrote. Otherwise it goes in the deepest folder above them all whose `conftest.py` is free, outside every source root. helios's tests sit in `backend/tests`, whose own `conftest.py` stays, so the plugin is `backend/conftest.py`. A package's own `tests/` in `src/` with no testpaths set, or a project that owns `tests/conftest.py`, gets the root `conftest.py`. The project's own `conftest.py` may already be in every such folder, as orca's root one is. The plugin then stays in `tests/conftest.py`, and render names the tests that never load it. A scenario test there records `notrun`. When `tests/conftest.py` is the project's own too, render asks before it writes over it, and its note says how to free a folder. |
| Claude | `.claude/settings.json` (SessionStart + PreToolUse:Bash hooks, the allow and deny seed) and `.claude/skills/sdd/`. The `.agents/skills/sdd` symlink to it comes only with `render --agents-symlink`. Use it when the M6 check shows pi or OpenCode cannot find the skill otherwise. Later renders keep the link. |
| Process | `specs/README.md` from `templates/specs-README.md` |
| Memory | `project_memory/README.md`, and the seeds `lessons.md` (an existing one is carried over) and `decisions/.gitkeep` (skipped once `decisions/` holds a file) |
| Team tier only (D9) | The `project_memory/team.md` seed: the roster of 6 months of human authors, with the one running project-init as Lead. A login is filled in only where a noreply address gives it. `.github/CODEOWNERS`, generated from its Ownership table on every render. `.github/pull_request_template.md`. |
| CI | `.github/workflows/ci.yml` with a GitHub remote, or in place of a v2 project-init `ci.yml`, remote or not ([9-migrate.md](9-migrate.md)). Once rendered, it stays rendered. A repo with its own CI keeps it, and gets `sdd.yml`, whose workflow and job are both named `sdd`. |
| Signals | A per-signal skill only for a file whose dry-run P5 can run: `run-<name>` for an api signal (`mise run start -- --help`). When the start command is a console script whose function only prints and returns (orca's usage stub), `run-<name>` says so. It names the server commands it found instead: compose `command:` lines, Makefile recipes and console scripts that run uvicorn, gunicorn, `dagster dev`, `python -m <pkg>.server` and the like. `db` comes for an `alembic.ini` (`alembic heads`), and `deploy` for a wrangler config (`wrangler deploy --dry-run`). Never a skill named `run`. Other evidence (a Dockerfile, compose, `fly.toml`, `k8s/`, db dependencies with no `alembic.ini`) doesn't get a skill, and render prints why. |

Not here: `AGENTS.md` and the README quickstart. P6 writes them after P5 proves the commands.

Nor the `## Trunk` section of `specs/tech-stack.md`. It is product text: P2 writes it from the probe's trunk candidates. While it is missing, render prints a `trunk` line with the candidates and writes nothing to `specs/`. `render --check` counts that line as drift ([8-extend.md](8-extend.md)).

**`[paths]`** holds `src` and `tests`, which D4's `Spec:` rule, I7 and prove-red read. The first render records them, and later renders keep them.
- `tests`: the project's pytest `testpaths`, from `pytest.ini`, `.pytest.ini`, `pyproject.toml`, `tox.ini` or `setup.cfg` in pytest's own order. With none set, pytest collects from the root, so it is the `tests/` and `test/` folders found there, top-level ones first. It is `tests` when there are none yet. A testpath inside a source root counts by the `tests/` folders in it: orca's `src/orca` gives `src/orca/api/tests` and its siblings, never the whole package.
- `src`: `src/`, else the top-level packages, else the code beside the tests. For helios that is each package and module in `backend/` that git tracks Python in, with `backend/tests` left out.

Once `.claude/settings.json` exists, this session runs under it, with the `pre-bash` denies listed in `SKILL.md` (scripts/init.py). That is expected: keep gate work inside `init.py` and `mise run` subprocesses.

### Template placeholders

render fills every `{UPPER_CASE}` token in the text templates. `scripts/project.py`, the spec plugin (`tests/conftest.py`), `settings.json`, `.gitleaks.toml`, `.editorconfig` and `skills/sdd/` are copied byte for byte: the braces in them (Python f-strings, the `${HOME}` in a leak rule) are not tokens. A rendered text file with a token left over is a render bug, and the EXTEND placeholder check catches it.

| Token | Value | Used in |
|---|---|---|
| `{NAME}` | `[project].name` from pyproject | most templates |
| `{DEFAULT_BRANCH}` | the default branch after the P3 rename | `specs-README.md`, `ci.yml`, the `D=` line of `.githooks/reference-transaction` |
| `{ENTRY}` | the console script from `[project.scripts]` | `mise.python.toml` (`start`) |
| `{OP_RUN}` | when the env contract has a secret row, a `sh -c` wrapper: `op run --env-file .env --` when `.env` exists, else the plain command, so a fresh checkout starts with no `.env`. Empty otherwise | `mise.python.toml` (`start`) |
| `{ENV_ROWS}` | per env read from P0: the `# NAME \| kind \| type \| required \| default \| notes` row, and for a `knob` row a commented `#NAME=<default>` line | `env.example` |
| `{TEST_TAG_SYNTAX}` | one sentence on the stack's tags. Python: `` `@pytest.mark.spec("<id>", ...)` tags a test, and a gap test also carries `@pytest.mark.xfail(strict=True, reason="<id>: <why>")`. `` | `specs-README.md` |
| `{TEST_TAG_EXAMPLE}` | the tag with a real scenario ID, e.g. `@pytest.mark.spec("cli.no-args")` | `AGENTS.md` (P6) |
| `{START_EXAMPLE}`, `{START_EXPECTED}` | the happy path P5 recorded green and its output; the quickstart comment is padded to line up, and dropped when there is no output | `AGENTS.md`, `README-quickstart.md` (P6) |
| `{CLONE_URL}`, `{CLONE_DIR}` | `origin_url` from `.project.toml` without any `user:password@`, and the folder `git clone` makes from it | `README-quickstart.md` (P6, and P7 once it creates the remote) |
| `{CHECKOUT_REF}`, `{MISE_ACTION_REF}` | the current major tag of `actions/checkout` and `jdx/mise-action`, resolved with `gh api` | `ci.yml` |
| `{CI_JOB}` | `verify`; `sdd` when the repo already has its own CI and this file becomes `sdd.yml` | `ci.yml` |
| `{CI_NAME}` | the workflow's `name:`: `ci`; `sdd` for `sdd.yml`, so it never shares a name with the repo's own CI | `ci.yml` |
| `{TEAM_ROWS}`, `{LEAD_OWNER}` | the roster rows, and the lead's `@login` or a hint to fill it in | `team.md` |
| `{CODEOWNERS_ROWS}` | one `path owners` line per Ownership row of `team.md` that lists a valid owner; a comment when none does | `CODEOWNERS.tmpl` |
| `{SERVICE}`, `{START_LINE}`, `{SERVICE_COMMANDS}`, `{DB_CONFIG}`, `{DB_DIR}`, `{DEPLOY_CONFIG}`, `{DEPLOY_DIR}` | from the evidence files, never from `--values` | `skills-per-signal/` |

Conditional lines hold `{IF_RELEASE}` (distribution is pypi, git or service), `{IF_TEAM}` (team tier) or `{IF_REMOTE}` (a hosted `origin_url`: the quickstart's clone line). Such a line is dropped when the condition is false. When it is true, render removes the marker, and a trailing `#` comment left empty by that.

## Entrypoint tests (product text, Write tool)

One test per scenario in `specs/capabilities/`, tagged with its ID, spawning the real console script:

```python
@pytest.mark.spec("cli.no-args")
@pytest.mark.xfail(strict=True, reason="cli.no-args: traceback today (gap entrypoint-hardening)")
def test_no_args() -> None:
    r = subprocess.run(["tipcalc"], capture_output=True, text=True, check=False)
    assert "Traceback" not in r.stderr
    assert r.returncode != 0
```

Characterization tests look the same, without the xfail. A gap test asserts the wanted behaviour, so it fails today, and its xfail reason contains its ID (I3).

## Brownfield debt

- **ruff lint (N3):** the venv's ruff (from the `uv sync` above) runs `ruff check --output-format json` under the config render writes. Each file with findings gets a `per-file-ignores` row under `# project-init baseline: shrink only`. A root file's key is `./setup.py`, since ruff matches a bare `setup.py` against every file of that name. Render also seeds one backlog item, `specs/backlog/<date>-ruff-baseline.md`. The baseline is taken once and `ruff_baseline` records it. Debt added later fails lint and doctor instead of joining the block. With no `.venv/bin/ruff`, render says so, and the next render tries again.
- **History leaks:** render runs `gitleaks git` over the history once, with the rendered leak rules. Any finding goes to `.gitleaksignore` as a `commit:file:rule:line` fingerprint, never a value, and render counts them by rule. Only a secret rule's finding puts "rotate the secrets" on the punch list. A `personal-path`, `personal-home-path` or `wiki-link` finding is a path in a committed file, and render says so: orca's 134 findings were all paths. `gitleaks_baseline` records the scan, so a leak committed later still fails verify.
- **ruff format:** run `uv run --locked ruff format <files>` on the files `ruff format --check` names. Those files join the P7 pathspec, and the commit body lists them. Markdown is never among them: the rendered config leaves `*.md` out of the formatter.
- **ty (Risk 8):** render runs the venv's ty (`ty check --output-format gitlab`, the project's own config) once. ty has no per-file ignore, so each file with a diagnostic goes into `[tool.ty.src] exclude` under `# project-init ty baseline: shrink only`, and render seeds one backlog item, `specs/backlog/<date>-ty-baseline.md`. ty 0.0.x exits 1 on a warning too, so warnings count. `ty_baseline` records the scan, and type debt added later still fails `mise run types`. The session doesn't edit it by hand. A project with its own `ty.toml` gets `skipped:`, and the exclude goes there by hand. With no `.venv/bin/ty`, render says so, and the next render tries again.

## Check

- `.venv/` exists, and postinstall ran `project.py hook install`: `git config --get core.hooksPath` prints `.githooks`, `git config --get-all receive.hideRefs` lists `refs/heads/<default>`, and `git config --get hook.project-main-guard.event` prints `reference-transaction`.
- `mise ls --current` doesn't list python (H16). `grep '^description' pyproject.toml` is the one-liner (H6).
- `mise tasks ls` lists the visible tasks, each with a description.
- render printed no `trunk` line: `specs/tech-stack.md` has its `## Trunk` section from P2.
- `mise run test` collects every scenario ID.
- `.project.toml` has `ruff_baseline`, `ty_baseline` and `gitleaks_baseline`, and none starts with `skipped:`. A skipped scan says which tool is missing: install it, then render again.

## Stop conditions

- render reports a customized file: it has not written anything, neither a file nor `.project.toml`. Show the diff and ask (R3), then render again with `--force-file <path>` or `--keep-file <path>` for each file. Never overwrite by hand. The diff runs from the render to the file as it is, so the project's own lines show as `+`.
- render exits 1 on an unfilled placeholder, again with nothing written: pass the value with `--values`. For `DESCRIPTION`, write the one-liner under `## One-liner` in `specs/mission.md` instead (P2).
- render refuses an origin that is a local folder, such as the source of a `git clone --no-local`, with nothing written. `.project.toml` is tracked, and a folder path names this machine. Run `git remote remove origin`, or point origin at the hosted repo, then render again.
- `prepare` fails: stop and show its output. The pin, the lock or the venv is not there, and render's baselines and every test need them.
- `mise install` fails: stop and show its output. No gate works without it.
- render printed `no db skill` or `no deploy skill`: copy the note into the report. render writes a skill only when P5 can run its dry-run.

## tipcalc

```text
branch ...... plan/project-init (from main df806ec)
rendered .... mise.toml .project.toml .env.example .githooks/ scripts/project.py .gitleaks.toml
              tests/conftest.py .claude/ specs/README.md project_memory/README.md
seeded ...... project_memory/lessons.md project_memory/decisions/.gitkeep (solo: no team.md; no CI)
baselines ... ruff clean, history clean (no .gitleaksignore)
tasks ....... start fmt test verify status change backlog tdd doctor approve merge abandon
              (12 listed; lint types secrets spec-check prove-red selftest hidden; no release)
test ........ 1 passed, 5 xfailed
```

## Next

[5-verify.md](5-verify.md).
