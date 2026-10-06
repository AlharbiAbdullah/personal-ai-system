---
name: create-skill
description: >
  Skill creation and management framework for Rai.
  USE WHEN the user wants to create a new skill, validate an existing skill,
  update a skill's definition, or review skill structure. Handles naming,
  folder layout, and SKILL.md frontmatter requirements.
---

# CreateSkill

Create, validate, and update Rai skills. Each skill is a folder with
a SKILL.md file and optional resources (scripts, references, assets).

Building or changing a skill follows [[24-changing-rai]]. This skill supplies its naming,
layout and validation rules.

## Naming Rules

- **kebab-case** folder names: `my-skill/`, not `MySkill/` or `my_skill/`
- Top-level folder structure: a skill is either a router (folder with `SKILL.md` + sub-skill `.md` files) or a leaf (folder with `SKILL.md` only). Routers live directly under `~/helm/03-rai/skills/`.
- Sub-skills inside a router are flat `.md` files — no nested subfolders of skills
- The `name:` field in a router's `SKILL.md` matches the folder name exactly
- Sub-skill `name:` fields match their filename stem (e.g. `architecture/adr-writer.md` → `name: adr-writer`)
- Routers MUST NOT contain a sub-skill file with the router's name. `foo/SKILL.md` + `foo/foo.md` is a collision — rename the sub-skill.

## SKILL.md Requirements

Frontmatter (required):
- `name`: Skill name (kebab-case, matches folder name)
- `description`: What it does + **USE WHEN** trigger phrase. The `USE WHEN` pattern is mandatory — Rai uses it to decide when to invoke.

Body (required):
- What the skill does (1-2 sentences)
- Workflows or modes (if multiple)
- Process steps
- Output format
- Examples (3-4 invocations)

Body length: aim for under 150 lines. A skill whose workflow genuinely needs the space is an acceptable exception (news-digest ≈ 1,235). A long procedure can instead split into phase files, the way project-init does (`SKILL.md` ≈ 150 lines plus `phases/`). Every line must earn its place.

## Workflows

### CREATE
Build a new skill from scratch.

1. Gather the skill's purpose, triggers, and workflows
2. Decide shape: top-level leaf, top-level router, or sub-skill inside an existing router
3. For a top-level skill: create the kebab-case folder under `~/helm/03-rai/skills/` with `SKILL.md` inside
4. For a sub-skill: create `<router>/<sub-skill>.md` — no folder
5. Write proper frontmatter (`name:`, `description:` with USE WHEN) and body
6. Add scripts/, references/, assets/ only if needed (top-level skills only)
7. Add the skill to `~/helm/03-rai/skills/MANIFEST.md` under the correct router
8. If it's a sub-skill, update the parent router's `SKILL.md` routing table
9. Validate the result

### VALIDATE
Check an existing skill for correctness.

1. Verify folder naming (kebab-case)
2. Check SKILL.md frontmatter has `name:` (matches folder) and `description:`
3. Check description contains USE WHEN trigger
4. Verify body has: purpose, process, output format, examples
5. For routers: verify no sub-skill file shares the router's name
6. Verify the skill is listed in MANIFEST.md
7. Report issues or confirm valid

### UPDATE
Modify an existing skill.

1. Read current SKILL.md
2. Apply requested changes
3. If name or scope changed, update MANIFEST.md
4. Re-validate after changes

## Examples

- "Create a skill for managing database migrations"
- "Validate the `research` skill"
- "Update the `browser` skill description"
- "Create a skill that generates test data"
