---
name: promote
description: Advance an idea one stage (Seed→Plant, Plant→Tree). Runs stage-appropriate research/planning.
allowed-tools: Read, Write, Edit, WebSearch, WebFetch, AskUserQuestion, Bash
---

# Promote

Advance an idea to the next pipeline stage. Reads current status; runs the right process.

## Instructions

### Step 0: Identify target

Ask John for the idea slug. Read `~/helm/09-ideas/{slug}.md`. Check current `status` in frontmatter.

### Step 1: Pick the promotion

- `seed` → `plant` (research + Q&A + web)
- `plant` → `tree` (plan + requirements + schedule)
- `tree` → graduated — use `/ideas graduate`, not this skill. Stop here.
- `graduated` → nothing. Tell John the idea has already graduated.

---

## Seed → Plant

**Your job**: heavy lifting. Research the idea from all angles.

### Process

1. **Re-read the Seed** — know the raw idea.

2. **Research the vault**:
   - `~/helm/05-projects/` — past projects, what John has built.
   - `~/helm/10-knowledge/` — relevant technical context.
   - `~/helm/06-learning/` — current learning / growth areas.
   - `~/helm/02-ana/identity/` — values, goals, vision.

3. **Ask clarifying questions** (AskUserQuestion, multiple rounds if needed):
   - What problem does this solve?
   - Who's the target user?
   - What's the unique angle — why you, why now?
   - What assumptions need validation?

4. **Search the internet** (WebSearch + WebFetch):
   - Who else has this problem?
   - What solutions exist?
   - What companies are doing this?
   - What's missing in the market?

5. **Rewrite the file as a Plant**: read `~/helm/12-system/templates/Plant.md` for the
   frontmatter and section shape (`type: idea`, `status: plant`, `domain`, `derived_from`,
   `spawned`, `created`, `updated`, `tags`), and fill it with the Spark, Problem, Idea,
   Research (what others are doing / what's missing / internal context), Q&A, open
   assumptions and next steps from this session.

---

## Plant → Tree

**Your job**: planning and requirements.

### Process

1. **Re-read the Plant** — all research and clarifications.

2. **Gather requirements** (AskUserQuestion):
   - What must it have to be viable?
   - What's the first milestone?
   - What defines "done" for v1?

3. **Define risks** — what could go wrong; what kills this.

4. **Set schedule** — realistic start date, milestones, review dates.

5. **Rewrite as Tree**: read `~/helm/12-system/templates/Tree.md` for the frontmatter and
   section shape (`type: idea`, `status: tree`, `domain`, `derived_from`, `spawned`,
   `created`, `updated`, `tags`), and fill it with the condensed Spark/Problem/Idea,
   Requirements, Plan (milestones + first actions), Schedule, Risks, and a graduation
   readiness checklist (requirements clear, plan realistic, risks named, John
   committed to starting) gating `05-projects/kitchen/`.

---

### Step 2: Update frontmatter

Change `status` from `seed` → `plant` (or `plant` → `tree`). Update `updated:` field.

### Step 3: Preserve lineage

If this idea derived from / relates to another idea, update `derived_from` (wiki-links) on both files.

### Step 4: Report

Summary: "Promoted {slug} from {old} to {new}. Next: {plant → tree | tree → graduate}."

## Rules

- Always write from research, not from prior knowledge alone. Use WebSearch for market / competitor context.
- Preserve the original Spark verbatim across stages.
- Don't skip a stage. Seed must go Plant first, Plant must go Tree before graduating.
- Never invent the frontmatter shape. Read `12-system/templates/Plant.md` / `Tree.md` and match it.
