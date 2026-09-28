"""Self-test: the coverage gates that keep the harness from drifting onto a corpse."""

from . import core
from .core import (ASSERTED_COLLECTIONS, FAIL, PASS, PROBE_COLLECTION, TOMBSTONED_COLLECTIONS,
                   WARN, P, check)
from .hooks import _registered_hooks


@check("META-1", "Self-test")
def collection_coverage():
    """The fix for the original drift: every LIVE collection must be either asserted-live or
    explicitly tombstoned. An unknown collection (a silently-added store) FAILs here so it can't
    rot unwatched — and a re-appearing husk gets flagged for cleanup."""
    cols = core._collections()
    live = set(cols)
    known = ASSERTED_COLLECTIONS | TOMBSTONED_COLLECTIONS | {PROBE_COLLECTION}
    unknown = live - known
    # Empty tombstoned husks should just be dropped (nag until they are). A non-empty tombstoned
    # collection (e.g. legacy `memories`=789) is an acknowledged, decision-pending corpse — no nag.
    empty_husks = sorted(h for h in (live & TOMBSTONED_COLLECTIONS) if cols[h] == 0)
    ev = f"live={sorted(live)}"
    if unknown:
        return FAIL, ev + f" UNKNOWN={sorted(unknown)}", "New store with no check — add to ASSERTED_COLLECTIONS + a check, or tombstone it."
    if empty_husks:
        return WARN, ev + f" empty_husks={empty_husks}", "Empty legacy collections — drop them (client.delete_collection)."
    return PASS, ev, ""


@check("META-2", "Self-test")
def hook_coverage():
    """Every registered hook must be covered by the firing/parse checks (which enumerate the
    registry dynamically). Verify the registry is reachable so coverage isn't silently zero."""
    try:
        reg = _registered_hooks()
    except Exception as e:
        return FAIL, f"can't read hook registry: {e}", "settings.json unreadable — coverage is blind."
    ev = f"{len(reg)} hooks under HOOK-1/2/3/4 coverage"
    return (PASS, ev, "") if reg else (FAIL, "0 hooks registered", "No hooks registered — settings.json wrong?")


@check("META-3", "Self-test")
def fault_test_coverage():
    """Every check has a fault test (`test_<id>_fault*` beside the harness): a check nobody has
    watched fail is a check nobody knows works."""
    tests = sorted(P.TESTS.glob("test_*.py")) if P.TESTS.is_dir() else []
    if not tests:
        return WARN, f"no tests in {P.TESTS}", "Restore the tests/ folder beside sanity.py from git."
    text = "".join(t.read_text(errors="replace") for t in tests)
    missing = [cid for cid, *_ in core.CHECKS
               if f"def test_{cid.lower().replace('-', '_')}_fault" not in text]
    ev = f"{len(core.CHECKS) - len(missing)}/{len(core.CHECKS)} checks have a fault test"
    if missing:
        return WARN, ev + f", missing {missing[:6]}", "Write test_<id>_fault_* for each: build the fault, assert the check catches it."
    return PASS, ev, ""
