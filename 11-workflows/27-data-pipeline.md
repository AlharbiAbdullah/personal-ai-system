# Data Pipeline

**Use when:** building or changing a pipeline: a new source, ETL or ELT work, a validation or transformation change, an incremental load, a backfill.
**Not for:** 28 data platform, for the warehouse or lakehouse around the pipelines and its assessment. 04 debugging, for a broken run or a number that does not reconcile. 29 air-gapped delivery, for shipping into a sealed network. 31 AI system build, for the model and retrieval side of an AI feature.
**Done when:** the reconciliation tests are green. Every stage reports completed, with non-zero counts that match the source. Moving to prod is a file or config swap only. The change merged through 21 or 02.

John's way to build a pipeline. Understand the source and write the contract. Land raw as-is, quarantine what fails, transform in one layer, and prove every number by reconciliation. It is a method workflow, so 21 or 02 carries the change and owns its gates.

```d2
direction: right

route: "0 Route\n21 or 02"
source: "1-3 Source\nunderstand, catalog,\ncontract"
layers: "4-7 Layers\nraw, validate,\ntransform, model"
prove: "8-10 Prove and run\nreconcile, run state,\none entry point"
ship: "11-12 Ship\nprod-mimic run,\nconfig-swap cutover"
quarantine: "Quarantine\nrejects kept\nwith their reason"
debug: "04 debugging"

route -> source -> layers -> prove -> ship
layers -> quarantine: "invalid rows" {style.stroke-dash: 3}
prove -> debug: "a number does not reconcile" {style.stroke-dash: 3}
```

---

## Steps

### 0. Route

- [ ] At the repo root: `test -f .project.toml && echo SDD || echo plain`.

> **Decision Point**: which delivery workflow carries the change?
> - SDD repo: run inside [[21-project-init]] Phase C. The "Slots in 21" table below says what each step supplies.
> - Any other repo: run through [[02-task]]. Steps 1 to 3 feed its Define step. Steps 4 to 10 become the plan's groups, one per layer, with step 8's proofs as their tests.

### 1. Understand the source and the business

- [ ] Read before building: the business question, who consumes the output, and what they decide with it.
- [ ] Map the source from real responses, never from its spec or its docs. Call every endpoint or open every file, and record what comes back.
- [ ] Hand the probe to the `engineer` agent when the source is large. Inputs: the endpoints or files. Returns: the observed shapes, keys and null patterns as a table. It writes a throwaway probe outside the repo, nothing else.
- [ ] Rai re-checks every shape the model will depend on.
- [ ] Write the grain in one line, and name the consumer.
- [ ] Write each consumer's freshness target beside the grain.
- [ ] Never assume. Ask John, and write the answer down.

> **Decision Point**: can the grain and the consumer each be written in one line?
> - Yes: step 2.
> - No: ask. You cannot model what you do not understand.

### 2. Catalog the source

- [ ] The usage policy: ingest, link only, or partner. And its tier.
- [ ] Access verified live, never taken from docs.
- [ ] The ingestion key. A monotonic id, where one exists, makes integer gaps the completeness check.
- [ ] The harvester checks content type and size. Never claim full coverage.
- [ ] A per-source on/off switch in config.
- [ ] Gate: licensing and access are known before any code.

### 3. Write the contract and prod-shaped fixtures

- [ ] The contract: the fields, types and keys the pipeline accepts. It is a gate, not a pipe.
- [ ] A validator checks a source file against the contract in one command: green means it matches.
- [ ] When he supplies the source files, the work splits. John owns making them match the production schema. Rai owns everything downstream of them.
- [ ] Dev fixtures mirror prod exactly: the same files, shapes and headers. Going to prod means replacing the dummy file with the real one, and everything runs end to end.
- [ ] No code path reads production paths in dev.
- [ ] Match the source owner's reality. Never ask them to do data engineering so they can ship to you.
- [ ] Gate: going to prod is a file or config swap only.

### 4. Land raw as-is

- [ ] Land the exact rows or bytes the source sent, each record once. No validation at landing.
- [ ] Idempotent and replayable: a unique content hash, insert or ignore. A rerun lands nothing new.
- [ ] Pull at the source's rate limit. An empty success, such as a 200 with no data, is never stored as landed.
- [ ] Source headers stay verbatim. The rename happens once, in the loader.
- [ ] Never retry when blocked: escalate the fetch method and continue from the offset.
- [ ] Raw is permanent by default. A transient landing is right only when storage or classification forces it, and it is written down as a decision.
- [ ] Gate: a rerun is a no-op.

### 5. Validate at promotion

- [ ] Validation runs when raw is promoted to the clean layer, never at landing.
- [ ] Quarantine, never drop: an invalid record is isolated with its reason. Drift is logged, and reprocessing stays possible.
- [ ] A rejected record never stops the run.
- [ ] A row that matches nothing is flagged for review, never dropped silently.
- [ ] Models accept new fields from the source. Only the required ids are strict.
- [ ] A null stays a null, never a zero.
- [ ] A high skip rate is a finding, never normal.
- [ ] Stop the run on a broken input contract, such as a schema change or a missing required file, and on an integrity failure. Quarantine and report row-level failures: a rejected record never stops the run.

### 6. Transform in one layer

- [ ] Every transformation lives in the transform layer, dbt in his dbt stacks, never in ingestion.
- [ ] Models read raw only through `source()`. The transform layer never writes raw.
- [ ] One shared pipeline up to the clean layer. Consumers diverge after it.
- [ ] Deterministic extraction first, such as rules and a gazetteer. An LLM handles only the residual.
- [ ] Delete a job that selects zero assets, and add a guard test.
- [ ] The loader owns raw. dbt starts at staging and reads raw through `source()`: dbt never writes raw.
- [ ] Lineage is dbt docs plus the orchestrator's asset lineage. OpenLineage only when a client platform requires it.

