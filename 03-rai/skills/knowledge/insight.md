---
name: insight
description: Propose an Insight Note from two or more existing notes (always propose before creating)
allowed-tools: Read, Write, AskUserQuestion, Bash
---

# Insight

Two existing notes interact in a useful way. Propose a new Insight Note that captures what neither note alone contains.

## Instructions

### Step 1: Identify the source notes

Ask John which notes sparked the insight (2+ notes). Read each.

### Step 2: Articulate the insight

In one sentence: what does the intersection of these notes reveal that neither says alone?

Examples of real insights:
- "[[RAG]] + [[Prompt Caching]] → caching the retrieved context is wasted unless the retrieval is stable across calls."
- "[[Docker Volumes]] + [[12-Factor Config]] → mounting a config file at runtime violates 12-factor's 'config in environment' principle."

Examples of non-insights (skip these):
- Just listing that two topics exist.
- A summary of both notes.
- A generic 'these are related' statement.

If no real insight emerges, tell John so. Don't force one.

### Step 3: Propose before creating

Show John the proposed insight in a single block:

```markdown
## Proposed Insight

**Title**: {1-line claim}
**Sources**: `[[{note-a}]]` + `[[{note-b}]]`
**What neither says alone**: {1-2 sentences}
**Destination**: `10-knowledge/{domain}/{slug}.md` OR inside an existing MOC under a new heading.
```

Ask: "Create this Insight Note?" (yes / no / revise).

### Step 4: If approved, write the note

File: `~/helm/10-knowledge/{domain}/{Insight Title}.md`

```markdown
---
type: insight
emerged_from: [[{note-a}]], [[{note-b}]]
created: {YYYY-MM-DD}
tags: [insight, {domain}]
---

# {Insight Title}

## Simplicity Theorem

> {the 1-line claim}

{the insight in 2-3 sentences}

## Simplicity Diagram

```
{3-5 line visual showing the intersection}
```

---

## Why This Matters

{what becomes possible or avoided because of this insight}

## The Sources

### From [[{note-a}]]
{the key claim this note contributes}

### From [[{note-b}]]
{the key claim this note contributes}

## The Synthesis

{the new knowledge that only emerges from combining them}

## Applies When

{specific scenarios where this insight triggers action}

## Doesn't Apply When

{the limits — when the insight fails}
```

### Step 5: Update the source notes

In each source note's "Connections" section, add a wiki-link to the Insight Note:

```
Because [[{Insight Title}|this-and-that together imply X]], ...
```

### Step 6: Report

"Insight Note created: `[[{Insight Title}]]`. Linked from `[[{note-a}]]` and `[[{note-b}]]`."

## Rules

- Always propose before creating. John approves.
- Never fabricate an insight. If the intersection is thin, say so.
- Always link bidirectionally — the new note AND the source notes must cross-reference.
- Follow the Simplicity Theorem rule like any other note.
