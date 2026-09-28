"""Self-test: the coverage gates."""

from conftest import hook_cmd, st
from sanity_checks.core import FAIL, PASS, WARN

LIVE = {"rai-semantic": [{"a": 1}], "rai-episodic": [{"a": 1}], "rai-daily": [], "rai-preferences": []}


# META-1 ────────────────────────────────────────────────────────────────────────
def test_meta_1_ok(w):
    w.chroma({**LIVE, "sanity-probe": []})
    assert st("META-1").status == PASS


def test_meta_1_fault_unknown_store(w):
    w.chroma({**LIVE, "rai-shadow": [{"a": 1}]})
    r = st("META-1")
    assert r.status == FAIL and "rai-shadow" in r.evidence


def test_meta_1_fault_empty_husk(w):
    w.chroma({**LIVE, "memories": []})
    assert st("META-1").status == WARN


def test_meta_1_ok_nonempty_tombstone(w):
    w.chroma({**LIVE, "memories": [{"a": 1}]})
    assert st("META-1").status == PASS


# META-2 ────────────────────────────────────────────────────────────────────────
def test_meta_2_ok(w):
    w.settings({"Stop": [hook_cmd(w, "turn-capture")]})
    assert st("META-2").status == PASS


def test_meta_2_fault_registry_empty(w):
    w.settings({})
    assert st("META-2").status == FAIL


def test_meta_2_fault_registry_unreadable(w):
    w.write(".claude/settings.json", "{broken")
    assert st("META-2").status == FAIL


# META-3 ────────────────────────────────────────────────────────────────────────
def test_meta_3_ok():
    r = st("META-3")
    assert r.status == PASS, r.evidence


def test_meta_3_fault_check_without_fault_test(w, monkeypatch):
    from sanity_checks import core
    tests = w.mkdir("tests")
    (tests / "test_x.py").write_text("def test_data_1_fault_x():\n    pass\n")
    monkeypatch.setattr(core.P, "TESTS", tests)
    r = st("META-3")
    assert r.status == WARN and r.evidence.startswith("1/") and "missing" in r.evidence


def test_meta_3_fault_tests_missing(w, monkeypatch):
    from sanity_checks import core
    monkeypatch.setattr(core.P, "TESTS", w.path("gone"))
    assert st("META-3").status == WARN
