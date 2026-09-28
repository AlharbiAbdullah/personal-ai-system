#!/usr/bin/env python3
"""
index_daily.py — Memory v3 (Phase D): batch-index the live-capture daily logs into
the `rai-daily` ChromaDB collection.

The Stop hook (turn-capture.py) appends observer bullets to semantic-memory/daily/
YYYY-MM-DD.md live; per the v3 invariant (MEMORY-ARCHITECTURE.md) ChromaDB stays
batch-written — THIS script is that batch step, run by the coordinator via
process_pending.py. One record per `### HH:MM (session:xxxxxxxx)` block; ids are
content-hashed so re-runs upsert idempotently (append-only files → old blocks keep
their ids, new blocks get new ones).

Derived + rebuildable: the committed daily/*.md are the source; this collection is
never exported (a rebuild is a run of this same script).

Run: semantic-memory/scripts/py-chroma.sh hooks/scripts/index_daily.py
"""

import hashlib
import sys
from pathlib import Path

import chromadb

sys.path.insert(0, str(Path.home() / "helm" / "03-rai" / "hooks"))
from lib.daily_log import parse_blocks  # noqa: E402 — the ONE daily-log parser

SM = Path.home() / "helm" / "03-rai" / "semantic-memory"
DAILY_DIR = SM / "daily"
CHROMADB_DIR = SM / "chromadb"
COLLECTION = "rai-daily"


def distilled_prefixes(client) -> set:
    """8-char session prefixes that already have rai-semantic rows — i.e. the quality
    record exists. Coupling B (M4): their daily blocks get `distilled: true` so recall
    treats rai-daily as the recency buffer, not a duplicate of the semantic store."""
    try:
        sem = client.get_or_create_collection(name="rai-semantic",
                                              metadata={"hnsw:space": "cosine"})
        if sem.count() == 0:
            return set()
        g = sem.get(include=["metadatas"])
        return {(m.get("source_session") or "")[:8]
                for m in g["metadatas"] if m.get("source_session")}
    except Exception:
        return set()


def main():
    if not DAILY_DIR.exists():
        print("index_daily: no daily/ dir yet — nothing to index")
        return 0
    client = chromadb.PersistentClient(path=str(CHROMADB_DIR))
    col = client.get_or_create_collection(name=COLLECTION, metadata={"hnsw:space": "cosine"})
    done = distilled_prefixes(client)

    ids, docs, metas = [], [], []
    seen = set()
    for f in sorted(DAILY_DIR.glob("*.md")):
        date = f.stem
        for time_s, sid, text in parse_blocks(f):
            if not text:
                continue
            bid = hashlib.sha256(f"{date}|{time_s}|{sid}|{text}".encode()).hexdigest()[:16]
            if bid in seen:  # same block appended twice by live capture -> one record
                continue
            seen.add(bid)
            ids.append(bid)
            docs.append(f"[{date} {time_s}] {text}")
            metas.append({"date": date, "time": time_s, "session": sid, "file": f.name,
                          "distilled": sid[:8] in done})

    B = 200
    for i in range(0, len(ids), B):
        col.upsert(ids=ids[i:i + B], documents=docs[i:i + B], metadatas=metas[i:i + B])
    print(f"index_daily: upserted {len(ids)} blocks -> {COLLECTION} ({col.count()} total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
