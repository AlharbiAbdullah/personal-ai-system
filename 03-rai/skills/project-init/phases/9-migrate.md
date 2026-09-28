# MIGRATE: legacy layouts

**Runs in:** MIGRATE (v1 JSON layout) and EXTEND + v2 migrate. The committed `.agent/` rule at the end also applies wherever a tracked `.agent/` turns up. **Writes:** a local quarantine, the redacted helm session archive (the one vault write), and moves and deletions on `plan/project-init`.

**Order:**
1. Right after P1, show the one migration prompt: each legacy item and its fate. 1. Apply all (Recommended: every fate below is the approved v3 home). 2. Stop. For v2, `init.py migrate-v2 "$PWD"` prints it and writes nothing. It lists each v2 item this repo has with its fate from the table below. It also lists each lesson that names what the migration removes or replaces, until a retiring lesson names it. A v2 path or make target counts, and so does a bare `doctor`: v3's `mise run doctor` judges differently (an empty value is unset, H17). For v1, `init.py migrate-v1 "$PWD"` prints the stores, `accumulated_knowledge.json`, each project-session hook and the `.gitignore` block, each with its fate, and writes nothing.
2. After the yes, and before P2 or anything that touches `.gitignore`, run the v1 transcript step.
3. P2 reads the legacy content as intake.
4. P4 applies the moves and deletions right after `git switch -c plan/project-init`, before render. For v2 that is `init.py migrate-v2 "$PWD" --apply`, which refuses until every D-NNN has its ADR. For v1 it is `init.py migrate-v1 "$PWD" --apply`, which refuses while a store is still in the repo. Render then records `migrated_from = "project-init v2"` in `.project.toml`. Some v2 files are covered by the prompt and not yet written by a v3 render: `mise.toml`, `.claude/settings.json`, `.env.example`, `.editorconfig`, `project_memory/README.md`, `ci.yml`, CODEOWNERS, the PR template and `AGENTS.md`. Render takes each as an unchanged render, so P4 and P6 do not ask about it again.

## v1 JSON layout (helios)

helios keeps these under `project_memory/`: `sessions/`, `pending/`, `summaries/` and `chromadb/` are gitignored by a "Project Memory (personal, not shared)" block, and `accumulated_knowledge.json` is tracked.

**1. Transcripts** (`sessions/`, `pending/`, `summaries/`), N1 and C4:

```sh
env -C ~ ~/.claude/skills/project-init/scripts/init.py migrate-transcripts "$PWD"
```

Give that Bash call a 10-minute timeout (`timeout: 600000`). A few thousand small transcripts take seconds, but a store of hundreds of MB takes minutes. A run the timeout cuts off is finished with `--resume` (below).

1. Move the three folders into `~/.local/state/project-init/quarantine/<repo>-<date>/` (mode 700, outside every repo and Syncthing folder), **before** the legacy `.gitignore` block is touched. `chromadb/` moves there too. It is a binary store, so it is never scanned or archived.
2. Make the archive set plain text. A link to a file becomes a copy of it, and a `.gz`, `.bz2` or `.xz` file is unpacked next to itself, its packed original kept in `<quarantine>/.held/`. A folder link, a broken link or a binary file moves to `.held/`.
3. `gitleaks dir -f json` runs over each store, then over a view of each file. A view is the file with its JSON decoded and inline allow comments defused, cut into pieces well under gitleaks' 100 KB read chunk. The pieces overlap, so a key at a chunk cut still sits whole in one of them. Each piece starts with a line of spaces and ends with a fresh fake key, the canary, which proves gitleaks read that piece. gitleaks skips a view that looks like a binary format, such as one with `ustar` at byte 257. That file's views are then built again behind 40 KB of spaces, past every offset its file-type check reads. The views live in `<quarantine>/.work/` and are deleted after each scan.
4. Replace every reported `Secret` in place with `REDACTED:<rule-id>`, raw and JSON-escaped, in every archived file. Rescan until it is clean, with every piece read.
5. **Held back:** a file moves to `.held/` when gitleaks skips even its padded view. So does a file with a finding that cannot be replaced in place. A secret found only by decoding base64 or hex is such a finding, because its value is not in the file as written. Each held file is printed with its reason and rule, and it goes on the rotation list.
6. Only then copy the redacted transcripts, less what was held, to `~/helm/13-archive/historical-sessions/<repo>/`. helm's own commit flow and security validator take it from there.
7. The rotation list (rule and file, never values) goes on the punch list. The quarantine is deleted only after John confirms, and after he has looked at `.held/`.
8. Nothing from these folders is ever staged in the project repo.

