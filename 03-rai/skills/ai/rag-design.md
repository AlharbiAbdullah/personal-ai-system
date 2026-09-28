---
name: rag-design
description: >
  Design a Retrieval-Augmented Generation pipeline. USE WHEN the user is
  building or tuning a RAG system — chunking, retrieval, reranking,
  context assembly, eval. Architectural + tuning, not code-copy.
---

# RAG Design

A RAG pipeline has 5 stages. Each has decisions. Each has failure modes.

## When to use

- Designing a new LLM-powered app that needs grounding in a document corpus
- Tuning a RAG pipeline that's hallucinating, missing relevant answers, or slow
- Choosing chunk strategy / embedding model / vector DB / reranker

## When NOT to use

- Fine-tuning a foundation model (different problem)
- Pure prompt engineering with no retrieval (use `/think/prompting`)
- Generic "how do I use LLMs" — use the system `claude-api` skill

## Pipeline stages

### 1. Ingest
Load source documents into the system.
- Sources: files (PDF, DOCX, HTML), APIs, databases, URLs
- Metadata: author, date, source URL, section, permissions
- Deduplication: hash content + URL to avoid duplicates
- Handling updates: full re-ingest vs incremental CDC

### 2. Chunk
Split documents into retrievable units.

**Strategies:**
- **Fixed-size** (e.g. 512 tokens with 50-token overlap) — simplest, works OK
- **Semantic / recursive** — split at paragraph/sentence boundaries
- **Structure-aware** — by headings, bullet points, code blocks
- **Hierarchical** — multi-level (section → paragraph → sentence)
- **LLM-generated** — ask an LLM to split at topic shifts (expensive; high-quality)

**Key decisions:**
- Chunk size: 200–800 tokens typical. Too small = context loss. Too big = retrieval imprecision.
- Overlap: 10–20% keeps continuity
- Metadata per chunk: source, section, position, date

### 3. Embed
Convert chunks to vectors.

**Model choices:**
- **OpenAI text-embedding-3-small / large** — strong baseline, cheap
- **Cohere embed-english / multilingual** — strong, especially multilingual
- **Voyage AI** — state-of-the-art for retrieval
- **Open-source**: BGE, E5, Nomic Embed — if you need to self-host

**Dimensions:** 384–3072. Larger = more accurate, more expensive to store + search.

### 4. Store + retrieve
Put vectors in a database + query by similarity.

**Vector DBs:**
- **ChromaDB** — simple, local-first, good for prototypes + small scale (this is what John uses)
- **Pinecone** — managed, scales, pay-per-use
- **Weaviate** — open source, supports hybrid
- **Qdrant** — open source, fast, Rust
- **pgvector** — Postgres extension; good if already using Postgres
- **Milvus** — open source, large scale

**Search modes:**
- **Dense (semantic)** — embedding similarity (cosine / dot product)
- **Sparse (keyword)** — BM25, TF-IDF
- **Hybrid** — combine both; usually outperforms either alone
- **Filtered** — metadata-filtered search (e.g. date range, author)

**Retrieve top-K:** typically 5–20 chunks, reranked down to 3–7 for context.

### 5. Rerank + assemble
Refine the retrieval + build the final context.

**Rerankers:**
- **Cohere Rerank** — state of the art, API-based
- **BGE Reranker** — open source, works well
- **LLM-as-reranker** — ask an LLM "is chunk X relevant to query Y?" (slow + expensive; high quality)

**Context assembly:**
- Order chunks by relevance
- Deduplicate similar chunks
- Include metadata (source, date) for citations
- Respect token budget of the LLM

### 6. Generate
Pass query + context to LLM.

**Prompt structure:**
```
You are answering based on provided documents. Only use info in the documents.

Documents:
[doc 1 with metadata]
[doc 2 with metadata]
...

Question: [user question]

Answer with citations to [doc N].
```

## Evaluation

You cannot improve what you don't measure. Set up a test set.

**Metrics:**
- **Retrieval**: precision@K, recall@K, MRR (mean reciprocal rank)
- **Generation**: answer correctness (human or LLM judge), faithfulness (not hallucinated), citation accuracy
- **System**: latency, cost per query

**Tools:**
- **RAGAS** — open-source RAG evaluation
- **Ragas / LangSmith / Braintrust** — managed eval platforms
- **DIY** — golden dataset + LLM-as-judge works fine

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Hallucinated answers | Context doesn't contain answer | Improve retrieval (reranker, hybrid search) |
| Missing relevant info | Chunk too small, lost context | Increase chunk size + overlap |
| Slow queries | Top-K too high, reranker slow | Reduce K, cache, batch |
| Inconsistent quality | No eval loop | Set up golden dataset + RAGAS |
| Irrelevant chunks retrieved | Query embedding mismatch | Rewrite query (HyDE), try different embedding model |
| Citations wrong | LLM inventing | Structured output with citation field; validate |

## Advanced patterns

- **HyDE** (Hypothetical Document Embeddings) — embed a hypothetical answer, not the query
- **Query expansion** — generate multiple queries for one user question
- **Multi-hop retrieval** — query, read, re-query based on what was found
- **Agentic RAG** — LLM decides when to retrieve, what to ask
- **Parent-child chunks** — retrieve small chunks, return larger context

## Examples

- "Design the RAG pipeline for OpenKit regulatory document Q&A"
- "Tune the Taskflow chat — it's hallucinating"
- "Pick chunking strategy for Arabic legal documents"
- "Set up eval harness for Matchbox RAG responses"
