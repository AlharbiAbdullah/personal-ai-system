# EXTEND: audit and upgrade

**Runs when:** `.project.toml` exists. Re-running `/project-init` is the audit. **Writes:** nothing tracked until the audit finds a change; then a branch, hash-aware renders and one ship commit. `mise install` sets up this clone's own tools and git gates, which git does not track.

## Run

```sh
env -C ~ ~/.claude/skills/project-init/scripts/init.py preflight "$PWD"        # P0, as always
env -C ~ ~/.claude/skills/project-init/scripts/init.py probe "$PWD"            # P1, as always
env -C ~ ~/.claude/skills/project-init/scripts/init.py render "$PWD" --check   # writes nothing
mise trust && mise install   # a fresh clone has its git gates off until this (postinstall: hook install)
mise run doctor              # the gates, the hook blobs, the trailer audit since audit_since
```

`render --check` lists every `[generated]` file as one of:

| Status | Meaning | Action |
|---|---|---|
| ok | matches the current template render | none |
| upgrade | the file still has its recorded hash; the template moved on | upgraded without asking |
| customized | the file's hash differs from the recorded one | diff + question (R3, N18) |
| missing | the standard expects it; the repo lacks it | rendered |

A front-door file (`AGENTS.md`, the README quickstart region) can't be rendered here, since its render needs P5's record. `--check` judges it by two hashes instead. Its own recorded hash shows an edit: `customized`. The diff runs from the version P6 wrote, found in history by that hash, to the file as it is now. The hash of the template P6 rendered it from (`[front_door_templates]` in `.project.toml`) shows a template that changed since. An untouched file is then `upgrade`, and a kept one is `customized` again, so P6 asks once more. A file with no template hash on record counts as changed. The keep-or-take diffs of `render` and of `--check` both run from the render to yours, so your own lines show as `+`.

Three more `render --check` lines. `gates` says `core.hooksPath` is not `.githooks`: the files can all match while this clone has its git gates off. `origin` says origin is a local folder, as in a `git clone --no-local` copy: `--check` audits as if there were no origin, and a writing render refuses it until `git remote remove origin`.

`trunk` says `specs/tech-stack.md` has no `## Trunk` section, so every path counts as leaf. A v3.0 repo is the usual case: its `scripts/project.py` is 3.0.x, and the line leads with `v3.1 upgrade`. The candidates follow it, one `- <glob>: <why>` line each, from the static scan P1 prints too. It counts as drift until the section exists:

```text
trunk ....... v3.1 upgrade: specs/tech-stack.md has no ## Trunk section, and scripts/project.py is 3.0.0. Until it has one, every path counts as leaf. P2 proposes it on the plan/ branch from 1 candidate:
              - src/tipcalc/__init__.py: the entrypoint of the tipcalc command (tipcalc:main)
```

## Checks (the audit list)

- Placeholders `\{[A-Z_]+\}` in tracked text files, and "Add your description here" (H6). The files render copies byte for byte are skipped (`scripts/project.py`, the spec plugin, `.gitleaks.toml` among them): their braces are not tokens.
- The CI push branch equals the default branch (H15). Render's own CI file is hash-checked, so its push branch and job name are the render's. A workflow render does not own is the project's own, or a v2 one left behind. It must push on the default branch, and every branch it names must exist: a renamed `master` fails that. `render --check` lists each miss as `ci` drift. The job names are compared with the required checks (H24) once the server rules below have recorded them.
- CODEOWNERS agrees with `team.md` (team tier).
- Every gate calls a mise task, and every `mise run X` in the docs is a task (I15).
- The ruff baseline only shrank. The `project.py` version is current.
- `mise run doctor` has 0 problems: `core.hooksPath` is `.githooks`, the hook files match their committed blobs, and the trailer audit since `audit_since` is clean. doctor runs only after `mise trust && mise install`.
- A tracked `.agent/` triggers D7: read it as P2 intake, then `git rm -r --cached .agent` (the local scratch stays, now ignored).
- 2+ human authors in 6 months on a solo repo: offer the team tier (D9). P0 counts them: a commit of their own, never a web-UI upload or a bot. 1. Add team.md, CODEOWNERS from it and the PR template (Recommended when the second author is a real collaborator). 2. Stay solo.
- **A remote appeared since the last run** (N23, N2): `origin_url`, the CI file, the repo settings from P7 step 5. Server rules come only after the first green CI run, from the observed job names.
- **The v3.1 upgrade** of a v3.0 repo. `render --check` lists `scripts/project.py`, the sdd skill, `specs/README.md` and `mise.toml` as `upgrade` (or `customized`, with a question), and prints the `trunk` line. The machinery goes through render like any upgrade. The Trunk section is product text, so P2 proposes it (step 2 below).
- A probe crash with no scenario, or a `[NEEDS CLARIFICATION` in the constitution: run [2-talk.md](2-talk.md) for those gaps only.

