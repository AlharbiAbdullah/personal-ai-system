# Data Platform

**Use when:** designing a warehouse, lake or lakehouse, or assessing, upgrading or migrating one. The platform may be his own, an employer's or a client's. Modeling a domain happens inside this work.
**Not for:** 27 data pipeline, for one pipeline, source or backfill. 23 audit, for running the audit session itself: this workflow supplies its rubric. 30 architecture decision, for a design question outside data platforms, and for the decision paper itself. 07 evaluate a technology, for adopting one tool. 29 air-gapped delivery, for shipping into a sealed network.
**Done when:** the assessment or design report is delivered, with scores for an assessment and ranked recommendations. Phase 0 is live and verified. The decision record is updated. An assessment with no build behind it ends at the delivered report.

John's way to design, assess or upgrade a data platform, the way his platform-assessment spec encodes it. Purpose and an owner come first, then the evidence, then a target design with his defaults, then one real use case end to end.

```d2
direction: down

purpose: "1 Purpose and owner"
collect: "2 Collection strategy\nwhen sources are unknown"
inventory: "3 Inventory"
assess: "4 Assess\n23 report mode,\nmaturity rubric"
design: "5 Target design\nhis defaults,\nkeep, change, cut"
paper: "6 Leadership paper\n30 step 7"
phase0: "7 Phase 0\none real use case"
implement: "8 Implement and migrate\n27 through 21 or 02"
record: "9 Record"

purpose -> collect -> inventory
inventory -> assess: "brownfield"
inventory -> design: "greenfield" {style.stroke-dash: 3}
assess -> design
design -> paper: "audience is management" {style.stroke-dash: 3}
design -> phase0
paper -> phase0
phase0 -> implement -> record
```

---

## Steps

### 1. Purpose and owner

- [ ] Write what the platform is for, who consumes it, the grain, and the service levels each consumer needs.
- [ ] Name the single technical owner, and who owns the operation. Architecture follows ownership.
- [ ] No infrastructure question comes before this. "Pick a database" sits downstream of the framing. Answering it first builds a shared dependency without a shared design.
- [ ] The framing is still open: run [[30-architecture-decision]] from step 1 first.
- [ ] Organization before design. A design does not survive without an aligned owner who holds real authority.
- [ ] No named single technical owner: do not start a shared platform. The output is then a framing paper through [[30-architecture-decision]], not a design.
- [ ] Write the non-functional targets before a design is approved: service levels per consumer (freshness, availability), the data classification and the production profile. Cost only for a cloud platform.
- [ ] Gate: the purpose, the consumers, the owner and the non-functional targets are written.

### 2. Collection strategy

For sources that are unknown or too broad to list:

- [ ] Lay out the approaches: top-down (requirements first, then targeted pipelines), bottom-up (ingest everything, find the value later), and a phased hybrid.
- [ ] Compare them in a matrix, with one Recommended. His proposals recommended the phased hybrid: start top-down with the priority needs, then open broader ingestion once the platform has proven value.
- [ ] Leadership decides. The answer gates the architecture.

> **Decision Point**: are the sources known and few?
> - Yes: skip to step 3.
> - No: the strategy is decided before any design.

### 3. Inventory

- [ ] List what exists: the sources, the tools, the people, the environments, and what each consumer reads today.
- [ ] Read before modifying. On a running platform, the ground truth comes from the runs in step 4, never from its docs.
- [ ] Before any scan, interview the owner and the main consumers: the purpose, the decisions made on the data, the pain, and the sources they know.

### 4. Assess

For a platform that already runs:

- [ ] Run [[23-audit]] in report mode, from its step 1. This workflow supplies its lens: the maturity rubric below.
- [ ] Each lens in 23's step 3 covers a group of layers. It returns a 0 to 4 score per layer, with file evidence behind every score.
- [ ] Check each point of the production-ready bar.
- [ ] Write each recommendation in the assessment form: the why, ranked options with one Recommended, the effort, the impact and a priority tier.
- [ ] Reason in capabilities, never products. Respect what exists and improve it. Never nuke it.
- [ ] The scores are findings, so 23's step 4 verifies each one before it enters the report.
- [ ] Score every assessment with the maturity rubric: nine layers, each 0 to 4, against the production-ready bar.
- [ ] A client assessment delivers a written report with the score table, as a PDF in his house style. Its three parts: what is solid, what breaks at scale, what to fix first. A short deck only when the client asks.

