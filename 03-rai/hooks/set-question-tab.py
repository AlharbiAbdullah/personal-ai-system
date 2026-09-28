#!/usr/bin/env python3
"""
PreToolUse Hook: Set Question Tab.

Changes tab title to question mode when AskUserQuestion
is invoked. Saves previous title for restoration.
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


def extract_summary(tool_input: dict) -> str:
    """Extract short summary from question data."""
    questions = tool_input.get("questions", [])
    if questions and isinstance(questions, list):
        first = questions[0]
        if isinstance(first, dict):
            header = first.get("header", "")
            if header:
                return header[:20]
            question = first.get("question", "")
            if question:
                words = question.split()[:3]
                return " ".join(words)
    return "Awaiting input"


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception as e:
        log_error("set-question-tab", e, "stdin decode")
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    session_id = data.get("session_id", "unknown")

    if tool_name != "AskUserQuestion":
        sys.exit(0)

    try:
        summary = extract_summary(tool_input)
        set_tab_state("question", session_id, summary)
    except Exception as e:
        log_error("set-question-tab", e, f"session={session_id}")


if __name__ == "__main__":
    with hook_timer("set-question-tab"):
        main()
