---
name: think
description: >
  Reasoning and thinking router. USE WHEN the user faces a hard decision,
  needs assumptions stripped, wants to explore an idea from multiple angles,
  needs scientific rigor, wants meta-prompting help, or is chasing a stubborn
  bug. Routes among 11 thinking modes including first-principles, iterative
  depth, multi-agent debate, red-team adversarial analysis, brainstorming,
  scientific method and systematic debugging.
---

# Thinking

Eleven thinking modes. Pick by the cognitive shape of the problem.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Strip assumptions, find root causes | FirstPrinciples | `first-principles.md` |
| Explore a topic deeply from multiple angles | IterativeDepth | `iterative-depth.md` |
| Brainstorm, generate ideas, lateral thinking | BeCreative | `be-creative.md` |
| Multi-perspective debate on a hard decision | Council | `council.md` |
| Adversarial stress-test an idea, plan, or design | RedTeam | `red-team.md` |
| World model across time horizons (geopolitics, economics) | WorldThreatModelHarness | `world-threat-model-harness.md` |
| Scientific method: hypothesis, evidence, falsification | Science | `science.md` |
| Evaluate AI agent / prompt output quality systematically | Evals | `evals.md` |
| Improve a prompt or write a new one | Prompting | `prompting.md` |
| Explain a concept so it clicks (mechanism first, diagram, analogy last) | ExplainSimply | `explain-simply.md` |
| Root-cause a bug that is non-trivial, intermittent or keeps coming back | SystematicDebug | `systematic-debug.md` |

## How to use

1. Pick the mode that fits the cognitive task.
2. `Read` the appropriate file in this directory.
3. Follow that file's instructions.

## When unsure

- Hard decision with tradeoffs → Council (multi-perspective debate)
- Want to attack an idea before reality does → RedTeam
- Want creative options → BeCreative
- Want to validate an assumption → Science
- Want to evaluate AI/prompt output quality → Evals
- Want to teach or explain → ExplainSimply
- Want to write a better prompt → Prompting
- Want to project an idea forward in time → WorldThreatModelHarness
- Want to break a problem into fundamentals → FirstPrinciples
- Want multiple analytical lenses on one problem → IterativeDepth
- A bug survived a quick fix → SystematicDebug

## Mode chaining

Thinking modes compose. Common chains:

- **FirstPrinciples → Science → Council**: Strip assumptions, formulate a hypothesis, then debate the hypothesis from multiple viewpoints. Best for high-stakes decisions where the framing itself might be wrong.
- **BeCreative → RedTeam**: Generate options broadly, then attack each one. Best for design work where you want both divergent and convergent thinking in sequence.
- **IterativeDepth → ExplainSimply**: Explore a topic through multiple analytical lenses, then compress the synthesis into a teachable form. Best for understanding a domain well enough to onboard someone else.
- **FirstPrinciples → ExplainSimply**: Decompose to the mechanism, then teach from it. The default for explaining anything to John: he does not keep a label or an analogy until the mechanism has made sense. ExplainSimply already opens with the mechanism, so this chain is usually one invocation, not two.
- **Prompting → Evals**: Draft a prompt, then evaluate its output quality systematically. Best for shipping LLM features: iterate until evals pass.
- **Science → WorldThreatModelHarness**: Form a hypothesis about the present, then project it forward across time horizons. Best for strategic bets (market, tech, geopolitics) where the hypothesis must survive future change.
- **Council → Evals**: Multi-perspective debate to surface options, then evaluate the winning option against concrete criteria. Best when the debate is useful but you need a final pass-fail judgment.

Chaining rule: each mode produces an artifact (hypothesis, list of options, rubric, etc.) that the next mode consumes. Don't chain without an explicit handoff artifact, or the next mode has nothing to chew on.

## When NOT to use

- Trivial, mechanical decisions (formatting, naming a variable): just do them
- Tasks where the bottleneck is execution, not thought: start executing
- Requests where the user already signaled the approach they want: follow it, don't re-litigate

Thinking modes are expensive cognitive overhead. Apply only when the decision is load-bearing or the answer is genuinely unclear.
