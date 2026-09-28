#!/usr/bin/env python3
"""
SessionEnd Hook: Update Counts.

Appends a skills/hooks snapshot to counts-history.jsonl for trend analysis,
only when the counters differ from the last line's (the timestamp is ignored),
so an unchanged vault adds nothing.
(It must never write settings.json: that file is the live symlinked
Claude Code config, and a read-modify-write here can corrupt it or
silently revert a concurrent manual edit.)
"""

import json
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.hook_errors import log_error
from lib.hook_timer import hook_timer
from lib.paths import get_hooks_dir, get_skills_dir, get_telemetry_dir
from lib.time_utils import get_iso_timestamp


def timeout_handler(signum, frame):
    sys.exit(0)


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)

HISTORY_LOG = get_telemetry_dir() / "counts-history.jsonl"
TIMESTAMP_KEY = "updatedAt"


def count_skills() -> int:
    skills_dir = get_skills_dir()
    if not skills_dir.exists():
        return 0
    return sum(
        1 for d in skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )


def count_hooks() -> int:
    hooks_dir = get_hooks_dir()
    if not hooks_dir.exists():
        return 0
    return len(list(hooks_dir.glob("*.py")))


def get_counts() -> dict:
    return {
        "skills": count_skills(),
        "hooks": count_hooks(),
        TIMESTAMP_KEY: get_iso_timestamp(),
    }


def last_counters() -> dict | None:
    """Counters of the last line in the history (timestamp dropped), or None."""
    try:
        with HISTORY_LOG.open("rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 4096))
            tail = f.read().decode("utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return None
    for line in reversed(tail):
        line = line.strip()
        if not line:
            continue
        try:
            last = json.loads(line)
        except ValueError:
            return None
        last.pop(TIMESTAMP_KEY, None)
        return last
    return None


def append_history(counts: dict):
    try:
        counters = {k: v for k, v in counts.items() if k != TIMESTAMP_KEY}
        if counters == last_counters():
            return
        HISTORY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY_LOG.open("a") as f:
            f.write(json.dumps(counts) + "\n")
    except Exception as e:
        log_error("update-counts", e, "history append")


def main():
    try:
        sys.stdin.read()
    except Exception:
        pass

    try:
        counts = get_counts()
        append_history(counts)
    except Exception as e:
        log_error("update-counts", e, "main")


if __name__ == "__main__":
    with hook_timer("update-counts"):
        main()
