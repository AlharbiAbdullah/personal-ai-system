---
name: plan
description: >
  Panel plan. Each voice drafts a complete plan, then names the defects in
  the merged steps; the coordinator builds ONE plan. USE WHEN /fusion
  plan, or John wants a plan built by the whole panel. In an SDD repo the
  spec comes from /grill; this plan feeds it, never replaces it.
---

# /fusion plan

## The ask (`$RUN/ask.md`)

- The goal in one sentence and what done looks like.
- The constraints and decisions already made, quoted, so no voice reopens them.
- The current state: what exists, where (files the voices can read in `--cwd`).
- What the plan is for: a build, a migration, a purchase, a week, a study.

## Rounds

- **Round 1:** each voice drafts a complete plan: goal, ordered steps (each
  with its output and how to check it), risks, what it would cut.
- **Between the rounds:** the ledger is every step and risk across the
  plans, merged, in dependency order. No recommended plan in it.
- **Round 2:** each voice names defects in the steps (gaps, wrong order,
  missed risks, wasted steps) and the steps missing. It does not write its
  plan again.

## Synthesis

1. **One plan.** Start from one sound dependency spine in the ledger, not a
   union of six plans. Take a change from round 2 only where it names the
   defect it fixes. Every step has its output and its check.
2. **Risks:** merged and deduped, most severe first, each with its mitigation.
3. **Cuts:** what 2 or more voices said to drop, and whether you agree.
4. **Open splits:** where the voices still disagreed, the options and your call.

Where the plan lands: show it to him. Write it to a file only when he asks, or
when the caller names one (in an SDD repo, `/grill` turns it into the spec).
The plan feeds [[02-task]] step 2, Define, or [[01-project]] for a new project.

## Examples

- `/fusion plan migrate the news pipeline to the hub`
- `/fusion plan a 6-week Rust learning track, just gemini and the pi voices`
- `/fusion plan the migration of the notes app to a new sync engine`
