#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""bench.py: /rai benchmark, which scores models and harnesses on John's own work.

Manual only. Runs only on his subscriptions (Claude Max through Claude Code, Google
Antigravity through agy), each attempt inside a bubblewrap sandbox over a vault snapshot.
Data: 03-rai/benchmark/. Skill text: 03-rai/skills/rai/benchmark.md.

  bench.py models                         the catalog: keys, harness, default, enabled
  bench.py tasks                          counts per area and status, the task-set version
  bench.py approve <id>... | --area A --all   draft tasks -> active
  bench.py plan  [selection]              what a run would do and how long; writes nothing
  bench.py start [selection] [--night] [--concurrency N] [--timeout S] [--foreground]
  bench.py status [run-id]                progress of a run (default: the newest)
  bench.py stop <run-id>                  stop a background run; resume later
  bench.py resume <run-id> [--foreground] continue a run where it stopped, in the background
  bench.py report [run-id]                rewrite a run's report.md and leaderboard.md

Selection: --mode model|harness (default model), --models k1,k2 (model mode; default: the
catalog defaults), --harnesses h1,h2 (harness mode), --efforts low,high,... (each target once per
effort level), --size quick|full|smoke (default quick), --areas a1,a2.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bench_lib import paths, report, runner, targets, tasks  # noqa: E402

AVG_ATTEMPT_S = 90


def _csv(s: str | None) -> list | None:
    return [x.strip() for x in s.split(",") if x.strip()] if s else None


def _selection(a) -> tuple:
    cat = targets.load(paths.bench_dir())
    tgts = targets.resolve(cat, a.mode, _csv(a.models), _csv(a.harnesses), _csv(a.efforts))
    all_tasks = tasks.load(paths.bench_dir())
    chosen = tasks.select(all_tasks, a.size, _csv(a.areas))
    if not chosen:
        raise tasks.TaskError(f"no active {a.size} tasks: approve drafts first (bench.py tasks)")
    ver = "smoke" if a.size == "smoke" else tasks.set_version(all_tasks)
    return cat, tgts, chosen, ver


def _plan_lines(tgts, chosen, size, conc) -> list:
    trials = tasks.SIZES[size]["trials"]
    n = len(tgts) * len(chosen) * trials
    mins = n * AVG_ATTEMPT_S / max(1, conc) / 60
    areas = Counter(t.area for t in chosen)
    return [f"targets: {', '.join(t.name for t in tgts)}",
            f"tasks: {len(chosen)} ({', '.join(f'{a} {n}' for a, n in areas.items())}), trials {trials}",
            f"attempts: {n}, roughly {mins:.0f} min at {conc} at a time, plus judging",
            "runs on: Claude Max and Google Antigravity quota (no money)"]


def cmd_models(a) -> int:
    cat = targets.load(paths.bench_dir())
    for h, cfg in cat.harnesses.items():
        state = "on" if cfg.get("enabled") else f"off: {cfg.get('reason', '')}"
        print(f"{h:12} {state}")
    print()
    for k, t in cat.models.items():
        mark = "*" if k in cat.defaults else " "
        on = "" if cat.enabled(t.harness) else "  (harness off)"
        print(f"{mark} {k:18} {t.label:28} {t.harness:12} {t.model}{on}")
    print("\n* = default in model mode. harness mode: " +
          ", ".join(f"{h} -> {k}" for h, k in cat.harness_mode.items()))
    return 0


def cmd_tasks(a) -> int:
    try:
        all_tasks = tasks.load(paths.bench_dir())
    except tasks.TaskError as e:
        print(f"task set has problems:\n{e}")
        return 1
    c = Counter((t.area, t.status) for t in all_tasks)
    q = Counter(t.area for t in all_tasks if t.quick and t.status == "active")
    for area in tasks.AREAS:
        print(f"{area:8} active {c[(area, 'active')]:3}  draft {c[(area, 'draft')]:3}  quick-active {q[area]}")
    print(f"task-set version {tasks.set_version(all_tasks)}")
    return 0


def cmd_approve(a) -> int:
    bench = paths.bench_dir()
    want = set(a.ids or [])
    changed = 0
    for area in tasks.RAI_AREAS:
        f = bench / "tasks" / f"{area}.jsonl"
        if not f.exists():
            continue
        out = []
        for line in f.read_text().splitlines():
            if line.strip():
                raw = json.loads(line)
                if raw["status"] == "draft" and (raw["id"] in want or (a.all and a.area == area)):
                    raw["status"] = "active"
                    changed += 1
                out.append(json.dumps(raw, ensure_ascii=False))
        f.write_text("\n".join(out) + "\n")
    print(f"approved {changed} task(s)")
    return 0


def cmd_plan(a) -> int:
    cat, tgts, chosen, ver = _selection(a)
    print("\n".join(_plan_lines(tgts, chosen, a.size, a.concurrency)))
    print(f"task set {ver}")
    return 0


def _unit(run_id: str) -> str:
    return "rai-bench-" + re.sub(r"[^A-Za-z0-9-]", "-", run_id)


def _unit_active(run_id: str) -> bool:
    r = subprocess.run(["systemctl", "--user", "is-active", _unit(run_id)], capture_output=True, text=True)
    return r.stdout.strip() in ("active", "activating")


