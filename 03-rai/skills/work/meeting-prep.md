---
name: meeting-prep
description: Pre-meeting briefing and agenda generator. Reads engagement context
allowed-tools: Read, Write, AskUserQuestion, Bash
---

# Meeting Prep

Before a meeting, generate a briefing: context, questions to ask, decisions needed, risks to watch. Save alongside the engagement.

## Instructions

### Step 1: Identify the engagement

Ask John which engagement the meeting is for. List options from `ls ~/helm/04-work/` (subfolders only).

### Step 2: Read engagement context

Load every `.md` file in `~/helm/04-work/{engagement}/` that looks relevant (PRDs, proposals, prior meeting notes).

List the open follow-ups first. They are the unchecked lines in the Follow-ups sections of the engagement's prior meeting files and its close-out note. They head the new briefing.

### Step 3: Ask for meeting specifics

Use AskUserQuestion:
- Who's in the meeting?
- What's the stated objective?
- Any pre-reading you want me to fold in?

### Step 4: Write the briefing

Save to `~/helm/04-work/{engagement}/meeting-{YYYY-MM-DD}-{topic-slug}.md`.

Template:

```markdown
# Meeting: {topic} — {YYYY-MM-DD}

## Attendees
{names + roles}

## Objective
{stated objective, 1 sentence}

## Context (from engagement docs)
{3-5 bullets summarizing relevant prior work, decisions, open threads}

## Proposed agenda
1. {item}
2. {item}
3. {item}

## Questions to ask
- {specific, pointed question tied to a decision or information gap}

## Decisions needed
- {decision} — {what's at stake}

## Risks / watch-outs
- {what could go wrong, what to listen for}

## Follow-ups (blank — fill after the meeting)
- [ ]
```

### Step 5: After the meeting

The Follow-ups section stays blank until the debrief. The debrief appends to this same file: [[11-meeting-to-followthrough]] step 3.

## Rules

- Briefings live inside the engagement folder, not at `04-work/` root.
- Don't invent participants or context — ask.
- Keep "Questions to ask" specific. Generic questions waste the meeting.
