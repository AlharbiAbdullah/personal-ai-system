---
name: brainstorm
description: >
  Panel brainstorm. The six voices work as a team on a thought John
  has: round 1 each explores it alone, round 2 each builds on the others.
  The coordinator collects every idea and every interesting fact or angle
  about the subject. USE WHEN /fusion brainstorm, "brainstorm with everyone",
  or he wants a thought explored wide before deciding anything.
---

# /fusion brainstorm

Divergence first. The goal is the widest useful map of the thought, not an
early answer.

## The ask (`$RUN/ask.md`)

- His thought in his own words, then the one-line question it raises.
- What he already knows or has tried, so the voices do not repeat it.
- Constraints that are real (budget, his stack, local availability). Leave out
  constraints he did not state: they narrow the range too early.
- `--cwd`: the folder the thought is about. Leave it out when there is none:
  the voices get an empty folder. Never his home folder.

## Rounds

- **Round 1:** each voice brings 10 or more distinct ideas, safe to bold, and the
  facts and surprises that make the subject interesting.
- **Between the rounds:** the ledger is every idea once, clustered by theme.
  In `ask-r2.md`, name the coverage gaps: clusters with one idea or none, and
  angles nobody took. Gaps beat a re-read: a voice that has just read 30
  ideas paraphrases them.
- **Round 2:** each voice pushes its assigned ideas further or kills one with
  a reason. It combines ideas, fills the gaps, and names the one idea it
  thinks the panel underrates.

## Synthesis

1. **Every idea, once.** The ledger plus round 2's NEW lines; keep the
   strongest wording. Cluster by theme.
2. **The interesting things:** facts, angles and surprises about the subject,
   each with the voice that raised it.
3. **Where the team converged:** ideas 3 or more voices raised on their own in
   round 1. Round 2 agreement is not convergence: the voices had read each other.
4. **Underrated:** the ideas round 2 named as underrated, each with its reason.
5. **The boldest live options:** ideas only one or two voices pushed, that
   still survive a sanity check.
6. Your own pick of what to explore next, and why.

Keep the full list: he asked for all of it. Use a table or clusters so he can
scan it.

Where it goes next: a design choice goes on at [[30-architecture-decision]]. A
new idea goes to `/ideas → start-seed`, and a project-sized one to [[01-project]].

## Examples

- `/fusion brainstorm a local-first recipe app: what could it become?`
- `/fusion brainstorm ways to use the six-voice panel in my weekly review`
- `/fusion brainstorm ways to automate the weekly review, skip opus`
