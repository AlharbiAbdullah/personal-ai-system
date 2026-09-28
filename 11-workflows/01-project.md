# Project Workflow

**Triggered by:** "new project" / "build {idea} from scratch" / "start the {idea} project"
**Cadence:** Per project.
**Done when:** the repo passed its G1 merge. At the end: a retrospective in `completed/{name}/`, the active folder removed, the MOC updated.

The vault side of a project: from the idea to the repo, then back to the vault when it is done. Everything from `/project-init` on, including every feature, replan and release, runs in [[21-project-init]].

```d2
direction: down

ideas: "09-ideas/" {
  seed: "Seed"
  plant: "Plant"
  tree: "Tree"
  seed -> plant -> tree: "/ideas → promote"
}

kitchen: "05-projects/kitchen/<name>/\nspecs/: mission, tech-stack,\nroadmap, backlog/\nresearch/ (vault only)"
repo: "~/projects/<name>/\n/project-init, then G1\nspecs/ + gates + sdd skill"
loop: "repo loop\nfeature, replan, release\n(21-project-init)"
active: "05-projects/active/<name>/\nnon-code work only:\nresearch, meeting notes"
completed: "05-projects/completed/<name>/\nretrospective + diagrams"

ideas.tree -> kitchen: "/ideas → graduate"
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

### 2. Kitchen (optional)

- [ ] `/ideas → graduate` scaffolds `kitchen/<name>/specs/` and `research/`.
- [ ] Work it with [[03-kitchen]]. Skip the kitchen for a small idea or existing code: the init talk asks what it needs.

### 3. Init and build

- [ ] Follow [[21-project-init]] from Phase B: `/project-init`, the G1 merge, the feature loop, replans and releases.
- [ ] The repo's own rulebook (lanes, gates, what each change type updates) is its `specs/README.md`, rendered from the process template `03-rai/skills/project-init/templates/specs-README.md`.
- [ ] After G1, the vault holds no second copy of the plan. The kitchen folder is deleted, and `active/<name>/` keeps non-code work only.

### 4. Close

- [ ] Write `05-projects/completed/<name>/retrospective.md` from `12-system/templates/Project Retrospective.md`, with the diagrams alongside.
- [ ] Mark the project done in `05-projects/projects-moc.md`.
- [ ] Remove `05-projects/active/<name>/`.
- [ ] Run `/map-updater` if the project produced reusable vault knowledge.
- [ ] Vault edits stay local for the coordinator.

---

## Connections

- Init, the feature loop, replan, release: [[21-project-init]]
- Kitchen: [[03-kitchen]]
- Repo process template: `03-rai/skills/project-init/templates/specs-README.md`
- Folder rules: `05-projects/AGENTS.md`
- Idea pipeline: the `/ideas` skill group
