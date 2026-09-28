# {NAME}
Why and scope: `specs/mission.md`. Stack and standing rules: `specs/tech-stack.md`. Next work: `specs/roadmap.md`.
The process (lanes, formats, gates, Definition of Done): `specs/README.md`.

## Commands
All commands are mise tasks (`mise tasks ls`). Once per machine: `mise install`.
Before you call anything done: `mise run verify`. CI runs verify plus prove-red, and merging adds the
Definition of Done (`specs/README.md#gates`). Run the app: `{START_EXAMPLE}`.

## How work happens
1. Every change starts with `/sdd "<what you want>"` (no skills in your agent? read `.claude/skills/sdd/SKILL.md`). It picks the lane.
2. approve, merge, abandon and release are human gates. Never run them; stop and ask.
3. No production code without a failing test tagged with its scenario id (`{TEST_TAG_EXAMPLE}`). Commit on green.
4. A behaviour change edits its scenario in `specs/capabilities/` in the same commit as its test and code.
5. Out-of-scope ideas: `mise run backlog -- <topic>`. Never edit `specs/roadmap.md` or `specs/mission.md` outside a `plan/` branch.
6. Merge shows a human the trunk diff to read (`## Trunk` in `specs/tech-stack.md`); the rest is skimmed against the proof `mise run proof` captures.
7. A merged roadmap item is launched with `/sdd launch <slug>`: a review of the whole feature, then its flag comes off.

## Memory
- Something surprised you: append to `project_memory/lessons.md` now.
- A choice future changes must respect: one file in `project_memory/decisions/`.
- Secrets: `op://` pointers only, never values.
