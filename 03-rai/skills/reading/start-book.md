---
name: start-book
description: Scaffold a book curriculum with progress.md, tier plan, first lesson stub
allowed-tools: Write, AskUserQuestion, Bash, WebSearch
---

# Start Book

Create a new book curriculum in `~/helm/07-reading/`.

## Instructions

### Step 1: Gather inputs

Ask John:
- **Book title + author** (full).
- **Curriculum folder name** (kebab-case, e.g., `thinking-fast-and-slow`, `robert-greene-curriculum` for multi-book author).
- **Book type** — for curriculum shape:
  - **Chaptered** (most non-fiction) → Chapter-lesson dominant.
  - **Many discrete units** (48 Laws, 33 Strategies, etc.) → Law/Rule-lesson dominant.
  - **Multi-book author** (Robert Greene: 48 Laws + Human Nature + Mastery) → Tier-organized.

### Step 2: Web-research the book structure

Use WebSearch for the book's table of contents / chapter list. You need:
- Chapter count + titles
- Named frameworks the author uses (preserve these exactly)
- Key historical stories / examples (Greene = named figures; Kahneman = experiments)

Confirm with John before proceeding.

### Step 3: Propose a tier plan

Based on book size + type:

**Small book (~200 pages)**: no tiers, 10-15 lessons.
**Medium book (300-500 pages)**: 1 tier, 15-25 lessons.
**Large or multi-book**: tiers (see AGENTS.md examples).

Include:
- Chapter/Law lessons (the core content)
- 1 Practice lesson per tier (personal application)
- 1 Synthesis lesson per tier boundary + 1 capstone at end

Example for a 48-Laws-of-Power style book:
```
Tier 1: Laws 1-10
  001-002 (5 laws each, grouped thematically)
  ...
  009 Practice: Power Audit
  010 Synthesis: Force-vs-Finesse patterns
```

### Step 4: Create structure

```bash
mkdir -p ~/helm/07-reading/{curriculum-slug}
```

Write `~/helm/07-reading/{curriculum-slug}/progress.md`:

```markdown
---
type: progress-tracker
created: {YYYY-MM-DD}
curriculum: {book-title-or-author}
---

# {Curriculum Name} — Progress

## Current Status
- Current Lesson: 001 - {first title}
- Last Session: {YYYY-MM-DD}
- Status: Not Started

## Where We Left Off
(blank)

## Coverage Map
{for books with discrete units, show which lesson covers which units}

## Lessons
| # | Lesson | Status | Date |
|---|--------|--------|------|
| 001 | {first} | ⬜ | - |
```

### Step 5: Scaffold first lesson

Create `Lesson 001 - {first subtopic}.md` with YAML frontmatter only (no content yet). `teach.md` fills it.

### Step 6: Hand off

"Curriculum scaffolded. Run `/reading teach` for Lesson 001."

## Rules

- Always verify book structure via WebSearch before scaffolding.
- Named frameworks from the author — preserve exact names in the plan.
- Don't pre-generate all lesson titles; let `teach` discover them as we go.
