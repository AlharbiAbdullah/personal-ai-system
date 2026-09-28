"""Hooks: every registered hook exists, parses, imports, fires, stays error-free, and the artifact
it is supposed to touch is fresh."""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from . import core
from .core import FAIL, PASS, WARN, P, check

HOOK_FIRING_DAYS = 7


def _registered_hooks() -> set:
    cfg = json.loads((P.DCLAUDE / "settings.json").read_text())
    out = set()
    for _e, groups in cfg.get("hooks", {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                for tok in h.get("command", "").split():
                    if tok.endswith(".py") and "/hooks/" in tok:
                        out.add(Path(tok).stem)
                        break
    return out


@check("HOOK-1", "Hooks")
def hook_scripts_exist():
    """Every hook settings.json registers exists in 03-rai/hooks."""
    reg = _registered_hooks()
    missing = [h for h in reg if not (P.HOOKS / f"{h}.py").exists()]
    ev = f"{len(reg)} registered, {len(missing)} missing"
    return (FAIL, ev + f" {missing}", "Registered hook script absent — fix config/settings.json.") if missing else (PASS, ev, "")


# Imports every lib module in a fresh interpreter, the way each hook process starts: a module that
# only imports cleanly because sanity already loaded its dependency would be a false PASS.
_IMPORT_PROBE = """
import importlib, json, sys
sys.path.insert(0, sys.argv[1])
bad = []
for m in sys.argv[2:]:
    try:
        importlib.import_module("lib." + m)
    except Exception as e:
        bad.append(f"{m}:{type(e).__name__}")
print(json.dumps(bad))
"""


@check("HOOK-2", "Hooks")
def libs_importable():
    """Every hooks/lib module imports in a fresh interpreter."""
    libdir = P.HOOKS / "lib"
    mods = sorted(p.stem for p in libdir.glob("*.py") if p.stem != "__init__")
    r = subprocess.run([sys.executable, "-c", _IMPORT_PROBE, str(P.HOOKS), *mods],
                       capture_output=True, text=True, timeout=60)
    try:
        bad = json.loads(r.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        bad = [f"probe:{(r.stderr.strip().splitlines() or ['no output'])[-1][:60]}"]
    ev = f"{len(mods)} modules, {len(bad)} import errors"
    return (FAIL, ev + f" {bad}", "A lib import cascade-fails every hook that uses it.") if bad else (PASS, ev, "")


def parse_both(files) -> list:
    """Names of files that fail to parse under sanity's own python (the chromadb one
    memory-injection and the store scripts run on) or under the system python3 the other hooks
    and scripts are registered with. Builtin compile(): no .pyc lands in the vault."""
    bad = []
    for p in files:
        try:
            compile(p.read_bytes(), str(p), "exec")
        except SyntaxError:
            bad.append(p.stem)
    bad += [f"{Path(b.rsplit(':', 1)[0]).stem} (python3)" for b in core.compile_with(core.SYSTEM_PYTHON, files)]
    return bad


@check("HOOK-3", "Hooks")
def hooks_parse():
    """Every hook and lib module parses under both interpreters the hooks run on."""
    hooks = sorted(P.HOOKS.glob("*.py"))
    libs = sorted((P.HOOKS / "lib").glob("*.py"))
    bad = parse_both(hooks + libs)
    ev = f"{len(hooks)} hooks + {len(libs)} lib, {len(bad)} syntax errors"
    return (FAIL, ev + f" {bad}", "A hook with a syntax error silently no-ops.") if bad else (PASS, ev, "")


@check("HOOK-4", "Hooks", slow=True)
def hooks_firing():
    """Every registered hook should appear in hook-perf.jsonl within the window. A hook that has
    stopped firing is a silent regression."""
    log = P.TELEMETRY / "hook-perf.jsonl"
    reg = _registered_hooks()
    if not log.exists():
        return WARN, "hook-perf.jsonl absent", "Hook timing log missing — can't verify firing."
    cut = time.time() - HOOK_FIRING_DAYS * 86400
    seen = set()
    from collections import deque
    with log.open() as f:
        for line in deque(f, maxlen=8000):
            try:
                e = json.loads(line)
                ts = datetime.fromisoformat(e.get("ts", "").replace("Z", "+00:00")).timestamp()
                if ts > cut:
                    seen.add(e.get("hook", ""))
            except Exception:
                continue
    silent = sorted(reg - seen)
    ev = f"{len(seen & reg)}/{len(reg)} fired in {HOOK_FIRING_DAYS}d"
    if silent:
        return (FAIL if len(silent) > 2 else WARN), ev + f", silent={silent}", "A silent hook stopped firing — check matchers + hook-errors.jsonl."
    return PASS, ev, ""


@check("HOOK-5", "Hooks")
def hook_errors():
    """The last 300 hook runs logged at most a handful of errors."""
    log = P.TELEMETRY / "hook-perf.jsonl"
    if not log.exists():
        return WARN, "no hook-perf log", ""
    from collections import deque
    errs = 0
    with log.open() as f:
        for line in deque(f, maxlen=300):
            if '"status":"error"' in line or '"status": "error"' in line:
                errs += 1
    ev = f"{errs} errors in last 300 events"
    if errs > 5:
        return FAIL, ev, "Hooks erroring repeatedly — inspect hook-errors.jsonl."
    if errs:
        return WARN, ev, "Occasional hook errors — review hook-errors.jsonl."
    return PASS, ev, ""


@check("HOOK-6", "Hooks")
def hook_effects():
    """Per-hook OUTPUT freshness — the behavioural matrix. A hook can be 'registered' and 'firing'
    yet produce nothing useful; assert the artifact each one is supposed to touch is fresh."""
    rows = []

    def fresh(label, path, days, glob=None):
        if glob:
            files = list(path.glob(glob)) if path.exists() else []
            if not files:
                rows.append((label, None)); return
            p = max(files, key=lambda x: x.stat().st_mtime)
        else:
            if not path.exists():
                rows.append((label, None)); return
            p = path
        rows.append((label, core._age_hours(p) / 24))

    fresh("tab-title->tab-titles", P.RUNTIME / "tab-titles", 14, glob="*.json")
    fresh("auto-name->session-names", P.RUNTIME / "session-names.json", 14)
    fresh("session-start->identity-cache", P.RUNTIME / "identity-cache.json", 30)
    fresh("turn-capture->daily", P.SM / "daily", 14, glob="*.md")
    # The batch scanner (sync_claude_sessions.py, run by the coordinator) queues sessions in
    # pending/ and the drain archives them: the newest file in either is the capture signal.
    pend = list((P.SM / "pending").glob("*.json")) if (P.SM / "pending").exists() else []
    arch = list((P.HELM / "13-archive/historical-sessions").glob("session_*.json"))
    newest = pend + arch
    capture_age = (core._age_hours(max(newest, key=lambda x: x.stat().st_mtime)) / 24) if newest else None
    rows.append(("scanner->capture", capture_age))

    stale = [lbl for lbl, age in rows if age is None or age > 14]
    ev = ", ".join(f"{lbl}={'?' if age is None else f'{age:.0f}d'}" for lbl, age in rows)
    if stale:
        return WARN, ev, f"Stale/absent effect: {stale} — the producing hook may have stopped."
    return PASS, ev, ""
