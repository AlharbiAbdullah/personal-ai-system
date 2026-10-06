"""Pipeline (producer): the queue drains, the scripts parse, the coordinator is wired, the
scanner captures every session, and distill keeps adding memory."""

import json
import re
import time

from . import core
from .core import FAIL, PASS, PRODUCER, WARN, P, check

PENDING_WARN = 10
PENDING_FAIL = 40

# Scripts the v3 pipeline cannot run without. PIPE-2 parse-checks EVERY *.py in
# hooks/scripts/ dynamically (so a new script is auto-covered) and additionally
# FAILs if any of these required ones is absent.
REQUIRED_SCRIPTS = {
    "distill_session", "store_episodic", "store_semantic", "route_preferences",
    "process_pending", "export_index", "rebuild_chromadb",
    "sync_claude_sessions", "index_daily", "render_memory_block", "curate_candidates",
}


@check("PIPE-1", "Pipeline", role=PRODUCER)
def pending_depth():
    """The pending queue stays short, or is visibly draining."""
    pend = list((P.SM / "pending").glob("*.json")) if (P.SM / "pending").exists() else []
    n = len(pend)
    ev = f"pending={n}"
    if n >= PENDING_FAIL:
        # A big queue that is ACTIVELY draining (fresh archive arrivals) is work in
        # progress, not a dead pipeline — don't flip the brain to BROKEN over it.
        arch = P.HELM / "13-archive" / "historical-sessions"
        newest = max((f.stat().st_mtime for f in arch.glob("session_*.json")), default=0)
        if time.time() - newest < 1800:
            return WARN, ev + " (actively draining)", "Large backlog mid-drain — re-check after it finishes."
        return FAIL, ev, "Queue piling and NOT draining — process_pending.py / distill is failing. Check distill_session stderr."
    if n >= PENDING_WARN:
        return WARN, ev, "Backlog building — run /process-sessions."
    return PASS, ev, ""


@check("PIPE-2", "Pipeline")
def pipeline_scripts_parse():
    """Every pipeline script is present and parses under both interpreters the pipeline spans."""
    from .hooks import parse_both
    present = {p.stem: p for p in (P.HOOKS / "scripts").glob("*.py")}
    bad = [f"{n}:MISSING" for n in sorted(REQUIRED_SCRIPTS - present.keys())]
    bad += [f"{n}:syntax" for n in parse_both([present[k] for k in sorted(present)])]
    ev = f"{len(present)} scripts, {len(REQUIRED_SCRIPTS)} required" + (f" — {bad}" if bad else ", all parse")
    return (FAIL, ev, "A pipeline script is missing or broken — the producer cannot run.") if bad else (PASS, ev, "")


@check("PIPE-4", "Pipeline", role=PRODUCER)
def coordinator_wiring():
    """The maintenance coordinator must still invoke every v3 step — an accidentally
    deleted line would silently drop a whole subsystem (scanner, curation, drain, sanity)."""
    script = P.RAI / "skills/rai/scheduled/run-maintenance-ubuntu.sh"
    if not script.exists():
        return FAIL, "run-maintenance-ubuntu.sh missing", "The coordinator script is gone — restore from git."
    txt = "\n".join(l for l in script.read_text().splitlines() if not l.lstrip().startswith("#"))
    required = ["sync_claude_sessions.py", "process-sessions", "curate_candidates.py", "sanity.py"]
    missing = [s for s in required if s not in txt]
    ev = f"{len(required)-len(missing)}/{len(required)} steps wired" + (f" — missing {missing}" if missing else "")
    return (FAIL, ev, "A coordinator step is unwired — re-add it to run-maintenance-ubuntu.sh.") if missing else (PASS, ev, "")


@check("SCAN-1", "Pipeline", role=PRODUCER)
def scanner_capture():
    """The batch scanner is the capture path — assert its ledger is live AND that no
    quiescent native session is slipping past it (the affirmative 'it captures' assertion)."""
    import sync_claude_sessions as scs
    if not scs.LEDGER.exists():
        return FAIL, "processed-sessions.jsonl missing", "Scanner never ran — run sync_claude_sessions.py."
    seen = scs.ledger_sids()
    if not seen:
        return FAIL, "ledger empty", "Scanner ledger holds nothing — seeding failed?"
    cut = time.time() - 86400  # anything quiescent >1 day should long be ledgered (scanner runs 4x/day)
    missed = 0
    # the scanner's own root list: Claude Code, pi's shadows, and each harness adapter's shadows
    for root in scs.transcript_roots():
        for f in root.glob("*/*.jsonl"):
            if not scs.UUID_RE.match(f.stem) or f.stem in seen:
                continue
            try:
                if f.stat().st_mtime < cut:
                    missed += 1
            except OSError:
                continue
    ev = f"ledger={len(seen)}, unledgered>1d={missed}"
    if missed > 25:
        return FAIL, ev, "Scanner is missing sessions wholesale — check coordinator step 2.7 / its stderr."
    if missed > 0:
        return WARN, ev, "A few sessions slipped the scanner — confirm the coordinator ran since they ended."
    return PASS, ev, ""


