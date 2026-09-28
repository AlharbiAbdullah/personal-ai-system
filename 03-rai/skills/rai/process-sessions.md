---
name: process-sessions
description: Drain pending session transcripts into the Memory v3 stores (rai-semantic + rai-episodic + rai-daily)
allowed-tools: Bash, Read, Glob
argument-hint: [--dry-run]
---

# Process Sessions — Memory v3 drain

Drain pending session transcripts from `~/helm/03-rai/semantic-memory/pending/` into the
Memory v3 ChromaDB stores — `rai-semantic` (distilled facts / decisions / summaries) and
`rai-episodic` (raw whole sessions) — then archive the processed files.

This is fully deterministic: a single script (`process_pending.py`) does the gating,
distillation (subscription Opus via `claude -p`), storage, routing, and archiving. There is
no manual per-session summarization to perform — run it and report.

## Arguments

| Argument | Description |
|----------|-------------|
| (none) | Distill + store + archive all gated pending sessions |
| `--dry-run` | Show what would be processed (no writes / no archive) |

## What it does, per pending session

1. **Gate** — THE shared policy (`hooks/lib/session_gate.py`, Memory v3): explicit-remember / memory-worthy → distill; archive-only / ephemeral pending files → archived WITHOUT distillation. A distill exit-2 ("too thin") also archives — never retries.
2. **Distill** (subscription Opus, `distill_session.py`) → `{summary, decisions[], facts[], preferences[]}`, each with verbatim evidence quotes + confidence.
3. **Store** → `store_episodic.py` (raw transcript → `rai-episodic`) + `store_semantic.py` (distill → `rai-semantic`, with dedup / supersede / provenance).
4. **Route** → `route_preferences.py` under py-chroma (preferences → `learned-candidates.jsonl`, SEMANTIC re-confirmation).
5. **Archive** → move the file to `~/helm/13-archive/historical-sessions/`.
6. After the batch: `export_index.py` (committed source), `render_memory_block.py` (frozen SessionStart snapshot), `index_daily.py` (live-capture daily logs → `rai-daily`).

Idempotent (episodic upserts, semantic dedups) — safe to re-run; a distill failure leaves
the file in `pending/` for the next run rather than losing it.

## Instructions

### Step 1 — List the pending queue

```bash
ls -la ~/helm/03-rai/semantic-memory/pending/*.json 2>/dev/null || echo "No pending files"
```

### Step 2 — Drain

```bash
python3 ~/helm/03-rai/hooks/scripts/process_pending.py
```

If the skill was invoked with `--dry-run`, append it:

```bash
python3 ~/helm/03-rai/hooks/scripts/process_pending.py --dry-run
```

### Step 3 — Report

Summarize the script's final `DONE: {...}` line:

```markdown
## Session Processing Complete
- Distilled + stored: N sessions
- Archived (trivial): M sessions
- Failed (left in pending): K sessions
```

## Notes

- Runs on the **producer (Ubuntu)** under the maintenance coordinator (`run-maintenance-ubuntu.sh`), and on demand via `/process-sessions`. The producer is the ONLY writer of the v3 stores. It mirrors `chromadb/` to the replica by rsync (`refresh_mac`); `rebuild_chromadb.py` rebuilds the stores from the committed `index/rai-semantic.jsonl` + the archive for disaster recovery.