### 7. Model the layer

- [ ] Run the modeling checklist in [[28-data-platform]]: grain, long or wide, star or one big table, keys, naming, and regional calendar and script columns when the data needs them.
- [ ] Check the model against real data, never against the spec.
- [ ] Hand the review to the `architect` agent. Inputs: the grain line, the model files and a sample of real data. Returns: each checklist item as pass or issue, with evidence. It writes nothing.
- [ ] Rai re-checks every issue the agent raises before the model changes.
- [ ] Gate: the model is reviewed against real data.

### 8. Prove it by reconciliation

- [ ] Answer-key tests: derive the numbers independently, then test them against a trusted source, in both directions.
- [ ] The mart under test never reads the table it is compared with. The reference stays on the other side of the test.
- [ ] Every run logs received versus stored counts.
- [ ] Invariant queries report zero violations per stage.
- [ ] Every count printed comes from a query, never from objects in memory.
- [ ] Never invent data so a demo number looks different.
- [ ] Hand the independent check to the `qa-tester` agent. Inputs: the source counts, the invariant queries and the marts. Returns: PASS or FAIL per check, with the query and its output. It cannot edit files.
- [ ] Rai re-runs every FAIL before acting on it.

> **Decision Point**: a number does not reconcile?
> - Follow [[04-debugging]] from step 1. The fix never touches the reference side of the test.

### 9. Keep run state

- [ ] A run table records every stage with its row counts.
- [ ] In production, load incrementally by an `updated_at` watermark kept in the run table.
- [ ] Rerun behaviour is defined per table: drop then create, or insert or ignore.
- [ ] Frozen answers never move on a rerun. A changed count is a defect.
- [ ] A backfill replays from raw by partition and resets the watermark for that range. A full rebuild only when the transform logic changed everywhere.
- [ ] Gate: a rerun leaves the numbers unchanged.

### 10. One operator surface

- [ ] One entry point with three modes. Fresh drops, builds and runs everything. Resume continues from where it stopped. Sanity is a new named run on a minimum of the data.
- [ ] No silent success. An ingest that swallows every error and reports green is a defect.
- [ ] A long stage reports progress. A silent one is a defect, and so is a green that has gone stale.
- [ ] Tests never touch the network.
- [ ] For a scheduled pipeline, hand the run review to the `sre` agent. Inputs: the schedule, the run table and the logs. Returns: freshness, the last failure, and whether the alarms fire honestly. It writes nothing.
- [ ] Rai re-checks every failure the agent reports.
- [ ] Pick the orchestrator. A plain CLI with the database as the queue fits a single host, a single operator or a sealed target. Dagster with dbt fits when sources, schedules and lineage multiply. Airflow only where it already runs.
- [ ] A failure raises a loud, honest alarm on a channel he watches, never a stale green. The alarm checks each consumer's freshness target from step 1.

### 11. Prod-mimic run

- [ ] Build for the production target. Dev limits never shape the design. Stub what cannot run locally.
- [ ] Run on a machine that mimics prod, with every consumer switched on, not only one.
- [ ] Run with the config the target will run.
- [ ] A sealed target rehearses in [[29-air-gapped-delivery]] step 3.
- [ ] Gate: every stage completed, with non-zero counts that match the source row count.

### 12. Cut over with a restore point

- [ ] Dev to prod is unplug and plug. Replace the fixtures with the real files, run the pipeline, flip the few env vars, restart and smoke test. No code change.
- [ ] Validate the real files with the step 3 validator before loading.
- [ ] Take a copy before the prod run. Rollback reverts the config and restores that copy.
- [ ] Verify every stage, and the counts against the source.
- [ ] Preserve data, delete code. When data is at stake, remove nothing.
- [ ] Gate: the restore point exists before the run.

### 13. Land the change

- [ ] SDD repo: the change merges at the G3 gate of [[21-project-init]] Phase C.
- [ ] Any other repo: [[02-task]] from its Review step.
- [ ] A choice later changes must respect gets a dated record: an ADR in an SDD repo, the repo's decision log elsewhere.

---

## Slots in 21

In a repo with `.project.toml`, this workflow fills the slots of [[21-project-init]]:

| 21 slot | What this workflow supplies |
|---|---|
| Talk, round 1 | The source contract, the grain, the layer the change touches, the consumer, and the data rollback |
| Trunk | The contract validator, the raw loader and dbt `sources.yml`. A plan group that touches them is `risk: high` |
| Plan groups | One per layer: land, validate, transform, serve, run state |
| `## Proof` rows | Row counts from queries, the reconciliation test output, the zero-violation invariant queries, the stage status |
| Rollback line | Replay from raw, or restore the copy taken before the run. A backfill that rewrites history is usually `one-way` |
| Launch, Phase F | The prod-mimic run of step 11 and the config-swap check of step 12, before the flag comes off |

---

## Connections

- Delivery: [[21-project-init]] Phase C in an SDD repo, [[02-task]] elsewhere.
- The modeling checklist and the platform around the pipeline: [[28-data-platform]].
- A number that does not reconcile: [[04-debugging]].
- A sealed target: [[29-air-gapped-delivery]].
- Skills: `/grill` and `/compile` through the delivery workflow, `/architecture → data-architect` (a generic pattern list: his rules here win where it differs), `/data → sql-patterns`, `/testing → tdd`, `/testing → e2e`, `/visual → data`, `/architecture → adr-writer`, `/fusion → review`.
- Agents: `engineer` (step 1), `architect` (step 7), `qa-tester` (step 8), `sre` (step 10).
