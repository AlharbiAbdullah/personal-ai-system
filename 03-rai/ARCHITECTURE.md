# 03-rai/ Architecture

Rai's brain. One paragraph per top-level dir or file. See `AGENTS.md` for how Rai behaves,
`skills/MANIFEST.md` for skill groupings and `agents/MANIFEST.md` for agent tiers.

## Top-level layout

```
03-rai/
  AGENTS.md                   # global instructions (canonical; mounted, see Harness mounts)
  ARCHITECTURE.md              # this file
  MEMORY-ARCHITECTURE.md       # the memory system: capture, stores, injection, recall, self-evolve
  SYNC-ARCHITECTURE.md         # optional multi-machine sync pattern (ignore on one machine)
  agents/                      # agent personas, one .md each, plus MANIFEST.md (tiers)
  config/
    settings.json              # Claude Code harness contract
    .skill-lock.json           # pins for the vendored kepano/obsidian-skills (source + commit)
    vale/                      # Vale prose styles (Rai), run by the root .vale.ini
  hooks/
    *.py                       # 11 event handlers, each registered in config/settings.json
    lib/                       # shared utilities
    scripts/                   # the batch memory pipeline + skill-called utilities
    tests/                     # pytest for the SDD memory routing (test_sdd_routing.py)
    context_mapping.json       # cwd-to-context label map, read by lib/session_extract.py
  identity/                    # Rai-only config; every *.md here auto-loads
  memory/
    state/                     # memory-block.md (the frozen snapshot) + README.md
    work/                      # example task record; nothing writes here now (see memory/)
    learning/                  # captured learnings, the hook error sink, the sanity status
  semantic-memory/
    chromadb/                  # the four memory collections, gitignored, rebuilt locally
    index/                     # rai-semantic.jsonl, the committed source of truth
    daily/                     # live turn-capture logs (YYYY-MM-DD.md)
    pending/                   # sessions waiting for the drain
    scripts/                   # py-chroma.sh, the chromadb wrapper
    CHROMADB-SCHEMA.md         # collection contract + the DISTILL JSON
  skills/                      # top-level skills (routers + leaves), MANIFEST.md, GAPS.md, synced/
```

Outside the vault, the hooks write two state folders that git never sees.
`~/.local/state/rai/telemetry/` holds hook performance and count-history telemetry
(`lib/hook_timer.py`, `update-counts.py`). `~/.local/state/rai/runtime/` holds per-session
state: injected pointer ids, turn-capture debounce stamps, tab titles, session names, the
identity cache and the CLI flag cache.

## Harness mounts

The vault is the canonical home; `setup.sh` mounts it into Claude Code through symlinks
(`ls -la ~/.claude`):

| Mount | Target |
|---|---|
| `~/.claude/CLAUDE.md` | `03-rai/AGENTS.md` (Claude Code has no user-level `AGENTS.md`, so this symlink is the one exception to "AGENTS.md is the only instruction filename") |
| `~/.claude/agents` | `03-rai/agents` |
| `~/.claude/hooks` | `03-rai/hooks` |
| `~/.claude/skills` | `03-rai/skills` |
| `~/.claude/settings.json` | `03-rai/config/settings.json` |

MCP servers are not configured in the vault: Claude Code reads them from `~/.claude.json`.
Register one at user scope with `claude mcp add --scope user ...` (`claude mcp list` shows
them). Context7, for current library docs, is a good first one.

Every subfolder in the vault (`00-landing/` through `13-archive/`) reads its own `AGENTS.md`
natively; only the user-level mount above needs the `CLAUDE.md` name.

## Paragraph per directory

### `identity/`

Rai-only config: persona, steering rules, response and coding formats. The memory system
maintains two more files here. `working-memory.md` is written by the `/remember` skill and
capped at 2,500 chars. `learned.md` is the self-evolve ACTIVE render, capped at 2,000 chars.
`hooks/session-start.py` loads every `*.md` in this folder and in `~/helm/02-ana/identity/`
at SessionStart. Your Life OS lives outside this folder in `~/helm/02-ana/`; `/life` reads
and writes your self-model there.

### `agents/`

Claude Code agent definitions: one `.md` per persona, each with frontmatter (`name`,
`description`, `tools`). Invoked through the Agent tool with `subagent_type: "<name>"`.
`agents/MANIFEST.md` holds the specialist and methodology tiers.

### `skills/`

Claude Code skill definitions. Routers hold sub-skill `.md` files; leaves hold a single
`SKILL.md`. The folder name matches the frontmatter `name:`, which drives the top-level
`/invocation`. Claude Code discovers skills by a depth-1 scan, so sub-skills are reachable
only through their router. `skills/MANIFEST.md` holds the count, the groupings and the full
inventory; `skills/GAPS.md` holds the open backlog. `synced/` is a harness-synced plugin
skill bucket (docs, docx, pdf and others), not a top-level skill, and this kit doesn't ship
it — Claude Code fills it in the first time you need one of those.

### `hooks/`

