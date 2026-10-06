# Project Workflow

**Use when:** a product goes from an idea to done, vault side. Starting a new project or building an idea from scratch. Planning a project before its repo exists: graduating the idea and drafting its specs (the mission, the stack, the roadmap, the PRD or spec). Handing it to a repo, and closing a finished project or work engagement with its retrospective.
**Not for:** 21 project-init, for everything from `/project-init` on: init, features, replans, launches, releases. 02 task, for one change in a repo without `.project.toml`. 30 architecture decision, for a big stack choice itself, which lands back here as a standing rule. 32 work engagement, for delivering a work engagement, whose retrospective closes here.
**Done when:** the project is closed: its retrospective sits in `05-projects/completed/<name>/`, the MOC marks it done, and `active/<name>/` is gone. The kitchen stage alone is done when its exit check passes and `/project-init` runs on the code folder.

The vault side of a project: the idea, the kitchen, the hand-off to a repo, then back to the vault when it is done. Everything from `/project-init` on, including every feature, replan, launch and release, runs in [[21-project-init]].

```d2
direction: down

ideas: "09-ideas/" {
  seed: "Seed"
  plant: "Plant"
  tree: "Tree"
  seed -> plant -> tree: "/ideas → promote"
}

kitchen: "05-projects/kitchen/<name>/\nspecs/: mission, tech-stack,\nroadmap, backlog/\nresearch/ (vault only)"
decision: "30 architecture decision\na big stack choice"
repo: "~/projects/<name>/\n/project-init, then G1\nspecs/ + gates + sdd skill"
loop: "repo loop\nfeature, replan, launch, release\n(21-project-init)"
active: "05-projects/active/<name>/\nnon-code work only:\nresearch, meeting notes"
completed: "05-projects/completed/<name>/\nretrospective + diagrams"

ideas.tree -> kitchen: "/ideas → graduate"
kitchen -> decision: "big choice" {style.stroke-dash: 3}
decision -> kitchen: "standing rule S-n" {style.stroke-dash: 3}
kitchen -> repo: "talk source 1"
ideas.tree -> repo: "small idea: no kitchen" {style.stroke-dash: 3}
repo -> loop
kitchen -> active: "research/ moves after G1" {style.stroke-dash: 3}
loop -> completed: "project done"
```

---

## Steps

### 1. Crystallize the idea

- [ ] Capture the spark as a Seed: `/ideas → start-seed`.
- [ ] Grow it to Plant, then Tree: `/ideas → promote`. Clarify the problem, not the solution.

> **Decision Point**: is this worth building?
> - Yes: step 2.
> - Not yet: leave it as a Tree and revisit it at the next weekly review.
> - No: leave the idea at its stage. Ideas never die; its lineage carries forward.

### 2. Kitchen or straight to init

The kitchen drafts a project's constitution in the vault before a repo exists. Its `specs/` has the shape of a repo's `specs/`, so `/project-init` reads it as the first source of its talk. The init talk copies and cleans it rather than asking again.

> **Decision Point**: kitchen or straight to init?
> - The product needs research, architecture or a long think before code: the kitchen, steps 3 to 8.
> - The idea is small, or the code already exists: skip to step 9. The init talk builds the constitution from the idea, the repo and his answers.

### 3. Open the kitchen

- [ ] The idea is a Tree in `09-ideas/`. `/ideas → graduate` scaffolds the tree below from the templates and fills what the Tree already says.

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

### 4. Mission first

- [ ] Fill `specs/mission.md`: the one-liner, who it is for, the problem, why now, scope in and out, the success signal.

> **Decision Point**: is the problem worth solving?
> - Yes: continue.
> - Unclear: research the problem with `/research → web-research` and keep the notes in `research/`. Decide again after that. `/ideas → promote` only moves an idea forward, so the idea keeps its `graduated` status.
> - No: stop and keep the learning. The idea stays in `09-ideas/` at its stage.

- [ ] Unclear: the research can go to the `researcher` agent. Inputs: the problem from `mission.md` and the questions still open. Returns: cited findings, each with a date and a confidence level. It cannot run commands or edit files, so Rai writes the notes into `research/`.
- [ ] Rai re-checks every load-bearing claim at its source before the decision.

### 5. Tech stack

