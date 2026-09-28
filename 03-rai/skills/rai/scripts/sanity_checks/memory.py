"""Live capture, Self-evolve and Retrieval: the Memory v3 loops that must keep producing."""

import json
from datetime import date

from . import core
from .core import FAIL, PASS, PRODUCER, SKIP, WARN, P, check

# ════════════════════════════════════════════════════════════════════════════════
# LIVE CAPTURE (Memory v3 — turn-capture daily logs + curated working memory)
# Not a BROKEN-class subsystem: capture failing = a feature off, data safe.
# ════════════════════════════════════════════════════════════════════════════════
DAILY_FRESH_DAYS = 3          # John works daily; no bullet in 3d = capture likely dead
WORKING_MEMORY_CAP = 2500     # the /remember hard cap
DAILY_INDEX_DRIFT_WARN = 50   # blocks appended since the last drain are expected lag
CANDIDATES_FRESH_DAYS = 10    # newest self-evolve candidate (distil cadence is bursty)


@check("LIVE-1", "Live capture")
def daily_log_fresh():
    """turn-capture.py must be producing: a recent daily file with well-formed blocks."""
    daily = P.SM / "daily"
    files = sorted(daily.glob("*.md")) if daily.exists() else []
    if not files:
        return WARN, "no daily logs yet", "turn-capture has produced nothing — new install, or the Stop hook is dead."
    newest = files[-1]
    age_d = core._age_hours(newest) / 24
    import index_daily
    blocks = sum(1 for f in files for _ in index_daily.parse_blocks(f))
    ev = f"{len(files)} files, {blocks} blocks, newest {newest.stem} ({age_d:.1f}d old)"
    if blocks == 0:
        return FAIL, ev, "Daily files exist but contain no parseable blocks — turn-capture format drift."
    if age_d > DAILY_FRESH_DAYS:
        return WARN, ev, "No live capture in days — check the Stop hook + hook-perf for turn-capture."
    return PASS, ev, ""


@check("LIVE-2", "Live capture")
def daily_index_parity():
    """index_daily.py must keep rai-daily tracking the daily files (batch step of every drain)."""
    daily = P.SM / "daily"
    files = sorted(daily.glob("*.md")) if daily.exists() else []
    if not files:
        return SKIP, "no daily logs yet", ""
    import index_daily
    blocks = sum(1 for f in files for _ in index_daily.parse_blocks(f))
    indexed = core._collections().get("rai-daily", 0)
    drift = blocks - indexed
    ev = f"file blocks={blocks}, indexed={indexed}, lag={drift}"
    if blocks >= 20 and indexed == 0:
        return FAIL, ev, "Indexer never ran — check index_daily in the drain."
    if drift > DAILY_INDEX_DRIFT_WARN:
        return WARN, ev, "Index lagging the files — confirm the drain is running index_daily."
    return PASS, ev, ""


@check("LIVE-3", "Live capture")
def working_memory_cap():
    """identity/working-memory.md is always-injected — the 2,500-char cap is a hard contract."""
    p = P.RAI / "identity" / "working-memory.md"
    if not p.exists():
        return WARN, "working-memory.md absent", "The curated scratchpad is gone — recreate from the /remember skill template."
    size = p.stat().st_size
    ev = f"{size}/{WORKING_MEMORY_CAP} chars"
    if size > WORKING_MEMORY_CAP:
        return FAIL, ev, "Over the hard cap — /remember must consolidate; trim the file."
    return PASS, ev, ""


# ════════════════════════════════════════════════════════════════════════════════
# SELF-EVOLVE
# ════════════════════════════════════════════════════════════════════════════════
@check("EVOLVE-1", "Self-evolve")
def candidates_present():
    """learned-candidates.jsonl exists, parses, and holds candidates."""
    p = P.SM / "learned-candidates.jsonl"
    if not p.exists():
        return FAIL, "learned-candidates.jsonl missing", "route_preferences.py never wrote — distill not routing."
    lines = [l for l in p.read_text().splitlines() if l.strip()]
    try:
        for l in lines:
            json.loads(l)
    except Exception as e:
        return FAIL, f"unparseable line: {e}", "Corrupt candidates file — inspect last appended line."
    ev = f"{len(lines)} candidates"
    return (FAIL, ev + " — self-evolve produced NOTHING", "The exact 3-month-blindness signal: distill isn't yielding preferences.") if not lines else (PASS, ev, "")


@check("EVOLVE-2", "Self-evolve", role=PRODUCER)
def candidates_fresh():
    """A new self-evolve candidate landed within ten days."""
    p = P.SM / "learned-candidates.jsonl"
    if not p.exists():
        return FAIL, "missing", "route_preferences.py not writing."
    age_d = core._age_hours(p) / 24
    ev = f"candidates file {age_d:.1f}d old"
    if age_d > CANDIDATES_FRESH_DAYS * 2:
        return FAIL, ev, "No new candidate in weeks — distill is producing no preferences."
    if age_d > CANDIDATES_FRESH_DAYS:
        return WARN, ev, "Going stale — confirm sessions are being distilled."
    return PASS, ev, ""


