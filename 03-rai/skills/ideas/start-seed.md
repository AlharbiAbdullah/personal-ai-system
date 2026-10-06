---
name: start-seed
description: Capture a raw idea as a Seed in 09-ideas/ with minimal frontmatter + spark
allowed-tools: Write, AskUserQuestion, Bash
---

# Start Seed

Capture effort: low. Just get the spark on paper. Detail comes later (via `/ideas promote`).

## Instructions

### Step 1: Get the spark

Ask John in one sentence: what's the idea? Don't explain, don't justify. Just the spark.

### Step 2: Classify domain

Ask (single-select): `ai | data | business | personal | other`.

### Step 3: Pick a slug

From the spark, propose a kebab-case slug (e.g., `offline-first-notes`, `invoice-ocr-pipeline`). Ask John to confirm or override.

### Step 4: Write the Seed

File: `~/helm/09-ideas/{slug}.md`

Read `~/helm/12-system/templates/Seed.md` for the frontmatter and section shape, and fill
it in: `type: idea`, `status: seed`, `domain: {domain}`, `derived_from: []`, `spawned: []`,
`created: {YYYY-MM-DD}`, `tags: [idea, seed, ...]`; title `# {Slug}`; Spark, What Is It?,
Trigger sections from John's answers.

### Step 5: Report

Tell John: "Seed captured at `~/helm/09-ideas/{slug}.md`. Run `/ideas promote {slug}` when it's time for research."

## Rules

- Keep the Seed minimal. Detail belongs in the Plant stage.
- Don't research the idea now. That's what `promote.md` does.
- Never skip frontmatter. Downstream skills rely on `status` and `derived_from`.
- Never invent the frontmatter shape. Read `12-system/templates/Seed.md` and match it.
