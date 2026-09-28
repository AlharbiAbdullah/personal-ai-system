#!/usr/bin/env python3
"""
UserPromptSubmit Hook: one-line response-format reminder.

The format contract (identity/response-format.md) auto-loads at session start, but
the baseline eval (2026-07-03, section c = 0.269) showed outputs ignoring it anyway:
em-dashes in 29/30 sampled replies. A per-prompt nudge keeps the contract in recent
context, where it actually steers generation. The banned-word list is parsed from
response-format.md at runtime (the same single source of truth the eval lint reads).
Fail-open: any problem prints nothing and exits 0.
"""

import re
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.hook_timer import hook_timer


def timeout_handler(signum, frame):
    sys.exit(0)


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(2)

RESPONSE_FORMAT = Path.home() / "helm" / "03-rai" / "identity" / "response-format.md"


def banned_words() -> str:
    try:
        m = re.search(r"^Never use:\s*(.+)$", RESPONSE_FORMAT.read_text(), re.MULTILINE)
        return m.group(1).strip().rstrip(".") if m else ""
    except Exception:
        return ""


def main():
    try:
        sys.stdin.read()
    except Exception:
        pass
    line = "[format] No em dashes (use . , :). Lead with the answer. No emojis. English only."
    words = banned_words()
    if words:
        line += f" Banned words: {words}."
    print(line)


if __name__ == "__main__":
    with hook_timer("response-format-reminder"):
        main()
