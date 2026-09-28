#!/usr/bin/env python3
"""
rebuild_chromadb.py — Memory v2: rebuild the derived ChromaDB binary from COMMITTED SOURCE.
No Opus calls — embedding only. Safe to run on any machine (Mac at cutover, or DR).

  rai-semantic  <-  index/rai-semantic.jsonl            (verbatim upsert; re-embeds documents)
  rai-episodic  <-  13-archive/historical-sessions/*    (gated transcripts, via store_episodic logic)

Flags:
  --target DIR      build into a scratch chromadb dir instead of the live store (validation)
  --semantic-only   rebuild only rai-semantic (skip episodic)
  --episodic-only   rebuild only rai-episodic

Run: semantic-memory/scripts/py-chroma.sh hooks/scripts/rebuild_chromadb.py [--target DIR]
"""

import argparse
import glob
import json
import sys
from pathlib import Path

import chromadb

ROOT = Path.home() / "helm" / "03-rai"
SM = ROOT / "semantic-memory"
ARCHIVE = Path.home() / "helm" / "13-archive" / "historical-sessions"
SCRIPTS = ROOT / "hooks" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "hooks"))
from lib.session_gate import classify, should_episodic  # noqa: E402


def rebuild_semantic(db: Path):
    src = SM / "index" / "rai-semantic.jsonl"
    rows = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    client = chromadb.PersistentClient(path=str(db))
    try:
        client.delete_collection("rai-semantic")
    except Exception:
        pass
    col = client.get_or_create_collection(
        name="rai-semantic", metadata={"hnsw:space": "cosine"}
    )
    B = 500
    for i in range(0, len(rows), B):
        chunk = rows[i:i + B]
        col.upsert(
            ids=[r["id"] for r in chunk],
            documents=[r["document"] for r in chunk],
            metadatas=[r["metadata"] for r in chunk],
        )
    print(f"rai-semantic: rebuilt {col.count()} rows from {src.name}")


def rebuild_episodic(db: Path):
    import store_episodic  # sibling module — reuse its build_document + metadata shape

    client = chromadb.PersistentClient(path=str(db))
    try:
        client.delete_collection("rai-episodic")
    except Exception:
        pass
    col = client.get_or_create_collection(
        name="rai-episodic", metadata={"hnsw:space": "cosine"}
    )
    n = 0
    for f in sorted(glob.glob(str(ARCHIVE / "session_*.json"))):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        # Shared gate (session_gate.py) so Mac rebuilds match the Ubuntu producer's
        # episodic gating — the old bare ">=4 user entries" check dropped plan-mode
        # sessions and counted tool_results as human messages.
        if not should_episodic(classify(d)):
            continue
        sid = d.get("session_id") or Path(f).stem
        doc = store_episodic.build_document(d)
        if not doc.strip():
            continue
        ts = d.get("timestamp", "")
        md = {
            "session_id": sid,
            "date": ts[:10] if ts else "",
            "context": d.get("context", ""),
            "project_name": d.get("project_name", ""),
            "duration_minutes": int(d.get("duration_minutes", 0) or 0),
            "tools_summary": json.dumps(d.get("tools_summary", {})),
            "files_modified": json.dumps(d.get("files_modified", [])),
            "message_count": len(d.get("messages", [])),
        }
        col.upsert(ids=[sid], documents=[doc], metadatas=[md])
        n += 1
    print(f"rai-episodic: rebuilt {n} sessions from archive ({col.count()} in store)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", default=str(SM / "chromadb"))
    p.add_argument("--semantic-only", action="store_true")
    p.add_argument("--episodic-only", action="store_true")
    a = p.parse_args()
    db = Path(a.target)
    db.mkdir(parents=True, exist_ok=True)
    if not a.episodic_only:
        rebuild_semantic(db)
    if not a.semantic_only:
        rebuild_episodic(db)


if __name__ == "__main__":
    main()
