# Semantic Memory

The vector layer of Memory v3. It lets Rai recall past context by meaning, not just by
filename. **It ships empty** and is built from your own usage. Nothing is pre-seeded.

Memory v3 is a hybrid. Live writes only ever append to plain TEXT (the daily logs under
`semantic-memory/daily/`). The vector store is derived from that text plus your session
history and is rebuilt locally, so it is never committed and never synced as a binary.

## The four collections

The store is one ChromaDB instance holding four collections, each with a distinct job.

- `rai-semantic`: distilled facts, decisions, and session summaries. The quality record.
  This is what recall leans on for durable knowledge.
- `rai-episodic`: raw whole sessions, kept verbatim as pointers for deep retrieval.
- `rai-daily`: the live-log blocks. Each turn's observer bullets from the daily TEXT files
  get indexed here. This is the recency buffer. Blocks whose session has already been
  distilled are marked and down-ranked, so the semantic collection wins on quality.
- `rai-preferences`: a derived, deduplicated index of learned preferences.

## Layout

- `pending/`: a queue of items waiting to be embedded. Session processing drops JSON here
  and the embed step consumes it.
- `daily/`: the append-only TEXT daily logs (`YYYY-MM-DD.md`). This is the live capture
  surface and the source of truth for the daily collection.
- `scripts/`: the helper scripts that build and query the store, including `py-chroma.sh`.
- `chromadb/`: the actual vector database. **Not included and gitignored.** It is a large
  binary derived from `pending/`, the daily logs, and your session memory, so it is rebuilt
  rather than shipped.

## Running the tools

The system python has no `chromadb` module, so the scripts do not touch it. `py-chroma.sh`
runs each python script in an isolated `uv` environment (python 3.12 with `chromadb`
installed, cached under `~/.cache/uv` so repeat runs are fast). Call a script through it:

```
scripts/py-chroma.sh scripts/your-script.py [args...]
```

## Building it

You do not have to do anything up front. The store builds itself as you use the system and
run `/process-sessions`. The first run creates `chromadb/` locally.

To rebuild from scratch, run the embed step in `scripts/` (the SessionStart hook and
`/process-sessions` call it for you). Because everything is derived, deleting `chromadb/` is
safe. It regenerates from `pending/`, the daily logs, and your memory.

## Why it is gitignored

The embeddings index was historically the single biggest source of git bloat, since it is
re-snapshotted whole on every change. The real information lives in your TEXT memory and
session history. This is just a fast lookup layer. Keep it out of git and let each machine
rebuild it.

---

Last updated: 2026-07-07
