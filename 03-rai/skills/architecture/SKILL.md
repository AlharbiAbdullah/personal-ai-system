---
name: architecture
description: >
  Architecture router. USE WHEN the user needs system-level design work:
  data systems, solution architecture, API design, Architecture Decision
  Records, migration playbooks, architectural patterns, or bootstrapping
  a CLI scaffold. Routes between data-architect, solution-architect,
  system-design, adr-writer, migration-playbook, patterns, create-cli.
---

# Architecture

Design work at the system level. Shape before code. Pick the sub-skill by
the kind of design artifact you need.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Data systems, ETL, warehouses, medallion | data-architect | `data-architect.md` |
| Application architecture, patterns, big-picture system design | solution-architect | `solution-architect.md` |
| Specific-system design (API, service boundaries, scale) | system-design | `system-design.md` |
| Draft an Architecture Decision Record | adr-writer | `adr-writer.md` |
| Plan a framework/runtime major-version migration | migration-playbook | `migration-playbook.md` |
| Pick a pattern (microservices, event-driven, saga, CQRS) | patterns | `patterns.md` |
| Bootstrap a TypeScript CLI tool | create-cli | `create-cli.md` |

## How to use

1. Pick the sub-skill that matches the design artifact.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## When two could fit

- **data-architect vs solution-architect:** data-architect owns data systems (ETL, warehouses, pipelines); solution-architect owns everything else (application architecture, patterns).
- **solution-architect vs patterns:** solution-architect helps pick and compose an overall architecture; patterns is the reference library for specific patterns (event-driven, saga, CQRS).
- **system-design vs solution-architect:** system-design is per-specific-system (designing THIS API, THIS service); solution-architect is cross-system pattern work.
- **adr-writer vs system-design:** ADRs capture a decision after it's made with consequences; system-design is the active exploration before the decision.

## Cross-references

- Tactical data patterns (SQL, streaming implementations) → `/data/`
- Deployment + infra patterns (Docker, K8s, CI/CD) → `/devops/`
