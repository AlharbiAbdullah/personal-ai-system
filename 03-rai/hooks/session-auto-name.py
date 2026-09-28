#!/usr/bin/env python3
"""
UserPromptSubmit Hook: Session Auto Name.

Auto-generates 2-3 word session names on first user prompt.
Heuristic extraction, no AI. Stores names in ~/.local/state/rai/runtime/session-names.json.
"""

import json
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.hook_errors import log_error
from lib.hook_timer import hook_timer
from lib.name_extraction import short_name
from lib.paths import get_runtime_dir
from lib.time_utils import get_iso_timestamp

NAMES_FILE = get_runtime_dir() / "session-names.json"


def timeout_handler(signum, frame):
    sys.exit(0)


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)


def load_names() -> dict:
    if NAMES_FILE.exists():
        try:
            return json.loads(NAMES_FILE.read_text())
        except Exception:
            pass
    return {}


def save_names(names: dict):
    NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    NAMES_FILE.write_text(json.dumps(names, indent=2))


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception as e:
        log_error("session-auto-name", e, "stdin decode")
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    prompt = data.get("prompt", "")

    if not prompt:
        sys.exit(0)

    try:
        names = load_names()
        if session_id in names:
            return

        name = short_name(prompt)
        names[session_id] = {
            "name": name,
            "created_at": get_iso_timestamp(),
        }
        save_names(names)
        print(name, file=sys.stderr)
    except Exception as e:
        log_error("session-auto-name", e, f"session={session_id}")


if __name__ == "__main__":
    with hook_timer("session-auto-name"):
        main()
