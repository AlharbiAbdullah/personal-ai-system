---
name: weekly-planner
description: Monday ritual. Generate a weekly work plan in 04-work/work-plans/ named by ISO week
allowed-tools: Read, Write, Bash, AskUserQuestion
---

# Weekly Planner

Generate the next week's plan. Reads last week's plan + identity goals + any open engagement threads.

## Instructions

### Step 1: Resolve ISO week

```bash
date +"%G-W%V"
```

Filename: `~/helm/04-work/work-plans/{ISO-week}.md` (e.g., `2026-W17.md`).

If a file for the current week already exists, ask John whether to replan (overwrite) or continue (edit).

### Step 2: Gather context

Read:
- Last week's plan (previous ISO week file, if it exists).
- `~/helm/02-ana/identity/goals.md` — current goals.
- `ls ~/helm/04-work/` — list engagements.

### Step 3: Ask John

Use AskUserQuestion: "What are this week's non-negotiables?" — free-form. No multi-choice ceremony.

### Step 4: Write the plan

Template:

```markdown
# Week Plan — {ISO week} ({Monday date} to {Sunday date})

## Non-negotiables
{John's top 1-3 items}

## By engagement
{For each engagement folder in 04-work/, a section with:}
### {engagement}
- {specific task / deliverable for the week}

## Personal / skills
{1-3 items for skill growth, brain work, etc.}

## Review cadence
- Daily: 07:00-10:30 deep-work block.
- Friday end-of-day: retro (what shipped, what blocked, what carries).
```

### Step 5: Link context

If the plan references a specific engagement doc, link to it with a wiki-link: `[[04-work/{engagement}/{file}]]`.

## Rules

- One file per ISO week. Don't split across files.
- Don't merge personal life goals here — that's `/life` territory. Work + work-adjacent skill growth only.
- Keep it short — a plan you won't read is useless.
