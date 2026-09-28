#!/usr/bin/env python3
"""
Stop Hook: Orchestrator.

Single entry point for Stop event. Parses transcript once,
distributes to isolated handlers. Handlers run independently
and failures are isolated.
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
signal.alarm(10)  # Longer timeout for orchestrator


def extract_last_response(data: dict) -> str:
    """Extract last assistant response from stop data."""
    transcript = data.get("transcript_path", "")
    if not transcript or not Path(transcript).exists():
        return data.get("response", "")

    last_response = ""
    try:
        with open(transcript) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "assistant":
                        msg = entry.get("message", {})
                        content = msg.get("content", [])
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict):
                                    if item.get("type") == "text":
                                        last_response = item.get(
                                            "text", ""
                                        )
                        elif isinstance(content, str):
                            last_response = content
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return last_response


def handle_tab_reset(session_id: str, response: str):
    """Reset tab to completed state."""
    try:
        summary = response[:50].strip() if response else "Done"
        set_tab_state("completed", session_id, summary)
    except Exception:
        pass


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception as e:
        log_error("stop-orchestrator", e, "stdin decode")
        sys.exit(0)

    session_id = data.get("session_id", "unknown")
    response = extract_last_response(data)

    for handler in [
        handle_tab_reset,
    ]:
        try:
            handler(session_id, response)
        except Exception as e:
            log_error("stop-orchestrator", e, f"handler={handler.__name__}")


if __name__ == "__main__":
    with hook_timer("stop-orchestrator"):
        main()
