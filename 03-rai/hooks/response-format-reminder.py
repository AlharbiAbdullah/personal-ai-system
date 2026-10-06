#!/usr/bin/env python3
"""
UserPromptSubmit Hook: the per-prompt reminders.

1. [format] The format contract (identity/response-format.md) auto-loads at session start,
   but the baseline eval (2026-07-03, section c = 0.269) showed outputs ignoring it anyway:
   em-dashes in 29/30 sampled replies. A per-prompt line keeps the contract in recent
   context, where it actually steers generation (5/30 after this hook landed). The length
   rule leads the line: it lived only in the
   identity file until 2026-10-01, and replies kept running to pages.
2. [workflows] John's workflows (~/helm/11-workflows/) went unopened in 197 of 197
   interactive sessions (2026-08-28 to 2026-09-28), although a menu of them sat in the
   SessionStart context. One constant line per prompt names the kinds of work, and the
   model does the matching: keyword and embedding matchers scored 0.41 and 0.32 precision
   on his real prompts. Skipped in headless runs, in learning folders (the Socratic rule
   in /learning wins there) and for prompts under MIN_PROMPT characters.

Fail-open: any problem prints nothing and exits 0.
"""

import json
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.hook_timer import hook_timer

HOME = Path.home()

WORKFLOW_LINE = (
    "[workflows] One of his kinds of work? Debugging, code review, shipping, a project or task, "
    "a data pipeline or platform, air-gapped delivery, an architecture decision, an AI build, "
    "a work engagement, an audit, an incident, a machine change, changing Rai, "
    "a learning stage, a purchase, a research write-up, Arabic writing. "
    "If so, read its file in ~/helm/11-workflows/ first and name it."
)

# Learning builds keep the Socratic rule, so the workflow line stays quiet there.
LEARNING_ROOTS = ("helm/06-learning", "helm/07-reading", "playground")
LAB_SUFFIX = "-lab"  # stage code lives in ~/projects/<topic>-lab/ (06-learning/AGENTS.md)
MIN_PROMPT = 8


def timeout_handler(signum, frame):
    sys.exit(0)


def read_payload(raw: str) -> dict:
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def in_learning_folder(cwd: str, home: Path = HOME) -> bool:
    if not cwd:
        return False
    try:
        path = Path(cwd).expanduser().resolve()
        home = home.resolve()
    except Exception:
        return False
    for root in LEARNING_ROOTS:
        if path == home / root or (home / root) in path.parents:
            return True
    projects = home / "projects"
    if projects in path.parents:
        return path.relative_to(projects).parts[0].endswith(LAB_SUFFIX)
    return False


def workflow_line_wanted(payload: dict) -> bool:
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or len(prompt.strip()) < MIN_PROMPT:
        return False
    if in_learning_folder(payload.get("cwd") or os.getcwd()):
        return False
    from lib.headless import invoked_from_headless

    return not invoked_from_headless()


def main():
    try:
        payload = read_payload(sys.stdin.read())
    except Exception:
        payload = {}
    line = (
        "[format] HARD RULE, deal breaker: SHORT. He is human and reads in small chunks. "
        "Length follows the need, never more. Answer in line 1. No preamble, recap, narration "
        "or offer menu. One question per turn. Cut every line that can go without loss. "
        "No em dashes (use . , :). No emojis. English only."
    )
    print(line)
    try:
        if workflow_line_wanted(payload):
            print(WORKFLOW_LINE)
    except Exception:
        pass


if __name__ == "__main__":
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(2)
    with hook_timer("response-format-reminder"):
        main()
