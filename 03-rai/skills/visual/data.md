---
name: data
description: >
  Explain a dataset, schema, or data model visually as a single self-contained animated HTML
  file — entity cards with FK edges, the medallion/layer flow (e.g. bronze→silver→gold)
  as lanes narrated beat by beat, and key field semantics. Light/dark toggle. Invoked via
  /visual router. Use when John says "visual data" / "explain this schema/dataset/pipeline
  visually".
---

# /visual · data

Make a dataset or data model graspable — in a **single self-contained HTML file**. Entities as
store/doc nodes with FK edges, layers as lanes, lineage as beats tracing one row's journey.
A focused cousin of `explain`, tuned for schemas, ER diagrams, and pipelines.

## How John uses it
1. He needs to see a dataset's shape — a schema, an ER model, a pipeline's layers, lineage.
2. He says **"visual data"** (or "explain this schema/dataset/pipeline visually").
3. You build the HTML: the entities, their links, the layer flow, the field semantics.
4. He reads the model, follows a column from source to gold, flips light/dark.

## Build it (from `references/engine.html` — see the router's Engine API)
1. **Read the real schema first.** Tables, columns, types, keys, the actual transforms between
   layers. Ground every node and edge — a data diagram that misstates a key is actively harmful.
2. **Clone the engine**, set `<body data-nav="scroll" data-skill="data">` when narrating
   source→gold as one story; `tabs` for jump-to-a-table reference.
3. **Draw the model, minimum words** (one framing line per section):
   - **The model** — ONE line: what this data represents, its grain, the key entity.
   - **Entities** — a `scene()`: tables as `store`/`doc` nodes (`sub` = grain or key
     column), edges = FK relationships with the join key as the edge label. Legend keyed
     by layer/domain. Column-level detail goes in click-open `detail-<id>` cards.
   - **The flow** — the medallion/pipeline as **lanes** (bronze / silver / gold), beats
     tracing one row's journey layer by layer with pulses on the transform edges.
   - **Counts** — row counts / cardinalities as `.metric[data-count]` stat tiles.
4. **Ground it in the real project where relevant.** Read the actual schema, catalog, and
   storage layer first (e.g. Postgres tables, a warehouse's medallion layers, a Parquet/lake
   catalog) and use the real layer and table names — never invent a structure that isn't there.

## When NOT to use
- A single `CREATE TABLE` or a one-line schema note answers it — just paste/say it.
- Explaining non-data system behavior → use `explain`. Planning a schema change → use `plan`.
