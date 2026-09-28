# P7 Ship and punch list

**Runs in:** every mode that passed P6. **Writes:** one commit on `plan/project-init` (EXTEND: on its own branch, see [8-extend.md](8-extend.md)), and with a GitHub remote chosen, the repo and its pushes. Then it stops at G1.

## Run

One line each, from the repo root. Look first, then ship:

```sh
env -C ~ ~/.claude/skills/project-init/scripts/init.py publish "$PWD" --dry-run
env -C ~ ~/.claude/skills/project-init/scripts/init.py publish "$PWD"
env -C ~ ~/.claude/skills/project-init/scripts/init.py publish "$PWD" --remote github [--repo <name>]
```

The second line ships locally. Use the third instead when the P2 answer was a private GitHub repo (D2). The GitHub repo is named after the folder, not the pyproject name: `--repo <name>` (or `<owner>/<name>`) names it. `--dry-run` works with either: it prints what would be staged, the commit body and the remote steps, and runs nothing.

Staging, the commit and the remote steps all run inside `publish`. From P4 on, the session's `pre-bash` hook denies command text that names `.githooks/` or `gh repo edit` (`SKILL.md`, scripts/init.py). A `git add .githooks/...` or a `gh repo edit` typed in the session would be blocked.

`publish` refuses, and doesn't change anything, when:

- HEAD is on the default branch or detached;
- `.project.toml` is missing, or P6 has not run (no `AGENTS.md` in `[generated]`);
- `verify.json` is missing, not green, or stale (the same rules as P6);
- the branch holds commits other than the ship commit;
- `.gitignore` ignores a path the commit needs (`--dry-run` lists them under `IGNORED`);
- `.agent/` is still tracked (D7: P4's `git rm -r -q --cached .agent`; `--dry-run` says so under `D7`);
- `--remote github` is asked and `gh auth status` fails.

## The commit

- **Pathspec:** `.project.toml`, every `[generated]` and `[seeded]` path, `specs/` (the constitution), `project_memory/decisions/`, the test roots (`[paths] tests`), the lockfiles `uv.lock` and `mise.lock` (D3) and the `.python-version` P4 wrote. The decisions folder holds the ADRs P2 and P9 write, which replace the `.gitkeep` seed. Then `git add -u`, for the tracked files P4 formatted or merged. The `git mv` and `git rm` from P9 and P6 are already staged, so the same commit records them. Never `git add -A` (N14).
- **Printed first:** every staged change, moves and deletions included. Untracked files outside the pathspec are listed as not staged, and never added. `--dry-run` lists them too, so the look before shipping shows a product file the commit would leave out.
- **Subject:** `chore(init): project-init v3`. EXTEND, whose default branch already holds a `.project.toml`, commits `chore(init): project-init v3 upgrade`.
- **Body:** written from `verify.json` after P5, with real results only (N21). It lists each check with its result and the happy path with its output. Then come the count of `[gap]` scenarios the probe left, and the ruff, ty and history-scan baselines. Last comes what the render changed, against the default branch's `.project.toml`. In EXTEND, that is the files it upgraded, added or stopped rendering. In every mode, it lists each file kept as the project wrote it (a new `[kept]` row). It also lists each file taken from the render after an earlier keep.
- **At G1** the squash keeps this body. Merge copies the prose of the commit its subject comes from into the squash body, so `main` keeps the P5 record once the branch is gone.
- **A re-run** with nothing new leaves the commit as it is, and `--dry-run` says `nothing new, no amend`. A late change is amended into the one ship commit.

The repo's own hooks run on the commit. When they refuse it, `publish` prints their output and stops, the changes staged. Fix what they name, then re-run.

## The remote (D2 = GitHub only)

1. `gh repo create <repo> --private --source . --remote origin -d "<one-liner>"`, with no `--push`. `<repo>` is the folder's name, or `--repo`.
2. `git push -u origin main`, the default branch (P3 renamed `master`). pre-push allows it because the remote lacks main (N10).
3. Record, then amend the ship commit, which is not pushed yet:
   - `origin_url` and `server_protection` into `.project.toml`;
   - the README quickstart region rendered again, now with its clone line (H31), when it is still the region P6 wrote.
4. `git push -u origin plan/project-init`.
5. `gh repo edit --default-branch main --delete-branch-on-merge --enable-squash-merge`. The default is `main` explicitly, never whatever HEAD was (C5).

Server rules are not applied here. Step 3 asks GitHub with `gh api repos/<owner>/<repo>/branches/main/protection`, so main must exist first. A 403 that says "Upgrade to GitHub Pro" means a private repo on the Free plan: step 3 records `unavailable: Free private`, and nothing retries it. Any other answer records `pending: ...`, and EXTEND applies the rules after the first green CI run, from the observed job names (N2, N23). `gh api user` can't answer this: its plan needs the `user` scope, which gh's default login lacks. For an origin that existed before init, P4's render asks the same question once.

Each step is recorded in `.agent/project-init/publish.json` as it succeeds. A step that fails stops `publish` and names the step. The same `--remote github` line then continues at that step and never runs `gh repo create` again. If create itself failed, check `gh repo view <n>` before anything else. The gh token has no `delete_repo` scope, so a half-made repo goes on the punch list for manual deletion.

An origin that `publish` did not create is left alone: the remote steps belong to EXTEND.

## Check

```sh
git status --porcelain                           # empty, or only the files publish listed as not staged
git log --oneline <default>..plan/project-init   # exactly 1 commit
git log -1 --format=%H <default>                 # unchanged since P3 (ADOPT: the adopted tip)
```

## Final prompt

```text
review, then `! mise run merge`            (G1: the constitution and the standard land on main)
then /clear before the first /sdd
```

In Claude Code the human types it with the `!` prefix. If that prefix is denied, they run it in a terminal they open themselves (Risk 3). Rai never opens one.

## Punch list (human-only, only what applies)

`publish` prints the items it can see. Rai adds the rest from the session.

- `git config --global init.defaultBranch main` (printed when it is not set to `main`).
- The 1Password items behind the `op://` secrets in `.env.example` (printed).
- The server rules state, as recorded in `.project.toml` (printed with a remote).
- The capture tools for the repo's proof, when P1 named a web or terminal UI (printed): `mise run proof -- setup web` or `mise run proof -- setup terminal`. They download a headless browser or vhs, so the human runs them. A repo with console scripts only needs none.
- README.md commands and file references P6 listed as stale (printed): prose is fixed by hand.
- Old leak-rule findings from P6's scoped scan: lines README.md or AGENTS.md already held. Rai adds each with its line and rule, and the prose is fixed by hand.
- Secrets to rotate, when render wrote `.gitleaksignore` (printed): each line holds a `commit:file:rule:line` fingerprint, never a value.
- CODEOWNERS owners, when the Ownership table of `team.md` has no valid owner (team tier, printed).
- The quarantine to delete after you confirm the archive (MIGRATE, printed). First, the files `migrate-transcripts` held back in its `.held/`, each printed with its file and rule: they were never archived.
- A remote default-branch rename (`master` with a remote, P3).
- A half-made GitHub repo to delete by hand, if `publish` failed at step 1.

## tipcalc

```text
committed ... plan/project-init: chore(init): project-init v3 (uv.lock included)
remote ...... none (local only)
next ........ review, then `! mise run merge`; then /clear before the first /sdd
punch list .. git config --global init.defaultBranch main
```

After the human's G1 merge, main is `df806ec` plus the squash `chore(init): project-init v3` with its `Merged-By: mise run merge` trailer.
