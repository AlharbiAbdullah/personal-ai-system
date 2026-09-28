---
name: journal
description: Occasional trigger-based journal - ask one question, document the answer
allowed-tools: Write, AskUserQuestion, Bash, Read
---

# Journal

One question. You talk, I write it up like a journal entry.

## Cadence: occasional, not daily

Occasional and trigger-based, not a daily obligation. No calendar reminder
fires for it.

`semantic-memory/daily/` already records what happened, every session, automatically.
The journal's job is the part no machine produces: what he decided, what changed his
mind, what he is avoiding.

Write when one of these is true:
- He made a decision, or refused to make one he should have
- Something changed his mind
- A pattern hit its third repeat
- He feels off and does not know why

A day with nothing on this list does not need an entry. One ordinary day carries no
signal on its own. A run of identical ones does, and `/routine/weekly-retro` is the
floor that catches those in bulk. Never nudge him toward writing daily, and never
frame a gap between entries as a lapse.

## Instructions

### Step 0: Determine Journal Date

Use Bash to run `date` and get the current time.

**Cutoff rule: 5:00 AM**
- Before 5:00 AM → journal belongs to **yesterday**
- 5:00 AM or later → journal belongs to **today**

### Step 1: Ask One Question

Use AskUserQuestion with a single open-ended prompt. Pick ONE naturally:

- "How was your day?"
- "What's on your mind?"
- "Tell me about today."
- "What happened today?"

Let them dump everything at once.

### Step 2: Write the Entry

Take their raw response and turn it into a clean journal entry — 1 to 3 paragraphs, prose style. Like writing in a real diary.

**No headers. No sections. No bullet points. Just paragraphs.**

**Filename**: `~/helm/02-ana/journal/<YYYY-MM-DD>.md` (use the resolved JOURNAL_DATE from Step 0)

**Writing Style**:
- First person, casual, honest
- Sound like them, not like a writer
- Short sentences. Direct.
- Light cleanup only: fix typos, trim filler, tighten run-on sentences. Preserve their voice, choices, and content. Do NOT add insight, structure, or polish they didn't put there.
- As long or short as what they gave you. Don't force a length.

**Format**:

```markdown
---
date: JOURNAL_DATE
time: HH:MM
type: journal
---

# JOURNAL_DATE

[Their thoughts, rewritten. Clean prose. No fixed length.]
```

The `time` field records the actual clock time (24h format).

### Step 3: Confirm

Show the file path. If the date was shifted (late-night writing), mention it.

## Notes

- If a journal entry already exists for that date, READ it first and APPEND below with a `---` separator and the time, preserving the original
- Don't add anything they didn't say. Don't pad. Don't embellish.
- Be warm but brief in prompts
