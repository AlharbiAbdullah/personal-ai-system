# Rai Memory Architecture

How Rai remembers: capture, storage, injection, recall and self-evolve, with the files each
part owns. ChromaDB collection contract and the DISTILL JSON: `semantic-memory/CHROMADB-SCHEMA.md`.
Running this across more than one machine: `SYNC-ARCHITECTURE.md` (optional, ignore on one machine).

**Live writes append to text only.** Nothing live-writes ChromaDB, the committed index or
the archive — a batch step does, whenever you (or a scheduled job, on the pattern in
`SYNC-ARCHITECTURE.md`) run `/rai process-sessions`.

**Repo rule (H27).** A session in a project-init repo (`.project.toml`, detected by
`hooks/lib/sdd_repo.py`) keeps only preferences you state yourself, cross-project lessons and
one `worked in <repo>` pointer. The rule holds in the daily log (`turn-capture.py`) and in the
distill output (`distill_session.py`). Repo facts live in the repo's `specs/` and
`project_memory/` instead — repo truth lives in the repo.

**Quality.** `/rai sanity` certifies function (structural integrity of skills, agents, memory).
`/rai eval` certifies quality: it scores memory recall against a golden set you build over
time, with a strong model as judge. Run either by hand whenever you like.

---

## 1. Layers

```
Live session
  │
  ├─ every turn ──────────► LIVE layer (text only)
  │                          semantic-memory/daily/YYYY-MM-DD.md (observer bullets, Stop hook)
  │
  └─ "remember this" ─────► identity/working-memory.md (curated, capped)

BATCH layer (you run it, or a scheduled job runs it for you)
  scan native transcripts ─► distill, store, route ─► ChromaDB (4 collections)
                                                        rai-semantic   (distilled facts)
                                                        rai-episodic   (whole sessions)
                                                        rai-daily      (live-log blocks)
                                                        rai-preferences (self-evolve dedup)

Every session start: injected
  ├─ frozen snapshot: identity + memory block + daily tail
  └─ per-prompt pointers: memory-injection.py, relevance-floored
```

The design pairs curated capped files with a frozen snapshot at session start (so every
session opens with the same cheap context) with per-turn observer notes and tiered recall (so
deep detail is there when you ask for it, without inflating every prompt). ChromaDB is the
only vector store. Your own hand-authored self-model (`02-ana/identity/`) plus
`identity/learned.md` (auto-evolved) together play the role a separate "user profile" file
would, so there's no separate one to keep in sync.

---

## 2. Capture

### Live: turn-capture

Each turn, once you get a response, `turn-capture.py` (a Stop hook) detaches a background
worker: it asks a fast model to write 2-10 terse third-person bullets about what was durable
in that exchange (decisions with their why, state changes, discoveries, standing rules you
established, open threads), then appends them to `semantic-memory/daily/YYYY-MM-DD.md` under
a `### HH:MM (session:xxxxxxxx)` header. It never blocks your response.

Guards (see the module docstring and constants in `turn-capture.py`):

- **headless skip**: a `claude -p` / `--print` ancestor process means no capture;
- **thin turns**: under `MIN_TURN_CHARS` of real text, no capture;
- **debounce**: a minimum interval between captures per session, armed only by a successful
  append;
- **fail-open**: every failure exits 0 and logs to the hook error sink. The model call has a
  timeout.

### Batch: the scanner

The batch scanner (`hooks/scripts/sync_claude_sessions.py`) is the only path that reaches
ChromaDB. It reads native transcripts (`~/.claude/projects/**/*.jsonl`), skips anything
touched in the last several minutes (still being written), converts each session to a pending
JSON (`lib/session_extract.py`) and classifies it with the one policy,
`lib/session_gate.py`. First match wins:

| Class | Rule | Result |
|---|---|---|
| headless | transcript entrypoint is a script/pipeline call, not an interactive session | ephemeral, checked first |
| explicit_remember | a user message matches the remember-language regex | pending: distill, episodic, archive |
| memory_worthy | several human messages, or plan mode, or multiple files edited | pending: distill, episodic, archive |
| archive_only | a couple of human messages plus tool use or several minutes | archive only |
| ephemeral | everything else | nothing |

Ephemeral sessions never reach `13-archive/`; their only record is the native transcript and
their daily-log bullets.

### Batch: the drain

`/rai process-sessions` runs `process_pending.py` over the queue:

- archive_only and ephemeral files go to `13-archive/historical-sessions/` without a distill;
- memory-worthy and explicit-remember sessions get distilled (`distill_session.py`):
  `{summary, decisions[], facts[], preferences[], capabilities[]}`, each item carrying 1-3
  verbatim evidence quotes and a confidence level. A transcript over the size threshold is
  split into windows, each distilled, then merged in one reduce pass;
- the distill is saved as `pending/<session>.distill.json`, the one artifact that can't be
  rebuilt, kept until every store (`store_episodic.py`, `store_semantic.py`,
  `route_preferences.py`) confirms the write, then the session moves to the archive.

After the batch: `export_index.py` rewrites the committed `index/rai-semantic.jsonl`, and
`render_memory_block.py` refreshes the frozen snapshot. `index_daily.py` runs on every drain,
distilled or not.

---

## 3. Injection

### Session start: the frozen snapshot

`session-start.py` runs under plain `python3` — no ChromaDB at startup — and reads, in
order: `03-rai/identity/*.md` (persona, `working-memory.md`, `learned.md`), your
`02-ana/identity/*.md` self-model, the vault index, a codemap when the cwd is a mapped repo,
the frozen `memory/state/memory-block.md` (top facts + recent sessions), and the last part of
today's daily log. It warns (advisory, never truncates) past a per-file and a total budget.