**Exit codes.** 0 means everything was archived. 1 means files were held back while the rest was archived, or the rescan was not clean and nothing was archived. A refusal also exits 1, and a stop by a signal exits 128 plus its number (143 for SIGTERM). `<quarantine>/project-init-migrate.json` records the outcome, the held files and the rotation list. Each (rule, file) pair is recorded before its file is rewritten or moved to `.held/`. No later scan finds a replaced secret again, and none reads a held file.

**Stopped runs.** A Bash-tool timeout sends SIGTERM. SIGTERM and SIGHUP run the same cleanup as an error: gitleaks is killed, `.work/` is removed, and the record says `stopped by SIGTERM`. A SIGKILL skips the cleanup. `.work/` then stays inside the mode-700 quarantine, next to the stores its views came from, until the next run removes it. Either way the stores stay in the quarantine, and one line finishes the job:

```sh
env -C ~ ~/.claude/skills/project-init/scripts/init.py migrate-transcripts "$PWD" --resume
```

`--resume` first moves in any store still in the repo, then runs steps 2 to 6 on the quarantine's contents. Its rotation list includes the files the stopped run had already redacted or held. Its count of secrets found only in held files covers its own scan, not the stopped run's. It refuses while the archive folder already holds files. A plain run refuses while this repo has an unfinished quarantine, and names the `--resume` line.

**A re-run** after the stores left the repo reads that record. It exits 0 and names the quarantine to delete when the archive was written whole. It exits 1 in every other case:

- `HELD`: the archive was written, and each held file is listed.
- `FAILED` (the run recorded why) or `UNFINISHED` (it never recorded an end): nothing was archived, and the `--resume` line is printed.
- `RUNNING`: another run holds the quarantine's lock right now.
- `UNKNOWN`: a folder with the repo's name and no record.

**2 to 4 run in one call**, on `plan/project-init` after the transcript step:

```sh
env -C ~ ~/.claude/skills/project-init/scripts/init.py migrate-v1 "$PWD" --apply
```

It refuses on the default branch, and while `sessions/`, `pending/`, `summaries/` or `chromadb/` is still under `project_memory/`. The `.gitignore` block keeps those out of git until the transcript step moves them. A re-run applies only what is left.

**2. `accumulated_knowledge.json`:** rendered once into `specs/backlog/<date>-legacy-knowledge.md`, one unchecked line per entry. A decision is dated by its field `date`, with `decided` as the fallback. `recent_files` and `tags_index` are left out: they are file lists and tags. The report carries the banner "Snapshot <date> of `project_memory/accumulated_knowledge.json`, unreviewed" (N16). The date is the JSON's last commit, else its `last_updated` field, else the file's mtime: a clone's mtime is the clone's date. Vault and home paths become `<vault path>` and `~`, and a wiki-link becomes its words, so the leak rules pass it. P2 read the JSON itself as intake, since it is still in the repo then. After the report is written, `git rm` takes the JSON file. A report from an earlier run is kept.

**3. Legacy hooks** (`.claude/hooks/project-session-*.py`): removed from whichever settings file registers them, `settings.local.json` included, then `git rm` takes the scripts.

**4. The legacy `.gitignore` block:** its lines go (the two comments, the four store folders and `!project_memory/accumulated_knowledge.json`), and render adds the standard lines. The staged gitleaks scan runs on the migration commit.

### Check

