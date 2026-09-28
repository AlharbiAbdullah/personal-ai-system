#!/usr/bin/env python3
"""
eval.py — /rai eval: the Memory v3 QUALITY certifier (sanity certifies function;
this certifies the OUTPUT is right). Decisions: .agent/decisions.md (2026-07-03).

MANUAL ONLY — John triggers every run; never wired into the coordinator.
Writes ONLY under semantic-memory/eval/ (reports, history, partials). Never
mutates the stores, preferences, or config it measures.

Sections (each its own process — timeout-proof, resumable):
  a       retrieval golden set + run-time freshness probes   (deterministic)
  b       per-prompt injection relevance                     (judged)
  c       identity adherence lint + tone sample              (lint + judged)
  d       daily-bullet fidelity                              (judged)
  e       distill fidelity                                   (judged)
  f       self-evolve precision (flags only — John demotes) (judged)
  smokes  5 end-to-end /recall runs vs golden                (judged)
  assemble  merge partials -> report + history line

Run (always under py-chroma.sh):
  py-chroma.sh eval.py --run-id 2026-07-04a --section a
  ...
  py-chroma.sh eval.py --run-id 2026-07-04a --section assemble [--baseline]
  py-chroma.sh eval.py --draft-golden      # stratified mining dump for golden authoring
"""

import argparse
import json
import random
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path.home() / "helm" / "03-rai"
SM = ROOT / "semantic-memory"
EVAL = SM / "eval"
GOLDEN = EVAL / "golden.jsonl"
HISTORY = EVAL / "history.jsonl"
REPORTS = EVAL / "reports"

sys.path.insert(0, str(ROOT / "hooks"))
sys.path.insert(0, str(Path(__file__).parent))
from lib.daily_log import DAILY_DIR, parse_blocks  # noqa: E402

SECTION_NAMES = {
    "a": "Retrieval (golden + freshness)", "b": "Injection relevance",
    "c": "Identity adherence", "d": "Bullet fidelity", "e": "Distill fidelity",
    "f": "Self-evolve precision", "smokes": "/recall end-to-end smokes",
}


def load_golden():
    rows, spec = [], None
    for line in GOLDEN.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("kind") == "freshness-spec":
            spec = r
        else:
            rows.append(r)
    return rows, spec


def write_partial(run_id: str, section: str, data: dict):
    pdir = REPORTS / ".partial" / run_id
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / f"{section}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(f"[eval] {section}: score={data.get('score')} -> {pdir / (section + '.json')}")


# ---------------------------------------------------------------- section a

def _match(expected: dict, hits: list) -> bool:
    subs = [s.casefold() for s in expected.get("content_substrings", [])]
    doc_id = expected.get("doc_id")
    sess = expected.get("session_id", "")
    for h in hits:
        text = (h.get("content") or "").casefold()
        if subs and any(s in text for s in subs):
            return True
        if doc_id and h.get("id") == doc_id:
            return True
        if sess and (h.get("session_id", h.get("session", "")) or "").startswith(sess[:8]):
            return True
    return False


def _stale(expected: dict, col) -> bool:
    """Expected doc superseded/archived -> the row needs a manual refresh, not a fail."""
    doc_id = expected.get("doc_id")
    try:
        if doc_id:
            got = col.get(ids=[doc_id], include=["metadatas"])
            if got.get("ids"):
                return (got["metadatas"][0] or {}).get("status") != "active"
        subs = expected.get("content_substrings", [])
        if subs:
            r = col.query(query_texts=[subs[0]], n_results=3,
                          where={"status": "archived"}, include=["documents"])
            return any(subs[0].casefold() in (d or "").casefold()
                       for d in r.get("documents", [[]])[0])
    except Exception:
        pass
    return False


