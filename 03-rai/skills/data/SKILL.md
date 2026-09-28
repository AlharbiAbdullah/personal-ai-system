---
name: data
description: >
  Data tactics router. USE WHEN the user needs concrete data implementation
  patterns: SQL patterns, real-time streaming (Kafka, Kinesis, Flink), or
  query-level work. For system-level data design (medallion, ETL shape,
  warehouse patterns), use /architecture/data-architect instead.
---

# Data

Tactical data patterns. Concrete code-level implementations.

For system-level data design (medallion, warehouse shape, ETL orchestration)
go to `/architecture/data-architect` instead.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| SQL query patterns, window functions, CTE tricks, DuckDB vs Postgres vs Spark | sql-patterns | `sql-patterns.md` |
| Real-time streaming (Kafka, Kinesis, Flink, CDC) | streaming | `streaming.md` |

## How to use

1. Pick the sub-skill that matches the tactical need.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## Cross-references

- System-level data design → `/architecture/data-architect`
- Containerizing data pipelines → `/devops/docker`
- Deploying streaming infra → `/devops/kubernetes`
