"""Scheduled jobs: PIPE-5/6 (the coordinator), JOB-1..3, DATA-5 (the offsite backup).
systemd is faked; the coordinator logs, digests and status files are real fixture files."""

import time
from datetime import date, timedelta

import pytest

from conftest import st
from sanity_checks import core
from sanity_checks.core import FAIL, PASS, SKIP, WARN
from sanity_checks.jobs import JOBS

LOGS = ".local/state/rai-maintenance/logs"


@pytest.fixture
def systemd(monkeypatch):
    """A fake `systemctl --user show`: every job starts healthy; tests break one."""
    units = {}

    def show(unit, *props):
        if units.get("_down"):
            raise RuntimeError("Failed to connect to bus")
        return {p: units.get(unit, {}).get(p, "") for p in props}

    def job(name, state="enabled", active="active", last_h=1.0, result="success"):
        units[f"{name}.timer"] = {"UnitFileState": state, "ActiveState": active,
                                  "LastTriggerUSec": f"@{int(time.time() - last_h * 3600)}" if last_h is not None else ""}
        units[f"{name}.service"] = {"Result": result}

    for name in JOBS:
        job(name)
    job.units = units
    monkeypatch.setattr(core, "systemctl_show", show)
    return job


# PIPE-5: the coordinator's timer ───────────────────────────────────────────────
def test_pipe_5_ok(w, systemd):
    assert st("PIPE-5").status == PASS


def test_pipe_5_fault_timer_disabled(w, systemd):
    systemd("rai-maintenance", state="disabled")
    r = st("PIPE-5")
    assert r.status == FAIL and "disabled" in r.evidence


def test_pipe_5_fault_timer_stopped(w, systemd):
    systemd("rai-maintenance", active="inactive")
    assert st("PIPE-5").status == FAIL


def test_pipe_5_fault_last_run_failed(w, systemd):
    systemd("rai-maintenance", result="exit-code")
    r = st("PIPE-5")
    assert r.status == WARN and "exit-code" in r.evidence


def test_pipe_5_fault_not_firing(w, systemd):
    systemd("rai-maintenance", last_h=20)
    assert st("PIPE-5").status == WARN


def test_pipe_5_fault_no_bus_is_warn_not_broken(w, systemd):
    systemd.units["_down"] = True
    r = st("PIPE-5")
    assert r.status == WARN and "unreachable" in r.evidence


# PIPE-6: the coordinator's own step results ────────────────────────────────────
def _run(w, stamp, steps=None, end="rc0=0 rc1=0 rc2=0 rc5=0", age_h=3.0, extra=""):
    steps = steps or {"sync-claude-sessions": 0, "process-sessions": 0, "git-commit": 0}
    body = f"════════ 2026-09-26 10:00:00 START maintenance (ubuntu coordinator) ════════\n{extra}"
    for name, rc in steps.items():
        body += f"──── STEP {name} start 10:00:01 ────\n──── STEP {name} end 10:01:02 rc={rc} ────\n"
    body += "──── STEP sanity end 10:01:47 verdict-rc=1 (0=HEALTHY 1=DEGRADED) ────\n"
    if end is not None:
        body += f"════════ 2026-09-26 10:03:09 END {end} ════════\n"
    w.write(f"{LOGS}/{stamp}-maintenance.log", body, age_h=age_h)


def test_pipe_6_ok(w):
    for s in ("2026-09-26-0400", "2026-09-26-1000", "2026-09-26-1600"):
        _run(w, s)
    r = st("PIPE-6")
    assert r.status == PASS and "newest 2026-09-26-1600 complete" in r.evidence


def test_pipe_6_ok_sanity_verdict_is_not_a_step_failure(w):
    _run(w, "2026-09-26-1600")
    assert st("PIPE-6").status == PASS


def test_pipe_6_fault_one_bad_run(w):
    _run(w, "2026-09-26-1000")
    _run(w, "2026-09-26-1600", steps={"sync-claude-sessions": 0, "process-sessions": 124, "git-commit": 0})
    r = st("PIPE-6")
    assert r.status == WARN and "process-sessions" in r.evidence


