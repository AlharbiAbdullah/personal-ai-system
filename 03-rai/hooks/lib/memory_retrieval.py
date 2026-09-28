#!/usr/bin/env python3
"""
memory_retrieval.py — query helpers for the Memory v3 stores (`rai-semantic`,
`rai-episodic`, `rai-daily`). See 03-rai/MEMORY-ARCHITECTURE.md.

Live consumers: memory-injection.py (per-prompt pointer RAG, under py-chroma.sh) and
the batch render_memory_block.py (session_start_block -> the frozen snapshot file).
session-start.py reads that FILE — it never imports this module (no ChromaDB at start).
The eval harness (skills/rai/scripts/eval.py) queries through here too.

Standalone CLI (also the /recall T1/T2 query path — every event logs to
recall-usage.jsonl through ONE writer, ONE schema):
  py-chroma.sh hooks/lib/memory_retrieval.py semantic|daily|episodic "the query"
  py-chroma.sh hooks/lib/memory_retrieval.py outcome T0|T1|T2|T3 hit|miss
"""

import json
import math
import sys
from datetime import date as _date, datetime
from pathlib import Path

import chromadb

CHROMADB_DIR = Path.home() / "helm" / "03-rai" / "semantic-memory" / "chromadb"


def _client():
    return chromadb.PersistentClient(path=str(CHROMADB_DIR))


def _collection(name):
    return _client().get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def _recency(date_str: str, half_life_days: int = 30) -> float:
    """1.0 today, decaying with age. Missing/odd dates -> neutral 0.5."""
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        days = max(0, (_date.today() - d).days)
        return math.exp(-days / half_life_days)
    except Exception:
        return 0.5


_CONF = {"high": 1.0, "medium": 0.6, "low": 0.3}


def query_semantic(query: str, top_k: int = 8):
    """Top-k distilled facts/decisions/summaries, scored relevance x recency x importance."""
    col = _collection("rai-semantic")
    if col.count() == 0:
        return []
    r = col.query(
        query_texts=[query], n_results=min(top_k * 2, col.count()),
        where={"status": "active"},
        include=["documents", "metadatas", "distances"],
    )
    rows = []
    for i, doc in enumerate(r.get("documents", [[]])[0]):
        md = r["metadatas"][0][i]
        rel = 1 - r["distances"][0][i]
        rec = _recency(md.get("source_date", ""))
        imp = _CONF.get(md.get("confidence", "medium"), 0.6)
        # cross-session confirmation as a small importance bonus; recency weighted up a notch so
        # a current decision outranks the older one it reversed (backfill rarely set supersede links).
        confirm_bonus = 0.05 * math.log1p(int(md.get("confirmation_count", 1) or 1))
        rows.append({
            "id": r["ids"][0][i],
            "content": doc, "type": md.get("type"), "confidence": md.get("confidence"),
            "source_session": md.get("source_session"), "date": md.get("source_date"),
            "relevance": round(rel, 3),
            "score": 0.55 * rel + 0.25 * rec + 0.20 * imp + confirm_bonus,
        })
    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows[:top_k]


def query_daily(query: str, top_k: int = 5):
    """Top-k live-capture blocks from the turn-capture daily logs (`rai-daily`).

    Blocks whose session was already distilled are down-ranked BY DEFAULT (coupling B):
    daily is the recency buffer; the quality record for distilled sessions lives in
    rai-semantic. The policy lives here, not in callers."""
    col = _collection("rai-daily")
    if col.count() == 0:
        return []
    r = col.query(
        query_texts=[query], n_results=min(top_k * 2, col.count()),
        include=["documents", "metadatas", "distances"],
    )
    rows = []
    for i, doc in enumerate(r.get("documents", [[]])[0]):
        md = r["metadatas"][0][i]
        rows.append({
            "id": r["ids"][0][i], "content": doc,
            "date": md.get("date"), "time": md.get("time"), "session": md.get("session"),
            "distilled": bool(md.get("distilled")),
            "relevance": round(1 - r["distances"][0][i], 3),
        })
    rows.sort(key=lambda x: x["relevance"] - (0.15 if x["distilled"] else 0), reverse=True)
    return rows[:top_k]


def query_episodic(query: str, top_k: int = 5):
    """Top-k whole sessions (receipts). Returns pointers, not full transcripts.

    Two merged paths (2026-07-04): the direct vector match against whole-session
    embeddings, PLUS a semantic bridge — question-shaped queries match distilled
    facts far better than session blobs (baseline eval: 0/6 episodic golden rows
    direct), so the top rai-semantic hits vote for their source sessions. `via`
    on each row says which path found it."""
    col = _collection("rai-episodic")
    if col.count() == 0:
        return []
    r = col.query(
        query_texts=[query], n_results=min(top_k, col.count()),
        include=["metadatas", "distances"],
    )
    rows = {}
    for i, sid in enumerate(r.get("ids", [[]])[0]):
        md = r["metadatas"][0][i]
        rows[sid] = {
            "session_id": sid, "date": md.get("date"), "context": md.get("context"),
            "project_name": md.get("project_name"), "message_count": md.get("message_count"),
            "relevance": round(1 - r["distances"][0][i], 3),
            "via": "direct",
        }
    # wider take than top_k: several facts often share a session, and the golden
    # probes showed right answers sitting at semantic rank 6-10
    for s in query_semantic(query, top_k=max(top_k * 2, 10)):
        sid = (s.get("source_session") or "").strip()
        if not sid:
            continue
        rel = round(s.get("relevance", 0), 3)
        if sid in rows:
            if rel > rows[sid]["relevance"]:
                rows[sid]["relevance"] = rel
                rows[sid]["via"] = "semantic"
            continue
        g = col.get(ids=[sid], include=["metadatas"])
        if not g.get("ids"):
            continue
        md = g["metadatas"][0]
        rows[sid] = {
            "session_id": sid, "date": md.get("date"), "context": md.get("context"),
            "project_name": md.get("project_name"), "message_count": md.get("message_count"),
            "relevance": rel,
            "via": "semantic",
        }
    out = sorted(rows.values(), key=lambda x: x["relevance"], reverse=True)
    return out[:top_k]