def section_a(run_id: str):
    from lib import memory_retrieval as mr
    rows, spec = load_golden()
    sem_col = mr._collection("rai-semantic")
    results, n_pass, n_stale = [], 0, 0
    for r in rows:
        q, tier, kind = r["question"], r.get("tier", "semantic"), r.get("kind", "positive")
        hits = {"semantic": lambda: mr.query_semantic(q, 8),
                "daily": lambda: mr.query_daily(q, 5),
                "episodic": lambda: mr.query_episodic(q, 5)}[tier]()
        hit = _match(r["expected"], hits)
        stale = False
        if kind == "positive" and not hit and tier == "semantic":
            stale = _stale(r["expected"], sem_col)
        passed = (not hit) if kind == "negative" else hit
        if stale:
            n_stale += 1
        elif passed:
            n_pass += 1
        results.append({"id": r["id"], "kind": kind, "tier": tier, "passed": passed,
                        "stale": stale, "question": q})
    fresh = _freshness(run_id, spec)
    scored = len(rows) - n_stale
    f_pass = sum(1 for x in fresh if x["passed"])
    score = round((n_pass + f_pass) / max(1, scored + len(fresh)), 3)
    write_partial(run_id, "a", {
        "score": score, "golden_pass": n_pass, "golden_scored": scored,
        "stale": [x["id"] for x in results if x["stale"]],
        "freshness_pass": f_pass, "freshness_total": len(fresh),
        "failures": [x for x in results if not x["passed"] and not x["stale"]],
        "freshness": fresh,
    })


