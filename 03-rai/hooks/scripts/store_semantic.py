#!/usr/bin/env python3
"""
store_semantic.py — write distilled facts/decisions/summary into the `rai-semantic`
ChromaDB collection, with dedup, supersede (model-flagged), and full provenance.
See 03-rai/MEMORY-ARCHITECTURE.md.

Input is the DISTILL JSON (the Opus distill output). Schema in semantic-memory/CHROMADB-SCHEMA.md:
  { "session_id", "date", "summary",
    "decisions": [ {content, confidence, evidence[], category, tags[], supersedes[]} ],
    "facts":     [ {content, confidence, evidence[], category, tags[], supersedes[]} ] }

This script does NO model calls — it is the deterministic write tool. The model (Opus)
produces the distill JSON; this routes it into the store.

Run:
  semantic-memory/scripts/py-chroma.sh hooks/scripts/store_semantic.py --distill-json <path>
"""

import argparse
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

import chromadb

CHROMADB_DIR = Path.home() / "helm" / "03-rai" / "semantic-memory" / "chromadb"
COLLECTION = "rai-semantic"
DEDUP_DISTANCE = 0.10  # cosine distance below which two records are "the same fact"


def get_collection():
    CHROMADB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMADB_DIR))
    return client.get_or_create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"}
    )


def content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


def find_duplicate(col, content: str):
    """Return the id of an existing near-identical active record, else None."""
    try:
        if col.count() == 0:
            return None
        r = col.query(
            query_texts=[content], n_results=1,
            where={"status": "active"}, include=["distances"],
        )
        dists = r.get("distances", [[]])[0]
        ids = r.get("ids", [[]])[0]
        if dists and dists[0] <= DEDUP_DISTANCE:
            return ids[0]
    except Exception:
        pass
    return None


def store_item(col, item: dict, kind: str, session_id: str, date: str, result: dict):
    content = (item.get("content") or "").strip()
    if not content:
        return

    dup = find_duplicate(col, content)
    if dup:
        got = col.get(ids=[dup], include=["metadatas"])
        md = (got.get("metadatas") or [{}])[0] or {}
        md["confirmation_count"] = int(md.get("confirmation_count", 1)) + 1
        md["last_confirmed"] = date
        col.update(ids=[dup], metadatas=[md])
        result["confirmed"].append(dup)
        return

    fid = f"{kind}-{content_hash(content)}-{uuid.uuid4().hex[:6]}"
    md = {
        "type": kind,
        "content": content,
        "source_session": session_id,
        "source_date": date,
        "confidence": item.get("confidence", "medium"),
        "evidence": json.dumps(item.get("evidence", [])),
        "category": item.get("category", ""),
        "tags": ",".join(item.get("tags", [])),
        "supersedes": json.dumps(item.get("supersedes", [])),
        "superseded_by": "",
        "last_confirmed": date,
        "confirmation_count": 1,
        "status": "active",
    }
    col.add(ids=[fid], documents=[content], metadatas=[md])
    result["added"].append(fid)

    # Apply model-flagged supersedes: archive the old record, point it at the new one.
    for old in item.get("supersedes", []):
        try:
            got = col.get(ids=[old], include=["metadatas"])
            if got.get("ids"):
                omd = got["metadatas"][0] or {}
                omd["status"] = "archived"
                omd["superseded_by"] = fid
                col.update(ids=[old], metadatas=[omd])
                result["superseded"].append(old)
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--distill-json", required=True)
    args = p.parse_args()

    if os.environ.get("RAI_TEST_FAIL_STORES"):
        # M1 test seam: simulate a store failure BEFORE any write, so the drain's
        # preserve-distill / leave-in-pending path can be exercised without touching the store.
        print("RAI_TEST_FAIL_STORES set — simulated store failure", file=sys.stderr)
        return 3

    d = json.loads(Path(args.distill_json).read_text())
    sid = d.get("session_id", "")
    date = d.get("date", "")
    col = get_collection()
    result = {"added": [], "confirmed": [], "superseded": []}

    if d.get("summary"):
        store_item(col, {"content": d["summary"], "confidence": "high", "category": "summary"},
                   "summary", sid, date, result)
    for dec in d.get("decisions", []):
        store_item(col, dec, "decision", sid, date, result)
    for fact in d.get("facts", []):
        store_item(col, fact, "fact", sid, date, result)

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
