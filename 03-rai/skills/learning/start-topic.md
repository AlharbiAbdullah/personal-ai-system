---
name: start-topic
description: Create a new learning topic folder with progress.md; ask mode; scaffold first lesson
allowed-tools: Write, AskUserQuestion, Bash
---

# Start Topic

Scaffold a new learning topic in `~/helm/06-learning/`. Creates the folder, progress.md, and the first lesson file.

## Instructions

### Step 1: Gather inputs

Ask John:
- **Topic name** — kebab-case (will be the folder name).
- **Method** — `review` (default: live drills, see `teach.md`) or `build` (legacy write-the-code, only if he asks for it).
- **Depth dial (mode)** — beginner / mid / expert (how much to assume; see `teach.md`).
- **Floor** — `yes` (a few hands-on reps at true foundations) or `no` (pure review). Default `yes` for a brand-new domain.
- **Shape** — flat lessons OR Phase/Module subfolders (pick based on estimated size: <20 lessons → flat, 20+ → subfolders).

### Step 2: Create structure

```bash
mkdir -p ~/helm/06-learning/{topic-slug}
```

If using Phase/Module structure, don't pre-create all phase folders — create the first one.

### Step 3: Write progress.md

File: `~/helm/06-learning/{topic-slug}/progress.md`

```markdown
---
type: progress-tracker
created: {YYYY-MM-DD}
method: {review | build}
mode: {beginner | mid | expert}
floor: {yes | no}
---

# {Topic Name} — Progress

## Current
- Lesson: (created per session)
- Last session: -
- Stuck on: nothing

## Method
{review | build}. For review: live sessions (concept + worked code, then drills answered before the reveal); lesson docs are records, not textbooks; `/learning quiz` re-tests weak spots on a delay. Depth dial = {mode}. Floor = {yes | no}. See `teach.md`.

## Lessons
| # | Lesson | Status | Date |
|---|--------|--------|------|
| - | (created per live session) | ⬜ | - |

## Weak areas log
(empty; populated from drills John misses; `/learning quiz` pulls from here)

## Mode History
- {YYYY-MM-DD}: Started. method={method}, mode={mode}, floor={floor}.
```

### Step 4: Write the curriculum overview

For `review` method, do NOT pre-create lesson files. Lesson docs are written per live session, as records. Instead create the planned path:

`~/helm/06-learning/{topic-slug}/00 - Curriculum Overview.md` — the planned lesson sequence (titles only) plus where this topic sits in any larger roadmap.

(Legacy `build` method only: scaffold `Lesson 001 - {subtopic}.md` with frontmatter + section headings, no content.)

### Step 5: Hand off

Tell John: "Topic scaffolded. Run `/learning teach` to start the first live session."

## Rules

- Default `method: review`. Only use `build` if John explicitly wants to write the code himself.
- Ask the depth dial and floor; don't assume.
- Use kebab-case for topic folder names.
- Don't fabricate lesson content. `start-topic` scaffolds the path; `teach` runs the session and writes the record.