def _freshness(run_id: str, spec):
    """Run-time probes: facts captured live in the last window MUST be retrievable.
    Static freshness rows go stale within days — sampling at run time cannot."""
    if not spec:
        return []
    from lib import memory_retrieval as mr
    cutoff = datetime.now() - timedelta(hours=spec.get("window_hours", 48))
    cands = []
    for f in sorted(DAILY_DIR.glob("*.md")):
        for t, sid, text in parse_blocks(f):
            try:
                dt = datetime.strptime(f"{f.stem} {t}", "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            if dt < cutoff:
                continue
            for ln in text.splitlines():
                ln = ln.strip().lstrip("- ").strip()
                if len(ln) >= 30:
                    cands.append({"date": f.stem, "time": t, "session": sid, "line": ln})
                    break
    sample = random.Random(run_id).sample(cands, min(spec.get("count", 20), len(cands)))
    out = []
    for c in sample:
        daily_hits = mr.query_daily(c["line"][:200], 5)
        hit_daily = any(c["line"][:60].casefold() in (h.get("content") or "").casefold()
                        for h in daily_hits)
        sem_hits = mr.query_semantic(c["line"][:200], 8)
        hit_sem = any((h.get("source_session") or "").startswith(c["session"][:8])
                      and h.get("relevance", 0) >= 0.35 for h in sem_hits)
        out.append({**c, "passed": hit_daily or hit_sem,
                    "via": "daily" if hit_daily else ("semantic" if hit_sem else "miss")})
    return out


# ---------------------------------------------------------------- assemble

def _baseline_scores():
    if not HISTORY.exists():
        return None
    lines = [json.loads(x) for x in HISTORY.read_text().splitlines() if x.strip()]
    for entry in lines:
        if entry.get("baseline"):
            return entry
    return lines[0] if lines else None


def _candidates():
    """Golden-set growth proposals: recent working-memory entries + newest decisions."""
    out = []
    wm = ROOT / "identity" / "working-memory.md"
    if wm.exists():
        out += [f"working-memory: {ln.lstrip('- ').strip()}"
                for ln in wm.read_text().splitlines() if ln.startswith("- ")][:5]
    idx = SM / "index" / "rai-semantic.jsonl"
    if idx.exists():
        rows = [json.loads(x) for x in idx.read_text().splitlines()[-400:] if x.strip()]
        dec = [r for r in rows if (r.get("metadata") or {}).get("type") == "decision"
               and (r.get("metadata") or {}).get("status") == "active"]
        dec.sort(key=lambda r: r["metadata"].get("source_date", ""), reverse=True)
        out += [f"decision {r['metadata'].get('source_date')}: {r['document'][:140]}"
                for r in dec[:5]]
    return out


def assemble(run_id: str, baseline: bool):
    pdir = REPORTS / ".partial" / run_id
    parts = {p.stem: json.loads(p.read_text()) for p in sorted(pdir.glob("*.json"))}
    missing = [s for s in list(SECTION_NAMES) if s not in parts]
    if missing:
        print(f"[eval] MISSING sections {missing} — run them, then re-assemble")
        return 1
    base = None if baseline else _baseline_scores()
    ts = datetime.now()
    name = f"{ts:%Y-%m-%d-%H%M}{'-baseline' if baseline else ''}.md"
    lines = [f"# Rai eval — {ts:%Y-%m-%d %H:%M} ({'BASELINE' if baseline else 'run'} · {run_id})",
             "", "| section | score | baseline | delta |", "|---|---|---|---|"]
    for s, title in SECTION_NAMES.items():
        sc = parts[s].get("score")
        b = (base or {}).get("scores", {}).get(s) if base else None
        delta = f"{sc - b:+.3f}" if isinstance(b, (int, float)) else "—"
        lines.append(f"| {s} · {title} | {sc} | {b if b is not None else '—'} | {delta} |")
    a = parts["a"]
    if a.get("stale"):
        lines += ["", "## Stale golden rows (refresh manually, excluded from score)",
                  *[f"- {i}" for i in a["stale"]]]
    lines += ["", "## Fix backlog"]
    for s in SECTION_NAMES:
        for issue in parts[s].get("issues", [])[:10]:
            lines.append(f"- [{s}] {issue}")
    for fx in a.get("failures", [])[:15]:
        lines.append(f"- [a] MISS {fx['tier']}/{fx['kind']}: {fx['question'][:100]}")
    lines += ["", "## Proposed golden candidates (accept/reject at next run)",
              *[f"- {c}" for c in _candidates()],
              "", f"<sub>manual run · judge=opus xhigh · partials merged from {run_id}</sub>"]
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text("\n".join(lines) + "\n")
    with open(HISTORY, "a") as h:
        h.write(json.dumps({"ts": ts.isoformat(timespec="seconds"), "run_id": run_id,
                            "baseline": baseline,
                            "scores": {s: parts[s].get("score") for s in SECTION_NAMES}}) + "\n")
    shutil.rmtree(pdir)
    print(f"[eval] report -> {REPORTS / name}")
    return 0


# ---------------------------------------------------------------- draft-golden

def draft_golden():
    """Stratified mining dump — Rai authors the 80 static rows from this in-session,
    John approves the mix + spot-checks (decisions.md)."""
    idx = [json.loads(x) for x in (SM / "index" / "rai-semantic.jsonl").read_text().splitlines()
           if x.strip()]
    by_month, archived = {}, []
    for r in idx:
        md = r.get("metadata") or {}
        row = {"id": r["id"], "text": r["document"][:220], "type": md.get("type"),
               "date": md.get("source_date"), "confidence": md.get("confidence"),
               "session": md.get("source_session")}
        if md.get("status") == "active" and md.get("type") in ("fact", "decision") \
                and md.get("confidence") in ("high", "medium"):
            by_month.setdefault((md.get("source_date") or "")[:7], []).append(row)
        elif md.get("status") == "archived":
            archived.append(row)
    rnd = random.Random("golden")
    pool = {m: rnd.sample(v, min(12, len(v))) for m, v in sorted(by_month.items())}
    learned = (ROOT / "identity" / "learned.md").read_text().splitlines()
    dump = {
        "positive_by_month": pool,
        "negative_candidates_archived": rnd.sample(archived, min(30, len(archived))),
        "preferences_active": [ln for ln in learned if ln.startswith("- ")],
        "daily_dates": sorted(f.stem for f in DAILY_DIR.glob("*.md")),
        "note": "author ~60 positive (mix months/types) + ~20 negative; tier per row; "
                "freshness handled by the freshness-spec row, not static rows",
    }
    EVAL.mkdir(parents=True, exist_ok=True)
    out = EVAL / "golden-draft-input.json"
    out.write_text(json.dumps(dump, indent=1, ensure_ascii=False))
    print(f"[eval] mining dump -> {out}")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-id")
    p.add_argument("--section", choices=list(SECTION_NAMES) + ["assemble"])
    p.add_argument("--baseline", action="store_true")
    p.add_argument("--draft-golden", action="store_true")
    a = p.parse_args()
    if a.draft_golden:
        return draft_golden()
    if not (a.run_id and a.section):
        p.error("--run-id and --section required (or --draft-golden)")
    if a.section == "a":
        return section_a(a.run_id) or 0
    if a.section == "assemble":
        return assemble(a.run_id, a.baseline)
    import eval_sections
    return eval_sections.run(a.section, a.run_id, write_partial) or 0


if __name__ == "__main__":
    sys.exit(main())
