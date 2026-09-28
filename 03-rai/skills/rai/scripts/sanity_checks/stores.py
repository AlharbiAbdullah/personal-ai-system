"""Environment + Stores: chromadb importable, the four collections populated, fresh, writable,
queryable, in parity with the committed index; and the replica's view on the consumer."""

import os

from . import core
from .core import (ASSERTED_COLLECTIONS, CONSUMER, CORE_COLLECTIONS, FAIL, PASS,
                   PROBE_COLLECTION, WARN, P, check)

STORE_FRESH_DAYS = 7        # newest distilled/rebuilt row


# ════════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT
# ════════════════════════════════════════════════════════════════════════════════
@check("ENV-1", "Environment")
def chromadb_importable():
    """chromadb imports under the wrapper's interpreter."""
    import chromadb
    return PASS, f"chromadb {chromadb.__version__}", ""


@check("ENV-2", "Environment")
def wrapper_executable():
    """py-chroma.sh exists and is executable."""
    if P.WRAP.exists() and os.access(P.WRAP, os.X_OK):
        return PASS, "py-chroma.sh executable", ""
    return FAIL, f"{P.WRAP} not executable", "chmod +x the wrapper."


# ════════════════════════════════════════════════════════════════════════════════
# STORES (Memory v2)
# ════════════════════════════════════════════════════════════════════════════════
@check("STORE-1", "Stores")
def stores_present_populated():
    """The four asserted collections exist and the core pair holds rows."""
    cols = core._collections()
    missing = ASSERTED_COLLECTIONS - cols.keys()
    if missing:
        return FAIL, f"missing {sorted(missing)} (live: {sorted(cols)})", "Run rebuild_chromadb.py from the committed index."
    empty = [c for c in CORE_COLLECTIONS if cols[c] == 0]
    ev = ", ".join(f"{c}={cols[c]}" for c in sorted(ASSERTED_COLLECTIONS))
    if empty:
        return FAIL, f"{ev} (EMPTY: {empty})", "Store empty — rebuild from index or re-run the pipeline."
    return PASS, ev, ""


@check("STORE-2", "Stores")
def store_freshness():
    """Newest distilled (producer) / rebuilt (consumer) row. Stale = distill stopped OR the
    replica rebuilt from a stale index. Either way the brain has stopped ingesting reality."""
    col = core._client().get_collection("rai-semantic")
    metas = col.get(include=["metadatas"])["metadatas"]
    dates = [m.get("source_date", "") for m in metas if m.get("source_date")]
    if not dates:
        return FAIL, "no source_date on any row", "Schema drift — rai-semantic rows lack source_date."
    newest = max(dates)
    d = core._days_old(newest)
    ev = f"newest source_date {newest} ({d}d ago), {len(metas)} rows"
    if d > STORE_FRESH_DAYS * 2:
        return FAIL, ev, "No fresh memory in 2+ weeks — pipeline or rebuild is dead."
    if d > STORE_FRESH_DAYS:
        return WARN, ev, "Slightly stale — confirm the coordinator ran recently."
    return PASS, ev, ""


@check("STORE-3", "Stores", slow=True)
def store_roundtrip():
    """Write/read/delete one row in the permanent probe collection — proves the real store accepts
    writes. Never drops the collection: each drop leaves an orphan HNSW dir behind on disk."""
    import uuid
    col = core._client().get_or_create_collection(PROBE_COLLECTION)
    pid = f"probe-{uuid.uuid4()}"
    try:
        col.add(ids=[pid], documents=["sanity probe"], metadatas=[{"t": "probe"}])
        got = col.get(ids=[pid])
        assert got["ids"] == [pid], "probe missing after write"
        col.delete(ids=[pid])
        assert col.get(ids=[pid])["ids"] == [], "probe survived delete"
        return PASS, "write/read/delete OK", ""
    finally:
        try:
            col.delete(ids=[pid])
        except Exception:
            pass


@check("STORE-4", "Stores")
def store_query():
    """A semantic query returns relevant rows."""
    from lib.memory_retrieval import query_semantic
    rows = query_semantic("brain memory vault sessions", top_k=3)
    if not rows:
        return FAIL, "query returned nothing", "Retrieval broken — embeddings or collection empty."
    top = max(r["score"] for r in rows)
    ev = f"{len(rows)} results, top score {top:.2f}"
    return (WARN, ev, "Low similarity — embedding model may have changed.") if top < 0.3 else (PASS, ev, "")


@check("STORE-5", "Stores")
def index_parity():
    """The committed rai-semantic.jsonl and the store hold the same number of rows."""
    idx = P.SM / "index" / "rai-semantic.jsonl"
    if not idx.exists():
        return FAIL, "rai-semantic.jsonl missing", "The committed source of truth is gone — export_index.py."
    lines = sum(1 for _ in idx.open())
    count = core._collections().get("rai-semantic", 0)
    drift = abs(lines - count)
    ev = f"index={lines}, store={count}, drift={drift}"
    if drift > max(50, count * 0.05):
        return WARN, ev, "Index and store diverged — re-export or rebuild to reconcile."
    return PASS, ev, ""


# ════════════════════════════════════════════════════════════════════════════════
# CONSUMER (Mac replica health)
# ════════════════════════════════════════════════════════════════════════════════
@check("REPLICA-1", "Stores", role=CONSUMER)
def replica_in_sync():
    """The Mac can't fetch GitHub; the coordinator fast-forwards it over SSH. If local HEAD lags
    origin by a lot, the refresh has stopped and recall is reading a stale brain."""
    local = core._git("rev-parse", "HEAD")
    # --verify --quiet: a plain rev-parse echoes an unknown ref back on stdout, which read as
    # "origin exists" and passed a replica that had never fetched origin at all
    origin = core._git("rev-parse", "--verify", "--quiet", "origin/main")
    if not origin:
        return WARN, "no origin/main ref", "Coordinator hasn't propagated origin ref yet."
    # BEHIND (origin commits the Mac lacks) = real staleness. AHEAD (local churn not yet pushed by
    # the coordinator) is normal between cycles and must not warn.
    behind = len([l for l in core._git("rev-list", "HEAD..origin/main").splitlines() if l])
    ahead = len([l for l in core._git("rev-list", "origin/main..HEAD").splitlines() if l])
    if behind == 0:
        ev = f"HEAD==origin @ {local[:10]}" if ahead == 0 else f"in sync (ahead {ahead}, awaiting coordinator push)"
        return PASS, ev, ""
    return (WARN if behind < 20 else FAIL, f"{behind} commits behind origin",
            "refresh_mac stopped landing — check Tailscale SSH from Ubuntu.")


@check("REPLICA-2", "Stores", role=CONSUMER)
def replica_chromadb_fresh():
    """The replica's chromadb was refreshed within a week."""
    if not P.CHROMADB_DIR.exists():
        return FAIL, "chromadb dir missing", "Run rebuild_chromadb.py from the committed index."
    sqlite = P.CHROMADB_DIR / "chroma.sqlite3"
    if not sqlite.exists():
        return FAIL, "chroma.sqlite3 missing", "Store not built — rebuild_chromadb.py."
    age_d = core._age_hours(sqlite) / 24
    ev = f"chromadb {age_d:.1f}d old"
    return (WARN, ev, "Replica store stale — rsync from Ubuntu / rebuild.") if age_d > 7 else (PASS, ev, "")
