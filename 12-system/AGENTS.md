# 12-system/ — Templates, References, Tools

## Purpose

Reusable system components for the vault. Templates for new notes, reference docs (snapshots), the manual pointer map, diagrams, media, harness docs.

## Subfolders

| Folder | Contents |
|--------|----------|
| `templates/` | Note templates (see inventory below) |
| `diagrams/` | Diagram source files (Obsidian Excalidraw target) |
| `media/` | Embedded images, audio, etc. (Obsidian attachment target) |
| `manual/` | `README.md` only: a pointer map from each vault topic to the live doc that owns it |

## Templates Inventory

**CRITICAL RULE: Always use existing templates. Never invent note structures.**

Before creating any note:
1. Check `12-system/templates/` for the appropriate template.
2. Read the template to understand the correct structure.
3. Use that exact structure (adapting Templater syntax to actual values).

| Template | Purpose | Destination |
|----------|---------|-------------|
| **Topic Note** | Comprehensive topic coverage with sections + toolbox | `10-knowledge/` |
| **Insight Note** | Emergent connections between notes | `10-knowledge/` |
| **MOC** | Map of content (topic hub) | `10-knowledge/_mocs/` |
| **Seed** | Raw idea capture, minimal effort | `09-ideas/` |
| **Plant** | Researched idea with Q&A and market validation | `09-ideas/` |
| **Tree** | Planned idea with requirements and schedule | `09-ideas/` |
| **Capture** | Quick inbox items | `01-inbox/` |
| **PRD** | Pointer that names the template by purpose: `sdd/` for a product, `/writing → prds` for someone else's requirements document. A task's post-hoc summary is its distill record in `rai-semantic` (Memory v3), not a freeform file from this template. | none: read it, then use the template it names; never `05-projects/kitchen/` |
| **SDD specs** (folder `sdd/`) | Product spec files for a code repo: mission, tech-stack, roadmap, capability, requirements, plan, validation, backlog, decision (ADR), lesson. Placeholders are `{UPPER_SNAKE}` tokens that the renderer fills | a repo's `specs/` and `project_memory/`, rendered by `/project-init`; `mission`, `tech-stack`, `roadmap` and `backlog` also fill `05-projects/kitchen/{name}/specs/` through `/ideas → graduate` |
| **Project Retrospective** | Completed project reflection | `05-projects/completed/{name}/` |
| **Learning** | Courses, books, tutorials | `06-learning/` or `07-reading/` |
| **Soul Note** | Personal writing: beliefs, worldview, reflections | `02-ana/soul/` |
| **Quote** | Captured quote | `02-ana/quotes/` |
| **Personal Chapter** | Long-form personal narrative | `02-ana/soul/` |

## Rules

- **Templates are read-only.** Copy via Templater, never modify originals during a normal session. Template changes are deliberate edits, made consciously.
- **References are snapshots.** When you find drift between a reference doc and reality, update the reference doc — but flag it as "snapshot from {date}" so future sessions know it's not the live source of truth.
- **Live source of truth lives in AGENTS.md files.** When references contradict AGENTS.md, AGENTS.md wins.

## What Claude should do

When creating a new note in `10-knowledge/`, `09-ideas/`, etc. — check `templates/` first. Use the appropriate template structure. Never invent.

When asked "where does X live?" or "what's the current state of Y?" about Rai, check `03-rai/ARCHITECTURE.md` and `03-rai/AGENTS.md` first.

Do not modify templates without an explicit user request. They are infrastructure.
