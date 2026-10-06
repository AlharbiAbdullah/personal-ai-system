"""Reports: one per run, and the leaderboard of every target ever run.

The headline number is the pass rate: the share of attempts that passed every check of their
task. Scores compare only within one task subset and one size, so the leaderboard has one table
per (tasks digest, size). A judged area shows both judges' views as `opus/gemini` when they
differ. pass^k is the share of tasks a target passed in every trial of a full run."""

import json
import statistics
from collections import defaultdict
from pathlib import Path

from . import paths, tasks
from .runner import read_rows

AREAS = tasks.AREAS
VIEWS = ("opus", "gemini")


def load_rows(results: Path) -> list:
    rows = []
    for f in sorted(results.glob("*/attempts.jsonl")):
        rows += read_rows(f)
    return rows


def _pct(x) -> str:
    return "-" if x is None else f"{round(100 * x)}"


def _views(vals: dict) -> str:
    a, b = (_pct(vals.get(v)) for v in VIEWS)
    return a if a == b else f"{a}/{b}"


def _name(t: dict) -> str:
    return f"{t['label']} @ {t['harness']}"


def summarize(rows: list) -> list:
    """One summary per target: area pass rates per judge view, overall, pass^k, latency, counts."""
    by_t = defaultdict(list)
    for r in rows:
        by_t[r["target"]["key"]].append(r)
    out = []
    for key, rs in by_t.items():
        scored = [r for r in rs if r.get("infra") != "error"]
        t = rs[0]["target"]
        s = {"key": key, "name": _name(t), "harness": t["harness"], "attempts": len(scored),
             "infra_errors": len(rs) - len(scored),
             "timeouts": sum(1 for r in scored if r.get("infra") == "timeout"),
             "runs": sorted({r["run_id"] for r in rs}), "areas": {}, "overall": {}, "pass_k": {}}
        for v in VIEWS:
            per_area = {}
            for a in AREAS:
                vals = [r["views"][v]["pass"] for r in scored if r["area"] == a and v in r["views"]]
                per_area[a] = (sum(vals) / len(vals)) if vals else None
            for a, x in per_area.items():
                s["areas"].setdefault(a, {})[v] = x
            present = [x for x in per_area.values() if x is not None]
            s["overall"][v] = statistics.mean(present) if present else None   # areas weigh equally
            per_run_task = defaultdict(list)
            for r in scored:
                if r["size"] == "full" and v in r["views"]:
                    per_run_task[(r["run_id"], r["task"])].append(r["views"][v]["pass"])
            runs = defaultdict(list)
            for (run_id, _), passes in per_run_task.items():
                if len(passes) > 1:
                    runs[run_id].append(all(passes))
            s["pass_k"][v] = statistics.mean(sum(p) / len(p) for p in runs.values()) if runs else None
        walls = [r["wall_s"] for r in scored if r.get("wall_s")]
        s["p50_s"] = round(statistics.median(walls)) if walls else None
        s["disagree"] = sum(1 for r in scored for c in r["checks"]
                            if c["type"] == "judge" and len({x for x in (c.get("judges") or {}).values() if x is not None}) > 1)
        out.append(s)
    return sorted(out, key=lambda s: -(s["overall"].get("opus") or 0))


def table(summaries: list) -> list:
    head = ["Target", "Overall"] + list(AREAS) + ["pass^k", "p50 s", "attempts", "infra", "judge split"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for s in summaries:
        cells = [s["name"], _views(s["overall"])]
        cells += [_views(s["areas"].get(a, {})) for a in AREAS]
        cells += [_views(s["pass_k"]), str(s["p50_s"] if s["p50_s"] is not None else "-"),
                  str(s["attempts"]), str(s["infra_errors"]), str(s["disagree"])]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


LEGEND = ("Numbers are pass rates in percent: attempts that passed every check of their task, areas "
          "weighted equally. `a/b` = Opus judge / Gemini judge where they differ. pass^k = tasks "
          "passed in every trial of a full run. infra = attempts lost to errors, left out of the "
          "rates. judge split = judged checks the two judges ruled apart.")


def run_report(run_id: str) -> str:
    d = paths.run_dir(run_id)
    spec = json.loads((d / "run.json").read_text())
    rows = read_rows(d / "attempts.jsonl")
    st = spec["status"]
    lines = [f"# Benchmark run {run_id}", "",
             f"Mode {spec['mode']}, size {spec['size']} ({spec['trials']} trial(s)), "
             f"{len(spec['tasks'])} tasks, task set {spec['set_version']}. "
             f"State: {st.get('state')}, {len(rows)}/{st.get('total')} attempts.", ""]
    lines += table(summarize(rows)) + ["", LEGEND, ""]
    fails = defaultdict(int)
    for r in rows:
        for c in r["checks"]:
            if c.get("ok") is False:
                fails[(_name(r["target"]), r["area"], c["type"])] += 1
    if fails:
        lines += ["## Most failed checks", "", "| Target | Area | Check | Fails |", "|---|---|---|---|"]
        for (t, a, c), n in sorted(fails.items(), key=lambda kv: -kv[1])[:15]:
            lines.append(f"| {t} | {a} | {c} | {n} |")
        lines.append("")
    text = "\n".join(lines)
    (d / "report.md").write_text(text)
    return text


def leaderboard() -> str:
    rows = load_rows(paths.results_dir())
    groups = defaultdict(list)
    for r in rows:
        if r["size"] != "smoke":        # route checks, not scores
            groups[(r.get("tasks_digest", r["set_version"]), r["size"])].append(r)
    lines = ["# Benchmark leaderboard", "",
             "Every model and harness `/rai benchmark` has run. Rows compare only inside one table: "
             "the same tasks and size.", "", LEGEND, ""]
    order = sorted(groups, key=lambda k: max(r["ts"] for r in groups[k]), reverse=True)
    for digest, size in order:
        rs = groups[(digest, size)]
        last = max(r["ts"] for r in rs)[:10]
        areas = sorted({r["area"] for r in rs}, key=AREAS.index)
        lines += [f"## Tasks {digest}, {size}: {', '.join(areas)} (last run {last})", ""]
        lines += table(summarize(rs)) + [""]
    text = "\n".join(lines)
    (paths.bench_dir() / "leaderboard.md").write_text(text)
    return text
