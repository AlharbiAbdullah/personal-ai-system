---
name: process-inbox
description: Research each file in 01-inbox/, rate relevance, enrich in place, route to destination
allowed-tools: Read, Write, Edit, WebSearch, WebFetch, AskUserQuestion, Bash
---

# Process Inbox

Research each file in `~/helm/01-inbox/`. Enrich it with the research template, rate it by relevance to John, then route the enriched file to its destination folder.

## Instructions

### Step 0: Read John's context

Read these to ground rating decisions:
- `~/helm/02-ana/identity/goals.md`
- `~/helm/02-ana/identity/who-i-am.md`
- `~/helm/02-ana/identity/vision.md`

### Step 1: List files

```bash
ls -1 ~/helm/01-inbox/*.md 2>/dev/null
```

Skip `AGENTS.md`, and any file he says he keeps for later.

### Step 2: For each file

Read the file. Then fetch external context as needed (WebFetch for linked URLs, WebSearch for the topic).

Enrich the file in place with this template (appended or replacing thin content):

```markdown
# {title}

{original content or link}

---

## What is it
{1-2 sentences describing the subject}

## Why I should care
{1-2 sentences tied to John's goals / identity — quote specifics from identity files}

## Why it matters
{urgency / leverage / uniqueness — what makes this non-ignorable}

## Rating
**{A | B | C | D}** — {one-line justification of the rating, relative to John's priorities}

## Suggested destination
`{folder path}` — {why this folder}
```

### Step 3: Propose destination

A and B items get a destination, and so does a C item that cross-links to something already live. Every other C item, and every D item, goes to the delete batch (Step 5).

Based on the enriched content, propose one of:
- Reading material → `07-reading/` (create a curriculum folder if a book)
- Curriculum / course → `06-learning/`
- Tool / library / concept → `10-knowledge/{domain}/`
- Idea seed → `09-ideas/` (as Seed status)
- Project → `09-ideas/` as a Seed (only `/ideas → graduate` opens a kitchen); research for a project that already has a kitchen → `05-projects/kitchen/{name}/research/`
- Work item → `04-work/{engagement}/`

The routing table in [[13-capture-sweep]] step 4 wins where this list differs.

### Step 4: Confirm and move

Use AskUserQuestion: "Move to {destination}?" A no means another home or the delete batch, never "keep for later".

On confirmation: `mv` the enriched file to the destination whole, research included. Keep the same filename or rename to match destination conventions.

### Step 5: Delete batch

Show John the C and D deletions as one batch. Delete on his yes: a delete needs his go.

### Step 6: Report

After the run: `enriched: N, moved: N, deleted: N`. Then confirm both folders at [[13-capture-sweep]] step 5.

## Rating scale

A / B / C / D — relevance to John, NOT generic importance.
- **A** — directly serves a current goal or deep identity anchor.
- **B** — clearly relevant; worth acting on soon.
- **C**: adjacent. Deleted, unless it cross-links to something already live.
- **D** — weak tie; consider deleting instead of routing.

If you think an item is worse than D, propose deletion.

## Rules

- One file at a time. Research + rate + propose destination + move.
- Never auto-move without John's confirmation.
- Never fabricate the "why I should care" — if you can't tie it to identity, rate it lower.
- Full coverage: go through every file in inbox unless John says stop.