def test_pipe_6_fault_dead_step(w):
    for s in ("2026-09-26-0400", "2026-09-26-1000", "2026-09-26-1600"):
        _run(w, s, steps={"sync-claude-sessions": 1, "process-sessions": 0, "git-commit": 0})
    r = st("PIPE-6")
    assert r.status == FAIL and "sync-claude-sessions" in r.evidence


def test_pipe_6_fault_aborted_runs(w):
    for s in ("2026-09-26-0400", "2026-09-26-1000", "2026-09-26-1600"):
        w.write(f"{LOGS}/{s}-maintenance.log", "START\nERROR: pull failed twice. Aborting run.\n", age_h=3)
    r = st("PIPE-6")
    assert r.status == FAIL and "pull" in r.evidence


def test_pipe_6_fault_crashed_run(w):
    _run(w, "2026-09-26-1000")
    _run(w, "2026-09-26-1600", end=None, age_h=5)
    r = st("PIPE-6")
    assert r.status == WARN and "unfinished" in r.evidence


def test_pipe_6_ok_running_and_skipped_runs(w):
    _run(w, "2026-09-26-1000")
    w.write(f"{LOGS}/2026-09-26-1605-maintenance.log", "START\nAnother run holds the lock (60s old) — skipping.\n")
    _run(w, "2026-09-26-2200", end=None, age_h=0.1)  # in progress: sanity is its step 3.5
    r = st("PIPE-6")
    assert r.status == PASS and "running" in r.evidence


def test_pipe_6_fault_mac_refresh_keeps_failing(w):
    for s in ("2026-09-26-0400", "2026-09-26-1000", "2026-09-26-1600"):
        _run(w, s, end="rc0=0 rc1=0 rc2=0 rc5=1")
    r = st("PIPE-6")
    assert r.status == WARN and "refresh_mac" in r.evidence


def test_pipe_6_fault_core_step_never_ran(w):
    """A step deleted from the coordinator never fails: it just stops appearing in the log."""
    _run(w, "2026-09-26-1600", steps={"sync-claude-sessions": 0, "git-commit": 0})
    r = st("PIPE-6")
    assert r.status == WARN and "process-sessions:never ran" in r.evidence


def test_pipe_6_ok_sync_only_run(w):
    _run(w, "2026-09-26-1705", steps={}, end="(SYNC_ONLY) rc5=0")
    assert st("PIPE-6").status == PASS


def test_pipe_6_fault_no_runs(w):
    assert st("PIPE-6").status == WARN


# JOB-1: news ───────────────────────────────────────────────────────────────────
def _iso(d):
    y, wk, _ = d.isocalendar()
    return f"{y}-W{wk:02d}"


def _news(w, daily_days_old=0, weekly_weeks_old=0, x_age_h=3.0, login_failed=False,
          digest=True, daily_age_h=None):
    today = date.today()
    day = today - timedelta(days=daily_days_old)
    w.write(f"helm/08-bawaba/daily/{day}.md", "# daily", age_h=daily_age_h)
    if digest:
        w.write(f"helm/08-bawaba/digest/{day}.md", "> [!abstract] Bottom line")
    w.write(f"helm/08-bawaba/weekly/{_iso(today - timedelta(weeks=weekly_weeks_old))}.md", "# issue")
    run = f"helm/03-rai/skills/news-digest/.runs/{today}"
    w.write(f"{run}/x_foryou.json", "[]", age_h=x_age_h)
    if login_failed:
        w.write(f"{run}/x_LOGIN_FAILED.json", "{}")


def test_job_1_ok(w, systemd):
    _news(w)
    assert st("JOB-1").status == PASS


def test_job_1_ok_yesterdays_digest_before_the_run(w, systemd):
    _news(w, daily_days_old=1)
    assert st("JOB-1").status == PASS


def test_job_1_fault_digest_stale(w, systemd):
    _news(w, daily_days_old=3)
    r = st("JOB-1")
    assert r.status == FAIL and "daily digest" in r.evidence


def test_job_1_fault_weekly_missing(w, systemd):
    _news(w, weekly_weeks_old=3)
    assert st("JOB-1").status == FAIL


def test_job_1_fault_timer_disabled(w, systemd):
    _news(w)
    systemd("news-daily", state="disabled")
    assert st("JOB-1").status == FAIL


def test_job_1_fault_x_login_dead(w, systemd):
    _news(w, login_failed=True)
    r = st("JOB-1")
    assert r.status == WARN and "X login failed" in r.evidence


