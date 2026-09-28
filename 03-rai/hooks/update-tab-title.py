#!/usr/bin/env python3
"""
UserPromptSubmit Hook: Update Tab Title.

Updates the terminal tab title (OSC escape, lib/tab_setter) on prompt receipt to show
what the session is working on.
"""

import json
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.hook_errors import log_error
from lib.hook_timer import hook_timer
from lib.tab_setter import set_tab_state


def timeout_handler(signum, frame):
    sys.exit(0)


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)


def extract_title(prompt: str) -> str:
    """Extract a short working title from the prompt."""
    clean = prompt.strip().split("\n")[0][:60]
    words = clean.split()[:4]
    if not words:
        return "Working"
    return " ".join(words)


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception as e:
        log_error("update-tab-title", e, "stdin decode")
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    prompt = data.get("prompt", "")

    if not prompt:
        sys.exit(0)

    try:
        title = extract_title(prompt)
        set_tab_state("working", session_id, title)
    except Exception as e:
        log_error("update-tab-title", e, f"session={session_id}")


if __name__ == "__main__":
    with hook_timer("update-tab-title"):
        main()
