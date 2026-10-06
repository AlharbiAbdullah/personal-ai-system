# 05-projects/: Project Management

Three lifecycle stages:
- `kitchen/`: project exists ONLY here. `specs/` (mission, tech-stack, roadmap,
  backlog) + `research/`. No code anywhere yet. The meal being prepared.
- `active/`: project is active. A folder per project holds non-code work only
  (research, meeting notes), never mission, roadmap or architecture.
  Code lives in `~/projects/{project}/` outside helm, and so do its
  mission, roadmap and decisions (the repo's `specs/` and `project_memory/`).
- `completed/`: project done. One folder per project: `retrospective.md` + diagrams/.

See `projects-moc.md` for the current project inventory.

## Project naming
Lowercase with dashes: `my-project-name`. Short, descriptive, no spaces.

## Lifecycle
1. Idea graduates from `09-ideas/` (Tree → Graduated).
2. `/ideas → graduate` scaffolds `kitchen/{name}/specs/` + `research/`; iterate there
   (the kitchen steps of `11-workflows/01-project.md`).
3. When ready: `/project-init` in `~/projects/{name}/` reads the kitchen specs into the
   repo. Everything from init on is `11-workflows/21-project-init.md`. After its G1
   merge, move the kitchen's `research/` worth keeping to `active/{name}/research/`,
   then delete the kitchen folder. `active/{name}/` holds non-code work only.
4. When done: create `completed/{name}/` with retrospective + diagrams. Remove the
   active folder.

## What Claude does
- "graduate X to kitchen" → `/ideas → graduate`: `kitchen/{name}/specs/` + `research/`.
- "start project X" → `11-workflows/01-project.md` for an idea, or `/project-init` in `~/projects/{name}/` for a folder (`11-workflows/21-project-init.md`). `active/{name}/` is created after the repo's G1 merge, for non-code work only (no Brief or Kanban).
- "complete project X" → create `completed/{name}/`, write retrospective, move diagrams.
- No auto-generated Brief.md, Kanban.md, or master board.
