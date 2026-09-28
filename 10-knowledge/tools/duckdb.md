---
type: tool
domain: [data-engineering]
created: 2026-01-01
tags: [tool, data, analytics, embedded, sql]
official_docs: https://duckdb.org/docs/
---

# DuckDB

> Example tool note. Tool notes capture *what a tool is for* and *when to reach for it* — not its
> full docs. One-line essence, a simplicity diagram, when-to-use, and alternatives. On
> [[02-ana/identity/tech-stack|my stack]] for local analysis.

## Simplicity Theorem

> An in-process analytics database — "SQLite for analytics" — that runs fast columnar queries
> right inside your program, no server.

DuckDB is a single embedded library. You point it at Parquet/CSV/Postgres and run SQL; it does the
columnar, vectorized heavy lifting locally. No cluster, no service to babysit.

## Simplicity Diagram

```
  your script ──▶ DuckDB (in-process) ──▶ SQL over Parquet/CSV/Postgres
                       │
                  columnar + vectorized = fast analytics, zero infra
```

---

## Why this tool
Most "data" tasks for one person don't need a warehouse — they need fast SQL over a few files.
DuckDB kills the gap between "a CSV" and "spin up a database". It reads Parquet directly, joins
across files, and returns answers in milliseconds, all from a script.

## When to Use

| Use Case | Good Fit | Poor Fit |
|----------|----------|----------|
| Ad-hoc analysis over local Parquet/CSV | Yes — instant SQL, no setup | A spreadsheet if it's tiny |
| Embedding analytics in an app/CLI | Yes — it's a library | Need many concurrent writers → Postgres |
| Powering a multi-user product DB | No — it's single-process | Postgres / a real OLTP DB |

## Key Concepts

| Concept | Meaning |
|---------|---------|
| In-process | Runs inside your program; no separate server |
| Columnar + vectorized | Reads only needed columns, batches work — fast scans |
| Zero-copy file scan | Queries Parquet/CSV in place without importing |

## Alternatives

| Tool | Comparison |
|------|------------|
| SQLite | Row-store, built for transactions; DuckDB is its analytics counterpart |
| Postgres | Real server, concurrent writers; reach for it when DuckDB's single-process model isn't enough |

## Related
- [[02-ana/identity/tech-stack|tech-stack]] — "PostgreSQL, DuckDB, plain Parquet for analysis".
- [[09-ideas/local-first-task-sync|Local-first task sync]] — embedded storage thinking.
