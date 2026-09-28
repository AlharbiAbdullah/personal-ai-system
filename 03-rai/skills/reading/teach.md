---
name: teach
description: Generate a book lesson in the right type (Chapter / Law / Practice / Synthesis). Absorbs the book-pedagogy framework.
allowed-tools: Read, Write, WebSearch, WebFetch, AskUserQuestion, Bash
---

# Teach (Reading)

Generate a lesson for the current book curriculum. Use the right lesson type. Preserve named frameworks. Stories are sacred.

## Instructions

### Step 1: Identify curriculum and lesson

Ask John which curriculum, or infer. Read `~/helm/07-reading/{curriculum}/progress.md` for:
- Current lesson number
- Coverage map
- Tier structure

### Step 2: Determine lesson type

Pick ONE:
- **Chapter** — covers 1-2 book chapters. Most lessons.
- **Law/Rule** — covers 3-7 discrete units (laws, strategies, principles).
- **Practice** — personal application exercises at end of each tier.
- **Synthesis** — cross-cutting pattern recognition at tier boundaries or capstone.

### Step 3: Write the lesson

Use the right shape for the type:

## Type A: Chapter Lesson (default)

```markdown
---
type: learning
course: {curriculum-name}
tier: {number}
book: {book-title}
status: pending | in-progress | done
---

# Lesson NNN - {Title}

## Simplicity Theorem
> [One sentence capturing the core insight]

[2-3 sentences max. Plain language.]

## Simplicity Diagram
[Mobile-friendly ASCII, max 30 chars wide, vertical layout]

---

## The Big Picture
[30-second overview: what this lesson covers and why it matters in the book's arc]

## Core Ideas
[### subsections for each major concept in the chapter(s).
Cover the author's argument faithfully. Reasoning, not just conclusions.]

## Chapter Covered

### Chapter N: [Author's Chapter Title]

**The Argument**: [Author's central claim]

**The Key Stories**: [Named figures with specific events. Enough detail to retell.]

**The Strategies / Framework**: [Named strategies, numbered lists, or frameworks.
Preserve the author's structure.]

**The Danger**: [What goes wrong if misapplied or ignored]

## Key Quotes
[3-5 direct quotes from the book]

## Reflection Prompts
[2-3 questions forcing John to apply to his own life]

## Common Misreadings
[**"The wrong reading."** followed by the correction.]

## Summary
[Key takeaways, one bullet per major idea]
```

## Type B: Law/Rule Lesson

```markdown
# Lesson NNN - {Thematic Title}

## Simplicity Theorem / Diagram / ---

## The Big Picture
[What connects these laws/rules thematically]

## Laws Covered

### Law N: [Title]

**What the Author Says**: [Argument + reasoning]
**The Story**: [Named figure, specific event, enough detail to retell]
**Signs to Watch For**: [How this plays out in real situations]
**The Danger**: [Misapplication or reverse trap]

## Key Quotes
## How These Laws Connect
[Cross-references between the laws in this lesson]
## Reflection Prompts
## Summary
```

## Type C: Practice Lesson

```markdown
# Lesson NNN - Practice: {Title}

## Simplicity Theorem / Diagram / ---

## Purpose
[Why this exercise exists]

## Exercise 1: {Name}
[Specific instructions. Not vague prompts.]

## Exercise 2: {Name}
...

## What to Write Down
## Summary
## Moving Forward
```

## Type D: Synthesis Lesson

```markdown
# Lesson NNN - {Synthesis Title}

## Simplicity Theorem / Diagram / ---

## Purpose
## {Thematic sections}
[Cross-reference patterns across chapters/laws.
Show reinforcement. Identify families, clusters, tensions, operating principles.]
## Summary
```

## Core Rules

1. **Full coverage is non-negotiable.** Every chapter / law / unit must appear somewhere.
2. **Stories are sacred.** Include enough detail to retell. Named figures, specific events. "Darwin on the Beagle" not "a scientist who traveled."
3. **Named frameworks are sacred.** "The Seven Deadly Realities" stays. Don't paraphrase.
4. **Author's voice matters.** Preserve arguments. Don't sanitize or editorialize.
5. **Apply to real life.** Every lesson connects to John's work (Data/AI), ambition (1000x engineer), relationships, culture (the United States), personal growth.
6. **Pacing:** dense chapters (~35 pages) max 2 per lesson; very dense max 1; laws/rules 6-7; light chapters max 3.
7. **Per-chapter treatment standard:** argument + named story + framework + danger. Missing any = insufficient coverage.

## Cross-Mode Writing Rules

- Mobile-first diagrams (max 30 chars wide, vertical, `↓` arrows).
- No em dashes. Periods/commas/colons instead.
- No AI-typical words (leverage, utilize, streamline, robust, comprehensive, seamless, holistic, facilitate, empower, enhance, furthermore, moreover, additionally, delve, dive into, ensure, enable, vast, foster).
- Short paragraphs. Concrete numbers.
- From, not about.

### Step 4: Save + update progress

File: `~/helm/07-reading/{curriculum}/Lesson {NNN} - {Title}.md`.

Update progress.md:
- Lesson table: mark ✅ done.
- Current Lesson: advance to NNN+1.
- Coverage Map: check off covered chapters/laws.

## Rules

- Quality bar: John should finish a curriculum able to (1) explain thesis, (2) retell 5-10 stories, (3) apply to novel situations, (4) discuss critically, (5) connect to other things he knows.
- If a lesson requires skimming any story, it has too much content. Split.
