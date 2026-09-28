---
name: audit-coverage
description: Verify a book curriculum covers every chapter/law with full treatment. Flags gaps before "done".
allowed-tools: Read, Bash, WebSearch, AskUserQuestion
---

# Audit Coverage (Reading)

Book curricula have strict coverage bars. Before declaring "done", verify every chapter/law has:
1. The author's argument (with reasoning)
2. At least one named story (specific historical figure, specific event, retellable)
3. The framework or strategies (any numbered lists / phases / methods, preserved in full)
4. The danger (what goes wrong when misunderstood or misapplied)

Missing any of these four = inadequate coverage.

## Instructions

### Step 1: Identify curriculum

Ask John which curriculum. Read `~/helm/07-reading/{curriculum}/progress.md`.

### Step 2: Get the book's canonical structure

Use WebSearch for the book's table of contents / chapter list / units list. Confirm with John.

Build the canonical list of units:
- For chaptered books: chapter titles.
- For law/rule books: law numbers + titles.
- For multi-book curricula: per-book unit lists.

### Step 3: Map canonical units to lessons

For each canonical unit, find the lesson (or synthesis) that covers it.

```
Law 1: Never Outshine the Master      → Lesson 001
Law 2: Use Enemies to Your Advantage  → Lesson 001
Law 3: Conceal Your Intentions        → Lesson 002
...
Law 48: Assume Formlessness           → Lesson 008 (or Synthesis)
```

### Step 4: Audit each lesson

Read every lesson file. For each unit it claims to cover, verify all four treatment elements are present:

- ✅ Argument — named, with reasoning
- ✅ Story — named figure + specific event
- ✅ Framework / strategies — preserved in full (no compression of "7 strategies" → "the key strategies")
- ✅ Danger — what goes wrong

### Step 5: Check named-framework preservation

Scan all lessons for named frameworks the author gives. Verify they appear with the exact author's name, not paraphrased.

Example: "The Seven Deadly Realities" stays that way, not renamed to "seven common tragedies."

### Step 6: Report

```markdown
# Audit: {curriculum}

## Coverage map
- Chapter 1: ✅ fully covered in Lesson 001.
- Chapter 2: ⚠️ covered in Lesson 001 but missing "The Danger".
- Chapter 3: ❌ not covered in any lesson.

## Named frameworks
- "The Seven Deadly Realities" — ✅ preserved exactly in Lesson 003.
- "Negative Capability" — ⚠️ paraphrased as "staying open" in Lesson 005. Fix.

## Story quality
- Lesson 002: "a historical figure who traveled" — ❌ generic. Needs named figure + specific event.

## Overall
{pass | needs N fixes | fail}
```

### Step 7: Offer to fix

For each gap, offer to regenerate the lesson via `/reading teach`. Don't auto-fix.

## Rules

- Strict four-element check. "Mostly covered" is not covered.
- Named frameworks: exact preservation. No synonyms.
- Generic stories ("a scientist who did something") = failure. Named + specific event required.
