---
name: fusion
description: >
  Convene a multi-model panel on one ask and synthesize a single answer.
  Five voices: four OpenRouter models (GPT-5.6 Sol, Grok 4.5, GLM 5.2,
  DeepSeek V4 Pro, all at high reasoning effort) plus Claude (this session,
  on the subscription). Modes: brainstorm, debug, solve, review, or freeform.
  Each model answers the same self-contained context independently; you merge
  their takes into one response with consensus, disagreements, and a
  recommendation. USE WHEN the user types /fusion, or asks to "get all the
  models on this", "panel this", "brainstorm with everyone", "let them all
  weigh in". Never spawns Agent/Workflow subagents.
---

# /fusion

Many minds on one problem. The four OpenRouter models answer the same prompt
independently and in parallel; you (Claude, this session) add a fifth
independent take, then synthesize all five into ONE answer for John. The
external models cannot see the repo or the conversation, so you distill the
session into a self-contained context block they can act on.

This is the general-purpose sibling of `/adversarial-review`. That one is a
narrow pipeline verify step; this one is for open questions: brainstorming,
debugging, weighing a solution, reviewing a design.

## The panel

| Voice | Alias | Model | How it is called |
|-------|-------|-------|------------------|
| 1 | `sol` | `openai/gpt-5.6-sol` | OpenRouter, `REASONING_EFFORT=high` |
| 2 | `grok` | `x-ai/grok-4.5` | OpenRouter, `REASONING_EFFORT=high` |
| 3 | `glm` | `z-ai/glm-5.2` | OpenRouter, `REASONING_EFFORT=high` |
| 4 | `deepseek` | `deepseek/deepseek-v4-pro` | OpenRouter, `REASONING_EFFORT=high` |
| 5 | Claude | this session | Your own take, on the subscription (no API call) |

Aliases resolve in `~/helm/03-rai/skills/ask-model/scripts/call.sh` (single
source). `scripts/fusion.sh` fans the four out in parallel.

## Modes

Pick from the ask; infer if obvious, confirm if not. The mode only changes how
each voice is told to shape its answer (via the `# MODE:` line in the context
block) and how you synthesize.

| Mode | For | Panel output | Your synthesis |
|------|-----|--------------|----------------|
| `brainstorm` | idea generation | many distinct ideas, safe to bold | dedupe, cluster, surface the boldest live options |
| `debug` | a bug / failure | ranked root-cause hypotheses + how to confirm each | converge on the most likely cause + the fastest test |
| `solve` | design / approach choice | candidate approaches with tradeoffs + each model's pick | recommend one path, note what the dissenters feared |
| `review` | critique a plan/design/code | strengths, then risks + fixes by severity | merged risk list, deduped, most severe first |
| `freeform` | anything else | direct answer | reconcile into one coherent response |

## Process

**Single-agent mandate: run inline. Never use the Agent or Workflow tools.
The four panelists are OpenRouter API calls; the fifth voice is you.**

### 1. Frame the ask + pick the mode
State the ask in one sentence and name the mode. If the ask is ambiguous or
under-specified, ask John before spending four high-effort calls.

### 2. Assemble the self-contained context block (one file in the scratchpad)
The external models have NO access to the session or repo. Put everything they
need into one prompt file:
- `# MODE: <mode>` on the first line.
- `# ASK` — the exact question, sharply stated.
- `# CONTEXT` — the relevant code (with file:line), error output, prior
  decisions, constraints, and what has already been tried. Paste real content,
  not references to it. Trim to what matters; do not dump the whole repo.

### 3. Fan out to the four + form your own take
Run the four panelists in parallel, and — before reading their answers — write
your OWN answer to the ask from your knowledge of the session, so the fifth
voice is genuinely independent and not anchored to theirs.

    ~/helm/03-rai/skills/fusion/scripts/fusion.sh <prompt-file>

All four run `freeform` at `REASONING_EFFORT=high` with the panel prelude
(`references/fusion-prelude.md`). Requires `OPENROUTER_API_KEY`. The panel
degrades gracefully: a failed model prints `[no response]` and the rest
proceed.

### 4. (optional) Cross-pollination round — hard problems only
For genuinely hard or contested asks, pool all five answers into a new file and
send it back through `fusion.sh` asking each model to critique the others and
revise. Skip it for quick brainstorms; it doubles the cost. Say when you use it.

### 5. Synthesize ONE answer
Read all five. Produce a single response, shaped by the mode:
- Lead with the answer / recommendation, not a roll call.
- **Consensus** — what all or most voices agreed on (treat as high-confidence,
  but you still own correctness; the panel is advisory).
- **Disagreements** — where they genuinely split, attributed (who argued what
  and why). Real splits are signal; do not paper over them.
- **Standouts** — the sharpest non-obvious point, attributed to the model that
  raised it.
- Close with your own judgment as the fifth voice, including where you overrule
  the majority and why.

Keep attribution light and useful (`grok pushed X; deepseek disagreed`), not a
transcript.

## Invocation

```bash
cat > /tmp/fusion.txt <<'EOF'
# MODE: debug
# ASK
Why does `openkit join` hang for ~30s before failing on a fresh hub?

# CONTEXT
<paste the failing command output>
<paste the relevant function, e.g. packages/coding-agent/src/openkit/hub.ts:120-160>
Already tried: bumping the timeout (no change); it only repros on first join.
EOF

~/helm/03-rai/skills/fusion/scripts/fusion.sh /tmp/fusion.txt
```

Restrict the panel (e.g. "just sol and deepseek") by calling `call.sh`
directly for those aliases instead of `fusion.sh`.

## Auth

Requires `OPENROUTER_API_KEY` in the environment (same key as `/ask-model` and
`/adversarial-review`). `fusion.sh` fails fast if the key is missing.

## Cost

Four high-reasoning-effort calls per round (eight if you run the
cross-pollination round). Not a cheap operation — reach for it when breadth of
perspective is worth it, not for routine questions you can answer directly.

## When NOT to use

- You can answer well yourself — just answer. Do not proxy for the sake of it.
- A single second opinion is enough — use `/ask-model`.
- Narrow pipeline verification of finished implementation work — use
  `/adversarial-review`.

## Files

```
fusion/
├── SKILL.md                      # this file
├── scripts/
│   └── fusion.sh                 # parallel fan-out to the 4 OpenRouter panelists
└── references/
    └── fusion-prelude.md         # panel-member system prompt (shared by all 4)
```
