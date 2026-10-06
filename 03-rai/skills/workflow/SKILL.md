---
name: workflow
description: >
  John's way of doing a kind of work: numbered workflows in ~/helm/11-workflows/.
  USE WHEN the work is one of these kinds, asked for or not. Debugging, code review,
  shipping, a project or task, a data pipeline or platform, air-gapped delivery, an
  architecture decision, an AI build, a work engagement or meeting. An audit, an
  incident on a machine, a machine change, changing Rai, a learning stage, a
  purchase, a research write-up, Arabic writing, the weekly review, money days. Plain
  /workflow prints the menu. Reads the matching workflow; Rai follows it and names it.
---

# Workflow

The router for `~/helm/11-workflows/`. A workflow is John's way of doing one kind of work. The definition, the conventions and the menu live in `~/helm/11-workflows/AGENTS.md`. These are his workflows, not Claude Code's Workflow-tool scripts.

## How to use

1. **Plain `/workflow`:** print the menu, the tables under `## The workflows` in `11-workflows/AGENTS.md`, and stop.
2. **Match by kind of work.** Read the headers live, never from a copy:
   ```sh
   grep -H -E '^\*\*(Use when|Not for):\*\*' ~/helm/11-workflows/[0-9]*.md
   ```
3. **Read the whole workflow file**, then say which one you follow: "Following 04 debugging."
4. **Follow it step by step.** Run the skills and agents its steps name. A hand-off goes to the named workflow and step.
5. **A step that does not fit the moment** gets a proposed adaptation, never a silent skip.
6. **Two workflows fit:** ask with 2 or 3 options, one marked (Recommended).

## Boundaries that trip

- Checking a repo against the project-init standard is 21. Auditing a system, the vault, a machine or an architecture is 23.
- An idea with no folder yet is 01. A folder or repo in hand is 21.
- A release is 06. In a repo with `.project.toml`, 06 hands the version, the changelog and the tag to 21 Phase E.
- A PRD for work or a client is `/writing → prds`. A decision paper for leadership is 30.
- A bug in code is 04. Something broken on a machine is 25. The news run is 10. A sanity alarm is 17.
- Buying something is 26. Purchase research lands in its shopping plan, not in `10-knowledge/`.
- A learning build keeps the Socratic rule in `/learning`, even when the work looks like debugging.

## Workflow and skill

- A skill is a capability. A workflow is his way of doing a kind of work, and it names the skills and agents its steps use.
- A workflow never pastes a skill's content. It names the skill at the step.

## Vault edits

Follow the commit rule in `11-workflows/AGENTS.md`, under Conventions.

## Cross-references

- The workflows, their rules and the menu: `~/helm/11-workflows/AGENTS.md`
- Reference checks: `/rai → sanity`, subsystem `Workflows` (FLOW-1 to FLOW-7)
