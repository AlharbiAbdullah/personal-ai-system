---
type: concept-note
domain: ai
created: 2026-01-01
tags: [ai, agents, concept]
---

# What Are AI Agents

> Example knowledge note. The `/knowledge` skill creates and links these; MOCs in
> `_mocs/` tie them together.

## In one line
An AI agent is an LLM given a goal, a set of tools, and a loop — so it can take actions,
observe results, and decide what to do next, rather than answer once and stop.

## The core loop
1. **Observe** — read the current state (the task, prior steps, tool outputs).
2. **Think** — decide the next action toward the goal.
3. **Act** — call a tool (search, run code, edit a file, call an API).
4. **Repeat** until the goal is met or a stop condition fires.

## Why it matters
It turns a model from a *question-answerer* into a *task-doer*. The leverage is real, but so
is the failure surface — loops can wander, tools can be misused, and cost grows with steps.

## What makes one good
- **Tight tools** — few, well-described, hard to misuse.
- **Clear stop conditions** — know when it's done or stuck.
- **Verification** — check the work, don't trust the first plausible result.
- **Bounded scope** — a narrow agent beats a do-everything one.

## Simplicity check
> The simplest agent that solves the task is the right one. If a single tool-call or a plain
> script would do, you don't need an agent.

## Links
- [[10-knowledge/_mocs/ai-moc|AI MOC]]
- Related: prompting, tool use, evaluation
