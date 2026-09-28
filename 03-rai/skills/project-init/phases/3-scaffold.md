# P3 Scaffold

**Runs in:** SCAFFOLD (the whole phase). ADOPT, MIGRATE and EXTEND + v2 migrate run only the branch rename. EXTEND skips it. **Writes:** the first commit on `main` (SCAFFOLD), or a branch rename.

No git hooks are active yet, so this is the one phase that commits on `main` directly.

## SCAFFOLD: an empty folder

P2 has already written `specs/` and settled the name and the mission one-liner. Run, in the folder:

```sh
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=init.defaultBranch GIT_CONFIG_VALUE_0=main \
  uv init --package --name <n> --description "<mission one-liner>" .
uv add --dev ruff ty pytest
uv lock
git add -- .gitignore .python-version README.md pyproject.toml src uv.lock
git commit -m "chore: scaffold <n>"
```

- The env triple forces `main` even when the global `init.defaultBranch` is unset; that global setting goes on the punch list.
- A `.git` with no commits is kept: run `git symbolic-ref HEAD refs/heads/main` before `uv init`. uv leaves an existing repo alone and then writes no `.gitignore`, so drop `.gitignore` from the `git add` line. P4 writes it.
- uv writes its Python `.gitignore`; P4 appends the standard lines.
- Stage by explicit path. `specs/` stays untracked here: it lands on `plan/project-init` in P4, so `main` holds only the scaffold.
- Never pip, black, isort, flake8 or mypy. ruff, ty and pytest are the dev deps; pydantic joins when the first external input boundary does.

**The Trunk section.** P2 talked before any code existed, so it left `## Trunk` in `specs/tech-stack.md` with its comment line only. The scaffold commit made the entrypoint, and an entrypoint is trunk. Run the probe on it, which reads the committed scaffold and writes nothing:

```sh
env -C ~ ~/.claude/skills/project-init/scripts/init.py probe "$PWD"
```

Its `trunk` block holds one candidate, `- src/<n>/__init__.py: the entrypoint of the <n> command (<n>:main)`. Ask [2-talk.md](2-talk.md)'s Trunk question with it, and write the answer under `## Trunk`. A headless run keeps it.

**Non-Python stacks** use a stack pack in `templates/stacks/<stack>/` with the same task names. No pack exists for the stack: stop and say so, and scaffold nothing.

### Check

```sh
git branch --show-current          # main
git log --oneline                  # 1 commit: chore: scaffold <n>
git status --porcelain             # only ?? specs/
grep '^description' pyproject.toml # the one-liner, not "Add your description here"
grep -A3 '^## Trunk' specs/tech-stack.md   # the comment line, then the entrypoint (or empty, if the human chose that)
```

## Every other mode: the default-branch rename

| State | Action |
|---|---|
| default branch `master`, no remote | `git branch -m master main` |
| default branch `master`, a remote exists | no rename. The rename goes on the punch list: a shared default branch is never renamed here. |
| any other name | nothing. P4 renders against the detected default branch. |

The rename happens before P4 renders the CI file and the `reference-transaction` hook, so both are rendered against the final name.

## tipcalc

```text
ADOPT: master -> main (no remote); main = df806ec, 1 commit, untouched otherwise
```

Run A (SCAFFOLD, `hello`): `main` holds exactly `chore: scaffold hello`.

## Next

[4-generate.md](4-generate.md).
