---
name: tomorrow-prep
description: Evening capture. List what you want to do tomorrow
allowed-tools: Read, Write, Glob
argument-hint: [items to add, or empty for interactive]
---

# Tomorrow Prep

Evening ritual. Dump what's on your mind for tomorrow before you sleep.

## Instructions

### If Arguments Provided

User passed items directly (e.g., `/routine tomorrow-prep finish API docs, review PR, gym`).

1. Parse the comma-separated items
2. Classify each as Work or Personal
3. Write the file

### If No Arguments

Ask the user: "What do you want to get done tomorrow?"

Wait for their response, then classify and write.

### Output Format

Save to `~/helm/02-ana/todos/tomorrow-plans/YYYY-MM-DD.md` where YYYY-MM-DD is **tomorrow's date**.

```markdown
---
date: YYYY-MM-DD
created: YYYY-MM-DD HH:MM
---

## Tomorrow Plans - YYYY-MM-DD

### Work
- [ ] Item 1
- [ ] Item 2

### Personal
- [ ] Item 1
- [ ] Item 2
```

Use checkboxes so Obsidian renders them as a task list.

### If File Already Exists

Append new items to the existing file under the correct section (Work/Personal). Don't overwrite what's already there.

**Dedup on append:** Before adding an item, check if a similar item already exists in the same section (case-insensitive substring match on the bullet text). If it does, skip the new item silently and report which duplicates were skipped at the end.

## Classification Logic

**Work signals**: code, API, deploy, review, meeting, docs (professional), pipeline, platform
**Personal signals**: gym, read, family, health, journal, organize, clean, cook, errands

When ambiguous, ask the user.

## Output

1. Display what was captured
2. Confirm the file path