Event handlers wired in `config/settings.json` for SessionStart, UserPromptSubmit,
PreToolUse, PostToolUse, Stop and SessionEnd; every `hooks/*.py` file is registered. The
memory hooks are `session-start.py` (the frozen snapshot), `memory-injection.py` (per-prompt
pointers) and `turn-capture.py` (live daily logs). `lib/` holds the shared utilities.

| `lib/` file | Role |
|---|---|
| `memory_retrieval.py` | queries and scoring |
| `session_gate.py` | the one session-classification policy |
| `session_extract.py` | transcript normalizer |
| `sdd_repo.py` | project-init repo detection for the H27 rule |
| `state_sweep.py` | orphan cleanup of runtime state |
| `paths.py` | vault, runtime and telemetry paths |

`scripts/` holds the batch pipeline (`sync_claude_sessions.py`, `process_pending.py`,
`distill_session.py`, `store_episodic.py`, `store_semantic.py`, `route_preferences.py`,
`index_daily.py`, `export_index.py`, `render_memory_block.py`, `curate_candidates.py`,
`rebuild_chromadb.py`) plus skill-called utilities. Nothing in `scripts/` is event-triggered;
`/rai process-sessions` and the other `/rai` sub-skills call them explicitly.

### `config/`

`settings.json` is the harness contract: permissions, hook registrations, plugins and the
status line. Its `statusLine` runs the claude-hud plugin. `.skill-lock.json` pins the vendored
kepano/obsidian-skills (obsidian-bases, obsidian-cli, obsidian-markdown) by source and commit.
`vale/` holds the hand-written `Rai` prose style that the root `.vale.ini` runs on every
`*.md`; `vale sync` downloads the `ai-tells` package next to it.

### `memory/`

Tracked runtime records only. `state/` holds `memory-block.md`, the frozen memory snapshot
that `render_memory_block.py` writes and `session-start.py` reads. `work/` keeps one example
task record; the post-hoc summary of a session is now its distill record in `rai-semantic`.
`learning/` holds captured learnings, the hook error sink (`hook-errors.jsonl`), the recall
log and the sanity certificate (`sanity-last.json`).
Per-session runtime state and hook telemetry live outside the vault in `~/.local/state/rai/`.

### `semantic-memory/`

Long-term recall. Design: `MEMORY-ARCHITECTURE.md`; collection contract:
`CHROMADB-SCHEMA.md`. ChromaDB holds `rai-semantic` (distilled facts, decisions, summaries),
`rai-episodic` (whole sessions), `rai-daily` (live turn-capture blocks) and
`rai-preferences` (the self-evolve index). It ships empty and is rebuilt locally.
`index/rai-semantic.jsonl` is the committed source of truth; `rebuild_chromadb.py` rebuilds
the stores from it and the archive. `daily/` holds the live logs, `pending/` the drain queue.
`scripts/py-chroma.sh` runs Python with `chromadb` available.

### `AGENTS.md`

Rai's global instructions: identity load paths, the session-memory summary, skill routing
and the PRD note. Loaded into every Claude Code session through the `~/.claude/CLAUDE.md`
symlink.

## Cross-file relationships

- **SessionStart**: `session-start.py` (plain python3, no ChromaDB) sweeps orphan runtime
  state. Then it loads both identity folders, the vault index, a codemap when present, the
  frozen `memory/state/memory-block.md` and today's daily-log tail. It warns when the
  identity surface exceeds 4KB per file or 44KB total.
- **UserPromptSubmit**: `memory-injection.py` embeds the prompt, queries the stores and
  injects short pointers, with a relevance floor and per-session dedup.
- **Stop**: `turn-capture.py` detaches a worker that summarizes the turn into
  `semantic-memory/daily/YYYY-MM-DD.md`. It skips headless runs and thin turns, and
  debounces so rapid turns don't each write.
- **SessionEnd**: `session-summary.py` clears the session's runtime files; `update-counts.py`
  appends skill and hook counts to telemetry when they change.
- **Batch capture**: the scanner `sync_claude_sessions.py` is the only capture path. The
  maintenance coordinator runs it 4 times a day (or run it yourself). It classifies each
  session with `lib/session_gate.py` and queues or archives it.
- **Batch drain (the ChromaDB writer)**: `/rai process-sessions` runs `process_pending.py`:
  the distill, then `store_episodic`, `store_semantic` and `route_preferences`, then
  `export_index.py`, `render_memory_block.py` and `index_daily.py`.
- **Weekly curation**: `curate_candidates.py` runs once per ISO week. It merges
  near-duplicate preferences, decays stale ones, promotes qualifiers and renders both
  `learned.md` files.
- **Health**: `/rai sanity` runs `skills/rai/scripts/sanity.py`, one check module per
  subsystem under `sanity_checks/`, each with a fault test under `tests/`.

## Out of scope

- Sub-skills inside routers follow the same kebab-case naming as top-level skills; the
  filename matches the frontmatter `name:`.
- `13-archive/` and the other sibling vault folders are outside Rai's scope.
- The optional multi-machine sync pattern lives in `SYNC-ARCHITECTURE.md`; on one machine
  you can ignore it.
