---
name: process-landing
description: Walk each file in 00-landing/ interactively, promote to 01-inbox/ or delete
allowed-tools: Read, AskUserQuestion, Bash
---

# Process Landing

Walk every file in `~/helm/00-landing/` with John. Each file has two exits: promote to `01-inbox/` or delete. No other outcome.

## Instructions

### Step 1: List files

```bash
ls -1 ~/helm/00-landing/*.md 2>/dev/null
```

Skip `AGENTS.md`. Skip hidden files.

If the list is empty, tell John the landing is clear and stop.

### Step 2: For each file

Read the file. Show its full contents to John in a short, readable format (no summary — let him see what he wrote).

Ask one question using AskUserQuestion:

- **Promote to inbox** — needs research / deserves attention. `mv` to `~/helm/01-inbox/`.
- **Delete** — not worth it. `rm` the file.
- **Skip**: only when he says he keeps the file for later. It stays in landing. Never offer Skip on your own.
- **Stop** — end the run.

### Step 3: Act on the answer

- Promote: `mv ~/helm/00-landing/{file} ~/helm/01-inbox/{file}`
- Delete: `rm ~/helm/00-landing/{file}`
- Skip or Stop: do nothing (or exit loop).

### Step 4: Report

After the run, print a one-line summary: `promoted: N, deleted: N, skipped: N`. The sweep goes on at [[13-capture-sweep]] step 2, the inbox.

## Rules

- Never batch-move or batch-delete. One file at a time. John's call on every file.
- Never edit file contents during triage.
- If a file is >10 KB (unusual for landing), show only the first 50 lines + note the full size.
