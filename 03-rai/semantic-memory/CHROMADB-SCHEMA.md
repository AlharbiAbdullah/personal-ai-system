# ChromaDB schema and the distill contract

The contract every memory script follows. Design: `03-rai/MEMORY-ARCHITECTURE.md`. All collections
live in `03-rai/semantic-memory/chromadb/` (gitignored). The embedding is the ChromaDB default
(`all-MiniLM-L6-v2`), and the four memory collections are created with `hnsw:space: cosine`. Only
the hub coordinator's batch steps write them; live hooks never do.

## Collections

### `rai-semantic`: distilled facts, decisions, summaries

One record per summary, decision or fact.

- **id**: `{type}-{sha256(content)[:16]}-{6 random hex}` (content lowercased and stripped before
  hashing)
- **document**: the claim text (embedded)
- **metadata**: `type` (summary, decision, fact), `content`, `source_session`, `source_date`,
  `confidence` (high, medium, low), `evidence` (JSON list of quotes), `category`, `tags`
  (comma-joined), `supersedes` (JSON list of ids), `superseded_by`, `last_confirmed`,
  `confirmation_count`, `status` (active, archived)
- **writer**: `hooks/scripts/store_semantic.py --distill-json <path>`
- **dedup**: an item within cosine distance 0.10 (`DEDUP_DISTANCE`) of an active record bumps that
  record's `confirmation_count` and `last_confirmed`; no new row
- **supersede**: each item's own `supersedes` ids are set to `status=archived` with
  `superseded_by` pointing at the new row. Rows are never hard-deleted.
- **committed source**: `index/rai-semantic.jsonl`, written by `export_index.py` after every drain
  that distilled something: one `{id, document, metadata}` row per record, sorted by id, keys sorted
- **ranking**: `hooks/lib/memory_retrieval.py` `query_semantic` (active rows only)

### `rai-episodic`: whole sessions (the receipts)

One record per session.

- **id**: `session_id`
- **document**: a topic header (`[context] project_name`, then `ASKS:` with the first six user
  messages, 200 chars each), followed by the full user and assistant text. The full text is stored;
  the header leads because the embedding model reads only the start of the document.
- **metadata**: `session_id`, `date`, `context`, `project_name`, `duration_minutes`, `tools_summary`
  (JSON), `files_modified` (JSON), `message_count`
- **writer**: `hooks/scripts/store_episodic.py --session-json <path>` (upsert, idempotent)
- **rebuild**: `rebuild_chromadb.py` from `13-archive/historical-sessions/`, for the sessions
  `lib/session_gate.py` classes for episodic

### `rai-daily`: live-capture blocks

One record per `### HH:MM (session:xxxxxxxx)` block in `semantic-memory/daily/*.md` (the
turn-capture observer bullets). Derived from those committed files and never exported.

- **id**: `sha256(date|time|session|text)[:16]` (content-addressed, so re-indexing is idempotent)
- **document**: `[date time] bullets`
- **metadata**: `date`, `time`, `session` (8 chars), `file`, `distilled` (true when the session
  already has rai-semantic rows; recall down-ranks those blocks)
- **writer**: `hooks/scripts/index_daily.py`, at the end of every drain; a rebuild is a re-run

### `rai-preferences`: self-evolve index

Embeddings of the `learned-candidates.jsonl` contents. Never queried for recall.

- **id**: the candidate id (`sha256` of the normalized text, 16 chars); **document**: the
  preference text; no metadata
- **used for**: semantic re-confirmation (distance at most `RECONFIRM_DISTANCE`, 0.25) and the
  weekly merge (distance at most `MERGE_DISTANCE`, 0.15), both in `hooks/scripts/route_preferences.py`
- **writers**: `route_preferences.py` (upsert on a new candidate) and `curate_candidates.py` (syncs
  in place: deletes ids that left the non-retired set, upserts the rest)

### `sanity-probe`: write probe

Used only by `/rai sanity` STORE-3, which adds a `probe-<uuid>` row, reads it back and deletes it.
It holds no rows between runs and is never dropped, because every dropped collection leaves an
orphan HNSW directory on disk.

## The DISTILL JSON

`hooks/scripts/distill_session.py` produces it from one session. The instruction lives in that
file's `PROMPT` (per window) and `REDUCE_PROMPT` (the merge pass); this doc does not copy them.