@check("EVOLVE-3", "Self-evolve")
def promotion_logic():
    """Smoke-test the promotion gate so a regression in route_preferences is caught BEFORE it
    silently stops promoting (or wrongly promotes everything)."""
    import importlib
    rp = importlib.import_module("route_preferences")
    old = date.today().replace(year=date.today().year - 1).isoformat()
    promote = {"status": "probation", "re_confirmations": 2, "confidence": "high", "first_seen": old}
    hold = {"status": "probation", "re_confirmations": 1, "confidence": "high", "first_seen": old}
    rp.maybe_promote(promote)
    rp.maybe_promote(hold)
    ok = promote["status"] == "active" and hold["status"] == "probation"
    ev = f"qualifying->{'active' if promote['status']=='active' else promote['status']}, under-confirmed->{hold['status']}"
    return (PASS, ev, "") if ok else (FAIL, ev, "Promotion gate broken — review maybe_promote() thresholds.")


@check("EVOLVE-4", "Self-evolve")
def active_render_invariant():
    """identity/learned.md must exist IFF there is at least one ACTIVE candidate — that is the
    wiring that puts promoted behavioural rules into the auto-load path."""
    import importlib
    rp = importlib.import_module("route_preferences")
    cands = rp.load_candidates()
    active = sum(1 for c in cands.values() if c.get("status") == "active")
    id_path = P.RAI / "identity" / "learned.md"
    id_md = id_path.exists()
    ev = f"ACTIVE={active}, identity/learned.md={'present' if id_md else 'absent'}"
    if (active > 0) != id_md:
        return FAIL, ev, "Invariant broken — re-run route_preferences.py to re-render the ACTIVE slice."
    # v3: the render is always-injected, so its cap is load-bearing (frontmatter + 2,000-char body)
    if id_md:
        size = id_path.stat().st_size
        ev += f", {size} chars"
        if size > rp.IDENTITY_RENDER_CAP + 600:
            return FAIL, ev, "ACTIVE render blew its cap — render_identity_active() cap logic broken."
    return PASS, ev, ""


@check("EVOLVE-5", "Self-evolve")
def learned_md_renders():
    """semantic-memory/learned.md renders its Counts, ACTIVE and PROBATION sections."""
    p = P.SM / "learned.md"
    if not p.exists():
        return FAIL, "learned.md missing", "route_preferences.py render step not running."
    txt = p.read_text()
    want = ("## Counts", "## ACTIVE", "## PROBATION")
    have = [s for s in want if s in txt]
    ev = f"sections {have}"
    return (PASS, ev, "") if len(have) == len(want) else (FAIL, ev, "Audit render malformed — check render_md().")


# ════════════════════════════════════════════════════════════════════════════════
# RETRIEVAL
# ════════════════════════════════════════════════════════════════════════════════
@check("RECALL-1", "Retrieval")
def session_start_block():
    """session_start_block() builds a non-empty memory block with its header."""
    from lib.memory_retrieval import session_start_block as ssb
    block = ssb()
    ev = f"{len(block)} chars"
    if not block:
        return FAIL, "empty block", "SessionStart injects no memory — stores empty or retrieval broken."
    if "## Memory" not in block:
        return WARN, ev + " (no Memory header)", "Block built but header changed — verify session_start_block()."
    return PASS, ev, ""


@check("RECALL-3", "Retrieval")
def frozen_memory_block():
    """Memory v3: session-start reads memory/state/memory-block.md (rendered by the drain),
    NOT ChromaDB. A missing/stale file means every new session starts memory-blind even
    though the stores are healthy."""
    p = P.RAI / "memory" / "state" / "memory-block.md"
    if not p.exists():
        if core._collections().get("rai-semantic", 0) == 0:
            return SKIP, "stores empty — nothing to render yet", ""
        return FAIL, "memory-block.md missing", "Run render_memory_block.py (or a full /process-sessions)."
    age_d = core._age_hours(p) / 24
    size = p.stat().st_size
    ev = f"{size} chars, {age_d:.1f}d old"
    if size < 100:
        return FAIL, ev, "Block file near-empty — render_memory_block produced nothing."
    if age_d > 7:
        return WARN, ev, "Frozen block stale — drains aren't re-rendering (no distills in a week?)."
    return PASS, ev, ""


@check("RECALL-4", "Retrieval")
def daily_query_path():
    """query_daily (the /recall T1 live-log tier) must return rows once rai-daily has data."""
    from lib.memory_retrieval import query_daily
    n = core._collections().get("rai-daily", 0)
    if n == 0:
        return SKIP, "rai-daily empty — nothing to query yet", ""
    rows = query_daily("session work", top_k=3)
    ev = f"{len(rows)} results from {n} blocks"
    return (FAIL, ev, "rai-daily populated but unqueryable — check query_daily/memory_retrieval.") if not rows else (PASS, ev, "")


@check("RECALL-2", "Retrieval")
def per_prompt_injection():
    """Per-prompt retrieval returns semantic or episodic rows."""
    from lib.memory_retrieval import query_semantic, query_episodic
    s = query_semantic("financial investment debt plan", top_k=3)
    e = query_episodic("news digest collection", top_k=2)
    ev = f"semantic={len(s)}, episodic={len(e)} pointers"
    return (FAIL, ev, "Per-prompt RAG returns nothing — memory-injection.py would no-op.") if not s and not e else (PASS, ev, "")
