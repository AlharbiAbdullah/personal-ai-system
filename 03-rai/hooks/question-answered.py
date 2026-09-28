#!/usr/bin/env python3
"""
PostToolUse Hook: Question Answered.

Resets terminal tab from question state back to working state
after user answers an AskUserQuestion prompt.
"""

import json
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.hook_errors import log_error
from lib.hook_timer import hook_timer
from lib.tab_setter import set_tab_state, read_tab_state


def timeout_handler(signum, frame):
    sys.exit(0)


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception as e:
        log_error("question-answered", e, "stdin decode")
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    session_id = data.get("session_id", "unknown")

    if tool_name != "AskUserQuestion":
        sys.exit(0)

    try:
        tab = read_tab_state(session_id)
        prev_title = tab.get("previous_title", "")
        if prev_title:
            set_tab_state("working", session_id, prev_title)
        else:
            set_tab_state("working", session_id)
    except Exception as e:
        log_error("question-answered", e, f"session={session_id}")


if __name__ == "__main__":
    with hook_timer("question-answered"):
        main()