> **Decision Point**: a greenfield platform?
> - Yes: skip to step 5. There is nothing to score yet.
> - No: step 5 starts from the report.

### 5. Target design

- [ ] Start from his defaults, and change one only when the purpose demands it:
  - medallion layers for a lake or lakehouse, ELT over ETL, metadata-driven orchestration;
  - one source of truth owns the data. Search and vector indexes are derived from it and rebuildable, never a second copy of record;
  - one engine where one engine can do it. A side project needs no more than DuckDB or SQLite, and the line is concurrent shared writers;
  - consumers read the product layers only: APIs read the clean layer, BI reads gold;
  - providers swap by config or env var, never through abstraction classes;
  - size to the production profile, and pin exact versions.
- [ ] Think in four layers: the query engine, the table format, object storage, the filesystem.
- [ ] A running platform gets a keep, change or cut verdict per component. Cut what nothing consumes.
- [ ] Model the domain with the modeling checklist below.
- [ ] Hand the options to the `architect` agent. Inputs: the purpose, the inventory and the scores. Returns: a keep, change or cut table, with the options and one Recommended per row. It writes nothing.
- [ ] Hand outside facts to the `researcher` agent, such as whether a tool is still maintained. Returns: cited facts. It cannot run commands or edit files.
- [ ] Rai re-checks every load-bearing claim either agent returns.
- [ ] The default stack, before the frame decides:
  - a side project: DuckDB or SQLite with dbt;
  - a single-host platform: an embedded engine such as DuckDB at its heart, a derived search index and a plain CLI;
  - a shared enterprise platform: no default product. The nine-layer frame and [[30-architecture-decision]] decide.
- [ ] Environments: a client or work platform gets dev, test and prod. His own side projects get dev and a prod-mimic run.
- [ ] Batch by default. Streaming only when a consumer's decision needs data faster than the batch cadence, and the broker is chosen then.
- [ ] Gate: John agrees the keep, change or cut table.

### 6. Leadership paper

When the audience is management:

- [ ] Hand to [[30-architecture-decision]] step 7, with this design as its input.
- [ ] The data sections the paper adds: the problem without a data foundation, what the platform does and does not do, and how data flows.
- [ ] Then what each consumer gets, security, the operating model and stewardship, a phased rollout, and the decisions owed.
- [ ] Pitch the foundation before the program starts.

### 7. Phase 0

- [ ] The first deliverable is always one real business use case, end to end, production-grade. Never the whole platform.
- [ ] It proves the architecture and the tooling, and it becomes the reference pattern for the rest.
- [ ] Build it as a [[27-data-pipeline]].
- [ ] Gate: Phase 0 is verified live.

### 8. Implement and migrate

- [ ] Each later item is a roadmap item, built as a [[27-data-pipeline]] inside [[21-project-init]] or [[02-task]].
- [ ] Every change needs approval first, shows its diff, and carries its rollback.
- [ ] Migration rules:
  - the new foundation lands first. The old store retires only after every consumer has moved;
  - each cutover phase sits behind an opt-in flag that defaults to the old path. The destructive drop comes last;
  - a provider cuts over by env vars, and the rollback removes them;
  - the old stack goes only after one release cycle live;
  - preserve data, delete code.
- [ ] A sealed target ships through [[29-air-gapped-delivery]].
- [ ] Old and new run side by side for one release cycle. The cutover needs zero unexplained difference on counts and key metrics.
- [ ] A cutover inside one live product runs behind flags that default to the old path. A product split or a hand-over runs on a branch that deletes.
- [ ] Gate: the rollback is written before each cutover.

### 9. Record

- [ ] Record each decision dated and append-only, in the shape and home that [[30-architecture-decision]] step 9 sets.
- [ ] Keep the design even if it never ships. He owns the thinking.

### 10. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## The maturity rubric

