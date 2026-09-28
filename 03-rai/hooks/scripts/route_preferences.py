#!/usr/bin/env python3
"""
route_preferences.py — the self-evolve router for the distill's preferences:
  preferences  -> learned-candidates.jsonl  (PROBATION, auto-promote on re-confirmation)
Memory v3 (see 03-rai/MEMORY-ARCHITECTURE.md, self-evolve).

Re-confirmation is SEMANTIC (Phase F fix): an incoming preference matches an existing
candidate when their embeddings sit within RECONFIRM_DISTANCE in the derived `rai-preferences`
collection — the v2 exact-hash match meant Opus's rephrasings never re-confirmed and 0 of
912 candidates ever promoted. Falls back to hash-only matching when chromadb is missing
(hence: invoke via py-chroma.sh; plain python3 still works, degraded).

`learned-candidates.jsonl` is the structured source of truth (probation counters live here);
`rai-preferences` is derived from it and rebuilt by curate_candidates.py. Two renders fall
out: `semantic-memory/learned.md` (ACTIVE in full, the top PROBATION_RENDER_TOP probation
items and a count per status) and `identity/learned.md` (ACTIVE-only, capped 2,000 chars —
auto-loaded at SessionStart, removed when empty).

Run: py-chroma.sh route_preferences.py --distill-json <path>
"""

import argparse
import hashlib
import json
import sys
from datetime import date, datetime
from pathlib import Path

SM = Path.home() / "helm" / "03-rai" / "semantic-memory"
CANDIDATES = SM / "learned-candidates.jsonl"
LEARNED_MD = SM / "learned.md"
# ACTIVE slice lands in identity/ so the SessionStart auto-load contract picks it up.
IDENTITY_LEARNED = Path.home() / "helm" / "03-rai" / "identity" / "learned.md"

CONF = {"high": 3, "medium": 2, "low": 1}
PROMOTE_MIN_CONFIRMS = 2
PROMOTE_MIN_CONF = "medium"
PROMOTE_MIN_AGE_DAYS = 3
# Two thresholds, deliberately split (M6, calibrated 2026-07-03 on the live 918-candidate
# index): nearest-neighbor spot-checks showed 0.26-0.31 pairs are DISTINCT-but-related
# preferences while true rephrasings sit below 0.25. Re-confirmation may be looser (a wrong
# +1 confirm is cheap, promotion still needs >=2 + human review); the weekly curation MERGE
# destroys rows, so it stays at the strict 0.15.
RECONFIRM_DISTANCE = 0.25      # semantic re-confirm: "same preference, new words"
MERGE_DISTANCE = 0.15          # curation merge: near-identical only (curate_candidates.py)
IDENTITY_RENDER_CAP = 2000     # hard char cap on the auto-loaded ACTIVE render
PROBATION_RENDER_TOP = 50      # probation items shown in semantic-memory/learned.md
STATUS_ORDER = ("active", "probation", "dormant")
CHROMADB_DIR = Path.home() / "helm" / "03-rai" / "semantic-memory" / "chromadb"
PREF_COLLECTION = "rai-preferences"