```sh
ls ~/.local/state/project-init/quarantine/<repo>-<date>/          # the moved folders
ls ~/.local/state/project-init/quarantine/<repo>-<date>/.held/    # absent, or each file in the report
git log -p main..plan/project-init | grep -c 'sessions/.*\.jsonl'  # 0
git diff --cached --name-status   # D for accumulated_knowledge.json and each project-session hook
```

## v2 to v3 (tipcalc with the v2 init merged)

The v2 stamp is the line `Standard: project-init v2` at the end of `project_memory/README.md`.

| v2 file | Fate |
|---|---|
| `.mise.toml` | `git mv` to `mise.toml`; the python pin is dropped; then rendered |
| `project_memory/facts.md` | content moves to `specs/tech-stack.md` and the mission glossary in P2; file deleted |
| `project_memory/decisions.md` | each D-NNN becomes `decisions/<date>-<slug>.md` with `aliases: [D-001]`; file deleted |
| `project_memory/lessons.md` | kept, unchanged. A lesson that names what the migration removes or reverses gets a lesson appended in P2 that retires it (below) |
| `project_memory/log.md` | deleted (D5) |
| `docs/spec.md` | P2 intake, then deleted |
| Makefile, `scripts/doctor.sh`, `scripts/verify.sh`, `scripts/git-hooks/`, `ONBOARDING.md` | deleted |
| `.claude/hooks/*` | unregistered from `.claude/settings.json` and `settings.local.json` first, then deleted. A hook whose script is gone exits 2, which Claude Code reads as a block of every Bash call |
| `.claude/skills/{run,verify,release}`, `.mcp.json` | deleted; `.claude/settings.json` re-rendered |
| `.github/CODEOWNERS`, `.github/pull_request_template.md`, `project_memory/team.md` | deleted when solo (D9) |
| `project_memory/.gitattributes` | deleted; the root `.gitattributes` carries the union-merge line |
| `AGENTS.md` | P2 intake, then replaced by the v3 render in P6 |
| The `## Quickstart` section of `README.md` | replaced whole by the v3 quickstart region in P6, its `make` lines and `ONBOARDING.md` pointer with it |
| `project_memory/README.md`, `.env.example`, `.editorconfig` | replaced by the v3 render in P4 |
| `.github/workflows/ci.yml` | replaced by the v3 render, remote or not: job `verify`, push branch = the default branch (H15/H24) |
| `CHANGELOG.md` | kept; the G1 merge regenerates it from history |
| `extend-exclude = [".claude"]` in pyproject | `migrate-v2 --apply` removes the `.claude` entry; the P4 render adds the two tool-owned files |
| v2 tests (`tests/test_smoke.py`) | kept: product code, not v2 machinery |

**Lessons the migration contradicts.** The lessons stay as v2 wrote them: the file is append-only and union-merged. But session-start shows the newest lessons in every session. A v2 rule the migration reverses would keep steering agents. The tipcalc lesson "keep `.claude` in `[tool.ruff] extend-exclude`" is one. For each lesson `migrate-v2` names, P2 appends one entry in the lesson format: `## <date> | Retired: <old title>`, a `Trigger:` line naming the v3 migration, and a `Rule:` line with what holds now.

### Check (Run C)

- Exactly one migration prompt.
- The file set equals a fresh ADOPT's (Run B), plus `project_memory/decisions/*` with `aliases:`, the v3 `ci.yml`, `CHANGELOG.md` and the v2 tests. It lacks `decisions/.gitkeep`, which render seeds only into an empty `decisions/`. The v2 lessons are unchanged, and a retiring lesson follows for each one `migrate-v2` named.
- No other v2 file from the table is left. The CI push branch is `main`. `mise run verify` is green.

## Committed `.agent/` (open-kit, orca), D7

Read every file as P2 intake. Then `git rm -r --cached .agent`: git history is the archive, and the local scratch stays on disk, now gitignored.

## Next

Back to the mode's phase order in `SKILL.md`: [2-talk.md](2-talk.md) after the prompt and the v1 transcript step, then [3-scaffold.md](3-scaffold.md) for the rename.
