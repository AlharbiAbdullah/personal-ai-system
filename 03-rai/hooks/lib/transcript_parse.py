"""Shared transcript JSONL walker."""

import json
from pathlib import Path
from typing import Iterator


def iter_transcript(transcript_path: str) -> Iterator[dict]:
    """Yield parsed JSON entries from a transcript JSONL file. Silent on failure."""
    if not transcript_path:
        return
    path = Path(transcript_path)
    if not path.exists():
        return
    try:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except Exception:
        return


def iter_assistant_tool_uses(transcript_path: str) -> Iterator[dict]:
    """Yield every tool_use block from assistant messages."""
    for entry in iter_transcript(transcript_path):
        if entry.get("type") != "assistant":
            continue
        content = entry.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                yield item