- [ ] Fill `specs/tech-stack.md`: runtime, tooling, the distribution as one word (`pypi`, `git`, `service` or `none`), standing rules, never-use.
- [ ] Test the big choices with `/architecture → solution-architect`, and with `/architecture → data-architect` when the data layer matters.
- [ ] Hand the options to the `architect` agent when a choice is open. Inputs: `mission.md` and the constraint behind the choice. Returns: 2 or 3 options with their trade-offs, one marked Recommended. It writes nothing. John picks, and Rai re-checks the load-bearing claims.
- [ ] A choice every later feature must respect becomes a standing rule `S-n`, and the reasoning goes in `research/`. A big one, such as a database, a platform or a topology, runs [[30-architecture-decision]] from step 1 first. Its record lands here as that standing rule.
- [ ] A product for a sealed network records the air-gap rules as standing rules. Each is a line in `specs/tech-stack.md`: exact pins, no runtime network calls, runners that verify and never install, and the rebundle matrix. The method is [[29-air-gapped-delivery]] steps 0 to 2.

### 6. Roadmap

- [ ] Phases of feature-sized items, `- [ ] <slug>: <title>`, one feat change each. Slugs are permanent. Graduation can leave `## Phase 2: next` empty, with the Gate `- Phase 2: what comes after Phase 1?`. Fill it here, or leave the Gate for the init talk, which needs at least 2 phases of items.
- [ ] Phase 1 is concrete. Later ideas go under `## Later`, or as backlog files.

### 7. Open questions are roadmap Gates

- [ ] A question that blocks a later phase is a line under `## Gates` in `specs/roadmap.md`: `- Phase <n>: <question>`. It gets answered when that phase comes up, in a replan.
- [ ] A gap in the mission or the tech stack stays a `[NEEDS CLARIFICATION: <question>]` marker. The init talk asks it, and the G1 merge refuses while one remains. The roadmap never takes a marker.
- [ ] A question that doesn't block a phase yet, or blocks only an item under `## Later`, is a line in `research/README.md`.
- [ ] Only a question that blocks Phase 1 holds the kitchen open.

### 8. Exit check

Run in `kitchen/<name>/`:

```sh
grep -rnE '\{[A-Z_]+\}' specs/          # nothing: every template field is filled or marked
grep -rn '\[\[' specs/                  # nothing: links and sources belong in research/
sed -n '/^## Gates/,$p' specs/roadmap.md   # no line names Phase 1
```

> **Decision Point**: a Gate blocks Phase 1?
> - Answer it now (research, a prototype, a decision), then run the check again.
> - Or reorder, so that Phase 1 is work that does not depend on the answer.

### 9. Hand off to the repo

- [ ] `mkdir ~/projects/<name>`, `cd` into it and run `/project-init`. From here, follow [[21-project-init]] Phase B. Never copy the kitchen files by hand: the talk reads, copies and cleans them.
- [ ] An older kitchen with `PRD.md`, `ROADMAP.md` or `BUILD-LOG.md` needs no conversion. The init talk reads it as its second source.
- [ ] The repo's own rulebook (lanes, gates, what each change type updates) is its `specs/README.md`, rendered from the process template `03-rai/skills/project-init/templates/specs-README.md`.
- [ ] After the G1 merge, run the vault steps at the end of [[21-project-init]] Phase B. They keep the research worth keeping and delete the kitchen folder, so the repo's `specs/` is the one copy of the plan.
- [ ] Every feature, replan, launch and release now runs in [[21-project-init]]. The project comes back here only to close.

### 10. Close

- [ ] Write `05-projects/completed/<name>/retrospective.md` from `12-system/templates/Project Retrospective.md`, with the diagrams alongside.
- [ ] Mark the project done in `05-projects/projects-moc.md`.
- [ ] Remove `05-projects/active/<name>/`.
- [ ] Run `/map-updater` if the project produced reusable vault knowledge.

### 11. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Init, the feature loop, replan, launch, release: [[21-project-init]]
- A big stack choice: [[30-architecture-decision]]. A sealed target's rules: [[29-air-gapped-delivery]].
- Closes here: a finished product from [[21-project-init]], and a work engagement from [[32-work-engagement]].
- Agents: the `researcher` agent (step 4), the `architect` agent (step 5).
- Repo process template: `03-rai/skills/project-init/templates/specs-README.md`
- Kitchen templates: `12-system/templates/sdd/`
- Folder rules: `05-projects/AGENTS.md`
- Idea pipeline: the `/ideas` skill group
