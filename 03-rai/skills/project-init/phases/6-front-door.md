# P6 Front door, assembled last

**Runs in:** every mode that passed P5; EXTEND only when `render --check` listed a front-door row (an edit, or a template that changed since P6). **Writes:** `AGENTS.md` and the tool-owned quickstart region of `README.md`, through `init.py render --front-door`.

The front door is written after everything it names has run (H7). A command enters it only if `.agent/project-init/verify.json` records it green (R2).

## Run

```sh
env -C ~ ~/.claude/skills/project-init/scripts/init.py render "$PWD" --front-door
```

## AGENTS.md

Rendered from `templates/AGENTS.md`:
- At most 40 lines. Admission test: nothing an agent could derive from the repo itself (H9).
- 3 pointers (mission, tech-stack, roadmap), the process pointer (`specs/README.md`), the commands paragraph, the 5-rule contract, the 3 memory lines.
- `{START_EXAMPLE}` is the happy path P5 recorded, such as `mise run start -- 100`. `{TEST_TAG_EXAMPLE}` names a real scenario ID from `specs/capabilities/`.
- The gate wording matches the gate ladder in `specs/README.md#gates` (H33).
- Team-only content. Rai extras live in the vault skills, never here (H8).

The render records the hash of each file's template, `templates/AGENTS.md` and `templates/README-quickstart.md`, under `[front_door_templates]` in `.project.toml`. EXTEND's `render --check` compares it with the templates it has, since it can't render the front door without P5's record ([8-extend.md](8-extend.md)).

An existing AGENTS.md is hash-checked like any render: a customized one gets a diff and a question (R3). The v2 AGENTS.md of a v2 migration is the exception: the one migration prompt covered it, so it renders as an upgrade ([9-migrate.md](9-migrate.md)).

## README.md

- **Audit:** every fenced command is checked against `mise tasks ls` and the repo's binaries. Every Markdown file the prose links to or quotes, such as `` `ONBOARDING.md` ``, must exist. Stale ones are listed for the human, and `publish` puts them on the punch list. This phase does not rewrite prose.
- **Quickstart:** the region from the line that starts with `<!-- project-init:quickstart:begin` to the line `<!-- project-init:quickstart:end -->` is replaced from `templates/README-quickstart.md`, and the diff is shown. The begin marker carries a note for readers, so match its prefix only. With no region yet, it goes after the first paragraph.
- **Clone line (H31):** with an `origin_url` in `.project.toml`, the region opens with `git clone <origin> && cd <folder>`, the URL without any `user:password@`. With no remote there is no clone line. P7 renders the region again once it creates the remote ([7-ship.md](7-ship.md)).
- **v2 migration:** the `## Quickstart` section project-init v2 wrote is the region's place. The region replaces that section whole, its `make` lines and its `ONBOARDING.md` pointer with it, and the diff is shown.
- **No README, or an empty one** (`uv init --package` writes one): a new one gets `# <name>`, the mission one-liner as its pitch, then the quickstart.

## No CLAUDE.md

A `CLAUDE.md` or `CLAUDE.local.md` would switch off native AGENTS.md loading. A legacy one was P2 intake. Show where each of its lines went (specs, AGENTS.md or dropped), then `git rm` it.

## Check

```sh
wc -l AGENTS.md                  # 40 or fewer
mise run spec-check              # I15: every `mise run X` in AGENTS.md, README.md, specs/README.md is a task
mise run verify                  # still green
```

P5 ran the leak rules over `specs/`, `.claude/` and `project_memory/`. Run the same scoped scan over `AGENTS.md` and `README.md` (`mise x -- gitleaks dir --no-banner --redact -c .gitleaks.toml AGENTS.md`, then `README.md`): verify scans history, and these files are not committed yet. The staged scan on the P7 commit is the backstop.

A finding there is new or old. Find its line in `git diff <file>`:
- **New:** a line P6 wrote (a `+` line, or any line of a file that did not exist). This is a stop. The text came from a value or a record render read, so fix that and render again.
- **Old:** a line the file already held at HEAD, such as the 2 vault paths in orca's README prose (`leaks found: 2`). History already holds it: render fingerprinted it in `.gitleaksignore`, so verify passes, and the P7 staged scan reads only the diff. It is not a stop, and P6 does not rewrite prose. Tell the human its line and rule, and put it on the punch list ([7-ship.md](7-ship.md)). A `personal-path`, `personal-home-path` or `wiki-link` finding is a path to take out by hand. A secret rule's finding is on the rotate list already.

## Stop conditions

- A command the template needs has no green record in `verify.json`: render refuses and names it. Go back to P5, never around it.
- The human declines the README diff: keep their README and put "quickstart region not applied" on the punch list.
- The scoped leak scan flags a line P6 wrote: fix the value or record it came from, then render again. A line the file already held is no stop (above).

## tipcalc (the quickstart region)

```text
curl https://mise.run | sh      # once per machine
mise install                    # tools, dependencies, git hooks
mise run verify                 # green = ready
mise run start -- 100           # tip: 15.0
```

## Next

[7-ship.md](7-ship.md).
