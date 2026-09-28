---
name: new-topic-note
description: Scaffold a Simplicity-Theory-compliant topic note with required structure
allowed-tools: Read, Write, AskUserQuestion, Bash
---

# New Topic Note

Create a topic note in `~/helm/10-knowledge/{domain}/`. Enforces Simplicity Theorem + Diagram + required sections.

## Instructions

### Step 1: Gather inputs

Ask John:
- **Topic title** — descriptive, Title Case (e.g., "SQL Fundamentals", "Containers & Docker").
- **Domain** — one of: `ai`, `data-engineering`, `devops`, `system-design`, `meta`. If none fit, propose a new domain and ask.

### Step 2: Check existing notes

Before scaffolding, grep `~/helm/10-knowledge/{domain}/` for overlapping topics. If one exists, propose merging into that note instead of creating a new one.

### Step 3: Ask for the theorem

Use AskUserQuestion: "What's the one-sentence Simplicity Theorem — the 'aha' for this topic?"

Push back if the answer is vague. Good theorems:
- "Give the LLM a cheat sheet before it answers." (RAG)
- "The filesystem is just a tree you can search with grep." (Unix)

Bad theorems (too abstract):
- "RAG augments LLM generation by retrieving relevant documents from a vector store using semantic similarity search."

Iterate until it's concrete.

### Step 4: Scaffold the note

File: `~/helm/10-knowledge/{domain}/{Topic Title}.md`

Template:

```markdown
---
type: topic
domain: {domain}
created: {YYYY-MM-DD}
tags: [{domain}, {relevant-tag}]
---

# {Topic Title}

## Simplicity Theorem

> {the one sentence from John}

{2-3 sentences max. Strip all complexity. A 12-year-old could follow.}

## Simplicity Diagram

```
{3-5 line ASCII, max 30 chars wide, vertical preferred}
```

---

## Why It Matters

{1 paragraph: the pressure that makes this topic worth learning}

## {Section 1: Core Concept}

{deep teaching — the author's argument with reasoning}

## {Section 2: ...}

{more sections, 1-8 total depending on topic breadth}

## Toolbox

{tools folded in here — commands, libraries, configs. Don't spin out as separate notes.}

## Connections

{wiki-links to related notes in prose, not as a footnote list.
"Because [[Containers & Docker|containers are ephemeral]], we need volumes."}

## Trade-offs

{what you give up; when NOT to use this}
```

### Step 5: Add to MOC

Check `~/helm/10-knowledge/_mocs/` for the relevant MOC. If it exists, add a wiki-link to the new note.

If no MOC exists for this topic cluster, propose creating one via the MOC template.

### Step 6: Report

"Scaffolded `{Topic Title}.md`. Simplicity Theorem captured. Sections are stubs — fill them via direct editing or subsequent conversations."

## Rules

- Never skip the Simplicity Theorem.
- Never let a vague theorem through — iterate.
- Never invent sections. Use the template.
- Always update the relevant MOC when adding a note.
- No AI-typical words (leverage, utilize, seamless, robust, comprehensive, holistic, facilitate, empower, enhance, furthermore, moreover, delve, etc.).
