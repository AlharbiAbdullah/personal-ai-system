---
title: "{{title}}"
status: DRAFT
created: "{{date}}"
updated: "{{date}}"
type: prd
---

# {{title}}

This template is a pointer. Pick the template by what the document is for.

| Writing | Use |
|---|---|
| a product you will build | `12-system/templates/sdd/`: `mission.md`, `tech-stack.md`, `roadmap.md`, `backlog.md`. `/ideas → graduate` fills them into `05-projects/kitchen/<name>/specs/`, and `/project-init` carries them into the repo's `specs/`. |
| one feature of an SDD repo | its change folder (`requirements.md`, `plan.md`, `validation.md`), which `mise run change` opens and `/grill` fills |
| a requirements document for someone else (work, a client) | `/writing → prds` for the drafting craft. Save it with that work's other documents, never in `05-projects/kitchen/`, which contains only a product's `specs/` and `research/`. |
| a Rai task record for a substantial multi-step task | freeform, AI-authored, no fixed schema: `03-rai/memory/work/<slug>/PRD.md` — problem, approach, outcome |
