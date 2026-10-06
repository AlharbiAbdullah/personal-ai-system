"""Identity + Eval: the auto-loaded surface exists, loads, stays in budget, and its cache is
current; the /rai eval golden set parses."""

import ast
import json
import os
import subprocess

from .core import FAIL, PASS, WARN, P, check


@check("ID-1", "Identity")
def identity_files():
    """Both identity folders exist and hold no empty file."""
    probs, counts = [], {}
    for label, d in (("rai", P.RAI / "identity"), ("ana", P.HELM / "02-ana/identity")):
        if not d.is_dir():
            probs.append(f"{label}:MISSING dir"); continue
        mds = list(d.glob("*.md"))
        counts[label] = len(mds)
        probs += [f"{label}/{p.name}:empty" for p in mds if p.stat().st_size == 0]
    ev = ", ".join(f"{k}={v}" for k, v in counts.items())
    if probs:
        return FAIL, ev + f" {probs}", "Restore: git checkout 03-rai/identity 02-ana/identity."
    if counts.get("rai", 0) < 4:
        return WARN, ev, "Rai core identity files fewer than expected (4)."
    return PASS, ev, ""


def _session_start_command() -> str | None:
    """The SessionStart command exactly as Claude Code runs it (interpreter included)."""
    cfg = json.loads((P.DCLAUDE / "settings.json").read_text())
    for group in cfg.get("hooks", {}).get("SessionStart", []):
        for h in group.get("hooks", []):
            if "session-start.py" in h.get("command", ""):
                return h["command"]
    return None


@check("ID-2", "Identity", slow=True)
def identity_loads():
    """Smoke-run session-start as settings.json registers it and confirm a real digest."""
    cmd = _session_start_command()
    if not cmd:
        return FAIL, "no SessionStart hook registered", "Register hooks/session-start.py under SessionStart in config/settings.json."
    # the registered interpreter (system python3), not sanity's own; stdin closed, as a hook's
    # is once Claude Code has written the payload, so a stdin read can never hang the run
    # as Claude Code runs it: no RAI_HARNESS (an adapter sets one)
    base = {k: v for k, v in os.environ.items() if k != "RAI_HARNESS"}
    r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=30,
                       stdin=subprocess.DEVNULL, env={**base, "HOME": str(P.HOME)})
    out = r.stdout
    markers = [m for m in ("Steering", "Identity", "Memory") if m in out]
    ev = f"{len(out)} chars, markers={markers}"
    if "Rai session context" in out:
        # Claude Code mode: the identity loads through the CLAUDE.md imports (HARN-7), and the
        # hook prints only the dynamic part. The full snapshot, as the adapters get it, must
        # still carry the sections, and the short part must stay under Claude Code's inline cap.
        full = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=30,
                              stdin=subprocess.DEVNULL, env={**base, "HOME": str(P.HOME), "RAI_HARNESS": "sanity"}).stdout
        markers = [m for m in ("Steering", "Identity", "Memory") if m in full]
        ev = f"{len(out)} chars in Claude Code, {len(full)} chars full, markers={markers}"
        if len(out) >= 10_000:
            return WARN, ev, "Claude Code shows only a 2 KB preview past 10,000 characters: trim session-start's Claude mode."
        return (PASS, ev, "") if markers else (WARN, ev, "Full snapshot produced but expected sections absent.")
    if not out.strip():
        err = (r.stderr.strip().splitlines() or [""])[-1][:100]
        return FAIL, f"blank output, rc={r.returncode}" + (f": {err}" if err else ""), "SessionStart produces nothing — identity load broken."
    if "identity load timed out" in out:
        return WARN, ev + ", session-start hit its own 8s timeout", "Sessions start without identity under load; see what slowed the identity read."
    return (PASS, ev, "") if markers else (WARN, ev, "Digest produced but expected sections absent.")


_BUDGET_NAMES = ("IDENTITY_FILE_BUDGET", "IDENTITY_TOTAL_BUDGET", "IDENTITY_BUDGET_EXEMPT")


