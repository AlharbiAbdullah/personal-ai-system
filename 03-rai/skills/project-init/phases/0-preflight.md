# P0 Preflight

**Runs in:** every mode, and `--plan`. **Writes:** nothing. **Executes project code:** never (no `uv sync`, no imports, no entrypoints).

## Run

From the target folder. The `scripts/init.py` section of `SKILL.md` explains the call form.

```sh
env -C ~ ~/.claude/skills/project-init/scripts/init.py preflight "$PWD"
```

## What it decides

**Mode**, first match wins:

| Evidence | Mode |
|---|---|
| `.project.toml` | EXTEND ([8-extend.md](8-extend.md)) |
| `Standard: project-init v2` in `project_memory/README.md` or `AGENTS.md` | EXTEND + v2 migrate ([9-migrate.md](9-migrate.md)) |
| any of `accumulated_knowledge.json`, `sessions/`, `summaries/`, `pending/`, `chromadb/` under `project_memory/`, where the v1 layout (helios) keeps them, or `.claude/hooks/project-session-*.py`. A root-level `sessions/` or `pending/` is the project's own code and never counts. | MIGRATE ([9-migrate.md](9-migrate.md)) |
| no code, and no `.git` or a `.git` with no commits | SCAFFOLD |
| anything else | ADOPT |

A lone `.claude/` never counts (N24).

**Facts:**
- Default branch. Only `origin` counts; other remotes are listed, and unreachable ones are flagged (N25). An `origin` that is a local folder is flagged too: P4's render refuses to record a folder path in the tracked `.project.toml`.
- Human authors in the last 6 months, one person under more than one email or spelling counted once (D9). One author means the solo tier, two or more the team tier. Only a commit of their own counts. Bots are left out. So is a commit made in GitHub's web UI, such as "Add files via upload" or a web edit. Its committer is `noreply@github.com`, and it was authored the moment it was committed. A pull request GitHub merged still counts. Its squash or merge commit names its number. A rebased commit keeps the author date from the author's own git commit. The authors line says who counted, with their commits, and who did not, with why. helios's `webuser` made 3 web uploads and no git commit, so helios is solo.
- The Python pin, for a repo with a root `pyproject.toml`: its `.python-version`, or with none the versions P1 and P4 try in order. Those are the versions the Dockerfiles (`FROM python:3.12`) and CI workflows (`python-version:`) run, then the `requires-python` floor, then uv's default, each within `requires-python`. P4's `init.py prepare` writes the first that builds. orca has no pin, so uv picked 3.14 and `lxml==5.4.0` failed to build. Its Dockerfile and CI name 3.12, which builds.
- A tracked `.agent/` (D7), with its file count. P2 reads it as intake, and P4 untracks it ([4-generate.md](4-generate.md)).
- `gh auth status`, and for a GitHub origin its plan and visibility.
- Tools, checked by **running** them: `<tool> --version` for mise, uv, git, gh and git-cliff, and `gitleaks version`. Never `command -v`: a shim that exists but fails is not a tool. Preflight runs them from the home folder. A tool that only the repo's own `mise.toml` pins, as in an EXTEND repo, is reported as pinned there.
- Env reads, from an AST scan for `os.environ`, `os.getenv` and pydantic-settings fields (`env_prefix` plus the field name, or its alias). Each name becomes a row of the typed env contract in P4.
- Lane-named branches from before adoption, in a repo with no `.project.toml` yet: a note, never a stop. It lists each `feat/`, `chg/`, `fix/`, `chore/`, `refactor/` or `plan/` branch that the default branch lacks, except the adoption's own `plan/project-init`. They are not changes. After G1, I8 skips a branch that forks before the adoption, and `mise run status` lists it. A v2 `chore/project-init` that was never merged is one.
- Vault matches (Rai only, read-only): `05-projects/kitchen/<name>/`, `05-projects/active/<name>/`, and an idea whose `spawned:` names the project or `09-ideas/<name>.md`. P2 reads them.

