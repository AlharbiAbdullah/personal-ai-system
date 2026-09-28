#!/usr/bin/env python3
"""
store_episodic.py — write a full session (raw conversation) into the `rai-episodic`
ChromaDB collection. See 03-rai/MEMORY-ARCHITECTURE.md.

The EPISODIC store holds whole sessions = the "receipts" layer, retrieved top-k for
"find the relevant past session". Reads a pending/archive session JSON (the shape
lib/session_extract writes; the messages[] array IS the conversation). Idempotent
(upsert by session_id) so a rebuild can re-run safely.

Run via the chromadb wrapper:
  semantic-memory/scripts/py-chroma.sh hooks/scripts/store_episodic.py --session-json <path>
"""

import argparse
import json
import sys
from pathlib import Path

import chromadb

CHROMADB_DIR = Path.home() / "helm" / "03-rai" / "semantic-memory" / "chromadb"
COLLECTION = "rai-episodic"


def get_collection():
    CHROMADB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMADB_DIR))
    return client.get_or_create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"}
    )


def message_text(entry: dict) -> str:
    """Pull plain text from a session-JSON message entry {type, message}."""
    m = entry.get("message")
    if isinstance(m, str):
        return m
    if isinstance(m, dict):
        content = m.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return "\n".join(parts)
    return ""


def build_document(session: dict) -> str:
    """Full conversation text, with a topic header up front.

    The header (date/context + the user's asks) leads the document so the truncated
    MiniLM embedding keys on what the session was ABOUT — full text is still stored
    for retrieval. (Chunked embedding is a planned v1.1 improvement.)
    """
    msgs = session.get("messages", [])
    user_asks = [message_text(m) for m in msgs if m.get("type") == "user"]
    header = (
        f"[{session.get('context', '')}] {session.get('project_name', '')}\n"
        "ASKS: "
        + " || ".join(t.strip().replace("\n", " ")[:200] for t in user_asks[:6] if t.strip())
    )
    body = []
    for m in msgs:
        txt = message_text(m).strip()
        if txt:
            body.append(f"{m.get('type', '').upper()}: {txt}")
    return header + "\n\n" + "\n\n".join(body)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--session-json", required=True, help="path to a session_*.json (pending/archive format)")
    args = p.parse_args()

    data = json.loads(Path(args.session_json).read_text())
    session_id = data.get("session_id") or Path(args.session_json).stem
    document = build_document(data)
    if not document.strip():
        print(f"episodic: skip {session_id} (empty)", file=sys.stderr)
        return 0

    ts = data.get("timestamp", "")
    metadata = {
        "session_id": session_id,
        "date": ts[:10] if ts else "",
        "context": data.get("context", ""),
        "project_name": data.get("project_name", ""),
        "duration_minutes": int(data.get("duration_minutes", 0) or 0),
        "tools_summary": json.dumps(data.get("tools_summary", {})),
        "files_modified": json.dumps(data.get("files_modified", [])),
        "message_count": len(data.get("messages", [])),
    }

    col = get_collection()
    col.upsert(ids=[session_id], documents=[document], metadatas=[metadata])
    print(f"episodic: stored {session_id} ({metadata['message_count']} msgs, {len(document)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