**Rai-only checks** (the vault is read-only):
- `05-projects/active/<name>/` holds vision, roadmap or architecture: report "direction lives in the vault; migrate to specs/".
- A fact kept in both places (the orca 518 vs 537 case): show both values and ask which is true. The repo wins by default.

## Nothing to do

```text
EXTEND: 0 changes
```

Print that when `render --check` reports 0 drift with no `gates` line and doctor reports 0 problems, then stop. No branch, no commit (Run D).

## Changes found

1. **Branch.** HEAD is still the unmerged `plan/project-init`: work there. Otherwise `mise run change -- <date>-project-init --lane plan`; the repo's own one-open-change rule (I8) applies.
2. **The Trunk section**, when `render --check` printed a `trunk` line: [2-talk.md](2-talk.md)'s Trunk question with the candidates that line listed, asked on this branch. Write the answer into `specs/tech-stack.md` with the Write tool, from the template's `## Trunk` block: its comment line, then the entries. The next `render --check` prints no `trunk` line.
3. **Customized files.** One question per file, with the diff `render --check` printed: 1. Keep yours (Recommended: a customized file is a decision someone made). 2. Take the new render. A kept file's declined template hash is recorded, so the next run asks again only when the template changes.
4. `init.py render` for the upgrade and missing rows, with one `--keep-file <path>` or `--force-file <path>` per customized machinery file, as answered. A front-door file is answered at P6 instead, `init.py render "$PWD" --front-door --keep-file AGENTS.md` (or `--force-file`): the machinery render refuses a front-door path.
5. [5-verify.md](5-verify.md), [6-front-door.md](6-front-door.md) if `render --check` listed a front-door row (an edit, or a template that changed since P6), then [7-ship.md](7-ship.md). `publish` commits `chore(init): project-init v3 upgrade`, since the default branch already holds a `.project.toml`.
6. When a gate file changed (the list in step 6 of [the Definition of Done](../templates/specs-README.md#definition-of-done)), the final prompt is `! mise run merge -- --gate-change`. The v3.1 upgrade changes `scripts/project.py`, so it always needs it.

Keeping a file is a change too. The `[kept]` row lives in the tracked `.project.toml`, so it goes through the EXTEND branch, P5, P6, the ship commit and G1 like any other change. After that merge, the audit reports the file as kept and asks again only when the template moves.

## tipcalc (Run D)

```text
re-run on Run B's output ........ a git clone --no-local copy, then git remote remove origin,
                                  mise trust && mise install, doctor 0 problems: EXTEND: 0 changes
AGENTS.md edited, uncommitted ... P0 stops on the dirty tree: an edit lands on main first, as every
                                  change does. change refuses a dirty tree (I8), so stash around it:
                                  git stash push -- AGENTS.md, mise run change -- <slug> --lane chore,
                                  git stash pop, commit, ! mise run merge
re-run after that merge ......... customized: AGENTS.md, diff from the version P6 wrote
                                  -> 1. keep yours (Recommended) 2. take the render; nothing overwritten
keep yours ...................... plan/<date>-project-init, P5, P6 with --keep-file AGENTS.md
                                  ("render: 1 change (.project.toml only ..."),
                                  chore(init): project-init v3 upgrade, then ! mise run merge
a v3.0 copy, once v3.1 ships .... upgrade: scripts/project.py, .claude/skills/sdd/*, specs/README.md,
                                  mise.toml; trunk: no ## Trunk section, 1 candidate
                                  -> plan/<date>-project-init, the Trunk question (keep all),
                                  render, P5, P6, chore(init): project-init v3 upgrade,
                                  then ! mise run merge -- --gate-change
```
