---
name: ideas
description: >
  Ideas pipeline router. USE WHEN the user wants to capture a new idea, advance
  one through the pipeline (Seed→Plant→Tree), graduate a Tree to a project, or
  find cross-idea connections. All sub-skills operate on `~/helm/09-ideas/`.
---

# Ideas

The ideas nursery. Pipeline: Seed → Plant → Tree → Graduated.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Capture a raw idea as Seed | start-seed | `start-seed.md` |
| Advance an idea to the next stage | promote | `promote.md` |
| Graduate a Tree into `05-projects/kitchen/<name>/`: `specs/` (mission, tech-stack, roadmap, backlog) + `research/`, the draft `/project-init` reads | graduate | `graduate.md` |
| Find cross-idea connections, propose hybrids/spin-offs | derive | `derive.md` |

## How to use

1. Pick the sub-skill by stage / action.
2. `Read` the file in this directory.
3. Follow that file's instructions.
