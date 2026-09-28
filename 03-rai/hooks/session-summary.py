#!/usr/bin/env python3
"""
SessionEnd Hook: Session Summary.

Clears this session's per-session state (session-names entry, tab-title /
injected-pointer / turn-capture-debounce files) so ended sessions leave no
droppings for the 6h orphan sweep to pick up.
"""

import json
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.hook_errors import log_error
from lib.hook_timer import hook_timer
from lib.paths import get_runtime_dir


def timeout_handler(signum, frame):
    sys.exit(0)


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)


def _clean_session_names(session_id: str) -> None:
    """Remove this session's entry from session-names.json (prevents IDLE ghosts)."""
    sn_path = get_runtime_dir() / "session-names.json"
    if not sn_path.exists():
        return
    try:
        names = json.loads(sn_path.read_text())
        if session_id in names:
            del names[session_id]
            sn_path.write_text(json.dumps(names, indent=2))
    except Exception:
        pass


def clear_session_work(session_id: str):
    """Clean up this session's per-session state."""
    # Clean session-names.json entry to prevent ghost IDLE entries
    _clean_session_names(session_id)

    # Session is terminating. Delete the persisted tab state without touching the
    # terminal first: no reader exists after session end.
    for sub in ("tab-titles", "injected"):
        p = get_runtime_dir() / sub / f"{session_id}.json"
        try:
            p.unlink()
        except OSError:
            pass
    # turn-capture debounce stamps have NO .json suffix (turn-capture.py touches
    # DEBOUNCE_DIR / session_id).
    try:
        (get_runtime_dir() / "turn-capture" / session_id).unlink()
    except OSError:
        pass


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception as e:
        log_error("session-summary", e, "stdin decode")
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    try:
        clear_session_work(session_id)
    except Exception as e:
        log_error("session-summary", e, f"session={session_id}")


if __name__ == "__main__":
    with hook_timer("session-summary"):
        main()
