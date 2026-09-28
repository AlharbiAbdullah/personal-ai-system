"""Data safety checks, each proven against the fault it exists for."""

import json
import time

import pytest

from conftest import st
from sanity_checks.core import FAIL, PASS, WARN

UNION = ("03-rai/memory/**/*.jsonl merge=union\n03-rai/semantic-memory/daily/*.md merge=union\n"
         "03-rai/semantic-memory/processed-sessions.jsonl merge=union\n")


# DATA-1: the git backup target ────────────────────────────────────────────────
def test_data_1_ok(w):
    w.git_repo()
    r = st("DATA-1")
    assert r.status == PASS and "remote=yes" in r.evidence


def test_data_1_ok_mid_cycle_unpushed(w):
    w.git_repo()
    w.commit("fresh", age_h=1)
    assert st("DATA-1").status == PASS


def test_data_1_fault_no_remote(w):
    w.git_repo(origin=False)
    r = st("DATA-1")
    assert r.status == FAIL and "remote=NO" in r.evidence


def _origin_idle(w, hours):
    """Re-date the tracking ref's reflog: origin last moved `hours` ago."""
    sha = w.git("rev-parse", "refs/remotes/origin/main")
    w.git("update-ref", "-d", "refs/remotes/origin/main")  # recreated below with a dated reflog entry
    when = f"@{int(time.time() - hours * 3600)} +0000"
    w.git("update-ref", "-m", "update by push", "refs/remotes/origin/main", sha, env={"GIT_COMMITTER_DATE": when})


def test_data_1_fault_push_stuck(w):
    w.git_repo()
    w.commit("stuck")
    _origin_idle(w, 10)
    r = st("DATA-1")
    assert r.status == WARN and "unpushed=1 (origin idle 10.0h)" in r.evidence


def test_data_1_ok_merged_old_commits(w):
    """A merged branch brings commits dated days ago; origin moved minutes ago, so no stuck push."""
    w.git_repo()
    w.commit("feature work from two days ago", age_h=48)
    assert st("DATA-1").status == PASS


def test_data_1_fault_no_upstream(w):
    """Without an upstream, `@{u}..HEAD` errors to an empty list: unpushed work looked like none."""
    w.git_repo()
    w.git("branch", "--unset-upstream")
    w.commit("never pushed", age_h=10)
    r = st("DATA-1")
    assert r.status == WARN and "no upstream" in r.evidence


def test_data_1_ok_consumer_ignores_unpushed(w, monkeypatch):
    monkeypatch.setenv("RAI_ROLE", "consumer")
    w.git_repo()
    w.commit("mac churn", age_h=10)
    assert st("DATA-1", role="consumer").status == PASS


# DATA-2: the coordinator heartbeat ────────────────────────────────────────────
def test_data_2_ok(w):
    w.git_repo(age_h=1)
    assert st("DATA-2").status == PASS


def test_data_2_fault_missed_cycles(w):
    w.git_repo(age_h=40)
    assert st("DATA-2").status == WARN


def test_data_2_fault_coordinator_down(w):
    w.git_repo(age_h=80)
    assert st("DATA-2").status == FAIL


def test_data_2_fault_no_history(w):
    w.git("init", "-q")
    assert st("DATA-2").status == FAIL


# DATA-3: the loss tripwire ───────────────────────────────────────────────────
def _notes(w, n):
    for i in range(n):
        w.write(f"helm/notes/n{i}.md", "x")


def test_data_3_ok(w):
    _notes(w, 20)
    w.json("helm/03-rai/.sanity-baseline.json", {"md_count": 20})
    assert st("DATA-3").status == PASS


def test_data_3_fault_notable_drop(w):
    _notes(w, 17)
    w.json("helm/03-rai/.sanity-baseline.json", {"md_count": 20})
    assert st("DATA-3").status == WARN


def test_data_3_fault_catastrophic_drop(w):
    _notes(w, 10)
    w.json("helm/03-rai/.sanity-baseline.json", {"md_count": 20})
    assert st("DATA-3").status == FAIL


def test_data_3_fault_no_baseline(w):
    _notes(w, 3)
    assert st("DATA-3").status == WARN


# DATA-4: union merge rules for the append-only logs ──────────────────────────
def test_data_4_ok(w):
    w.write("helm/.gitattributes", UNION)
    assert st("DATA-4").status == PASS


def test_data_4_fault_rule_missing(w):
    w.write("helm/.gitattributes", UNION.splitlines()[0] + "\n")
    r = st("DATA-4")
    assert r.status == WARN and "1/3" in r.evidence


def test_data_4_fault_file_missing(w):
    assert st("DATA-4").status == WARN


def test_baseline_counts_match_the_tripwire(w):
    """write_baseline and DATA-3 must count .md files the same way, or a fresh baseline reads
    as drift on the very next run."""
    import sanity
    from sanity_checks import core
    _notes(w, 5)
    w.write("helm/proj/node_modules/pkg/README.md", "x")
    w.chroma({"rai-semantic": [{"k": "v"}]})
    sanity.write_baseline()
    assert json.loads(core.P.BASELINE.read_text())["md_count"] == 5
    assert st("DATA-3").status == PASS


# DATA-6: tracked file sizes ──────────────────────────────────────────────────
def _sized(w, rel, mb):
    p = w.helm / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as f:
        f.truncate(int(mb * 1024 * 1024))  # sparse: no real disk use


def test_data_6_ok(w):
    w.git_repo()
    _sized(w, "13-archive/historical-sessions/session_1.json", 30)
    w.git("add", "-A")
    assert st("DATA-6").status == PASS


def test_data_6_fault_near_limit(w):
    w.git_repo()
    _sized(w, "04-work/render-v6.mp4", 60)
    w.git("add", "-A")
    r = st("DATA-6")
    assert r.status == WARN and "render-v6.mp4" in r.evidence


def test_data_6_fault_push_blocker(w):
    w.git_repo()
    _sized(w, "04-work/render-v7.mp4", 120)
    w.git("add", "-A")
    assert st("DATA-6").status == FAIL


def test_data_6_ok_untracked_big_file(w):
    w.git_repo()
    _sized(w, "scratch/big.bin", 120)
    assert st("DATA-6").status == PASS


# DATA-7: no unattended pull --rebase ───────────────────────────────────────────
RUNNER = "helm/03-rai/skills/news-digest/scheduled/run-news-ubuntu.sh"


def test_data_7_ok(w):
    w.write(RUNNER, '#!/bin/bash\n# never git pull --rebase here\ngit -C "$HELM" fetch origin main\n'
                    'git -C "$HELM" merge --ff-only FETCH_HEAD\ngit pull --ff-only --autostash linux main\n'
                    'P="if behind, never pull --rebase at behind=0"\n')
    assert st("DATA-7").status == PASS


@pytest.mark.parametrize("line", [
    'git pull --rebase --autostash origin main',
    'git -C "$HELM" pull --rebase origin main',
    'git -C "$HELM" pull -r',
    '{ git fetch && git pull --rebase; } || true',
])
def test_data_7_fault_rebase_pull(w, line):
    w.write(RUNNER, f"#!/bin/bash\n{line}\n")
    r = st("DATA-7")
    assert r.status == FAIL and "run-news-ubuntu.sh:2" in r.evidence
