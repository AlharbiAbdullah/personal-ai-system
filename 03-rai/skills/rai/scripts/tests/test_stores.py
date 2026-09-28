"""Environment + Stores + Replica checks."""

import sys
from datetime import date, timedelta

import pytest

from conftest import st
from sanity_checks import core
from sanity_checks.core import FAIL, PASS, WARN

FOUR = ("rai-semantic", "rai-episodic", "rai-daily", "rai-preferences")


def _stores(w, semantic_days_old=0, empty=()):
    day = (date.today() - timedelta(days=semantic_days_old)).isoformat()
    rows = {n: ([] if n in empty else [{"source_date": day}] * 3) for n in FOUR}
    w.chroma(rows)


# ENV ───────────────────────────────────────────────────────────────────────────
def test_env_1_ok(w):
    assert st("ENV-1").status == PASS


def test_env_1_fault_chromadb_missing(w, monkeypatch):
    monkeypatch.setitem(sys.modules, "chromadb", None)
    r = st("ENV-1")
    assert r.status == FAIL and "chromadb" in r.evidence


def test_env_2_ok(w):
    w.write("helm/03-rai/semantic-memory/scripts/py-chroma.sh", "#!/bin/sh\n", mode=0o755)
    assert st("ENV-2").status == PASS


def test_env_2_fault_not_executable(w):
    w.write("helm/03-rai/semantic-memory/scripts/py-chroma.sh", "#!/bin/sh\n", mode=0o644)
    assert st("ENV-2").status == FAIL


# STORE-1..2 ──────────────────────────────────────────────────────────────────
def test_store_1_ok(w):
    _stores(w)
    assert st("STORE-1").status == PASS


def test_store_1_fault_collection_missing(w):
    w.chroma({"rai-semantic": [{"a": 1}], "rai-episodic": [{"a": 1}]})
    r = st("STORE-1")
    assert r.status == FAIL and "missing" in r.evidence


def test_store_1_fault_core_empty(w):
    _stores(w, empty=("rai-semantic",))
    r = st("STORE-1")
    assert r.status == FAIL and "EMPTY" in r.evidence


def test_store_2_ok(w):
    _stores(w)
    assert st("STORE-2").status == PASS


@pytest.mark.parametrize("days,want", [(10, WARN), (20, FAIL)])
def test_store_2_fault_stale(w, days, want):
    _stores(w, semantic_days_old=days)
    assert st("STORE-2").status == want


def test_store_2_fault_schema_drift(w):
    w.chroma({"rai-semantic": [{"other": "x"}]})
    assert st("STORE-2").status == FAIL


# STORE-3: the write probe ─────────────────────────────────────────────────────
class _Col:
    def __init__(self, broken_add=False, sticky=False):
        self.rows, self.broken_add, self.sticky = set(), broken_add, sticky

    def add(self, ids, **_):
        if self.broken_add:
            raise RuntimeError("readonly database")
        self.rows |= set(ids)

    def get(self, ids):
        return {"ids": [i for i in ids if i in self.rows]}

    def delete(self, ids):
        if not self.sticky:
            self.rows -= set(ids)


class _Client:
    def __init__(self, col):
        self.col = col

    def get_or_create_collection(self, name):
        return self.col


def test_store_3_ok(w, monkeypatch):
    monkeypatch.setattr(core, "_client", lambda: _Client(_Col()))
    assert st("STORE-3").status == PASS


def test_store_3_fault_write_rejected(w, monkeypatch):
    monkeypatch.setattr(core, "_client", lambda: _Client(_Col(broken_add=True)))
    r = st("STORE-3")
    assert r.status == FAIL and "readonly" in r.evidence


def test_store_3_fault_delete_ignored(w, monkeypatch):
    monkeypatch.setattr(core, "_client", lambda: _Client(_Col(sticky=True)))
    assert st("STORE-3").status == FAIL


# STORE-4: retrieval returns something relevant ────────────────────────────────
def _retrieval(monkeypatch, **fns):
    import lib.memory_retrieval as mr
    for name, fn in fns.items():
        monkeypatch.setattr(mr, name, fn)


def test_store_4_ok(w, monkeypatch):
    _retrieval(monkeypatch, query_semantic=lambda q, top_k=8: [{"score": 0.6}])
    assert st("STORE-4").status == PASS


def test_store_4_fault_empty(w, monkeypatch):
    _retrieval(monkeypatch, query_semantic=lambda q, top_k=8: [])
    assert st("STORE-4").status == FAIL


def test_store_4_fault_low_similarity(w, monkeypatch):
    _retrieval(monkeypatch, query_semantic=lambda q, top_k=8: [{"score": 0.1}])
    assert st("STORE-4").status == WARN


# STORE-5: committed index vs store ────────────────────────────────────────────
def test_store_5_ok(w):
    w.chroma({"rai-semantic": [{"a": 1}] * 3})
    w.write("helm/03-rai/semantic-memory/index/rai-semantic.jsonl", "{}\n" * 3)
    assert st("STORE-5").status == PASS


def test_store_5_fault_index_missing(w):
    w.chroma({"rai-semantic": [{"a": 1}]})
    assert st("STORE-5").status == FAIL


def test_store_5_fault_diverged(w):
    w.chroma({"rai-semantic": [{"a": 1}]})
    w.write("helm/03-rai/semantic-memory/index/rai-semantic.jsonl", "{}\n" * 80)
    assert st("STORE-5").status == WARN


# REPLICA (consumer) ───────────────────────────────────────────────────────────
def _origin_ahead(w, n):
    """Push n commits to origin from a second clone, then fetch, so HEAD lags origin/main."""
    other = w.home / "other"
    w.git("clone", "-q", str(w.home / "origin.git"), str(other), cwd=w.home)
    for i in range(n):
        (other / f"o{i}.txt").write_text(str(i))
        w.git("add", "-A", cwd=other)
        w.git("commit", "-q", "-m", f"o{i}", cwd=other)
    w.git("push", "-q", "origin", "main", cwd=other)
    w.git("fetch", "-q", "origin")


def test_replica_1_ok(w):
    w.git_repo()
    assert st("REPLICA-1", role="consumer").status == PASS


def test_replica_1_ok_ahead_is_normal(w):
    w.git_repo()
    w.commit("local churn")
    assert st("REPLICA-1", role="consumer").status == PASS


def test_replica_1_fault_behind(w):
    w.git_repo()
    _origin_ahead(w, 2)
    r = st("REPLICA-1", role="consumer")
    assert r.status == WARN and "2 commits behind" in r.evidence


def test_replica_1_fault_far_behind(w):
    w.git_repo()
    _origin_ahead(w, 20)
    assert st("REPLICA-1", role="consumer").status == FAIL


def test_replica_1_fault_no_origin_ref(w):
    w.git_repo(origin=False)
    assert st("REPLICA-1", role="consumer").status == WARN


def test_replica_2_ok(w):
    w.write("helm/03-rai/semantic-memory/chromadb/chroma.sqlite3", "x", age_h=24)
    assert st("REPLICA-2", role="consumer").status == PASS


def test_replica_2_fault_stale(w):
    w.write("helm/03-rai/semantic-memory/chromadb/chroma.sqlite3", "x", age_h=24 * 8)
    assert st("REPLICA-2", role="consumer").status == WARN


def test_replica_2_fault_missing(w):
    assert st("REPLICA-2", role="consumer").status == FAIL
