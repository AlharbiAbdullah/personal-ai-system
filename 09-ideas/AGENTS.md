# 09-ideas/ — Ideas Nursery

Where ideas grow or die. Pipeline: Seed → Plant → Tree → Graduated.

## Layout
Flat. All idea files at the root. Kebab-case filenames.
Status tracked in frontmatter, not in folder structure.

## Frontmatter (required)
- `type`: idea
- `status`: seed | plant | tree | graduated
- `domain`: ai | data | business | personal | ...
- `derived_from`: parent ideas (wiki-links)
- `spawned`: ideas or projects this created (wiki-links)
- `created`: YYYY-MM-DD

Matches `12-system/templates/{Seed,Plant,Tree}.md`, which the `/ideas` skills read when
writing or promoting a note.

## Skills
The `/ideas` skill group (`03-rai/skills/ideas/`) drives the pipeline:
- `start-seed` — create a new Seed
- `promote` — advance to next stage (Seed→Plant→Tree)
- `graduate` — Tree → `05-projects/kitchen/{name}/`
- `derive` — find cross-idea connections

Stage-specific process (what happens during Plant research, Tree planning, etc.)
lives inside the `promote` skill.

## Retention
Ideas never die. Graduated ideas stay — they seed future ideas via lineage.
No pruning.

## Relationship to 02-ana/identity/ideas.md
- `09-ideas/` = nursery (all seeds, including rejected/abandoned).
- `02-ana/identity/ideas.md` = top-ideas shortlist (graduated ones committed to pursuit).
