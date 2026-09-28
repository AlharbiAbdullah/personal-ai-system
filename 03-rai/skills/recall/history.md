---
name: history
description: Tiered recall (T0-T3) over the Memory v3 stores — rai-semantic + rai-daily + rai-episodic. Invoked via /recall router.
allowed-tools: Bash, Read, Grep
argument-hint: [--search "query"] [--sessions "query"] [--recent] [--project X] [--open SESSION_ID]
---

# History Recall — tiered cascade over rai-semantic + rai-episodic

Escalate-only recall. Each tier is cheaper than the next — **stop at the first tier
that answers**; never run a deeper tier "just in case".

| Tier | What | Cost |
|------|------|------|
| **T0** | The answer is already in loaded context (identity, memory block, daily-log tail, per-prompt pointers) | free |
| **T1** | `rai-semantic` — distilled facts/decisions/summaries · `rai-daily` — live turn-capture bullets | one embed query |
| **T2** | `rai-episodic` — whole-session pointers ("which session was that?") | one embed query |
| **T3** | Verbatim receipts — the full session text | file read |

## T0 — check context first (always, before any command)

Before running anything below: is the answer already in this session's context? The
SessionStart block (identity + memory block) and any `[memory v3]` pointer injections
count. If yes — answer from context and **stop**. Only proceed when the answer is
genuinely missing.

## Arguments

| Argument | Tier | Description |
|----------|------|-------------|
| `--search "query"` | T1→(T2) | Semantic search over distilled memory; escalate to sessions only if facts don't answer |
| `--sessions "query"` | T2 | Find the relevant past session(s) directly |
| `--recent` / (none) | T1+T2 | Overview: top durable facts + most recent sessions |
| `--project X` | T2 | Sessions filtered by project/context name |
| `--open SESSION_ID` | T3 | Full verbatim conversation of one session |

## T1 — distilled memory + live log (`--search`)

```bash
~/helm/03-rai/semantic-memory/scripts/py-chroma.sh ~/helm/03-rai/hooks/lib/memory_retrieval.py semantic "QUERY_HERE"
```

