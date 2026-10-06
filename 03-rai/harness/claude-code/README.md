# Claude Code harness edge

`setup.sh` mounts the vault into Claude Code through `~/.claude/*` symlinks (see
`ARCHITECTURE.md`, Harness mounts). This folder holds the one piece of that edge that is not a
plain link: how Claude Code loads Rai's identity.

## Why identity comes through CLAUDE.md

Claude Code shows a SessionStart hook's output inline only up to 10,000 characters per hook.
Past that it shows a short preview and a file path, and session-start's full snapshot is far
larger. So Claude Code loads the static parts through imports, which have no such cap:

| File | Role |
|---|---|
| `~/.claude/CLAUDE.md` | a symlink to `user-instructions.md` |
| `user-instructions.md` | imports `03-rai/AGENTS.md` and `identity-imports.md` |
| `identity-imports.md` | imports every `03-rai/identity/*.md`, `02-ana/identity/*.md`, and the memory block and the vault index once they exist |

`hooks/session-start.py` re-renders `identity-imports.md` at every session start and writes it
only when the list changes. A file moved in or out of an identity folder reaches Claude Code
from the next session, with no code change.

Session-start then prints only the dynamic part, within 9,500 characters. That is the sanity
and news banners and the status line. It adds the codemap (or only its path when it would not
fit) and the newest lines of today's daily log.

The file is not named `CLAUDE.md`: Claude Code would load a `CLAUDE.md` inside the vault as
nested memory, and `AGENTS.md` is the vault's only instruction filename.

Every Claude Code session loads the user `CLAUDE.md`, and so do its Agent-tool subagents. That
is by design: each subagent works as Rai, with the whole identity.

## Pipeline calls stay isolated

The brain's own `claude -p` calls (turn-capture's observer, the distill, the eval judge) go
through `hooks/lib/claude_cli.py`. They run with `--setting-sources project`,
`--strict-mcp-config` and `--no-session-persistence`, with CLAUDE.md files and auto-memory
switched off, from a neutral folder. So none of them loads the identity, the hooks or the MCP
servers, and none leaves a transcript. The distill asks for `xhigh` effort itself, since user
settings no longer reach it. The eval's `/recall` smoke is the one exception (`isolate=False`):
it tests the real assistant, with its skills and settings.

## Checks

`/rai sanity` CFG-2 checks the `~/.claude` links, and HARN-7 checks that the imports list every
identity file. Tests: `hooks/tests/test_session_start_modes.py` and
`hooks/tests/test_harness_capture.py`.
