<!-- tech-stack.md: runtime, tooling, distribution, standing rules, never-use, environment. Living; edit it on the branch that adds, removes or swaps a runtime dep or tool (I11). No line cap. -->
# Tech stack: tipcalc

## Runtime
- Language: Python >=3.14, pinned in `.python-version` and owned by uv.
- Dependencies: none (standard library only).

## Tooling
- mise: tools, env, tasks and setup (`mise install`).
- uv: the interpreter, dependencies and `uv.lock`.
- ruff: lint and format.
- ty: type check.
- pytest: tests, tagged with scenario IDs.
- gitleaks: secret and leak scan.
- git-cliff: CHANGELOG.md.

## Distribution
none

## Standing rules
- S-1: external input is parsed by pydantic at the boundary; env via pydantic-settings with `env_ignore_empty=True`.
- S-2: secrets are `op://` pointers only.
- S-3: scripts are uv PEP 723.

## Never use
- `pip install`: dependencies go through `uv add`.
- `uv run --frozen`: it exits 0 while skipping new dependencies; every command uses `--locked`.

## Environment
The typed contract is `.env.example` (NAME | kind | type | required | default | notes). An empty value means unset, so the default applies.
