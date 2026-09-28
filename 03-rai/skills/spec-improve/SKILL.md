---
name: spec-improve
description: >
  One improvement pass over a draft spec before approval: the open change folder in a repo
  with .project.toml, or .agent/plan.md elsewhere. Critiques it against Ousterhout's A
  Philosophy of Software Design and the spec lint, rewrites it, and scores the pass 1-10. At
  3 or less it logs `skip`, and a later pass that sees `skip` makes no edits. Every pass stops
  at approval and never starts implementation. USE WHEN the user types /spec-improve or asks
  to improve or tighten a spec or plan before approving it. Safe to queue repeatedly.
---

# Spec Improve

One critique-and-rewrite pass per call. The score and `skip` protocol make queueing safe: once a pass finds nothing structural, later passes change nothing. Every pass ends at the approval gate. Building is John's call, never this skill's.

**Single-agent mandate:** run inline. Never use the Agent or Workflow tools.

## 0. Target and skip gate (check first)

- **SDD repo** (`.project.toml` at the root): the target is the open change folder `specs/changes/<date>-<slug>/`, plus its scenario diff from `mise run status -- --change`.
  - Only a `status: draft` folder is edited. Approved: make no edits, say the spec is approved and next is `/compile`, stop.
  - A fast lane has no change folder, so there is nothing to improve.
- **Elsewhere:** the target is the plan `/grill` named: `.agent/plan.md`, or `.agent/plan-<slug>.md` when the user passes a slug. The decisions file its header names is read, never edited. No plan: point to `/grill` and stop.
- **Skip gate.** Read `.agent/spec-improve.log`. The target key is the change folder path, or the plan path plus its `# Plan:` title. A `skip` line for this key means: make **no edits**, say "spec locked, next is approval", give the hand-off in section 4, stop.

## 1. Code-grounded critique

Read the target AND the code paths it names. An improvement must rest on real code, not on spec prose.

**Ousterhout checklist:**
- **Deep modules:** does each proposed interface hide real complexity, or is it a thin wrapper?
- **Information hiding:** do steps leak sequencing or policy into callers?
- **Change amplification:** does one conceptual change force edits in more than one place?
- **Cognitive load:** can a newcomer hold each group in their head?
- **Pull complexity downward:** does the module absorb the difficulty, instead of its users?
- **Define errors out of existence:** can a failure mode be made impossible instead of handled?
- **General over special-case:** are special cases multiplying where one mechanism would do?

**Spec lint:**
- SDD: the checks in section 5 of `.claude/skills/sdd/talk.md`, and the formats and size caps in `specs/README.md#formats`.
- Elsewhere: the plan rules in [section 2.5 of `grill/SKILL.md`](../grill/SKILL.md#25-write-the-plan-file).

## 2. Rewrite

Apply the structural fixes to the target, keeping its format.
- Never reopen a settled decision: `## Decisions` in `requirements.md`, or the decisions file. Only John reopens one, so raise it as a question.
- Never rename complexity and call it an improvement.
- SDD: edit only the change folder and the scenarios in `specs/capabilities/` that this change touches. Size caps hold: split or cut, never raise one.
- Elsewhere: tasks stay newcomer-executable and paths stay concrete.

## 3. Score and log (every pass)

Say `Improvement score: N/10`: the value THIS pass added. Append one line to `.agent/spec-improve.log`, creating it if needed. By the rule in [grill 2.1](../grill/SKILL.md#21-stage-check) the log is scratch. In a repo that already tracks `.agent/` files, such as helm, it is a record:
- **N of 4 or more:** `<date> | <target key> | pass K | N/10 | <one-line summary>`
- **N of 3 or less:** `<date> | <target key> | pass K | N/10 | skip`

K is the count of earlier lines for this key, plus one. Score honestly. Cosmetic edits are not structural value. Finding nothing structural IS the 3-or-less case.

## 4. Stop at approval

- **SDD:** run `mise run status`. It must still say `ready for approve`; fix whatever it lists. Say: "run `! mise run approve`, then `/clear` before `/compile`."
- **Elsewhere:** say: "plan at `<path>`. Say go, or run `/compile`." For a slugged plan, the command is `/compile <slug>`.

Then stop. Never read or run `/compile` from here, not even after a `skip`. When `/grill` ran this pass, its step 6 gives the hand-off in place of this one, and it stops at the same gate.

## Examples

- `/spec-improve`, queued 3 times after `/grill`
- `/spec-improve focus on the error-handling groups`