def _launch(run_id: str) -> int:
    """Run the job as a transient systemd --user unit, so it outlives this shell."""
    env = [f"--setenv={k}={v}" for k, v in os.environ.items()
           if k in ("PATH", "HOME", "LANG") or k.startswith("RAI_BENCH_")]
    r = subprocess.run(["systemd-run", "--user", f"--unit={_unit(run_id)}", "--collect", *env,
                        str(Path(__file__).resolve()), "resume", "--foreground", run_id],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"could not start the background unit: {r.stderr.strip()}")
        return 1
    print(f"running in the background as {_unit(run_id)}. Progress: bench.py status {run_id}")
    return 0


def cmd_start(a) -> int:
    cat, tgts, chosen, ver = _selection(a)
    if not shutil.which("bwrap"):
        print("bwrap is missing: the sandbox needs bubblewrap")
        return 1
    run_id = f"{datetime.now():%Y-%m-%d-%H%M}-{a.mode}-{a.size}"
    runner.new_run(run_id, a.mode, a.size, tgts, chosen, ver, night=a.night,
                   concurrency=a.concurrency, timeout=a.timeout)
    print("\n".join(_plan_lines(tgts, chosen, a.size, a.concurrency)))
    print(f"run {run_id}")
    return _resume(run_id) if a.foreground else _launch(run_id)


def _resume(run_id: str) -> int:
    try:
        runner.Runner(run_id).run()
    except runner.RunBusy as e:
        print(e)
        return 1
    report.run_report(run_id)
    report.leaderboard()
    print(f"done: {paths.run_dir(run_id) / 'report.md'}")
    return 0


def cmd_resume(a) -> int:
    if not (paths.run_dir(a.run_id) / "run.json").exists():
        print(f"no run {a.run_id}")
        return 1
    if a.foreground:
        return _resume(a.run_id)
    if _unit_active(a.run_id):
        print(f"{a.run_id} is already running as {_unit(a.run_id)}")
        return 1
    return _launch(a.run_id)


def _newest() -> str | None:
    """The run started last (by run.json's created stamp, then name)."""
    runs = []
    for p in paths.results_dir().glob("*"):
        try:
            runs.append((json.loads((p / "run.json").read_text()).get("created", ""), p.name))
        except (OSError, json.JSONDecodeError):
            continue
    return max(runs)[1] if runs else None


def cmd_status(a) -> int:
    run_id = a.run_id or _newest()
    if not run_id:
        print("no runs yet")
        return 0
    spec = json.loads((paths.run_dir(run_id) / "run.json").read_text())
    st = spec["status"]
    active = "active" if _unit_active(run_id) else "not running"
    rows = runner.read_rows(paths.run_dir(run_id) / "attempts.jsonl")
    per = Counter(r["target"]["key"] for r in rows)
    print(f"run {run_id}: {st.get('state')} (unit {active}), {len(rows)}/{st.get('total')} attempts")
    for t in spec["targets"]:
        print(f"  {t['label']} @ {t['harness']}: {per[t['key']]}")
    for acct, until in (st.get("paused") or {}).items():
        print(f"  {acct} paused until {datetime.fromtimestamp(until):%a %H:%M}")
    if st.get("resume_at"):
        print(f"  resumes at {datetime.fromtimestamp(st['resume_at']):%a %H:%M}")
    return 0


def cmd_stop(a) -> int:
    r = subprocess.run(["systemctl", "--user", "stop", _unit(a.run_id)], capture_output=True, text=True)
    print(r.stderr.strip() or f"stopped {a.run_id}. Resume with: bench.py resume {a.run_id}")
    return r.returncode


def cmd_report(a) -> int:
    run_id = a.run_id or _newest()
    if run_id:
        print(report.run_report(run_id))
    report.leaderboard()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="/rai benchmark")
    sub = p.add_subparsers(dest="cmd", required=True)

    def selection(sp):
        sp.add_argument("--mode", choices=["model", "harness"], default="model")
        sp.add_argument("--models")
        sp.add_argument("--harnesses")
        sp.add_argument("--efforts", help="run each target once per effort, e.g. low,medium,high,xhigh,max")
        sp.add_argument("--size", choices=list(tasks.SIZES), default="quick")
        sp.add_argument("--areas")
        sp.add_argument("--concurrency", type=int, default=4, choices=range(1, 17), metavar="1-16")

    sub.add_parser("models").set_defaults(fn=cmd_models)
    sub.add_parser("tasks").set_defaults(fn=cmd_tasks)
    sp = sub.add_parser("approve")
    sp.add_argument("ids", nargs="*")
    sp.add_argument("--area", choices=tasks.RAI_AREAS)
    sp.add_argument("--all", action="store_true")
    sp.set_defaults(fn=cmd_approve)
    sp = sub.add_parser("plan")
    selection(sp)
    sp.set_defaults(fn=cmd_plan)
    sp = sub.add_parser("start")
    selection(sp)
    sp.add_argument("--night", action="store_true")
    sp.add_argument("--timeout", type=int, default=900)
    sp.add_argument("--foreground", action="store_true")
    sp.set_defaults(fn=cmd_start)
    for name, fn in (("status", cmd_status), ("report", cmd_report)):
        sp = sub.add_parser(name)
        sp.add_argument("run_id", nargs="?")
        sp.set_defaults(fn=fn)
    sp = sub.add_parser("stop")
    sp.add_argument("run_id")
    sp.set_defaults(fn=cmd_stop)
    sp = sub.add_parser("resume")
    sp.add_argument("run_id")
    sp.add_argument("--foreground", action="store_true")
    sp.set_defaults(fn=cmd_resume)
    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except (targets.TargetError, tasks.TaskError) as e:
        print(e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
