---
type: concept-note
domain: ai
created: 2026-01-01
tags: [ai, rag, retrieval, concept]
---

# RAG — Retrieval-Augmented Generation

> Example knowledge note (a second one in the `ai/` topic, so the
> [[10-knowledge/_mocs/ai-moc|AI MOC]] has more than one node). Every note carries a one-line
> essence and a simplicity check.

## In one line
RAG is giving an LLM the *relevant facts at answer time* — retrieve the right context, put it in
the prompt, then generate — so the model reasons over your data instead of guessing from memory.

## The core loop
1. **Index** — chunk your documents, embed each chunk into a vector, store them.
2. **Retrieve** — embed the question, find the nearest chunks (semantic search).
3. **Augment** — stuff those chunks into the prompt as context.
4. **Generate** — the model answers grounded in what you retrieved.

## Why it matters
It's the cheapest way to make a model *know your stuff* without fine-tuning. The model stays
general; the knowledge lives in a store you control and can update instantly. (This is exactly
how the assistant's own [[03-rai/semantic-memory/README|semantic memory]] recalls past sessions.)

## Where it goes wrong
- **Bad retrieval = bad answer.** If the right chunk isn't retrieved, the model can't use it. Most
  "RAG is bad" complaints are really "retrieval is bad".
- **Chunking matters more than the model.** Too big = noise; too small = lost context.
- **No grounding check.** The model can still ignore the context and hallucinate — verify.

## Simplicity check
> If the whole knowledge base fits in the context window, you may not need RAG at all — just put
> it in the prompt. Reach for retrieval when the corpus is too big to paste.

## Links
- [[10-knowledge/_mocs/ai-moc|AI MOC]]
- [[10-knowledge/ai/what-are-ai-agents|What Are AI Agents]] — agents often use retrieval as a tool.
- [[09-ideas/agent-eval-harness|Agent Eval Harness]] — eval should test retrieval, not just the LLM.