### Per prompt: pointers

`memory-injection.py` embeds the prompt, queries `rai-semantic` and `rai-episodic`, and — only
above a relevance floor, and only once per session per fact — injects a short pointer: a fact
cut to a line, or a past session's date and context. Never full content. It runs with a hard
time limit, so a slow query injects nothing rather than stalling your prompt.

---

## 4. Recall (`/recall`)

Each tier costs more than the one before it, and recall stops at the first tier that answers:

1. **T0 — already in context**: identity, memory block, daily tail, this session's pointers. Free.
2. **T1 — distilled memory**: query `rai-semantic` + `rai-daily`. Facts with evidence and source, one query.
3. **T2 — session pointers**: query `rai-episodic`. Which session, when, what it was about.
4. **T3 — verbatim receipts**: the archived session JSON, or the native transcript. The actual conversation.

`rai-daily` down-ranks blocks whose session has already been distilled (daily is the recency
buffer, semantic is the quality record), and every query and tier outcome is logged so you can
see what recall actually used.

---

## 5. Self-evolve

The distill also extracts *how Rai should behave*. Nothing becomes standing behavior before
it earns it:

```
new preference ──► PROBATION ──(re-confirmed enough times, held long enough)──► ACTIVE
                       │                                                          │
                       └──(no re-confirm in a while)──► DORMANT ──(re-confirmed)──┘
                                                                                   │
                                                                    renders to identity/learned.md
                                                                    (capped) → auto-loads every session
```

`route_preferences.py` appends new candidates to `learned-candidates.jsonl` (the source of
truth) on every drain; a preference close enough to an existing candidate re-confirms it
instead of adding a row. A periodic "dreaming" pass (`curate_candidates.py`) merges
near-duplicates, decays stale probation items to dormant, promotes qualifiers, and renders
both `semantic-memory/learned.md` (ACTIVE in full, top probation, counts per status) and the
capped `identity/learned.md` (ACTIVE only, auto-loaded). Everything here is quarantined from
your hand-authored identity files, git-tracked and reversible — delete a line from
`learned.md` any time you disagree with what it decided.

---

## 6. Rebuild

Every collection is rebuildable from committed text, without re-running any model:

- `rebuild_chromadb.py`: `rai-semantic` from `index/rai-semantic.jsonl`, `rai-episodic` from
  the sessions in `13-archive/historical-sessions/` that the session gate classes for it;
- `index_daily.py`: `rai-daily` from `daily/*.md`;
- `curate_candidates.py`: `rai-preferences` from `learned-candidates.jsonl`.

`semantic-memory/chromadb/` is gitignored on purpose — it's a large derived binary, and
re-snapshotting it whole on every change is the single biggest source of git bloat in a vault
like this. Delete it any time; the next run rebuilds it. Running this on more than one
machine, and keeping exactly one of them the ChromaDB writer, is `SYNC-ARCHITECTURE.md`.

---

## 7. File map

Paths under `03-rai/` unless absolute. Live = written during a session (text only); batch =
written when you (or a scheduled job) run the drain.

| Piece | Path | Written by | When |
|---|---|---|---|
| Daily live logs | `semantic-memory/daily/YYYY-MM-DD.md` | `turn-capture.py` (Stop hook) | live, every captured turn |
| Working memory | `identity/working-memory.md` | `/remember` skill | live, on ask |
| Native transcripts | `~/.claude/projects/**/*.jsonl` | Claude Code | live |
| Capture queue | `semantic-memory/pending/` | `sync_claude_sessions.py` | batch |
| Scanner ledger | `semantic-memory/processed-sessions.jsonl` | scanner, drain | batch |
| Distilled store | ChromaDB `rai-semantic` | `store_semantic.py` | batch |
| Session receipts | ChromaDB `rai-episodic` + `13-archive/historical-sessions/` | `store_episodic.py`, drain | batch |
| Live-log index | ChromaDB `rai-daily` | `index_daily.py` | batch |
| Preference index | ChromaDB `rai-preferences` | `route_preferences.py`, `curate_candidates.py` | batch |
| Committed truth | `semantic-memory/index/rai-semantic.jsonl` | `export_index.py` | batch, after distills |
| Frozen snapshot | `memory/state/memory-block.md` | `render_memory_block.py` | batch, after distills |
| Preference candidates | `semantic-memory/learned-candidates.jsonl` | `route_preferences.py`, curator | batch |
| Learned behavior | `identity/learned.md`, `semantic-memory/learned.md` | router and curator renders | batch |
| Health certificate | `memory/learning/sanity-last.json` | `/rai sanity` | on demand |
| Hook errors | `memory/learning/hook-errors.jsonl` | `lib/hook_errors.py` | live, on error |
| Hook telemetry | `~/.local/state/rai/telemetry/` | `lib/hook_timer.py`, `update-counts.py` | live, outside git |
| Runtime state | `~/.local/state/rai/runtime/` | the hooks | live, outside git |

Runtime state is per session: `session-summary.py` removes a session's files at SessionEnd,
and the SessionStart sweep (`lib/state_sweep.py`) clears orphans past a threshold.

---

## 8. The invariant, drawn

```
LIVE writes (append-only TEXT)          NEVER live-written
  daily/*.md                            ChromaDB (all 4 collections)
  working-memory.md          ──only via the batch step──►  index/rai-semantic.jsonl
  native transcripts                    13-archive/
                                         learned-candidates.jsonl
```

Text merges cleanly if you ever run this from more than one place; the database has one
writer per your own setup, so its binary files never conflict.
