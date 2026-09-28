#!/usr/bin/env python3
"""
render_memory_block.py — Memory v3 (Phase C): freeze the SessionStart memory block.

Computes session_start_block() (top durable facts + recent sessions from the v2 stores)
ONCE per drain and writes it to memory/state/memory-block.md. session-start.py then just
reads the file — no ChromaDB at session start (faster, stabler, degrades gracefully), and
the block is frozen between drains: it changes only when memory actually changed.

Called at the end of process_pending.py (and manually after rebuilds).
Run: semantic-memory/scripts/py-chroma.sh hooks/scripts/render_memory_block.py
"""

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "helm" / "03-rai"
sys.path.insert(0, str(ROOT / "hooks"))

OUT = ROOT / "memory" / "state" / "memory-block.md"


def main():
    from lib.memory_retrieval import session_start_block

    block = session_start_block()
    if not block:
        print("render_memory_block: stores empty — nothing rendered")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    OUT.write_text(f"{block}\n\n<sub>frozen snapshot · rendered {stamp} by the drain</sub>\n")
    print(f"render_memory_block: wrote {OUT} ({len(block)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
