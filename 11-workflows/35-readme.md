# README

**Use when:** a repo's README is written, rewritten or brought to the standard. That covers a new repo, a repo whose system changed, or an old README that drifted.
**Not for:** 34 diagrams, for drawing the architecture and tech stack pair: this workflow embeds them. Docs beyond the README go in `docs/` through [[02-task]].
**Done when:** the README follows the skeleton below, every claim in it was checked against the repo, Vale is clean, and he approved it.

One standard for every repo, public or private. Settled from a `/fusion → brainstorm` run.

```d2
direction: right

read: "1. Read the repo"
tier: "2. Pick the tier" {shape: diamond}
write: "3. Write the skeleton"
check: "4. Check every claim"
cut: "5. Cut"
land: "6. Land it"

read -> tier -> write -> check -> cut -> land
```

---

## The skeleton

The order never changes. A section appears only when it has content.

```
# repo-name
One-liner: what it is and for whom. One sentence, under 120 characters.
Status: <design | building | working | in production | archived> · <kind> · YYYY-MM
![alt: the flow in one sentence](docs/diagrams/architecture.excalidraw.svg)

## What it does
## How it works
## Tech stack
## Decisions
## Results
## Run it
## Checks
## Layout
## Docs
## License
```

| Section | Rule |
|---|---|
| One-liner | A mechanism, not a slogan. The same sentence goes in the GitHub About field. |
| Status | Stage, kind (learning build, product, kit, fork of X) and month. No private paths. |
| Architecture | The diagram right under the status line, with no heading above it. The alt text is the flow in one sentence. |
| What it does | What it answers or does, in at most 4 lines. No non-goals, no gaps list. Replaces any Features list. |
| How it works | Numbered steps, one per diagram zone, named with the zone's title. At most 8 steps of 2 lines. A tool appears only as the actor in a step. |
| Tech stack | The tech stack diagram only. Its alt text lists the tools in zone order. Never a table under it. |
| Decisions | 3 to 5 bullets: "X over Y: why. Cost: …". Each one backed by the code, a task file or a decision record. |
| Results | One dated artifact: a table of at most 6 rows or one screenshot, from a real run or a dated file in the repo. |
| Run it | One prerequisites line, one code block of at most 10 lines from the repo root, no `git clone`. A longer setup moves to `docs/setup.md`. |
| Checks | The commands CI runs, each with the invariant it protects, then one line on what CI runs. |
| Layout | One level, at most 10 folders a reader would open. |
| Docs | At most 5 links, each saying what is inside. |
| License | One line, last. A fork adds one credit line. No LICENSE file: leave it out and ask him. |

The whole file stays near 120 lines.

## Steps

### 1. Read the repo

- [ ] Read the code, the config and CI, not only the old README. The README describes what the repo does today.
- [ ] Read the diagram scene script for the zone titles, so How it works uses the same names.
- [ ] Note what the old README holds that a stranger does not need: env-var dumps, endpoint lists, runbooks, troubleshooting, changelogs.

### 2. Pick the tier

> **Decision Point**: what stage is the repo at?
> - Design, no code: one-liner, status, What it does, Decisions, Docs, License. No diagram until the architecture is decided.
> - Building, working or in production: the full skeleton.
> - Archived: one-liner, status with the reason, diagram, What it does, License. No Run it.

### 3. Write the skeleton

- [ ] Keep every good line the old README already has. Rewrite only what breaks a rule.
- [ ] Reference material that is still true moves whole to `docs/`, linked from Docs. Nothing true is lost.
- [ ] A course follow-along names and links the course in the status line.

### 4. Check every claim

- [ ] Every number carries its date. Every command was run, or exists verbatim in CI or the task runner.
- [ ] Results come from a real run or a dated file in the repo. Never an invented number.
- [ ] A decision states only a reason the repo records. No reason found, no bullet.
- [ ] One fact, one place: no two numbers for the same thing.
- [ ] Vale is clean: `vale --config ~/helm/.vale.ini --filter='.Name matches "^Rai"' README.md`.

### 5. Cut

- [ ] No badges, emoji, banners, ASCII art, hand-made table of contents, or `---` between sections.
- [ ] No second picture of the system: no ASCII flow, no Mermaid.
- [ ] No Contributing, Author, Credits or Acknowledgments sections, and no praise words.
- [ ] No `~/` paths or vault words (kitchen, grill, helm) in the text.
- [ ] No default credentials in the text: point to `.env.example`.

### 6. Land it

- [ ] SDD repo: the change merges at the G3 gate of [[21-project-init]] Phase C.
- [ ] Any other repo: [[02-task]] from its Review step. It commits on his word.

---

## Connections

- Workflows: [[34-diagrams]] draws the pair this README embeds. [[02-task]] or [[21-project-init]] lands the change.
- Skills: `/media → diagram`, `/git → commit`.
