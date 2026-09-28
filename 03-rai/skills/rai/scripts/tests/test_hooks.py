"""Hook checks: registered, present, importable, parseable, firing, error-free, effective."""

from datetime import datetime, timedelta, timezone

import pytest

from conftest import hook_cmd, st
from sanity_checks.core import FAIL, PASS, WARN

HOOKS = ["session-start", "turn-capture", "memory-injection"]
PERF = ".local/state/rai/telemetry/hook-perf.jsonl"


@pytest.fixture
def registry(w):
    w.settings({"SessionStart": [hook_cmd(w, "session-start")],
                "Stop": [hook_cmd(w, "turn-capture")],
                "UserPromptSubmit": [hook_cmd(w, "memory-injection") + " || true"]})
    for h in HOOKS:
        w.write(f"helm/03-rai/hooks/{h}.py", "x = 1\n")


def _perf(w, rows):
    now = datetime.now(timezone.utc)
    w.jsonl(PERF, [{"hook": h, "ts": (now - timedelta(days=d)).isoformat(), "status": s}
                   for h, d, s in rows])


# HOOK-1 ────────────────────────────────────────────────────────────────────────
def test_hook_1_ok(w, registry):
    r = st("HOOK-1")
    assert r.status == PASS and "3 registered" in r.evidence


def test_hook_1_fault_script_missing(w, registry):
    w.path("helm/03-rai/hooks/turn-capture.py").unlink()
    r = st("HOOK-1")
    assert r.status == FAIL and "turn-capture" in r.evidence


# HOOK-2 ────────────────────────────────────────────────────────────────────────
def test_hook_2_ok(w):
    w.write("helm/03-rai/hooks/lib/__init__.py", "")
    w.write("helm/03-rai/hooks/lib/paths.py", "X = 1\n")
    w.write("helm/03-rai/hooks/lib/uses.py", "from .paths import X\n")
    assert st("HOOK-2").status == PASS


def test_hook_2_fault_import_error(w):
    w.write("helm/03-rai/hooks/lib/__init__.py", "")
    w.write("helm/03-rai/hooks/lib/paths.py", "X = 1\n")
    w.write("helm/03-rai/hooks/lib/uses.py", "from .paths import GONE\n")
    r = st("HOOK-2")
    assert r.status == FAIL and "uses:ImportError" in r.evidence


# HOOK-3 ────────────────────────────────────────────────────────────────────────
def test_hook_3_ok(w, registry):
    assert st("HOOK-3").status == PASS


def test_hook_3_fault_syntax_error(w, registry):
    w.write("helm/03-rai/hooks/turn-capture.py", "def f(:\n")
    r = st("HOOK-3")
    assert r.status == FAIL and "turn-capture" in r.evidence


# HOOK-4 ────────────────────────────────────────────────────────────────────────
def test_hook_4_ok(w, registry):
    _perf(w, [(h, 1, "ok") for h in HOOKS])
    assert st("HOOK-4").status == PASS


def test_hook_4_fault_one_silent(w, registry):
    _perf(w, [("session-start", 1, "ok"), ("turn-capture", 1, "ok"), ("memory-injection", 9, "ok")])
    r = st("HOOK-4")
    assert r.status == WARN and "memory-injection" in r.evidence


def test_hook_4_fault_many_silent(w, registry):
    w.settings({"Stop": [hook_cmd(w, n) for n in ("a", "b", "c", "d")]})
    _perf(w, [("a", 1, "ok")])
    assert st("HOOK-4").status == FAIL


def test_hook_4_fault_no_log(w, registry):
    assert st("HOOK-4").status == WARN


# HOOK-5 ────────────────────────────────────────────────────────────────────────
def test_hook_5_ok(w):
    _perf(w, [("session-start", 0, "ok")] * 10)
    assert st("HOOK-5").status == PASS


def test_hook_5_fault_occasional(w):
    _perf(w, [("session-start", 0, "ok")] * 10 + [("turn-capture", 0, "error")] * 2)
    assert st("HOOK-5").status == WARN


def test_hook_5_fault_repeated(w):
    _perf(w, [("turn-capture", 0, "error")] * 6)
    assert st("HOOK-5").status == FAIL


# HOOK-6 ────────────────────────────────────────────────────────────────────────
def _effects(w, age_h=1):
    w.json(".local/state/rai/runtime/tab-titles/a.json", {}, age_h=age_h)
    w.json(".local/state/rai/runtime/session-names.json", {}, age_h=age_h)
    w.json(".local/state/rai/runtime/identity-cache.json", {}, age_h=age_h)
    w.write("helm/03-rai/semantic-memory/daily/2026-09-26.md", "x", age_h=age_h)
    w.json("helm/13-archive/historical-sessions/session_1.json", {}, age_h=age_h)


def test_hook_6_ok(w):
    _effects(w)
    assert st("HOOK-6").status == PASS


def test_hook_6_fault_effect_stale(w):
    _effects(w)
    w.age(".local/state/rai/runtime/session-names.json", 24 * 20)
    r = st("HOOK-6")
    assert r.status == WARN and "auto-name->session-names" in r.fix


def test_hook_6_fault_effect_absent(w):
    _effects(w)
    w.path(".local/state/rai/runtime/identity-cache.json").unlink()
    assert st("HOOK-6").status == WARN