def test_job_1_fault_x_dumps_stale(w, systemd):
    _news(w, x_age_h=50)
    assert st("JOB-1").status == WARN


def test_job_1_ok_digest_still_being_written(w, systemd):
    _news(w, digest=False, daily_age_h=0.5)
    assert st("JOB-1").status == PASS


def test_job_1_fault_digest_missing(w, systemd):
    _news(w, digest=False, daily_age_h=3)
    r = st("JOB-1")
    assert r.status == WARN and "no digest for daily" in r.evidence


# JOB-2: portfolio, gold-skim, Obsidian Sync watcher ─────────────────────────────
PLOG = "helm/02-ana/financial/investment/paper-portfolio/portfolio.log"


def test_job_2_ok(w, systemd):
    w.write(PLOG, "run", age_h=5)
    assert st("JOB-2").status == PASS


def test_job_2_ok_gold_skim_not_run_yet(w, systemd):
    systemd("gold-skim", last_h=None)
    w.write(PLOG, "run")
    assert st("JOB-2").status == PASS


def test_job_2_fault_portfolio_log_stale(w, systemd):
    w.write(PLOG, "run", age_h=50)
    assert st("JOB-2").status == WARN


def test_job_2_fault_watcher_disabled(w, systemd):
    w.write(PLOG, "run")
    systemd("obsidian-sync-watch", state="disabled")
    assert st("JOB-2").status == FAIL


def test_job_2_fault_watcher_failing(w, systemd):
    w.write(PLOG, "run")
    systemd("obsidian-sync-watch", result="exit-code")
    assert st("JOB-2").status == WARN


# JOB-3: coverage gate over the user timers ─────────────────────────────────────
def _units(w, names, extra=None):
    for n in names:
        w.write(f".config/systemd/user/{n}.timer", "[Timer]\nOnCalendar=daily\n")
        w.write(f".config/systemd/user/{n}.service", "[Service]\nExecStart=%h/.local/bin/x\n")
    for n, exec_line in (extra or {}).items():
        w.write(f".config/systemd/user/{n}.timer", "[Timer]\nOnCalendar=daily\n")
        w.write(f".config/systemd/user/{n}.service", f"[Service]\nExecStart={exec_line}\n")


def test_job_3_ok(w):
    _units(w, JOBS, extra={"xremap-restart": "/usr/bin/xremap"})
    assert st("JOB-3").status == PASS


def test_job_3_fault_unasserted_helm_job(w):
    _units(w, JOBS, extra={"ideas-digest": "%h/helm/03-rai/skills/ideas/scheduled/run.sh"})
    r = st("JOB-3")
    assert r.status == WARN and "ideas-digest" in r.evidence


def test_job_3_fault_asserted_job_gone(w):
    _units(w, [n for n in JOBS if n != "gold-skim"])
    r = st("JOB-3")
    assert r.status == WARN and "gold-skim" in r.evidence


# DATA-5: the offsite backup ────────────────────────────────────────────────────
STATUS = ".local/state/backup-drive/status"


def _backup(w, days_old=1, outcome="OK"):
    w.write(STATUS, f"{date.today() - timedelta(days=days_old)} {outcome}\n")


def test_data_5_ok(w, systemd):
    _backup(w)
    assert st("DATA-5").status == PASS


def test_data_5_fault_missed_run(w, systemd):
    _backup(w, days_old=10)
    assert st("DATA-5").status == WARN


def test_data_5_fault_two_missed_runs(w, systemd):
    _backup(w, days_old=16)
    assert st("DATA-5").status == FAIL


def test_data_5_fault_last_run_failed(w, systemd):
    _backup(w, outcome="FAIL backup check reported errors")
    r = st("DATA-5")
    assert r.status == FAIL and "backup check" in r.evidence


def test_data_5_fault_no_status(w, systemd):
    assert st("DATA-5").status == FAIL


def test_data_5_skip_never_set_up(w, systemd):
    systemd("backup-drive", state="")
    assert st("DATA-5").status == SKIP


def test_data_5_fault_timer_disabled(w, systemd):
    _backup(w)
    systemd("backup-drive", state="disabled")
    assert st("DATA-5").status == WARN
