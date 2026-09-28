# Memory

File-based memory for the assistant. It starts empty. The directories below fill in
as you use the system. Nothing here ships pre-populated. Your memory is yours.

This is the file half of Memory v3. The vector half (four ChromaDB collections:
`rai-semantic`, `rai-episodic`, `rai-daily`, `rai-preferences`) lives in
`03-rai/semantic-memory/` and is rebuilt locally, also starting empty. The rule of thumb:
live writes append to plain-text logs first, and the vector store is batch-written later.

| Folder | What accumulates here |
|--------|------------------------|
| `learning/` | Captured learnings, hook error sink and other system change logs. |
| `state/` | The frozen `memory-block.md` snapshot `session-start.py` reads, refreshed by the batch drain. |
| `work/` | One folder per non-trivial task: its post-hoc PRD and working notes. |

## How it fills

- **Hooks** write `learning/` and `state/` automatically as sessions run. Per-session runtime
  state (tab titles, debounce stamps, the identity cache) lives outside git, in
  `~/.local/state/rai/`, not here.
- For substantial multi-step tasks, a brief **post-hoc PRD** (problem, approach, outcome) is
  derived from the transcript after the work is done and lands in `work/{slug}/`. It is
  AI-authored, with no fixed ritual. Trivial tasks (greetings, lookups) skip it.
- **Session processing** (`/rai process-sessions`) distills finished sessions and queues facts
  for the semantic index in `03-rai/semantic-memory/`.

## Privacy

This whole tree is meant to hold your real accumulated memory once you use the system, and
it is tracked by git like everything else in the vault: git log is the archive (see the
root `AGENTS.md`). If you publish your own fork of the vault publicly, uncomment the
`02-ana/` and `03-rai/memory/` lines in the root `.gitignore` first so your real content
never leaves your machine.