```json
{
  "session_id": "...", "date": "YYYY-MM-DD",
  "summary": "3-6 sentence summary",
  "decisions": [
    {"content": "the decision with its rationale", "confidence": "high|medium|low",
     "evidence": ["verbatim quote"], "category": "", "tags": [], "supersedes": []}
  ],
  "facts": [
    {"content": "an atomic durable state", "confidence": "high|medium|low",
     "evidence": ["verbatim quote"], "category": "technical|preference|project|reference",
     "tags": [], "supersedes": ["id of the rai-semantic row this replaces"]}
  ],
  "preferences": [{"content": "how Rai should behave", "confidence": "", "evidence": []}],
  "supersedes": []
}
```

The script sets `session_id` and `date` itself. It adds `sampling` when a long transcript was
sampled, and `sdd_repo` when the H27 repo rule applied. The top-level `supersedes` is part of the
prompt's shape, but no script reads it: `store_semantic.py` applies each item's own `supersedes`.

Each fact and decision carries 1 to 3 verbatim quotes because the prompt demands them. No code
checks the quotes against the transcript: they are stored as provenance in the `evidence` metadata.

### How a distill runs

- **Model**: `--model opus` through `hooks/lib/claude_cli.py` `run_claude` (subscription
  `claude -p`, 300 s per call).
- **Windows**: a transcript up to 60,000 chars (`MAX_TRANSCRIPT_CHARS`) is one call. A longer one is
  split into 60,000-char windows, each distilled with a "window i of n" note. Beyond
  `MAX_WINDOWS` (10), ten evenly spaced windows are sampled across the whole transcript. One
  `REDUCE_PROMPT` pass then merges the partials into the final JSON.
- **Bullets map**: `--bullets-file` carries the session's daily-log blocks (written by
  `process_pending.py`). The first 8,000 chars go into every prompt as a turn-by-turn observer map.
- **Repo rule (H27)**: the session's cwd comes from the session JSON, else its native transcript.
  When it sits in a project-init repo, `sdd_note` adds the routing rule to the prompts. `apply_repo_rule`
  then enforces it on the output. The summary becomes one `worked in <repo>` pointer line and
  `decisions` is emptied. Facts of category `project` are dropped. Items and quotes that
  `lib/sdd_repo.py` flags (repo scenario ids, file paths) are dropped too.
- **Exit codes**: 0 means written. 2 means the transcript is under 200 chars, and the drain
  archives the session without a distill. 1 is a model or parse failure; the session stays in
  pending.

## Routing (`process_pending.py`)

| Source | Destination | Script |
|---|---|---|
| the session JSON | `rai-episodic` | `store_episodic.py` |
| `summary`, `decisions`, `facts` | `rai-semantic` | `store_semantic.py` |
| each item's `supersedes` | archive the named `rai-semantic` rows | `store_semantic.py` |
| `preferences` | `learned-candidates.jsonl` (probation) and `rai-preferences` | `route_preferences.py` |

The distill output waits at `pending/<session>.distill.json` until all three store steps succeed,
and a retry reuses it instead of calling Opus again.

`evolve-capabilities.jsonl` is a closed record: the capability flags that earlier distills raised,
all `unreviewed`. The prompt does not ask for capabilities, and nothing writes the file.

## `learned-candidates.jsonl` and the renders

A candidate row: `id`, `type` (preference), `content`, `confidence`, `evidence`, `source_session`,
`sources`, `first_seen`, `last_seen`, `re_confirmations`, `contradictions`, `status`, and
`promoted_at` once active.

- **probation to active** (`route_preferences.maybe_promote`): `re_confirmations` at least 2,
  confidence at least medium, at least 3 days since `first_seen`. Each promotion appends a line to
  `promotions.log`.
- **probation to dormant** (`curate_candidates.py`): more than 45 days since `last_seen`.
- **dormant to probation**: any re-confirmation.
- **retired**: counted in the render and left out of the index, but no code sets it.
  `contradictions` is summed on merges and never incremented.

Renders: `semantic-memory/learned.md` shows ACTIVE in full and a count per status. It also shows
the top `PROBATION_RENDER_TOP` (50) probation items, most confirmed first, then most recently
seen. The jsonl holds the rest. `identity/learned.md` holds the ACTIVE slice (top-confirmed first, capped at 2,000
chars by `IDENTITY_RENDER_CAP`) and is deleted when nothing is active. Every file here is
git-committed, so each change has provenance and can be reverted.