The lens step 4 hands to [[23-audit]]. It is tool-agnostic: any tool can fill a layer.

| Layer | The question |
|---|---|
| Storage and warehouse | Where does data live? |
| Ingestion | How does data get in? |
| Transformation | How is data transformed? |
| Orchestration | What schedules and coordinates? |
| Data quality | How is data validated? |
| CI/CD | How are changes deployed? |
| Observability | How do you know it is working? |
| Secrets management | How are credentials handled? |
| Environments | Is there dev, test and prod separation? |

| Score | Level | What it means |
|---|---|---|
| 0 | Absent | The layer is not present |
| 1 | Ad-hoc | Manual, inconsistent, undocumented |
| 2 | Developing | Some automation, partly documented |
| 3 | Defined | Consistent, documented, tested |
| 4 | Optimized | Automated, monitored, improved continuously |

The platform score is the sum of the nine, out of 36. The grade bands: F 0-9 critical, D 10-15, C 16-21, B 22-27, A 28-33 production-ready, A+ 34-36.

**The production-ready bar.** A platform needs all ten: environments, CI/CD, orchestration, idempotent pipelines, data quality checks, observability, a standard structure, documentation, secrets management and reproducibility.

**Priority tiers.** Critical: security holes, data loss risks, broken production. High: missing core capabilities, scale blockers, reliability. Medium: developer experience, automation, documentation gaps. Low: nice-to-have features, optimization opportunities and future-proofing.

---

## Modeling checklist

Used by step 5 here and by [[27-data-pipeline]] step 7. In his record, modeling always happens inside a pipeline or a platform build.

- [ ] **The model follows the real data.** A field prod does not have leaves the model. A duplicate the source keeps by design stays.
- [ ] **Grain first.** An attribute at document grain rides on the fact, not on a dimension.
- [ ] **Store long, read wide.** Land long or key-value data as-is, and pivot it in the engine. Never flatten at ingest.
- [ ] **Pick the shape by consumer:**
  - gold as an analytics-ready star schema;
  - one big table in the clean layer as the facing layer for every service;
  - a graph only for multi-hop traversal. Co-occurrence is a join over the clean layer;
  - a statement-centric, bitemporal claim model when provenance is the product. A wrong fact is demoted with evidence, never deleted.
- [ ] **History where it matters.** SCD2 only where history matters, such as customer profiles. Facts are rebuilt in full.
- [ ] **Deterministic keys.** A hash or a concatenation, never a random UUID. A uuid5 key joins across databases.
- [ ] **Naming.** `{entity}_id`, `{action}_at`, `is_{state}`, and bilingual `{field}_ar` with `{field}_en`. Layer prefixes `stg_`, `int_`, `fct_`, `dim_`. Data-layer names are never renamed for branding.
- [ ] **Regional calendars and scripts (when your data needs them).** For example, a Hijri-aware date dimension. The printed calendar is authoritative, and every conversion is labeled. Two Arabic normalization columns: one for search recall, one for identity. A Hijri year with no date stays empty, never guessed.
- [ ] **Data Vault.** Knowledge only, until a project uses it.
- [ ] **One big table or a star.** One big table is the facing layer when services read one entity. A star schema in gold serves BI and analytics.
- [ ] **Default history.** Until someone asks for history, overwrite (SCD1), rebuild facts in full and keep raw, so history can be rebuilt later.

---

## Connections

- The assessment: [[23-audit]] report mode, with the rubric above.
- The framing and the paper: [[30-architecture-decision]] steps 1, 7 and 9.
- Each build item: [[27-data-pipeline]], inside [[21-project-init]] or [[02-task]].
- One tool inside the design: [[07-learning-tech]]. A sealed target: [[29-air-gapped-delivery]].
- Skills: `/architecture → data-architect` (a generic pattern list: his rules here win where it differs), `/architecture → solution-architect`, `/architecture → system-design`, `/architecture → adr-writer`, `/visual → data`, `/visual → plan`, `/testing → e2e`, `/fusion → review`.
- Agents: `architect` and `researcher` (step 5). The `reviewer` lenses of step 4 run inside [[23-audit]] step 3.
