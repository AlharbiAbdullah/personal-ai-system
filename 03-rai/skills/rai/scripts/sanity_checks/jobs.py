"""Jobs (producer): every systemd user timer that works for helm fires, exits clean and leaves
its output behind. A disabled timer never fails, it just stops; only its silence shows."""

import time
from datetime import date, timedelta

from . import core
from .core import FAIL, PASS, PRODUCER, WARN, P, check

# unit stem -> (longest normal gap between two runs in hours, the check that asserts it).
# JOB-3 WARNs on any user timer that runs something in helm and is missing here.
JOBS = {
    "rai-maintenance": (6, "PIPE-5"),
    "news-daily": (24, "JOB-1"),
    "news-weekly": (24 * 7, "JOB-1"),
    "news-x-collect": (21, "JOB-1"),          # 21:00 and 00:00: the long gap is 21h
    "paper-portfolio": (24, "JOB-2"),
    "gold-skim": (24 * 31, "JOB-2"),          # monthly, on the 1st
    "obsidian-sync-watch": (1 / 6, "JOB-2"),  # every 10 minutes
    "backup-drive": (24 * 7, "DATA-5"),
}
NEWS_RUNS = "03-rai/skills/news-digest/.runs"          # symlink to ~/.local/state/news-digest/runs
PORTFOLIO_LOG = "02-ana/financial/investment/paper-portfolio/portfolio.log"
OUTPUT_FRESH_H = 30   # a daily job's output: one day plus a run's slack


def timer_health(name: str) -> tuple:
    """(hard, soft) problems for one job. Hard: the timer no longer fires at all. Soft: the last
    run failed (its OnFailure alert already fired) or fired late (the box was off)."""
    try:
        t = core.systemctl_show(f"{name}.timer", "UnitFileState", "ActiveState", "LastTriggerUSec")
        s = core.systemctl_show(f"{name}.service", "Result")
    except Exception as e:
        return [], [f"systemd unreachable from this shell ({str(e)[:50]})"]
    hard, soft = [], []
    if t.get("UnitFileState") != "enabled":
        hard.append(f"{name}.timer {t.get('UnitFileState') or 'not installed'}")
    elif t.get("ActiveState") != "active":
        hard.append(f"{name}.timer {t.get('ActiveState') or 'inactive'}")
    last = core.epoch_of(t.get("LastTriggerUSec", ""))
    gap_h = JOBS[name][0]
    if last is not None and (time.time() - last) / 3600 > gap_h * 2 + 1:
        soft.append(f"{name} last fired {(time.time() - last) / 3600:.0f}h ago")
    if s.get("Result") not in ("success", ""):
        soft.append(f"{name} last run {s.get('Result')}")
    return hard, soft


def _verdict(hard, soft, ok_ev, fix):
    if hard:
        return FAIL, "; ".join(hard + soft), fix
    if soft:
        return WARN, "; ".join(soft), fix
    return PASS, ok_ev, ""


def _iso_label(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _news_outputs() -> tuple:
    """(hard, soft) problems with what the news jobs leave behind."""
    hard, soft = [], []
    daily = sorted((P.HELM / "08-bawaba/daily").glob("????-??-??.md"))
    newest = daily[-1].stem if daily else "none"
    if core._days_old(newest) > 1:  # 03:00 run: before it lands, yesterday's is current
        hard.append(f"newest daily digest {newest}")
    weekly = sorted((P.HELM / "08-bawaba/weekly").glob("????-W??.md"))
    issue = weekly[-1].stem if weekly else "none"
    if issue not in {_iso_label(date.today()), _iso_label(date.today() - timedelta(days=7))}:
        hard.append(f"newest weekly issue {issue}")
    runs = P.HELM / NEWS_RUNS
    dumps = sorted(runs.glob("*/x_foryou.json")) if runs.exists() else []
    if not dumps or core._age_hours(max(dumps, key=lambda p: p.stat().st_mtime)) > OUTPUT_FRESH_H:
        soft.append("no fresh X dump (x_foryou.json)")
    days = sorted(d for d in runs.glob("????-??-??") if d.is_dir()) if runs.exists() else []
    if days and (days[-1] / "x_LOGIN_FAILED.json").exists():
        soft.append(f"X login failed on {days[-1].name}")
    return hard, soft


@check("JOB-1", "Jobs", role=PRODUCER)
def news_jobs():
    """News: the three timers fire clean, a digest exists from today or yesterday, this or last
    ISO week's issue exists, and the X passes keep landing dumps."""
    hard, soft = [], []
    for name in ("news-daily", "news-weekly", "news-x-collect"):
        h, s = timer_health(name)
        hard, soft = hard + h, soft + s
    h, s = _news_outputs()
    return _verdict(hard + h, soft + s, "3 timers clean, digest current, weekly current, X dumps fresh",
                    "Playbook 10 (news-digest-recovery); logs in ~/.local/state/news-digest.")


@check("JOB-2", "Jobs", role=PRODUCER)
def other_jobs():
    """Paper portfolio, gold-skim and the Obsidian Sync watcher fire clean, and the portfolio log
    moves every day."""
    hard, soft = [], []
    for name in ("paper-portfolio", "gold-skim", "obsidian-sync-watch"):
        h, s = timer_health(name)
        hard, soft = hard + h, soft + s
    log = P.HELM / PORTFOLIO_LOG
    if not log.exists() or core._age_hours(log) > OUTPUT_FRESH_H:
        soft.append("portfolio.log not written in 30h")
    return _verdict(hard, soft, "3 timers clean, portfolio log current",
                    "journalctl --user -u <unit> -n 50; each unit's OnFailure alert names it.")


@check("JOB-3", "Jobs", role=PRODUCER)
def job_coverage():
    """Every user timer that runs something in helm is asserted by a check, and every asserted
    job is still installed."""
    units = P.SYSTEMD_USER
    timers = {t.stem for t in units.glob("*.timer")} if units.is_dir() else set()

    def works_for_helm(name):
        svc = units / f"{name}.service"
        return svc.exists() and "helm" in svc.read_text(errors="replace")

    unknown = sorted(n for n in timers if n not in JOBS and works_for_helm(n))
    gone = sorted(n for n in JOBS if n not in timers)
    ev = f"{len(timers)} user timers, {len(JOBS)} asserted"
    if unknown or gone:
        return (WARN, ev + (f", unasserted={unknown}" if unknown else "") + (f", not installed={gone}" if gone else ""),
                "Add the job to JOBS in sanity_checks/jobs.py with an output check, or drop a retired one.")
    return PASS, ev, ""