For recent day-to-day detail (today/yesterday's turns, not yet distilled), also query
the live-capture blocks. Daily is the RECENCY BUFFER: blocks whose session already has
rai-semantic rows carry `distilled: true` and are down-ranked automatically — prefer the
semantic (quality) record for those; daily shines for what the batch hasn't reached yet:

```bash
~/helm/03-rai/semantic-memory/scripts/py-chroma.sh ~/helm/03-rai/hooks/lib/memory_retrieval.py daily "QUERY_HERE"
```

Semantic returns top-8 facts/decisions/summaries as JSON: `content`, `type`, `confidence`,
`source_session`, `date`, `score`. Daily returns turn-capture bullets with `date`, `time`,
`session`. If this answers the question, report and stop.
To see a fact's evidence quotes, fetch its full record:

```bash
~/helm/03-rai/semantic-memory/scripts/py-chroma.sh -c "
import chromadb, json
from pathlib import Path
col = chromadb.PersistentClient(path=str(Path.home()/'helm/03-rai/semantic-memory/chromadb')).get_collection('rai-semantic')
r = col.query(query_texts=['QUERY_HERE'], n_results=5, where={'status': 'active'}, include=['metadatas'])
for md in r['metadatas'][0]:
    print(f\"[{md.get('type')}/{md.get('confidence')}] {md.get('content')}\")
    print(f\"  evidence: {md.get('evidence')}\")
    print(f\"  source: {md.get('source_session')} ({md.get('source_date')})\")
"
```

## T2 — session pointers (`--sessions`, or escalation from T1)

```bash
~/helm/03-rai/semantic-memory/scripts/py-chroma.sh ~/helm/03-rai/hooks/lib/memory_retrieval.py episodic "QUERY_HERE"
```

Returns top-5 sessions: `session_id`, `date`, `context`, `project_name`,
`message_count`, `relevance`, `via`. `via` says how the pointer was found:
`direct` (whole-session embedding match) or `semantic` (a distilled fact's
source session — the bridge that answers question-shaped queries the session
blobs miss). Report the pointers; open one (T3) only if the user needs the
actual conversation content.

### `--project X` (metadata filter, no embedding)

```bash
~/helm/03-rai/semantic-memory/scripts/py-chroma.sh -c "
import chromadb
from pathlib import Path
col = chromadb.PersistentClient(path=str(Path.home()/'helm/03-rai/semantic-memory/chromadb')).get_collection('rai-episodic')
g = col.get(include=['metadatas'])
rows = [m for m in g['metadatas'] if 'PROJECT_HERE'.lower() in (m.get('project_name','') + ' ' + m.get('context','')).lower()]
for m in sorted(rows, key=lambda m: m.get('date',''), reverse=True)[:15]:
    print(f\"{m.get('date')} | {m.get('session_id')} | {m.get('project_name')} ({m.get('message_count')} msgs, {m.get('duration_minutes')}m)\")
"
```

## `--recent` / no arguments — overview

```bash
~/helm/03-rai/semantic-memory/scripts/py-chroma.sh ~/helm/03-rai/hooks/lib/memory_retrieval.py start
```

Prints the tiered block: top durable facts by importance + the most recent sessions.

## T3 — verbatim receipts (`--open SESSION_ID`)

The episodic store holds the full conversation text:

```bash
~/helm/03-rai/semantic-memory/scripts/py-chroma.sh -c "
import chromadb
from pathlib import Path
col = chromadb.PersistentClient(path=str(Path.home()/'helm/03-rai/semantic-memory/chromadb')).get_collection('rai-episodic')
r = col.get(ids=['SESSION_ID_HERE'], include=['documents', 'metadatas'])
if not r['ids']:
    print('not in episodic store — fall back to the archive (below)')
else:
    md = r['metadatas'][0]
    print(f\"{md.get('date')} | {md.get('project_name')} | {md.get('duration_minutes')}m | files: {md.get('files_modified')}\")
    print(r['documents'][0][:8000])
"
```

Fallbacks when the session isn't in the store (archived-only, or pre-gate):

```bash
# vault archive (canonical)
grep -l "SESSION_ID_HERE" ~/helm/13-archive/historical-sessions/*.json | head -3
# native Claude transcript (machine-local, auto-cleaned ~30d)
ls ~/.claude/projects/*/SESSION_ID_HERE.jsonl 2>/dev/null
```

Then `Read` the matched file (archive JSONs hold `messages[]`; read selectively —
they can be large).

## Output format

```markdown
## 🧠 Recall — [what was asked]

[T-level used and findings; facts with confidence + source date, or session pointers]

*Tier stopped at: T1|T2|T3 · query: "..."*
```

## Log the tier outcome (always, last step)

T1/T2 CLI queries self-log (`event: query`); this step records the OUTCOME (which tier
answered, hit or miss) through the SAME single writer — never append to the file directly:

```bash
~/helm/03-rai/semantic-memory/scripts/py-chroma.sh ~/helm/03-rai/hooks/lib/memory_retrieval.py outcome T1 hit
```

(`outcome <T0|T1|T2|T3> <hit|miss>` — one schema, one writer, tz-aware timestamps.)

## Schema reference (v3 stores)

**rai-semantic** metadata: `type` (summary|decision|fact), `content`, `source_session`,
`source_date`, `confidence` (high|medium|low), `evidence` (json quotes), `category`,
`tags`, `supersedes`, `superseded_by`, `last_confirmed`, `confirmation_count`,
`status` (active|archived — always filter `status=active`).

**rai-daily** metadata: `date`, `time`, `session` (8-char prefix), `file`. Document =
`[date time] ` + the turn-capture bullets of one `### HH:MM (session:x)` block. Batch-indexed
from `semantic-memory/daily/*.md` by `index_daily.py`; the recency buffer of T1.

**rai-episodic** metadata: `session_id`, `date`, `context`, `project_name`,
`duration_minutes`, `tools_summary` (json), `files_modified` (json), `message_count`.
Document = topic header + full conversation.

Full contract: `~/helm/03-rai/semantic-memory/CHROMADB-SCHEMA.md`.
