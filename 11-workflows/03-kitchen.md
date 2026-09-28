# Kitchen Workflow

**Triggered by:** "plan {project}" / "write the PRD/SPEC for {project}" / "graduate this idea" / "draft the specs for {project}"
**Cadence:** Per project, before init.
**Done when:** `kitchen/<name>/specs/` passes the exit check below, and `/project-init` runs on the code folder ([[21-project-init]] Phase B).

The kitchen drafts a project's constitution in the vault before a repo exists. Its `specs/` has the shape of a repo's `specs/`, so `/project-init` reads it as the first source of its talk. The init talk copies and cleans it rather than asking again.

```text
kitchen/<name>/
├── specs/
│   ├── mission.md       one-liner, who it is for, problem, why now, scope in and out, success
│   ├── tech-stack.md    runtime, tooling, distribution (one word), standing rules S-n, never use
│   ├── roadmap.md       phases of "- [ ] slug: title", Later, Gates (questions that block a phase)
│   └── backlog/         one file per idea that is in no phase and not under Later
└── research/            vault only: README.md (origin link, sources, risks) + notes; never copied into a repo
```

The templates are `12-system/templates/sdd/{mission,tech-stack,roadmap,backlog}.md`.

---

## Steps

### Entry

- [ ] The idea is a Tree in `09-ideas/`. `/ideas → graduate` scaffolds the tree above from the templates and fills what the Tree already says.

### Mission first

- [ ] Fill `specs/mission.md`: the one-liner, who it is for, the problem, why now, scope in and out, the success signal.

> **Decision Point**: is the problem worth solving?
> - Yes: continue.
> - Unclear: research the problem with `/research` and keep the notes in `research/`. Decide again after that. `/ideas → promote` only moves an idea forward, so the idea keeps its `graduated` status.
> - No: stop and keep the learning. The idea stays in `09-ideas/` at its stage.

### Tech stack

- [ ] Fill `specs/tech-stack.md`: runtime, tooling, the distribution as one word (`pypi`, `git`, `service` or `none`), standing rules, never-use.
- [ ] Test the big choices with `/architecture → solution-architect`, and with `/architecture → data-architect` when the data layer matters. A choice every later feature must respect becomes a standing rule `S-n`. The reasoning goes in `research/`.

### Roadmap

- [ ] Phases of feature-sized items, `- [ ] <slug>: <title>`, one feat change each. Slugs are permanent. Graduation can leave `## Phase 2: next` empty, with the Gate `- Phase 2: what comes after Phase 1?`. Fill it here, or leave the Gate for the init talk, which needs at least 2 phases of items.
- [ ] Phase 1 is concrete. Later ideas go under `## Later`, or as backlog files.

### Open questions are roadmap Gates

- [ ] A question that blocks a later phase is a line under `## Gates` in `specs/roadmap.md`: `- Phase <n>: <question>`. It gets answered when that phase comes up, in a replan.
- [ ] A gap in the mission or the tech stack stays a `[NEEDS CLARIFICATION: <question>]` marker. The init talk asks it, and the G1 merge refuses while one remains. The roadmap never takes a marker.
- [ ] A question that doesn't block a phase yet, or blocks only an item under `## Later`, is a line in `research/README.md`.
- [ ] Only a question that blocks Phase 1 holds the kitchen open.

### Exit check

Run in `kitchen/<name>/`:

```sh
grep -rnE '\{[A-Z_]+\}' specs/          # nothing: every template field is filled or marked
grep -rn '\[\[' specs/                  # nothing: links and sources belong in research/
sed -n '/^## Gates/,$p' specs/roadmap.md   # no line names Phase 1
```

> **Decision Point**: a Gate blocks Phase 1?
> - Answer it now (research, a prototype, a decision), then run the check again.
> - Or reorder, so that Phase 1 is work that does not depend on the answer.

### Hand off

- [ ] `mkdir ~/projects/<name>`, `cd` into it and run `/project-init`. From here, follow [[21-project-init]] Phase B. Never copy the kitchen files by hand: the talk reads, copies and cleans them.
- [ ] After the G1 merge, run the vault steps at the end of [[21-project-init]] Phase B. They keep the research worth keeping and delete the kitchen folder, so the repo's `specs/` is the one copy.
- [ ] Vault edits stay local for the coordinator.

An older kitchen with `PRD.md`, `ROADMAP.md` or `BUILD-LOG.md` needs no conversion. The init talk reads it as its second source.

---

## Connections

- Init and the build loop: [[21-project-init]]
- The whole project, vault side: [[01-project]]
- Folder rules: `05-projects/AGENTS.md`
- Templates: `12-system/templates/sdd/`
