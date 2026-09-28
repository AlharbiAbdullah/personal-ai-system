#!/usr/bin/env python3
"""
sanity.py — Rai brain end-to-end integrity CERTIFIER (Memory v3 — hybrid).

Run via the chromadb wrapper (the harness queries the live stores):
    semantic-memory/scripts/py-chroma.sh skills/rai/scripts/sanity.py [flags]

Flags:
    --quick         skip the slow checks (subprocess smoke-runs, full-tree symlink scan)
    --json          emit machine-readable JSON instead of the human table
    --baseline      write current counts to .sanity-baseline.json (the only writing flag besides
                    --write-status); used to reset drift detection
    --write-status  write memory/learning/system/sanity-last.json (the artifact the Mac's
                    session-start surfaces as a banner). The maintenance coordinator passes this.

WHY THIS EXISTS — the brain was sick for ~3 months and the old healthcheck stayed green. Two
blind spots, both designed out here:
  1. It tested STRUCTURE (file exists / hook registered), never FUNCTION (did the thing produce
     fresh output). A loop that runs but writes nothing looked identical to a healthy one.
  2. It could silently drift onto a corpse — it kept querying the dead `memories` collection long
     after the live brain moved to rai-semantic/rai-episodic, and reported PASS on the dead one.
The cure: every productive component asserts an OUTPUT + FRESHNESS contract; the harness discovers
live components dynamically and FAILs on any it doesn't recognise (coverage gate); nothing
load-bearing is "advisory".

ROLE-AWARE — the Mac is a read-replica, Ubuntu is the sole producer/coordinator (see
SYNC-ARCHITECTURE.md). Producer-only checks ("is it distilling?") would false-FAIL on the Mac,
where not-distilling is correct. So each check is tagged producer / consumer / shared; the runner
detects its role (darwin -> consumer, linux -> producer; override with RAI_ROLE) and SKIPs the
checks that don't apply, never failing a machine for doing its job.

The checks live in sanity_checks/, one module per subsystem; this file runs them and reports.
"""

import argparse
import json
import sys
import threading
import traceback
from datetime import datetime

from sanity_checks import CHECKS
from sanity_checks import core
from sanity_checks.core import (BROKEN_SUBSYSTEMS, FAIL, PASS, SHARED, SKIP, SUBSYSTEM_ORDER,
                                WARN, P, R)
from sanity_checks.data import _git_du, md_count

# One hung check (a network call, a held sqlite lock) must not eat the coordinator's 5-minute
# cap and leave sanity-last.json unwritten: past this it reports FAIL and the run moves on.
CHECK_TIMEOUT_S = 90
STATUSES = (PASS, WARN, FAIL, SKIP)


