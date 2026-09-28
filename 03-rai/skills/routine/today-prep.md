---
name: today-prep
description: Morning day prep. Prioritizes tomorrow-plans from last night, fills gaps from vault + memory
allowed-tools: Bash, Read, Glob, Grep, Write
---

# Today Prep

Two parts of life: **Work** and **Personal**. Everything funnels into these.

## Instructions

### Step 1: Check Tomorrow Plans from Last Night

Check if yesterday's tomorrow-plans file exists:
`~/helm/02-ana/todos/tomorrow-plans/YYYY-MM-DD.md` (where YYYY-MM-DD is TODAY's date)

- If it exists: these items are **top priority**. They go first in the output.
- If it doesn't exist: skip to Step 2 (normal day prep).

### Step 2: Gather Context to Fill Gaps

**Read these sources:**

1. **Journals** (last 7 days): `~/helm/02-ana/journal/*.md`
   - Prose entries with no fixed sections (per `/routine journal` rules).
   - Scan the paragraphs for implicit plans, open loops, or commitments — work or personal.

2. **Work folder**: `~/helm/04-work/*.md`
   - All work-related

3. **Session memory** (last 7 days — recent sessions + live turn-capture logs):
```bash
~/helm/03-rai/semantic-memory/scripts/py-chroma.sh -c "
import chromadb
from pathlib import Path
from datetime import datetime, timedelta

client = chromadb.PersistentClient(path=str(Path.home() / 'helm/03-rai/semantic-memory/chromadb'))
col = client.get_collection('rai-episodic')
result = col.get(include=['metadatas'])
cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
rows = [m for m in result['metadatas'] if m.get('date', '') >= cutoff]
for m in sorted(rows, key=lambda m: m.get('date', ''), reverse=True):
    print(f\"[{m.get('date')}] {m.get('context','')} {m.get('project_name','')} ({m.get('message_count')} msgs, {m.get('duration_minutes')}m)\")
"
# the day-by-day detail lives in the live-capture logs:
ls ~/helm/03-rai/semantic-memory/daily/*.md 2>/dev/null | tail -7
```
Read the listed daily files for what actually happened each day (observer bullets per turn).

4. **Active projects**: `~/helm/05-projects/projects-moc.md` for the list. For a repo with `.project.toml`, its state is in the repo: the open change, or the first unticked item in `~/projects/{name}/specs/roadmap.md` (`mise run status` there prints both). `05-projects/active/{name}/` keeps only research and meeting notes.

### Step 3: Classify and Prioritize

Parse everything and classify:
- **Work**: job tasks, professional projects, career goals, learning for work
- **Personal**: family, health, hobbies, personal projects, life goals

**Priority order:**
1. Items from tomorrow-plans (if any). These were intentional. Respect them.
2. Urgent items from vault/sessions that weren't in tomorrow-plans.
3. Ongoing work that needs continuation.

Work is always priority — list work options first.

### Step 4: Generate Output

```markdown
## Today Prep - YYYY-MM-DD

> Source: tomorrow-plans / vault scan / both

### Work
1. [Most important/urgent work item] (planned)
2. [Second option]
3. [Third option]

### Personal
1. [Most important personal item] (planned)
2. [Second option]
3. [Third option]
```

If tomorrow-plans existed, mark each item that came from it with `(planned)` so the user can see what came from their evening planning vs what was pulled from context. Unmarked items are surfaced from vault/session context.

## Classification Logic

**Work signals**: 04-work/, job-related tags, professional projects, career learning
**Personal signals**: family, health, personal goals, hobbies, 02-ana/

Be smart about context. Use common sense.

## Output

1. Display the formatted output
2. Save to `~/helm/02-ana/todos/today-plans/YYYY-MM-DD.md` (overwrite if exists)
