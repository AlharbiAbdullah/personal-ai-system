---
name: ai
description: >
  AI engineering router. USE WHEN the user designs LLM-powered systems:
  RAG pipelines, multi-agent architectures, prompt patterns, or eval
  harnesses. Not for consuming the Claude API (use the system `claude-api`
  skill for that) — this router is about BUILDING AI systems.
---

# AI

AI-system design. For John's work on Taskflow, OpenKit, Matchbox,
Dataforge — anything where the output is an LLM-powered product.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Design a RAG pipeline (chunking, retrieval, reranking, eval) | rag-design | `rag-design.md` |
| Design a multi-agent system (planner/executor, critic/generator, fan-out) | agent-design | `agent-design.md` |

## How to use

1. Pick the sub-skill by the design artifact needed.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## Not yet built

Deferred until 3+ manual uses prove the pattern:
- `eval-harness` — LLM evaluation suites (RAGAS, faithfulness, CI gates)
- `prompt-patterns` — few-shot, CoT, refinement, structured output patterns

When either is invoked 3 times manually, promote to a real sub-skill.

## Cross-references

- Consuming the Claude API in code → system skill `claude-api`
- Prompt engineering meta-thinking → `/think/prompting`
- Writing tests for LLM features → `/testing/verify-completion`
