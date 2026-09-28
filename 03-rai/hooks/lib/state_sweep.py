"""Sweep orphan per-session runtime files (~/.local/state/rai/runtime) left by crashed sessions."""

import json
from datetime import datetime, timedelta
from pathlib import Path

STALE_HOURS = 6


def _active_uuids(state_dir: Path, cutoff_ts: float) -> set[str]:
    """Collect UUIDs with any state file touched inside the cutoff window."""
    active: set[str] = set()
    for sub in ("tab-titles", "injected"):
        d = state_dir / sub
        if not d.exists():
            continue
        for p in d.glob("*.json"):
            try:
                if p.stat().st_mtime >= cutoff_ts:
                    active.add(p.stem)
            except OSError:
                pass
    tc = state_dir / "turn-capture"
    if tc.exists():
        for p in tc.iterdir():  # bare session-id stamps, no suffix
            try:
                if p.is_file() and p.stat().st_mtime >= cutoff_ts:
                    active.add(p.name)
            except OSError:
                pass
    return active


def _safe_unlink(path: Path) -> bool:
    try:
        path.unlink()
        return True
    except OSError:
        return False


def sweep_orphans(
    current_session_id: str,
    state_dir: Path,
    stale_hours: int = STALE_HOURS,
) -> dict:
    """Delete per-session files whose session has no recent activity.

    Returns counts keyed by kind: tab_titles, injected, turn_capture, session_names.
    """
    cutoff_ts = (datetime.now() - timedelta(hours=stale_hours)).timestamp()
    active = _active_uuids(state_dir, cutoff_ts)
    if current_session_id:
        active.add(current_session_id)

    counts = {"tab_titles": 0, "session_names": 0, "injected": 0}

    for sub, key in (("tab-titles", "tab_titles"), ("injected", "injected")):
        d = state_dir / sub
        if not d.exists():
            continue
        for p in d.glob("*.json"):
            if p.stem not in active and _safe_unlink(p):
                counts[key] += 1

    # turn-capture debounce stamps: bare session-id filenames, no .json suffix.
    tc = state_dir / "turn-capture"
    if tc.exists():
        counts["turn_capture"] = 0
        for p in tc.iterdir():
            if p.is_file() and p.name not in active and _safe_unlink(p):
                counts["turn_capture"] += 1

    sn_path = state_dir / "session-names.json"
    if sn_path.exists():
        try:
            names = json.loads(sn_path.read_text())
            removed = [u for u in names if u not in active]
            for u in removed:
                del names[u]
            if removed:
                sn_path.write_text(json.dumps(names, indent=2))
            counts["session_names"] = len(removed)
        except (OSError, json.JSONDecodeError):
            pass

    return counts