**Signals** come only from parsed evidence, and the evidence path is stored with each one (H4). Prose never counts.

| Signal | Evidence |
|---|---|
| cli | `[project.scripts]` |
| api | fastapi, flask, django or litestar deps |
| db | sqlalchemy, psycopg, asyncpg or redis deps, `alembic.ini`, `migrations/` |
| ui | react, svelte or next deps |
| deploy | Dockerfile, compose, fly.toml, wrangler.toml, `k8s/` |
| pipeline | airflow, dagster, prefect or dbt deps, `dags/` |

## Stops

Each stop is one prompt with 2 or 3 options and exactly one (Recommended). Exit code 1 means a stop was hit. The no-stack-pack stop prints first: it decides the run, and clearing any other stop only leads back to it.

| Stop | Options |
|---|---|
| Dirty tree (untracked lockfiles are exempt, D3) | 1. Stop so you can commit or stash (Recommended: init stages only its own paths, and your edits would ride along on its branch). 2. Run `--plan` only. |
| Upstream both ahead and behind | 1. Stop so you can reconcile (Recommended: init branches from the default branch as it is). 2. Run `--plan` only. |
| `origin` has a different root commit from HEAD, or another checkout under `~/projects/` or `~/work/` pushes to the same place. That is the same origin URL (helios-demo shares helios's), or a URL of the same owner with the same root commit. GitHub redirects a renamed repo's old URL: geo-context's `GeoContext.git` lands in orca. A fork under another owner shares the root commit and is not flagged. When origin's name is this repo's, the other checkout is named in a note instead. | 1. Treat this as its own repo and re-point origin yourself. 2. Stop (Recommended: that origin belongs to the other repo). |
| Code with no `.git` | 1. Run `git init -b main`, make the first commit yourself, then re-run (Recommended: you choose what the first commit holds). 2. Stop. |
| No stack pack: code with no `pyproject.toml` at the repo root (open-kit is node). v3 ships the Python pack only, and P4's render would refuse after the talk. | 1. Stop here (Recommended: v3 ships the Python pack only). 2. Adopt `specs/` and memory only, no gates: `git switch -c plan/project-init`, then P2 there (below). |
| A `.git` with no commits but an `origin` (a fresh clone of an empty remote) | 1. Run `git remote remove origin` and re-run. After the G1 merge, add the remote back, push `main` to it and re-run `/project-init`. EXTEND then finishes the remote steps (Recommended: init never pushes to a remote it did not create). 2. Stop. |

## No stack pack

v3 ships the Python pack only. A node, Rust or Go repo, or a Python repo with no root `pyproject.toml`, stops here, before any talk is spent on it. Option 2 of that stop takes only the parts that need no pack:

- First `git switch -c plan/project-init` from the default branch. P4 makes that branch in a full run, and this path never reaches P4.
- P2 as usual on that branch: the constitution in `specs/` and ADRs in `project_memory/decisions/`, through the Write tool. D7 applies too: `git rm -r -q --cached .agent`.
- Nothing is rendered: no mise tasks, git gates, hooks, `sdd` skill or CI, and P5 to P7 do not run.
- The human stages those paths by name, commits them and merges them the repo's own way.
- Once the stack's pack ships, `/project-init` adopts the repo in full.

## Output (tipcalc, P0 part)

```text
mode ........ ADOPT            git ..... master, 1 commit, no origin, untracked: uv.lock (lockfile: will commit)
stack ....... python/uv, cli (tipcalc = tipcalc:main)       signals .. cli; no db/api/ui/deploy/pipeline
tools ....... mise 2026.9.12, uv 0.12.10, gh 2.101.0 (Free); gitleaks not runnable (pinned in P4)
vault ....... no kitchen/active/idea named tipcalc
```

## Next

- SCAFFOLD: go to [2-talk.md](2-talk.md). There is no code to probe.
- Every other mode: [1-probe.md](1-probe.md).
- `--plan`: P1, then print both reports and stop.