_CAT_W = {"preference": 1.4, "project": 1.3, "reference": 1.2, "technical": 0.8}


def _importance(md) -> float:
    """Durable-identity score for the no-query cold start. Confidence x cross-session
    confirmation x FLOORED recency (60-day half-life, 0.4 floor) x category weight — so a
    durable identity/preference/project fact outranks recent one-off ops/implementation churn."""
    conf = _CONF.get(md.get("confidence", "medium"), 0.6)
    confirms = 1.0 + math.log1p(int(md.get("confirmation_count", 1) or 1))
    rec = 0.4 + 0.6 * _recency(md.get("source_date", ""), half_life_days=60)
    cat = _CAT_W.get((md.get("category") or "").lower(), 1.0)
    return conf * confirms * rec * cat


def recent_semantic(n: int = 12):
    """Top active facts by IMPORTANCE (durable identity first), deduped on near-identical
    content — replaces the old recency×confidence sort that let yesterday's churn dominate."""
    col = _collection("rai-semantic")
    if col.count() == 0:
        return []
    g = col.get(where={"status": "active"}, include=["metadatas", "documents"])
    # facts + decisions only — session `summary` rows are recaps, surfaced via "recent sessions".
    # `content` normally lives in metadata; fall back to the document so a missing copy can
    # never silently dedup every row to the same empty key (= empty memory-block).
    cand = []
    for m, doc in zip(g["metadatas"], g.get("documents") or [None] * len(g["metadatas"])):
        if m.get("type") not in ("fact", "decision"):
            continue
        if not m.get("content") and doc:
            m = {**m, "content": doc}
        cand.append(m)
    rows = sorted(cand, key=_importance, reverse=True)
    out, seen = [], set()
    for r in rows:
        key = (r.get("content") or "")[:60].strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
        if len(out) >= n:
            break
    return out


def recent_episodic(n: int = 5):
    """Most recent sessions by date (no query — for SessionStart)."""
    col = _collection("rai-episodic")
    if col.count() == 0:
        return []
    g = col.get(include=["metadatas"])
    return sorted(g["metadatas"], key=lambda m: m.get("date", ""), reverse=True)[:n]


def _session_names() -> dict:
    """sid -> live tab name (session-names.json in the runtime dir, written by the
    session-auto-name hook). The episodic `context` label is a coarse intent
    bucket — five sessions all rendering as 'brainstorm' tell John nothing;
    the tab names are what he actually saw."""
    try:
        from .paths import get_runtime_dir
        p = get_runtime_dir() / "session-names.json"
        return {k: (v.get("name") or "").strip()
                for k, v in json.loads(p.read_text()).items()}
    except Exception:
        return {}


def session_start_block(n_semantic: int = 12, n_episodic: int = 5) -> str:
    """The tiered memory section rendered into the frozen snapshot (memory-block.md)."""
    facts = recent_semantic(n_semantic)
    eps = recent_episodic(n_episodic)
    if not facts and not eps:
        return ""
    out = [f"## Memory (v3 · {len(facts)} facts + {len(eps)} recent sessions)"]
    for f in facts:
        out.append(f"- [{f.get('type')}/{f.get('confidence')}] {f.get('content')}")
    if eps:
        names = _session_names()
        out.append("\n### Recent sessions")
        for e in eps:
            parts = [(e.get("context") or "").strip(), (e.get("project_name") or "").strip()]
            fallback = " ".join(p for p in parts if p and p.lower() != "unknown")
            label = names.get((e.get("session_id") or "").strip()) or fallback or "session"
            out.append(f"- [{e.get('date')}] {label}".rstrip())
    return "\n".join(out)


def _log_usage(event: str, **fields):
    """One line per recall event — the month-end review's data source
    (decisions.md 2026-07-03). ONE writer, ONE schema (unified 2026-07-04):
      event=query   {mode, query_hash, n, top_relevance} — CLI tier queries
      event=outcome {tier, hit} — /recall's last step via the `outcome` CLI mode
    tz-aware timestamps. Fail-open, never blocks."""
    try:
        rec = {
            "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
            "event": event,
            **fields,
        }
        log = Path.home() / "helm" / "03-rai" / "memory" / "learning" / "system" / "recall-usage.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def _log_query(mode: str, query: str, rows: list):
    import hashlib
    _log_usage(
        "query", mode=mode,
        query_hash=hashlib.sha256(query.encode()).hexdigest()[:8],
        n=len(rows),
        top_relevance=max((r.get("relevance", 0) for r in rows), default=0),
    )


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "semantic"
    if mode == "start":
        print(session_start_block())
        sys.exit(0)
    if mode == "outcome":
        tier = sys.argv[2] if len(sys.argv) > 2 else "?"
        hit = sys.argv[3].strip().lower() in ("hit", "true", "1") if len(sys.argv) > 3 else False
        _log_usage("outcome", tier=tier, hit=hit)
        sys.exit(0)
    q = sys.argv[2] if len(sys.argv) > 2 else "test"
    fn = {"semantic": query_semantic, "episodic": query_episodic, "daily": query_daily}.get(mode, query_semantic)
    rows = fn(q)
    _log_query(mode, q, rows)
    print(json.dumps(rows, indent=2, ensure_ascii=False))
