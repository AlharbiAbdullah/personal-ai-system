"""Live capture, Self-evolve and Retrieval checks."""


import pytest

from conftest import st
from sanity_checks.core import FAIL, PASS, SKIP, WARN

DAILY = "helm/03-rai/semantic-memory/daily"


def _block(i: int) -> str:
    return f"### 10:{i % 60:02d} (session:{i:08x})\n- did a thing\n\n"


def _daily(w, day: str, n_blocks: int, age_h: float = 0):
    w.write(f"{DAILY}/{day}.md", f"# Daily log — {day}\n\n" + "".join(_block(i) for i in range(n_blocks)),
            age_h=age_h)


# LIVE-1..3 ─────────────────────────────────────────────────────────────────────
def test_live_1_ok(w):
    _daily(w, "2026-09-26", 3)
    assert st("LIVE-1").status == PASS


def test_live_1_fault_capture_stopped(w):
    _daily(w, "2026-09-20", 3, age_h=24 * 5)
    assert st("LIVE-1").status == WARN


def test_live_1_fault_format_drift(w):
    w.write(f"{DAILY}/2026-09-26.md", "## 10:00 session abc\n- no longer parseable\n")
    assert st("LIVE-1").status == FAIL


def test_live_1_fault_no_logs(w):
    assert st("LIVE-1").status == WARN


def test_live_2_ok(w):
    _daily(w, "2026-09-26", 3)
    w.chroma({"rai-daily": [{"a": 1}] * 3})
    assert st("LIVE-2").status == PASS


def test_live_2_fault_indexer_never_ran(w):
    _daily(w, "2026-09-26", 25)
    w.chroma({"rai-daily": []})
    assert st("LIVE-2").status == FAIL


def test_live_2_fault_lagging(w):
    _daily(w, "2026-09-26", 60)
    w.chroma({"rai-daily": [{"a": 1}] * 5})
    assert st("LIVE-2").status == WARN


def test_live_2_skips_without_logs(w):
    assert st("LIVE-2").status == SKIP


def test_live_3_ok(w):
    w.write("helm/03-rai/identity/working-memory.md", "x" * 100)
    assert st("LIVE-3").status == PASS


def test_live_3_fault_over_cap(w):
    w.write("helm/03-rai/identity/working-memory.md", "x" * 2600)
    assert st("LIVE-3").status == FAIL


def test_live_3_fault_absent(w):
    assert st("LIVE-3").status == WARN


# EVOLVE-1..5 ───────────────────────────────────────────────────────────────────
CANDS = "helm/03-rai/semantic-memory/learned-candidates.jsonl"


@pytest.fixture
def rp(w, monkeypatch):
    import route_preferences
    monkeypatch.setattr(route_preferences, "CANDIDATES", w.path(CANDS))
    return route_preferences


def _cand(i, status="probation"):
    return {"id": f"c{i}", "key": f"k{i}", "status": status, "text": "prefers x",
            "confidence": "high", "re_confirmations": 1, "first_seen": "2026-01-01"}


def test_evolve_1_ok(w):
    w.jsonl(CANDS, [_cand(1)])
    assert st("EVOLVE-1").status == PASS


def test_evolve_1_fault_corrupt(w):
    w.write(CANDS, '{"ok": 1}\n{broken\n')
    assert st("EVOLVE-1").status == FAIL


def test_evolve_1_fault_empty(w):
    w.write(CANDS, "")
    assert st("EVOLVE-1").status == FAIL


def test_evolve_2_ok(w):
    w.jsonl(CANDS, [_cand(1)], age_h=24)
    assert st("EVOLVE-2").status == PASS


@pytest.mark.parametrize("days,want", [(12, WARN), (25, FAIL)])
def test_evolve_2_fault_stale(w, days, want):
    w.jsonl(CANDS, [_cand(1)], age_h=24 * days)
    assert st("EVOLVE-2").status == want


def test_evolve_3_ok(w):
    assert st("EVOLVE-3").status == PASS


