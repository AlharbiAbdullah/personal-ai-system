"""Pipeline checks: queue, scripts, coordinator wiring, scanner, distill productivity."""

import uuid

import pytest

from conftest import st
from sanity_checks.core import FAIL, PASS, WARN
from sanity_checks.pipeline import REQUIRED_SCRIPTS

COORD = "helm/03-rai/skills/rai/scheduled/run-maintenance-ubuntu.sh"
WIRED = "sync_claude_sessions.py\nprocess-sessions\ncurate_candidates.py\nsanity.py\n"


def _pending(w, n):
    for i in range(n):
        w.json(f"helm/03-rai/semantic-memory/pending/p{i}.json", {})


# PIPE-1 ────────────────────────────────────────────────────────────────────────
def test_pipe_1_ok(w):
    _pending(w, 3)
    assert st("PIPE-1").status == PASS


def test_pipe_1_fault_backlog(w):
    _pending(w, 12)
    assert st("PIPE-1").status == WARN


def test_pipe_1_fault_not_draining(w):
    _pending(w, 45)
    w.write("helm/13-archive/historical-sessions/session_1.json", "{}", age_h=5)
    assert st("PIPE-1").status == FAIL


def test_pipe_1_ok_mid_drain_is_warn_not_fail(w):
    _pending(w, 45)
    w.write("helm/13-archive/historical-sessions/session_1.json", "{}")
    r = st("PIPE-1")
    assert r.status == WARN and "actively draining" in r.evidence


# PIPE-2 ────────────────────────────────────────────────────────────────────────
def _scripts(w, skip=(), broken=()):
    for n in REQUIRED_SCRIPTS - set(skip):
        w.write(f"helm/03-rai/hooks/scripts/{n}.py", "def f(:\n" if n in broken else "x = 1\n")


def test_pipe_2_ok(w):
    _scripts(w)
    assert st("PIPE-2").status == PASS


def test_pipe_2_fault_required_missing(w):
    _scripts(w, skip=("index_daily",))
    r = st("PIPE-2")
    assert r.status == FAIL and "index_daily:MISSING" in r.evidence


def test_pipe_2_fault_syntax_error(w):
    _scripts(w, broken=("export_index",))
    assert st("PIPE-2").status == FAIL


# PIPE-4 ────────────────────────────────────────────────────────────────────────
def test_pipe_4_ok(w):
    w.write(COORD, WIRED)
    assert st("PIPE-4").status == PASS


def test_pipe_4_fault_step_unwired(w):
    w.write(COORD, WIRED.replace("curate_candidates.py\n", ""))
    r = st("PIPE-4")
    assert r.status == FAIL and "curate_candidates.py" in r.evidence


def test_pipe_4_fault_step_only_in_a_comment(w):
    w.write(COORD, "# 3. process-sessions (claude) drains the queue\n" + WIRED.replace("process-sessions\n", ""))
    assert st("PIPE-4").status == FAIL


def test_pipe_4_fault_script_gone(w):
    assert st("PIPE-4").status == FAIL


# SCAN-1 ────────────────────────────────────────────────────────────────────────
@pytest.fixture
def scanner(w, monkeypatch):
    import sync_claude_sessions as scs
    ledger = w.path("helm/03-rai/semantic-memory/processed-sessions.jsonl")
    projects = w.mkdir(".claude/projects")
    pi = w.mkdir(".pi/agent/rai-transcripts")
    monkeypatch.setattr(scs, "LEDGER", ledger)
    monkeypatch.setattr(scs, "CLAUDE_PROJECTS", projects)
    monkeypatch.setattr(scs, "TRANSCRIPT_ROOTS", (projects, pi))
    monkeypatch.setattr(scs, "SHADOW_ROOT", w.mkdir(".local/share/rai/transcripts"))

    def session(age_h=48, ledgered=True, root=".claude/projects"):
        sid = str(uuid.uuid4())
        w.write(f"{root}/-home-x/{sid}.jsonl", "{}\n", age_h=age_h)
        if ledgered:
            with ledger.open("a") as f:
                f.write(f'{{"session_id": "{sid}"}}\n')
        return sid
    ledger.parent.mkdir(parents=True, exist_ok=True)
    return session


def test_scan_1_ok(w, scanner):
    scanner()
    scanner(age_h=1, ledgered=False)  # still live: not yet quiescent for a day
    assert st("SCAN-1").status == PASS


def test_scan_1_fault_slipped_sessions(w, scanner):
    scanner()
    scanner(ledgered=False)
    r = st("SCAN-1")
    assert r.status == WARN and "unledgered>1d=1" in r.evidence


def test_scan_1_fault_slipped_adapter_shadow(w, scanner):
    scanner()
    scanner(ledgered=False, root=".local/share/rai/transcripts/agy")
    r = st("SCAN-1")
    assert r.status == WARN and "unledgered>1d=1" in r.evidence


def test_scan_1_fault_pi_session_slipped(w, scanner):
    scanner()
    scanner(ledgered=False, root=".pi/agent/rai-transcripts")
    assert st("SCAN-1").status == WARN


def test_scan_1_fault_missing_wholesale(w, scanner):
    scanner()
    for _ in range(26):
        scanner(ledgered=False)
    assert st("SCAN-1").status == FAIL


def test_scan_1_fault_ledger_missing(w, scanner):
    assert st("SCAN-1").status == FAIL


# PIPE-3 ────────────────────────────────────────────────────────────────────────
def test_pipe_3_ok(w):
    w.chroma({"rai-semantic": [{"a": 1}] * 6})
    w.json("helm/03-rai/.sanity-baseline.json", {"rai_semantic_count": 5})
    assert st("PIPE-3").status == PASS


def test_pipe_3_fault_count_dropped(w):
    w.chroma({"rai-semantic": [{"a": 1}] * 4})
    w.json("helm/03-rai/.sanity-baseline.json", {"rai_semantic_count": 5})
    assert st("PIPE-3").status == WARN


def test_pipe_3_fault_no_baseline(w):
    w.chroma({"rai-semantic": [{"a": 1}]})
    assert st("PIPE-3").status == WARN
