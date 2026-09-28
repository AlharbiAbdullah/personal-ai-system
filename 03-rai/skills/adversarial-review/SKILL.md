---
name: adversarial-review
description: >
  External adversarial review of finished pipeline work by a PANEL of DIFFERENT frontier
  models (GPT-5.6 Sol, Grok 4.5, GLM 5.2, DeepSeek V4 Pro, all at high reasoning effort) via
  the ask-model OpenRouter script. Each model reviews independently; you merge and dedupe
  their findings. Hunts subtle state defects, edge-case crashes, pattern drift and spec
  violations; findings are verified, then fixed inline or sent to the backlog. In an SDD repo
  /compile runs it after validate's lenses. USE WHEN the user types /adversarial-review or
  asks for an adversarial/external review of pipeline work. Never spawns subagents.
---

# Adversarial Review

Do not trust your own validation. Models that did not write the code review the diff against the spec. You verify each finding in the actual code and act on what is real.

**Pipeline:** `/grill` → `/spec-improve` → approval → `/compile` → **`/adversarial-review`**. In an SDD repo, `/compile` runs it after validate's lenses and before the merge preview.

**Single-agent mandate: run inline. Never use the Agent or Workflow tools.
The external reviewer is an OpenRouter API call, not a subagent.**

## Process

### 0. Stage check

- **SDD repo** (`.project.toml` at the root): `mise run status` shows no group left. If groups are still open, confirm John wants a mid-flight review.
- **Elsewhere:** every box in the plan `/grill` named (`.agent/plan.md` or `.agent/plan-<slug>.md`) is ticked. If not, confirm the same way.

### 1. Assemble the evidence (one prompt file in the scratchpad)

`<default>` is `default_branch` from `.project.toml`. Without it, take `git symbolic-ref --short refs/remotes/origin/HEAD` minus `origin/`, else `main`.

- **SDD repo:**
  - the change folder `specs/changes/<date>-<slug>/`: `requirements.md`, `plan.md` and `validation.md`. A fast lane has no folder, so use the commit bodies from `git log <default>..HEAD` instead;
  - the capability diff: `mise run status -- --change`;
  - the branch diff: `git diff <default>...HEAD`, plus the full text of every new test file.
- **Elsewhere:**
  - the plan file and the decisions file its header names, in full;
  - `git diff <default>...HEAD`, plus `git diff` and `git diff --staged` for uncommitted work;
  - the full contents of new untracked files;
  - outside a git repo, instead of the diffs: the full text of every file the plan's `Files:` lines name.

### 2. Call the external review panel
Run all four reviewers on the SAME prompt file at once, each to its own output
file. They are independent OpenRouter calls (not subagents), all at high
reasoning effort. Run the block as ONE Bash call with a 600000 ms timeout.

    SK=~/helm/03-rai/skills
    PRELUDE=$SK/adversarial-review/references/reviewer-prelude.md
    OUT=<scratchpad>        # session scratchpad dir

    for m in sol grok glm deepseek; do
      REASONING_EFFORT=high bash $SK/ask-model/scripts/call.sh $m freeform <prompt-file> $PRELUDE \
        > $OUT/review-$m.md 2> $OUT/review-$m.err &
    done
    wait

Each call gives up after 540 s (`ASK_MODEL_TIMEOUT` in `call.sh`) and exits 5,
so one hung model cannot hold the panel past that. Panel: GPT-5.6 Sol, Grok
4.5, GLM 5.2, DeepSeek V4 Pro (all at high reasoning effort). Requires
`OPENROUTER_API_KEY`. The panel degrades gracefully: an empty review file, with
the reason in its `.err` file, is a model that failed or timed out. Skip it and
proceed with whichever reviewers returned. Never block on a single model. There is no fallback
chain: the other models are the fallback. The prelude makes each reviewer
hunt state defects, edge-case crashes, contract violations, pattern drift,
and silent failure, with file:line citations and severity.

### 3. Merge, dedupe, then triage: the panel is advisory, not authoritative

First pool the four reviews into one finding list. Collapse duplicates: the same defect at the same file:line from more than one model is ONE finding, and you record which models raised it. Agreement across models is a confidence signal, not proof. A lone finding can be real, and one every model agreed on can be a false positive. Verify each merged finding in the code yourself, then give it one disposition:

- **SDD repo:** one of the outcomes in "Every finding gets one outcome" of `.claude/skills/sdd/validate.md`. A false positive is its Dismissed outcome.
- **Elsewhere:**
  - Real: fix it inline and re-run the group's `Verify:`.
  - False positive: the reason goes in the report.
  - Real but out of scope: listed for John as a follow-up, never fixed silently.

### 4. Report

Findings table: # · severity · file:line · raised-by (which models) · finding · disposition (fixed / backlog / false positive / follow-up). Note any panel model that failed to return.

The durable record is the repo: the commits, their bodies and the backlog items. In an SDD repo the squash merge deletes the branch, so a dismissal is a `Dismissed:` line, which merge copies into the squash body. Nothing the review must keep goes in `.agent/`.

- **Run by `/compile`:** stop at the report. `/compile` runs validate's Close once, after it.
- **Run on its own in an SDD repo:** finish with validate's Close in `.claude/skills/sdd/validate.md`: the lesson check, `mise run status -- --merge`, then its hand-over line.

## Examples

- `/adversarial-review` after validate's lenses: runs the full 4-model panel
- `/adversarial-review just sol and grok` (restrict the panel)
- `/adversarial-review mid-flight: G1 and G2 only`