def session_start_budget() -> tuple:
    """(per-file bytes, total bytes, exempt names), read from session-start.py itself: one set
    of numbers for the audit and the live warning, where two copies used to drift apart."""
    tree = ast.parse((P.HOOKS / "session-start.py").read_text())
    vals = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
            if isinstance(n, ast.Assign) and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name) and n.targets[0].id in _BUDGET_NAMES}
    return tuple(vals[name] for name in _BUDGET_NAMES)


@check("ID-4", "Identity")
def identity_budget():
    """The always-injected surface budget (MEMORY-ARCHITECTURE.md, injection), advisory, with
    the numbers session-start warns on. identity/learned.md and working-memory.md have their
    own HARD caps (EVOLVE-4, LIVE-3)."""
    PER_FILE, TOTAL, EXEMPT = session_start_budget()
    # An ADVISORY ceiling should not flip the whole brain to DEGRADED over a rounding error.
    # 1KB of headroom: inside it the row passes and says how close it is; past it, the WARN is real.
    GRACE = 1_024
    offenders, total = [], 0
    for d in (P.RAI / "identity", P.HELM / "02-ana/identity"):
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            size = p.stat().st_size
            total += size
            if size > PER_FILE and p.name not in EXEMPT:
                offenders.append(f"{p.name}:{size//1024}KB")
    # exact bytes, not KB: rounding hid a 184B overage as a flat "40KB/40KB" and made a true
    # WARN read as a false alarm (2026-08-27)
    delta = total - TOTAL
    ev = (f"total={total}B/{TOTAL}B ({delta:+d}B), over-4KB: {offenders or 'none'}")
    if offenders or delta > GRACE:
        return WARN, ev, "Identity surface over budget — digests pending John's per-file sign-off (never auto-truncate)."
    if delta > 0:
        return PASS, ev + f" [within {GRACE}B grace]", ""
    return PASS, ev, ""


@check("EVAL-1", "Eval")
def eval_surface():
    """/rai eval (Memory v3 quality certifier) — existence/parse ONLY, no freshness
    contract: runs are MANUAL by decision (.agent/decisions.md 2026-07-03), so a stale
    report is John's choice, not a failure."""
    ev_dir = P.SM / "eval"
    golden = ev_dir / "golden.jsonl"
    if not golden.exists():
        return WARN, "no golden.jsonl", "Run eval.py --draft-golden + author the set (skills/rai/eval.md)."
    rows, spec = 0, 0
    try:
        for line in golden.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("kind") == "freshness-spec":
                spec += 1
            else:
                rows += 1
    except Exception as e:
        return FAIL, f"golden.jsonl unparseable: {e}", "Fix the JSONL — the eval cannot run on it."
    reports = ev_dir / "reports"
    ok = reports.is_dir() and os.access(reports, os.W_OK)
    ev = f"golden={rows} rows + {spec} freshness-spec, reports dir {'writable' if ok else 'MISSING'}"
    if rows < 50 or spec != 1 or not ok:
        return WARN, ev, "Golden set thin/malformed or reports dir missing."
    return PASS, ev, ""


@check("ID-3", "Identity")
def identity_cache():
    """session-start's identity cache matches the identity files' newest mtime."""
    cache = P.RUNTIME / "identity-cache.json"
    if not cache.exists():
        return PASS, "no cache (first-run — OK)", ""
    try:
        data = json.loads(cache.read_text())
    except Exception as e:
        return FAIL, f"unparseable: {e}", "Delete the cache; next SessionStart rebuilds it."
    files = []
    for d in (P.RAI / "identity", P.HELM / "02-ana/identity"):
        if d.is_dir():
            files += [p for p in d.glob("*.md")]
    actual = max((p.stat().st_mtime for p in files), default=0)
    drift = abs(actual - data.get("max_mtime", 0))
    ev = f"mtime drift {drift:.0f}s"
    return (PASS, ev, "") if drift <= 60 else (WARN, ev, "Cache drift — next SessionStart self-heals; persistent = writer issue.")
