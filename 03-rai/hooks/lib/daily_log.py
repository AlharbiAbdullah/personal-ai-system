#!/usr/bin/env python3
"""
daily_log.py — the ONE parser for Memory v3 live-capture daily logs
(semantic-memory/daily/YYYY-MM-DD.md).

turn-capture.py appends `### HH:MM (session:xxxxxxxx)` blocks live; every consumer
of that format parses it through here: index_daily.py (rai-daily indexing), the
drain's bullets→distill coupling (process_pending.py), and the eval harness
(freshness probes + bullet fidelity). Do not re-implement the block format elsewhere.
"""

import re
from pathlib import Path

DAILY_DIR = Path.home() / "helm" / "03-rai" / "semantic-memory" / "daily"

BLOCK_RE = re.compile(r"^### (\d{2}:\d{2}) \(session:([0-9a-f-]+)\)\s*$")


def parse_blocks(path: Path):
    """Yield (time, session8, text) per turn-capture block in one daily file."""
    time_s, sid, lines = None, None, []
    for line in path.read_text().splitlines():
        m = BLOCK_RE.match(line)
        if m:
            if time_s and lines:
                yield time_s, sid, "\n".join(lines).strip()
            time_s, sid, lines = m.group(1), m.group(2), []
        elif time_s is not None:
            lines.append(line)
    if time_s and lines:
        yield time_s, sid, "\n".join(lines).strip()


def blocks_for_session(session_id_prefix: str, daily_dir: Path = DAILY_DIR):
    """All (date, time, text) blocks for a session, oldest first.

    turn-capture records the first 8 chars of the session id; match either
    direction so callers can pass a full id or a prefix.
    """
    prefix = session_id_prefix[:8]
    out = []
    if not daily_dir.exists():
        return out
    for f in sorted(daily_dir.glob("*.md")):
        for time_s, sid, text in parse_blocks(f):
            if sid.startswith(prefix) or prefix.startswith(sid):
                out.append((f.stem, time_s, text))
    return out
