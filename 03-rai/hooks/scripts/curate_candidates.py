#!/usr/bin/env python3
"""
curate_candidates.py — Memory v3 (Phase F): the formalized "dreaming" pass over the
self-evolve candidates (learned-candidates.jsonl).

Deterministic, batch-only, weekly (coordinator, Sundays) + one-time to consolidate the
912-candidate graveyard v2's exact-hash matching produced:

  1. REBUILD the derived `rai-preferences` embedding index from the candidate file.
  2. MERGE semantic near-duplicates (cosine <= MERGE_DISTANCE, strict 0.15): the earliest-seen
     candidate is canonical; re_confirmations are summed, sources unioned, confidence
     maxed. Merged ids are dropped from the file (git history is the audit).
  3. DECAY: probation candidates not seen in DECAY_DAYS -> dormant (revived by any
     later re-confirmation in route_preferences).
  4. PROMOTE: standard gate (>=2 confirms · >=medium · >=3d) over the merged counts.
  5. RENDER learned.md (full audit) + identity/learned.md (ACTIVE, capped 2,000 chars).
  6. RE-SYNC the embedding index to the post-merge candidate set.

Run: semantic-memory/scripts/py-chroma.sh hooks/scripts/curate_candidates.py [--dry-run]
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path.home() / "helm" / "03-rai"
sys.path.insert(0, str(ROOT / "hooks" / "scripts"))

import route_preferences as rp  # noqa: E402 — reuse constants, loaders, renders

DECAY_DAYS = 45
NEIGHBORS = 12  # M6: 6 under-merged clusters larger than 6 near-dupes


def rebuild_index(cands: dict):
    import chromadb
    client = chromadb.PersistentClient(path=str(rp.CHROMADB_DIR))
    # Sync in place, never drop: each delete_collection left an orphan HNSW dir on disk.
    col = client.get_or_create_collection(name=rp.PREF_COLLECTION, metadata={"hnsw:space": "cosine"})
    ids = [c["id"] for c in cands.values() if c.get("status") != "retired"]
    docs = [cands[i]["content"] for i in ids]
    B = 200
    keep = set(ids)
    stale = [i for i in col.get(include=[])["ids"] if i not in keep]
    for i in range(0, len(stale), B):
        col.delete(ids=stale[i:i + B])
    for i in range(0, len(ids), B):
        col.upsert(ids=ids[i:i + B], documents=docs[i:i + B])
    return col


def merge_into(canon: dict, dup: dict):
    canon["re_confirmations"] = int(canon.get("re_confirmations", 1)) + int(dup.get("re_confirmations", 1))
    canon["sources"] = sorted(set(canon.get("sources", [])) | set(dup.get("sources", [])))
    canon["first_seen"] = min(canon.get("first_seen", ""), dup.get("first_seen", "")) or canon.get("first_seen", "")
    canon["last_seen"] = max(canon.get("last_seen", ""), dup.get("last_seen", ""))
    if rp.CONF.get(dup.get("confidence"), 0) > rp.CONF.get(canon.get("confidence"), 0):
        canon["confidence"] = dup["confidence"]
    ev = canon.get("evidence", []) + dup.get("evidence", [])
    canon["evidence"] = ev[:3]
    canon["contradictions"] = int(canon.get("contradictions", 0)) + int(dup.get("contradictions", 0))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    cands = rp.load_candidates()
    if not cands:
        print("curate: no candidates")
        return 0

    if rp._pref_collection() is None:
        print("curate: chromadb unavailable — run under py-chroma.sh", file=sys.stderr)
        return 1
    col = rebuild_index(cands)

    # ── merge near-duplicates (earliest first_seen = canonical) ──
    order = sorted(cands.values(), key=lambda c: (c.get("first_seen", ""), c["id"]))
    merged_away: dict[str, str] = {}   # dup id -> canonical id
    for c in order:
        cid = c["id"]
        if cid in merged_away:
            continue
        try:
            r = col.query(query_texts=[c["content"]], n_results=min(NEIGHBORS, col.count()),
                          include=["distances"])
        except Exception:
            continue
        for nid, dist in zip(r.get("ids", [[]])[0], r.get("distances", [[]])[0]):
            if nid == cid or nid in merged_away or nid not in cands:
                continue
            if dist <= rp.MERGE_DISTANCE:
                merge_into(c, cands[nid])
                merged_away[nid] = cid
    for dup in merged_away:
        cands.pop(dup, None)

    # ── decay + promote ──
    today = date.today()
    dormant = promoted = 0
    for c in cands.values():
        if c.get("status") == "probation":
            try:
                last = datetime.strptime((c.get("last_seen") or c.get("first_seen", ""))[:10], "%Y-%m-%d").date()
                if (today - last).days > DECAY_DAYS:
                    c["status"] = "dormant"
                    dormant += 1
                    continue
            except Exception:
                pass
        before = c.get("status")
        rp.maybe_promote(c)
        if before != "active" and c.get("status") == "active":
            promoted += 1

    stats = {
        "candidates_before": len(cands) + len(merged_away),
        "merged_away": len(merged_away),
        "candidates_after": len(cands),
        "promoted_now": promoted,
        "active_total": sum(1 for c in cands.values() if c.get("status") == "active"),
        "dormant_now": dormant,
        "dormant_total": sum(1 for c in cands.values() if c.get("status") == "dormant"),
        "probation_total": sum(1 for c in cands.values() if c.get("status") == "probation"),
    }
    if a.dry_run:
        print(f"curate (dry-run): {json.dumps(stats)}")
        return 0

    rp.save_candidates(cands)
    rp.render_md(cands)
    rp.render_identity_active(cands)
    rebuild_index(cands)
    print(f"curate: {json.dumps(stats)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