def _pref_collection():
    """The derived embedding index over candidates. None when chromadb is unavailable
    (plain python3) — matching then degrades to exact-hash only."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMADB_DIR))
        return client.get_or_create_collection(name=PREF_COLLECTION, metadata={"hnsw:space": "cosine"})
    except Exception:
        return None


def semantic_match(col, content: str) -> str | None:
    """id of an existing candidate whose text means the same thing, else None."""
    if col is None:
        return None
    try:
        if col.count() == 0:
            return None
        r = col.query(query_texts=[content], n_results=1, include=["distances"])
        dists = r.get("distances", [[]])[0]
        ids = r.get("ids", [[]])[0]
        if dists and dists[0] <= RECONFIRM_DISTANCE:
            return ids[0]
    except Exception:
        pass
    return None


def norm(s: str) -> str:
    return " ".join(s.strip().lower().split())


def chash(s: str) -> str:
    return hashlib.sha256(norm(s).encode()).hexdigest()[:16]


def load_candidates() -> dict:
    out = {}
    if CANDIDATES.exists():
        for line in CANDIDATES.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                out[c["id"]] = c
            except Exception:
                pass
    return out


def save_candidates(cands: dict):
    CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATES.write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in cands.values()) + "\n"
    )


def log_promotion(c: dict):
    """Append to promotions.log — the maintenance commit body surfaces new lines, so
    every promotion is VISIBLE to John (decisions.md: notify on promotion).
    Content-less candidates (sanity's EVOLVE-3 smoke dicts) are never logged."""
    content = c.get("content")
    if not content:
        return
    try:
        with open(SM / "promotions.log", "a") as fh:
            fh.write(f"{date.today().isoformat()} PROMOTED: {content}\n")
    except OSError:
        pass


def maybe_promote(c: dict):
    if c["status"] != "probation":
        return
    try:
        age = (date.today() - datetime.strptime(c["first_seen"][:10], "%Y-%m-%d").date()).days
    except Exception:
        age = 0
    if (
        c["re_confirmations"] >= PROMOTE_MIN_CONFIRMS
        and CONF.get(c["confidence"], 2) >= CONF[PROMOTE_MIN_CONF]
        and age >= PROMOTE_MIN_AGE_DAYS
    ):
        c["status"] = "active"
        c["promoted_at"] = date.today().isoformat()
        log_promotion(c)


def render_md(cands: dict):
    """The human-readable view of learned-candidates.jsonl: ACTIVE in full, the top
    PROBATION_RENDER_TOP probation items (most confirmed, then most recently seen) and a
    count per status. The jsonl holds every candidate, so the rest is a pointer."""
    def by_status(status):
        return [c for c in cands.values() if c.get("status") == status]

    def bullets(items):
        if not items:
            return "_(none yet)_"
        lines = []
        for c in items:
            lines.append(f"- **{c['content']}**  ")
            lines.append(
                f"  <sub>confidence: {c['confidence']} · seen {c['re_confirmations']}× · "
                f"source: {c['source_session']} · since {c['first_seen'][:10]}</sub>"
            )
        return "\n".join(lines)

    counts = {}
    for c in cands.values():
        st = c.get("status") or "unknown"
        counts[st] = counts.get(st, 0) + 1
    order = [st for st in STATUS_ORDER if st in counts] + sorted(set(counts) - set(STATUS_ORDER))
    count_rows = "\n".join(f"| {st.upper()} | {counts[st]} |" for st in order) or "| (none) | 0 |"

    active = sorted(by_status("active"), key=lambda x: -x.get("re_confirmations", 1))
    probation = sorted(
        by_status("probation"),
        key=lambda x: (x.get("re_confirmations", 1), x.get("last_seen") or x.get("first_seen") or ""),
        reverse=True,
    )
    shown = probation[:PROBATION_RENDER_TOP]

    md = f"""---
description: >
  Auto-evolved preference candidates (Memory v3), rendered from learned-candidates.jsonl: ACTIVE
  in full, the top probation items and a count per status. Quarantined from the hand-authored
  identity core; git-tracked, reversible. ACTIVE items influence how Rai behaves. DORMANT =
  decayed (no re-confirm in 45d), revivable.
status: living
generated: {date.today().isoformat()}
---

# Learned (self-evolve)

Every candidate, with its full provenance, is in `semantic-memory/learned-candidates.jsonl`.
This page shows the ACTIVE items and the top {PROBATION_RENDER_TOP} probation items.

## Counts

| Status | Candidates |
|---|---|
{count_rows}

## ACTIVE
<!-- promoted: re_confirmations>={PROMOTE_MIN_CONFIRMS}, confidence>={PROMOTE_MIN_CONF}, age>={PROMOTE_MIN_AGE_DAYS}d -->

{bullets(active)}

## PROBATION

Top {len(shown)} of {len(probation)}: most confirmed first, then most recently seen.

{bullets(shown)}
"""
    LEARNED_MD.write_text(md)


def render_identity_active(cands: dict):
    """Write the ACTIVE slice to identity/learned.md so the SessionStart auto-load picks it up.
    These are promoted, cross-session-confirmed *preferences* (behavioral rules) — they must be
    present every session, not retrieved on relevance. Terse on purpose: provenance stays in
    learned-candidates.jsonl (and semantic-memory/learned.md). No ACTIVE items -> no file, so the
    identity/ folder never auto-loads an empty husk (the disease Memory v2 cured)."""
    active = sorted(
        (c for c in cands.values() if c.get("status") == "active"),
        key=lambda x: -x.get("re_confirmations", 1),
    )
    if not active:
        if IDENTITY_LEARNED.exists():
            IDENTITY_LEARNED.unlink()
        return
    # Hard render cap (IDENTITY_RENDER_CAP): top-confirmed items only — this file is
    # always-injected, so it must stay small. The full list lives in learned-candidates.jsonl.
    lines, used = [], 0
    for c in active:
        line = f"- {c['content']}"
        if used + len(line) + 1 > IDENTITY_RENDER_CAP:
            break
        lines.append(line)
        used += len(line) + 1
    body = "\n".join(lines)
    md = f"""---
description: >
  Auto-evolved preferences confirmed across sessions (Memory v3), promoted from probation.
  Quarantined from the hand-authored identity core; git-tracked, reversible. These influence
  how Rai behaves. Top probation items and counts: semantic-memory/learned.md; every
  candidate: semantic-memory/learned-candidates.jsonl.
status: living
generated: {date.today().isoformat()}
---

# Learned preferences (self-evolve · ACTIVE)

{body}
"""
    IDENTITY_LEARNED.parent.mkdir(parents=True, exist_ok=True)
    IDENTITY_LEARNED.write_text(md)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--distill-json", required=True)
    a = p.parse_args()

    d = json.loads(Path(a.distill_json).read_text())
    sid = d.get("session_id", "")
    date_s = d.get("date", "")
    cands = load_candidates()
    col = _pref_collection()
    added, confirmed = [], []

    def reconfirm(cid: str):
        c = cands[cid]
        c["re_confirmations"] += 1
        c["last_seen"] = date_s
        if c.get("status") == "dormant":
            c["status"] = "probation"  # a re-confirm revives a decayed candidate
        if sid and sid not in c.get("sources", []):
            c.setdefault("sources", []).append(sid)
        maybe_promote(c)
        confirmed.append(cid)

    for pref in d.get("preferences", []):
        content = (pref.get("content") or "").strip()
        if not content:
            continue
        cid = chash(content)
        if cid in cands:
            reconfirm(cid)
            continue
        # semantic re-confirmation: same meaning, different phrasing (the v2 gap)
        match = semantic_match(col, content)
        if match and match in cands:
            reconfirm(match)
            continue
        cands[cid] = {
            "id": cid, "type": "preference", "content": content,
            "confidence": pref.get("confidence", "medium"),
            "evidence": pref.get("evidence", []),
            "source_session": sid, "sources": [sid],
            "first_seen": date_s, "last_seen": date_s,
            "re_confirmations": 1, "contradictions": 0, "status": "probation",
        }
        added.append(cid)
        if col is not None:
            try:
                col.upsert(ids=[cid], documents=[content])
            except Exception:
                pass

    save_candidates(cands)
    render_md(cands)
    render_identity_active(cands)

    print(json.dumps({
        "preferences_added": added,
        "preferences_confirmed": confirmed,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