@check("PIPE-3", "Pipeline", role=PRODUCER)
def distill_productivity():
    """Did the producer actually ADD distilled memory since the last baseline? This is the
    affirmative 'it is producing' assertion the old check never made."""
    count = core._collections().get("rai-semantic", 0)
    if not P.BASELINE.exists():
        return WARN, f"rai-semantic={count} (no baseline)", "Run `/sanity --baseline` after a known-good cycle."
    base = json.loads(P.BASELINE.read_text()).get("rai_semantic_count", 0)
    ev = f"rai-semantic {base} -> {count} ({count - base:+d} since baseline)"
    if count < base:
        return WARN, ev, "Count dropped — supersede/archive churn, or a rebuild from a smaller index."
    return PASS, ev, ""


@check("PIPE-5", "Pipeline", role=PRODUCER)
def coordinator_timer():
    """rai-maintenance.timer is enabled and armed, fired within two cycles, and its last run
    exited clean."""
    from .jobs import _verdict, timer_health
    hard, soft = timer_health("rai-maintenance")
    return _verdict(hard, soft, "rai-maintenance.timer enabled, armed, last run clean",
                    "systemctl --user enable --now rai-maintenance.timer; journalctl --user -u rai-maintenance -n 50")


# ── the coordinator's own log: which steps failed, run by run ──────────────────
STEP_END = re.compile(r"──── STEP (\S+) end \S+ (?:verdict-)?rc=(\d+)")
# every full run executes these (merge-collisions and curate-candidates are conditional)
CORE_STEPS = ("sync-claude-sessions", "process-sessions", "sanity", "git-commit")
RUN_END = re.compile(r"════════ .* END (.*?) ═+")
RUNNING_H = 2        # a log without its END line younger than this is a run in progress
PERSISTENT_RUNS = 3  # the same step failing this many runs in a row is a dead step


def parse_run(path) -> dict:
    """One coordinator log -> {"state", "failed": [step, ...], "mac": bool (refresh_mac failed)}.
    States: complete, aborted (step 0/1 gave up), skipped (lock held, news running), running,
    crashed (no END line and too old to be running)."""
    txt = path.read_text(errors="replace")
    steps = STEP_END.findall(txt)
    # sanity's own rc is its verdict, already reported by sanity itself
    failed = [name for name, rc in steps if rc != "0" and name != "sanity"]
    end = RUN_END.search(txt)
    if end:
        rc5 = re.search(r"rc5=(\d+)", end.group(1))
        ran = {name for name, _ in steps}
        # a step deleted from the script never fails; it just stops appearing
        skipped = [] if "SYNC_ONLY" in end.group(1) else [f"{s}:never ran" for s in CORE_STEPS if s not in ran]
        return {"state": "complete", "failed": failed + skipped, "mac": bool(rc5 and rc5.group(1) != "0")}
    if "Aborting run" in txt:
        return {"state": "aborted", "failed": failed + ["pull"], "mac": False}
    if "──── STEP" not in txt and "skipping." in txt:
        return {"state": "skipped", "failed": [], "mac": False}
    if core._age_hours(path) < RUNNING_H:
        return {"state": "running", "failed": failed, "mac": False}
    return {"state": "crashed", "failed": failed + ["unfinished"], "mac": False}


@check("PIPE-6", "Pipeline", role=PRODUCER)
def coordinator_runs():
    """The coordinator's own step results. One bad run WARNs (a drain timeout heals itself);
    the same step failing three runs in a row FAILs (that step is dead)."""
    logs = sorted(P.COORD_LOGS.glob("*-maintenance.log"))[-12:]  # names sort by start time
    runs = [(p.name[:15], parse_run(p)) for p in logs]
    runs = [(n, r) for n, r in runs if r["state"] != "skipped"]
    if not runs:
        return WARN, "no coordinator run on record", "Has rai-maintenance.timer ever fired? See PIPE-5."
    name, newest = runs[-1]
    last = [r for _, r in runs[-PERSISTENT_RUNS:]]
    dead = set(newest["failed"]).intersection(*(r["failed"] for r in last)) if len(last) == PERSISTENT_RUNS else set()
    ev = f"{len(runs)} runs read, newest {name} {newest['state']}"
    if newest["failed"]:
        ev += f", failed: {newest['failed']}"
    if dead:
        return FAIL, ev + f", failing {PERSISTENT_RUNS} runs in a row: {sorted(dead)}", \
            f"Read the step's lines in {P.COORD_LOGS}/<run>-maintenance.log; it has stopped working."
    if newest["failed"]:
        return WARN, ev, f"One run failed a step; it FAILs if the next {PERSISTENT_RUNS - 1} runs fail it too."
    if len(last) == PERSISTENT_RUNS and all(r["mac"] for r in last):
        return WARN, ev + ", refresh_mac failed 3 runs in a row", "The Mac is not receiving origin: check `ssh mac` (asleep, Tailscale)."
    return PASS, ev, ""
