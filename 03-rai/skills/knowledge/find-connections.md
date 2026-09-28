---
name: find-connections
description: Scan 10-knowledge/ for emergent-insight opportunities across notes
allowed-tools: Read, Bash, AskUserQuestion
---

# Find Connections

Proactive scan for notes that interact in ways worth capturing as Insight Notes. Complements `/knowledge insight` (which creates one specific insight given source notes).

## Instructions

### Step 1: Scope

Ask John:
- Full vault (all of `10-knowledge/`) — slow, thorough.
- One domain (`ai/`, `data-engineering/`, etc.) — moderate.
- Specific note — what does THIS note connect to?

### Step 2: Load notes in scope

```bash
ls ~/helm/10-knowledge/{scope}/*.md
```

Read each note's Simplicity Theorem + first section. Don't read all content (too much); the theorem + opening usually gives enough signal.

### Step 3: Scan for candidates

For each pair (or note-to-insight-candidate), check:
- **Same scenario, different angle** — two notes that both apply to the same problem.
- **Extension/specialization** — one note generalizes, another specializes.
- **Tension/trade-off** — two notes whose recommendations conflict in certain contexts.
- **Composition** — two notes whose techniques combine into a new capability.

### Step 4: Rank candidates

Score each candidate 1-3:
- **3** — a real insight; neither note says this alone.
- **2** — worth noting a connection, but no new knowledge emerges.
- **1** — same topic mentioned in both; not actionable.

Show only score-3 candidates (top 3-5).

### Step 5: Propose each candidate

For each, use AskUserQuestion:

```markdown
## Candidate: {title}

**Notes**: `[[{note-a}]]` + `[[{note-b}]]`
**Shared scenario / tension**: {1 sentence}
**What emerges**: {1 sentence — the new claim}
```

Options:
- **Create an Insight Note** (defer to `/knowledge insight`)
- **Just link the two notes** (cross-reference in the Connections section of each)
- **Skip** (not worth it)

### Step 6: Execute

For "Insight Note": hand off to `/knowledge insight` with the two source notes.
For "Just link": edit both notes' Connections sections to add the wiki-link.
For "Skip": nothing.

### Step 7: Report

Summary: "Scanned N notes. Proposed M candidates. Created P Insight Notes. Added Q cross-links."

## Rules

- Don't flood. 3-5 strong candidates > 20 weak ones.
- Never force connections. If pairs are unrelated, say so.
- Always show the "what emerges" sentence — it's the test for whether this is really an insight.
