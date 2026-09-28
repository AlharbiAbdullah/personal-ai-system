---
name: agent-design
description: >
  Design a multi-agent / agentic LLM system. USE WHEN the user is
  architecting agent orchestration — planner/executor, critic/generator,
  fan-out, sequential chains, tool use, memory. Design doc output.
---

# Agent Design

Agents = LLMs in a loop with tools. Design the loop deliberately.

## When to use

- Building an LLM feature that needs > 1 LLM call
- Designing a multi-step workflow with tool use
- Tuning an agent that's inefficient / loops / hallucinates tool calls

## When NOT to use

- One-shot prompts (no loop) — just use `/think/prompting`
- RAG pipeline design → `/ai/rag-design`
- Consuming the Claude API → system `claude-api` skill

## Core agent patterns

### 1. ReAct (reason + act)
Single agent loops: think → act → observe → think ...
- Most common pattern
- Good for: general task completion with tools
- Failure mode: infinite loops, wrong tool calls

### 2. Planner + Executor
Planner produces a multi-step plan; Executor runs each step.
- Good for: complex multi-step tasks where planning benefits from isolation
- Separates "what to do" from "how to do it"

### 3. Critic + Generator
Generator produces output; Critic evaluates + requests changes.
- Good for: quality-sensitive work (code, writing, designs)
- Implement with two prompts (or two models), iterating until critic approves

### 4. Fan-out / fan-in (map-reduce)
One agent divides work into N; N parallel agents execute; one aggregates.
- Good for: independent sub-tasks that can run in parallel
- Reduces wall-clock time

### 5. Sequential chain
Agents in series; each consumes prior output.
- Good for: pipeline transformations (extract → classify → summarize)
- Less flexible but predictable

### 6. Supervisor + specialists
Supervisor routes to one of N specialized agents.
- Good for: diverse task types under one interface
- Similar to router skills — but with LLM doing the routing

## Frameworks

- **LangGraph** — state-machine-style agent graphs. Declarative. Good default.
- **LangChain** — broader framework; includes agents but now heavier than needed for most cases
- **LlamaIndex** — retrieval-focused, has agent layer
- **AutoGen** — multi-agent conversations
- **CrewAI** — role-based agent teams
- **Vanilla Python + Claude SDK** — Often simplest for single-agent ReAct

John uses LangGraph + ChromaDB + FastAPI frequently.

## Design doc checklist

When designing an agent system, answer these:

1. **Purpose** — what does the agent do? (one sentence)
2. **Inputs** — what does it receive from the user / upstream?
3. **Outputs** — what does it produce?
4. **Tools** — what can it call? Each tool has schema + side effects + cost
5. **Stopping condition** — when does the loop end?
   - Max iterations (usually 10–30)
   - Goal-reached signal (agent says "done")
   - Error threshold
6. **Memory** — what persists across turns?
   - Short-term: conversation history
   - Long-term: vector DB, user profile, task state
7. **Failure modes** — enumerate + handle
   - Tool call with wrong args → retry with feedback
   - Loop without progress → break + ask user
   - Tool unavailable → fallback tool or graceful fail
8. **Observability** — every LLM call + tool call logged with inputs/outputs/tokens/latency
9. **Evaluation** — golden tasks, success rate, tokens per task
10. **Cost envelope** — max tokens / calls per user interaction

## Tool design

A good tool has:
- **Clear, narrow purpose** — one thing well
- **JSON schema** — typed args, typed return
- **Deterministic when possible** — same args → same result
- **Idempotent** — safe to retry
- **Informative errors** — tell the LLM what went wrong so it can correct
- **Rate limits + cost budgets** — especially for external APIs

## Prompt patterns inside agents

### System prompt
- Agent's identity + constraints + available tools
- Style guide (concise, avoid hallucination, cite sources)
- Iteration discipline ("think step by step; if you're stuck, ask")

### Tool-use prompt
- Tool name + description + schema
- Examples of correct tool calls
- What to do when tool fails

### Reflection / scratchpad
- Let the agent reason before acting
- Keeps the context window useful

## Memory strategies

| Type | Example | When |
|---|---|---|
| Turn-only | Last N messages | Short conversations |
| Sliding window | Last 4K tokens | Longer conversations |
| Summarization | Compress old turns | Very long conversations |
| Vector store | RAG over past turns | Search-based recall |
| Structured state | Task plan, user profile | Stateful workflows |
| Hybrid | Recent raw + older summarized + vector | Production systems |

## Anti-patterns

- Single mega-prompt for everything — break into agents
- No max iterations — cost explodes on loops
- Tools that do too much — model gets confused on args
- No observability — you can't debug what you can't see
- No eval loop — quality drifts invisibly
- Over-engineering — start with ReAct, add complexity when needed
- Using LLM to do deterministic work (e.g. parsing dates) — use regex/library

## Design doc output

```
# Agent Design: [Name]
Author: [Name] | Date: YYYY-MM-DD

## 1. Purpose
## 2. Inputs + Outputs
## 3. Pattern (ReAct / Planner-Executor / etc.)
## 4. Tools
| Name | Purpose | Schema | Side effects | Cost |
...

## 5. Stopping condition
## 6. Memory
## 7. Failure modes
## 8. Observability
## 9. Evaluation
## 10. Cost envelope

## Diagram
[state machine or sequence diagram]
```

## Examples

- "Design the OpenKit compliance-scan agent"
- "Taskflow chat agent — add tool use for Dremio + Superset"
- "Multi-agent system for Matchbox: scan + classify + report"
- "Critique-generator loop for PRD drafting"
