#!/usr/bin/env python3
"""
export_index.py — Memory v2: dump the `rai-semantic` collection (the irreplaceable Opus
distillation) to a git-committable JSONL source file.

`semantic-memory/chromadb/` is gitignored (a derived binary that was the #1 git-bloat
source). This JSONL is the DURABLE SOURCE the binary is rebuilt from on any machine
(rebuild_chromadb.py) — no Opus re-run needed. `rai-episodic` is NOT exported here: it is
rebuilt cheaply from the committed archive transcripts.

Run: semantic-memory/scripts/py-chroma.sh hooks/scripts/export_index.py
"""

import json
from pathlib import Path

import chromadb

SM = Path.home() / "helm" / "03-rai" / "semantic-memory"
DB = SM / "chromadb"
OUT = SM / "index"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB))
    col = client.get_or_create_collection(
        name="rai-semantic", metadata={"hnsw:space": "cosine"}
    )
    g = col.get(include=["documents", "metadatas"])
    ids, docs, metas = g["ids"], g["documents"], g["metadatas"]
    rows = [
        {"id": ids[i], "document": docs[i], "metadata": metas[i]}
        for i in range(len(ids))
    ]
    rows.sort(key=lambda r: r["id"])  # stable order → clean git diffs
    path = OUT / "rai-semantic.jsonl"
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"exported {len(rows)} rai-semantic rows -> {path}")


if __name__ == "__main__":
    main()
