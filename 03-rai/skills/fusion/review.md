---
name: review
description: >
  Panel review. Two targets: finished pipeline work on a branch (the external
  adversarial review /compile runs after validate), or anything John asks
  to have reviewed: code, a design, a plan, a document, prose or a
  translation. Every finding is verified, then fixed, logged or dismissed.
  USE WHEN /fusion review, /compile's review step, or an adversarial or
  external review is asked for.
---

# /fusion review

Do not trust your own validation. Models that did not write the work review
it, and you verify each finding before acting on it.

**Pipeline:** `/grill` → `/spec-improve` → approval → `/compile` → **`/fusion review`**.
In an SDD repo, `/compile` runs it after validate's lenses and before the merge preview.

## 0. Pick the target

- **Pipeline work** (a branch built by `/compile` or a plan): steps 1 to 5.
- **On request** (a file, a design, a doc, prose, a translation): skip the
  stage check. The ask is the target, the source it must match (if any) and
  what John wants judged. English prose uses
  `$P new review --prelude review-prose --cwd <dir>`, Arabic prose and
  translations into Arabic `--prelude review-prose-ar`; code uses the default.

## 1. Stage check (pipeline work)

- **SDD repo** (`.project.toml` at the root): `mise run status` shows no group
  left. If groups are open, confirm John wants a mid-flight review.
- **Elsewhere:** every box in the plan `/grill` named (`.agent/plan.md` or
  `.agent/plan-<slug>.md`) is ticked. If not, confirm the same way.

## 2. The ask (`$RUN/ask.md`)

`<default>` is `default_branch` from `.project.toml`; without it, take
`git symbolic-ref --short refs/remotes/origin/HEAD` minus `origin/`, else `main`.

- **SDD repo:** the change folder `specs/changes/<date>-<slug>/`: its
  `requirements.md`, `plan.md` and `validation.md`. A fast lane has no folder,
  so use the commit bodies from `git log <default>..HEAD`. Add the capability
  diff (`mise run status -- --change`), the branch diff
  (`git diff <default>...HEAD`) and the full text of every new test file.
- **Elsewhere:** the plan file and the decisions file its header names, in
  full; `git diff <default>...HEAD`, plus `git diff` and `git diff --staged`
  for uncommitted work; the full contents of new untracked files. Outside a
  git repo, the full text of every file the plan's `Files:` lines name.
- **On request:** the target in full, the source it must match, and the
  question.

The voices run in the repo (`--cwd <repo root>`), so they can read the code
around each hunk.

## 3. Run it

Follow the run in `SKILL.md`. In round 1 each voice reviews alone.

Between the rounds: run `$P cites $RUN 1`, read the cited code for every
critical and major finding, and run the repo's quick tests when they take
minutes. Each result goes under FACTS ESTABLISHED in `ask-r2.md`, with the
commit it ran on. The ledger is the finding list, one item per defect, with
its severity in the claim; critical and major findings are `open!`. A finding
the facts already settled is `verified: <how>` or `dropped: <why>`.

In round 2 each voice checks its assigned findings: real or not, severity
right or not, with evidence. It adds what all missed.

## 4. Merge, dedupe, verify: the panel is advisory

The ledger is the finding list; add each round-2 NEW line to it. The same
defect from 2 or more voices is ONE finding. Record who raised it on its own in
round 1, and who disputed it or added evidence in round 2. A round-2 line with
no evidence counts for nothing. A dispute that would remove a finding gets the
same check as the finding. Agreement is a confidence signal, not
proof: a lone finding can be real, and one every voice agreed on can be false.
Verify each finding in the
code yourself, then give it one disposition:

- **SDD repo:** one of the outcomes in "Every finding gets one outcome" of
  `.claude/skills/sdd/validate.md`. A false positive is its Dismissed outcome.
- **Elsewhere:**
  - Real: fix it inline and re-run the group's `Verify:`.
  - False positive: the reason goes in the report.
  - Real but out of scope: a follow-up for John, never fixed silently.
- **On request:** report only. Fix what he asks you to fix.

## 5. Report

Findings table: L-number · severity · file:line · raised by · disputed by ·
finding · disposition (fixed / backlog / false positive / follow-up). Name any
voice that failed to return. The table goes in `$RUN/synthesis.md`; `panel.sh
check` confirms every ledger item has its row.

The durable record is the repo: the commits, their bodies and the backlog
items. In an SDD repo the squash merge deletes the branch, so a dismissal is a
`Dismissed:` line, which merge copies into the squash body. Nothing the review
must keep goes in `.agent/`.

- **Run by `/compile`:** stop at the report. `/compile` runs validate's Close once, after it.
- **Run on its own in an SDD repo:** finish with validate's Close in
  `.claude/skills/sdd/validate.md`: the lesson check, `mise run status -- --merge`,
  then its hand-over line.
- **Elsewhere:** the work goes on at [[02-task]] step 6, Merge.
- **On request:** a diff before merge goes on at [[05-code-review]] step 7, Merge.
  Any other target goes back to the work that asked for the review.

## Examples

- `/fusion review` after validate's lenses: the full panel, two rounds.
- `/fusion review mid-flight: G1 and G2 only`
- `/fusion review 04-work/... the Arabic translation against the English master` (needs his go: work content)
- `/fusion review this design doc, just gemini and opus`
