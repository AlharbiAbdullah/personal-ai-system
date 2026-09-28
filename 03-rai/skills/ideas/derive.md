---
name: derive
description: Scan existing ideas for cross-connections; propose hybrids, spin-offs, or combinations
allowed-tools: Read, Bash, AskUserQuestion
---

# Derive

Find where existing ideas connect. Propose new Seeds that combine or spin off from existing ideas. Proactive lineage building.

## Instructions

### Step 1: Load all ideas

```bash
ls ~/helm/09-ideas/*.md
```

Skip `AGENTS.md`. Read every idea file. Capture for each: slug, status, domain, spark, core concept.

### Step 2: Find connections

Look for patterns:
- **Combinations** — two ideas that solve related problems, together better than apart.
- **Spin-offs** — one idea's research reveals a new angle that deserves its own Seed.
- **Cross-stage connections** — a Plant's research applies to a separate Seed.
- **Domain crossovers** — an AI idea that could plug into a data idea.

### Step 3: Propose

For each non-obvious connection, propose:

```markdown
## Connection: {title}

**From**: `[[{slug-a}]]` ({status-a}) + `[[{slug-b}]]` ({status-b})

**What they share**: {1-2 sentences}

**The combined angle**: {1-2 sentences — the new idea that emerges}

**Suggested action**:
- [ ] Create new Seed: `{new-slug}` (combining both)
- [ ] OR: Add `derived_from: [[{slug-b}]]` to {slug-a}
- [ ] OR: Note in both files' "Related" section
```

Show top 3-5 proposals. Don't flood.

### Step 4: Confirm actions

For each proposal, use AskUserQuestion:
- Create new Seed
- Update lineage
- Skip

### Step 5: Act on confirmed actions

For new Seeds: invoke the same logic as `start-seed.md` (write frontmatter, spark, what-is-it, trigger). Include `derived_from: [[{slug-a}]], [[{slug-b}]]`.

For lineage updates: edit frontmatter of the source ideas.

### Step 6: Report

Summary: "Found N connections. Created M new Seeds. Updated P lineage links."

## Rules

- Quality over quantity. 3 strong connections beats 10 weak ones.
- Never fabricate connections. If two ideas aren't really connected, don't force it.
- Always update `derived_from` / `spawned` on BOTH sides of a new link.