def test_evolve_3_fault_gate_never_promotes(w, monkeypatch):
    import route_preferences
    monkeypatch.setattr(route_preferences, "maybe_promote", lambda c: None)
    assert st("EVOLVE-3").status == FAIL


def test_evolve_4_ok(w, rp):
    w.jsonl(CANDS, [_cand(1, "active")])
    w.write("helm/03-rai/identity/learned.md", "---\n---\n- prefers x\n")
    assert st("EVOLVE-4").status == PASS


def test_evolve_4_fault_render_missing(w, rp):
    w.jsonl(CANDS, [_cand(1, "active")])
    r = st("EVOLVE-4")
    assert r.status == FAIL and "absent" in r.evidence


def test_evolve_4_fault_render_over_cap(w, rp):
    w.jsonl(CANDS, [_cand(1, "active")])
    w.write("helm/03-rai/identity/learned.md", "x" * (rp.IDENTITY_RENDER_CAP + 700))
    assert st("EVOLVE-4").status == FAIL


def test_evolve_5_ok(w):
    w.write("helm/03-rai/semantic-memory/learned.md", "## Counts\n## ACTIVE\n## PROBATION\n")
    assert st("EVOLVE-5").status == PASS


def test_evolve_5_fault_malformed(w):
    w.write("helm/03-rai/semantic-memory/learned.md", "## Counts\n")
    assert st("EVOLVE-5").status == FAIL


# RECALL-1..4 ───────────────────────────────────────────────────────────────────
def _retrieval(monkeypatch, **fns):
    import lib.memory_retrieval as mr
    for name, fn in fns.items():
        monkeypatch.setattr(mr, name, fn)


def test_recall_1_ok(w, monkeypatch):
    _retrieval(monkeypatch, session_start_block=lambda: "## Memory\n- fact")
    assert st("RECALL-1").status == PASS


def test_recall_1_fault_empty(w, monkeypatch):
    _retrieval(monkeypatch, session_start_block=lambda: "")
    assert st("RECALL-1").status == FAIL


def test_recall_1_fault_header_changed(w, monkeypatch):
    _retrieval(monkeypatch, session_start_block=lambda: "## Something\n- fact")
    assert st("RECALL-1").status == WARN


def test_recall_2_ok(w, monkeypatch):
    _retrieval(monkeypatch, query_semantic=lambda q, top_k=8: [{}], query_episodic=lambda q, top_k=5: [])
    assert st("RECALL-2").status == PASS


def test_recall_2_fault_rag_dead(w, monkeypatch):
    _retrieval(monkeypatch, query_semantic=lambda q, top_k=8: [], query_episodic=lambda q, top_k=5: [])
    assert st("RECALL-2").status == FAIL


BLOCK = "helm/03-rai/memory/state/memory-block.md"


def test_recall_3_ok(w):
    w.write(BLOCK, "## Memory\n" + "- fact\n" * 30)
    assert st("RECALL-3").status == PASS


def test_recall_3_fault_stale(w):
    w.write(BLOCK, "## Memory\n" + "- fact\n" * 30, age_h=24 * 8)
    assert st("RECALL-3").status == WARN


def test_recall_3_fault_near_empty(w):
    w.write(BLOCK, "## Memory\n")
    assert st("RECALL-3").status == FAIL


def test_recall_3_fault_missing(w):
    w.chroma({"rai-semantic": [{"a": 1}]})
    assert st("RECALL-3").status == FAIL


def test_recall_4_ok(w, monkeypatch):
    w.chroma({"rai-daily": [{"a": 1}]})
    _retrieval(monkeypatch, query_daily=lambda q, top_k=5: [{}])
    assert st("RECALL-4").status == PASS


def test_recall_4_fault_unqueryable(w, monkeypatch):
    w.chroma({"rai-daily": [{"a": 1}]})
    _retrieval(monkeypatch, query_daily=lambda q, top_k=5: [])
    assert st("RECALL-4").status == FAIL