def run_one(entry, quick: bool, role: str, timeout: float = CHECK_TIMEOUT_S) -> R:
    """One check, contained: a raise, a hang or a malformed return becomes a FAIL row."""
    cid, sub, crole, slow, fn = entry
    if crole != SHARED and crole != role:
        return R(cid, sub, crole, SKIP, f"{crole}-only (role={role})")
    if quick and slow:
        return R(cid, sub, crole, SKIP, "slow (--quick)")
    box = {}

    def target():
        try:
            box["out"] = fn()
        except Exception as e:
            box["err"] = (e, traceback.format_exc())

    t = threading.Thread(target=target, name=cid, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return R(cid, sub, crole, FAIL, f"timed out after {timeout:.0f}s",
                 "A hung check is a finding: find what it waits on (network, lock, subprocess).")
    if "err" in box:
        e, tb = box["err"]
        return R(cid, sub, crole, FAIL, f"raised {type(e).__name__}: {str(e)[:120]}",
                 "Check itself errored — " + tb.splitlines()[-1][:80])
    out = box.get("out")
    if not (isinstance(out, tuple) and len(out) == 3 and out[0] in STATUSES):
        return R(cid, sub, crole, FAIL, f"malformed result {str(out)[:80]}",
                 "A check must return (status, evidence, fix).")
    return R(cid, sub, crole, *out)


def run(quick: bool, role: str):
    """Every check, reported one block per subsystem (registration order inside a block)."""
    results = [run_one(e, quick, role) for e in CHECKS]
    rank = {s: i for i, s in enumerate(SUBSYSTEM_ORDER)}
    return sorted(results, key=lambda r: rank.get(r.subsystem, len(rank)))


def print_catalog():
    """--list: the catalog, straight from the registry (the docs point here, never at a count)."""
    rank = {s: i for i, s in enumerate(SUBSYSTEM_ORDER)}
    for cid, sub, role, slow, fn in sorted(CHECKS, key=lambda e: rank.get(e[1], len(rank))):
        doc = " ".join((fn.__doc__ or fn.__name__).split())
        first = doc.split(". ")[0].rstrip(".")  # the first sentence carries what the check asserts
        print(f"{cid:<10} {sub:<13} {role:<9} {'slow' if slow else '    '}  {first}")
    print(f"\n{len(CHECKS)} checks")


def verdict(results):
    fails = [r for r in results if r.status == FAIL]
    warns = [r for r in results if r.status == WARN]
    broken = [r for r in fails if r.subsystem in BROKEN_SUBSYSTEMS]
    if broken:
        return "BROKEN", fails, warns
    if fails or len(warns) >= 3:
        return "DEGRADED", fails, warns
    return "HEALTHY", fails, warns


def write_status(v, results, role):
    fails = [{"id": r.id, "subsystem": r.subsystem, "evidence": r.evidence}
             for r in results if r.status == FAIL]
    # warns flip the verdict to DEGRADED at >=3 (see verdict()), so the status
    # file must name them or the session-start banner can't explain itself.
    warns = [{"id": r.id, "subsystem": r.subsystem, "evidence": r.evidence}
             for r in results if r.status == WARN]
    P.STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    P.STATUS_FILE.write_text(json.dumps({
        "verdict": v, "role": role,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "counts": {s: sum(1 for r in results if r.status == s) for s in (PASS, WARN, FAIL, SKIP)},
        "fails": fails,
        "warns": warns,
    }, indent=2))


BASELINE_REFRESH_D = 7


def refresh_baseline(results) -> bool:
    """--write-status keeps the loss tripwire current without a human (a 3-month-old baseline
    once blunted DATA-3). It rewrites the baseline when it is missing, or when it is a week old
    and this run saw no drop (DATA-3 and PIPE-3 clean). A drop keeps warning until reset by hand."""
    by_id = {r.id: r.status for r in results}
    if P.BASELINE.exists():
        try:
            written = datetime.fromisoformat(json.loads(P.BASELINE.read_text()).get("written", ""))
            age_d = (datetime.now() - written).total_seconds() / 86400
        except (ValueError, TypeError):
            age_d = BASELINE_REFRESH_D  # unreadable date: treat as due
        if age_d < BASELINE_REFRESH_D or by_id.get("DATA-3") != PASS or by_id.get("PIPE-3") not in (PASS, SKIP):
            return False
    write_baseline(quiet=True)
    return True


def write_baseline(quiet: bool = False):
    cols = core._collections()
    data = {
        "md_count": md_count(),  # the same count DATA-3 compares against
        "chromadb_kb": int(_git_du(P.CHROMADB_DIR) / 1024),
        "rai_semantic_count": cols.get("rai-semantic", 0),
        "rai_episodic_count": cols.get("rai-episodic", 0),
        "written": datetime.now().isoformat(timespec="seconds"),
    }
    P.BASELINE.write_text(json.dumps(data, indent=2))
    if not quiet:
        print(f"baseline written: {data}")


def print_table(results, v, fails, warns, role):
    from itertools import groupby
    ICON = {PASS: "✓", WARN: "!", FAIL: "✗", SKIP: "·"}
    print(f"\n# Brain Sanity — {datetime.now():%Y-%m-%d %H:%M}  (role: {role})\n")
    for sub, group in groupby(results, key=lambda r: r.subsystem):
        rows = list(group)
        print(f"## {sub}")
        for r in rows:
            line = f"  {ICON[r.status]} {r.id:<10} {r.status:<5} {r.evidence}"
            print(line)
            if r.status in (FAIL, WARN) and r.fix:
                print(f"       ↳ fix: {r.fix}")
        print()
    counts = {s: sum(1 for r in results if r.status == s) for s in (PASS, WARN, FAIL, SKIP)}
    print(f"PASS {counts[PASS]}  WARN {counts[WARN]}  FAIL {counts[FAIL]}  SKIP {counts[SKIP]}")
    print(f"VERDICT: {v}")
    if fails:
        print("\nFAILED:")
        for r in fails:
            print(f"  ✗ [{r.subsystem}] {r.id}: {r.evidence}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--write-status", action="store_true")
    ap.add_argument("--list", action="store_true", help="print the check catalog and exit")
    a = ap.parse_args()

    if a.list:
        print_catalog()
        return 0
    if a.baseline:
        write_baseline()
        return 0

    role = core.detect_role()
    results = run(a.quick, role)
    v, fails, warns = verdict(results)

    if a.write_status:
        write_status(v, results, role)
        refresh_baseline(results)

    if a.json:
        print(json.dumps({
            "verdict": v, "role": role,
            "results": [vars(r) for r in results],
        }, indent=2))
    else:
        print_table(results, v, fails, warns, role)

    return {"HEALTHY": 0, "DEGRADED": 1, "BROKEN": 2}[v]


if __name__ == "__main__":
    sys.exit(main())
