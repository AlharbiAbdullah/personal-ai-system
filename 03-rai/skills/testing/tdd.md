---
name: tdd
description: >
  Test-first build: red, green, refactor. A pointer, so there is one TDD text: the SDD compile
  loop. USE WHEN building new behaviour test-first, in an SDD repo or anywhere else.
---

# TDD

The canonical TDD text is the repo's `.claude/skills/sdd/compile.md`. Its template, for a repo without one, is [`project-init/templates/skills/sdd/compile.md`](../project-init/templates/skills/sdd/compile.md). Read that file and follow it.

- **In an SDD repo** (`.project.toml` at the root): follow the repo's copy as written. `/compile` does this.
- **Outside an SDD repo:** skip the spec-ID steps and the `mise run tdd` steps. See red and green with the project's own test command. Skip too every step that writes an SDD file (`specs/`, `project_memory/`, `mise run backlog`). Those files exist only in an SDD repo, so a lesson or a new idea goes in the report. The rest holds: red for the right reason, minimal code, refactor with the tests unedited, commit on green.
