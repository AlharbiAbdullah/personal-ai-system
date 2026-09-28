---
name: plan
description: >
  Render a planned change as a single self-contained animated HTML file that John reviews
  before he approves it. Input: the open change folder in an SDD repo (requirements, plan,
  validation + the scenario diff), else .agent/decisions.md + .agent/plan.md. Output:
  .agent/visual/<slug>.html. Diagram-first, minimum words, light/dark toggle, an animated
  Current/Planned morph. USE WHEN John says "visual plan", or picks it when /grill offers
  it before approval. Invoked via the /visual router.
---

# /visual · plan

Render a planned change in a **single self-contained HTML file**, not chat prose. Drawings argue the plan: the target architecture, the flow, and a Current/Planned morph that shows the change as motion. The HTML is the approval view. Code begins only after John approves.

The spec stays the plan of record: the change folder in an SDD repo, `.agent/plan.md` elsewhere. This skill only renders it, and never writes the spec.

## Input and output

| Where | Reads | Writes |
|---|---|---|
| SDD repo (`.project.toml` at the root) | the open change folder `specs/changes/<date>-<slug>/` (`requirements.md`, `plan.md`, `validation.md`) and the scenario diff from `mise run status -- --change` | `.agent/visual/<slug>.html` |
| Elsewhere | the plan `/grill` named (`.agent/plan.md` or `.agent/plan-<slug>.md`) and the decisions file its header names, or the planning conversation when neither exists yet | `.agent/visual/<slug>.html` |

Before the first write, apply the scratch-or-record rule in [grill 2.1](../grill/SKILL.md#21-stage-check). When the repo tracks nothing under `.agent/`, the HTML is scratch. The rule adds `.agent/` to the exclude file, in a form that also works in a linked worktree. In a repo that already tracks `.agent/` files, such as helm, the HTML is a record. The next vault commit picks it up, like any other visual output there.

## How John uses it
1. `/grill` offers it once the spec is ready for approval, or he says **"visual plan"**.
2. You **render the HTML**, and re-render it whenever the spec changes.
3. He opens it in a browser, reviews, comments. Changes go into the spec, then the HTML follows.
4. **He approves:** `! mise run approve` in an SDD repo, or "go" elsewhere. Only then does code begin.

## Plan-specific rules
- **No source-code edits while the plan is built or reviewed.** The only file you write is
  `.agent/visual/<slug>.html`. Spec edits go through `/grill` or `/spec-improve`.
- **Argue a future state.** Lead with the outcome (what + why) in ONE lead line, then let
  the drawings sell the shape, then the open blockers.

> Strict plan mode blocks all file writes, including this HTML. To live-update as you plan,
> work in normal mode and let the no-source-edits rule be the gate. If he insists on strict
> mode, write the HTML at each ExitPlanMode checkpoint instead of continuously.

## Build it (from `references/engine.html`: see the router's Engine API)
1. **Inspect first:** read the spec files and the real code they name. Ground every node and file reference.
2. **Clone the engine**, set `<body data-nav="tabs" data-skill="plan">`. Tabs keep the plan
   scroll-reviewable; the **last tab is the approval gate**.
3. **Draw the plan, minimum words** (one framing line per section; delete unused):
   - **The change:** `sceneDiff()`, the killer move. Nodes/edges carry
     `status:"add"|"remove"`; the Current/Planned toggle glides kept nodes, ghosts
     removed, badges added. Lead with this. Build it from the `Files:` lines and the scenario diff.
   - **Target map:** `scene()` of the planned architecture with lanes + beats narrating
     the new flow end to end.
   - **Groups:** one scene of the `plan.md` groups in order, badged `risk: high` and `parallel: yes`, each with its scenario IDs.
   - **Data:** a small scene of entities touched (store/doc kinds), if data changes.
   - **Decisions:** trade-off cards (`note` / `warn`), one line each, with the rejected option.
   - **Questions:** every `[NEEDS CLARIFICATION]` marker and open blocker in ONE checklist.
   - **Approval:** the final gate tab. It prints the exact next step: `! mise run approve` in an SDD repo, "say go" elsewhere.
4. For a light-weight textual diff inside cards, `.diff-add` (green +) / `.diff-rem`
   (red −) glyphs still exist, but prefer drawing the change with `sceneDiff`.
5. **Update live:** re-edit the same file as the spec evolves; tell him to refresh.

## When NOT to use
- Trivial, single-file, or one-line changes: just do them.
- A change folder he can read in two minutes: approve it as text.
- Explaining something that already exists → use `explain`. Teaching a concept → use `teach`.
