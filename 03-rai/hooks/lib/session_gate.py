#!/usr/bin/env python3
"""
session_gate.py — THE single session-classification policy (Memory v3, Phase A).

One shared policy for the batch scanner, the drain (process_pending) and
rebuild_chromadb (see MEMORY-ARCHITECTURE.md, capture):

  HEADLESS           entrypoint == sdk-cli       -> EPHEMERAL, checked FIRST. Pipeline
                                                    self-calls (distill Opus, turn-capture
                                                    Sonnet, scheduled -p jobs) embed user
                                                    transcripts in their prompts, so the
                                                    remember-regex matches quoted text and
                                                    the memory system re-ingests its own
                                                    distill calls in a loop (2026-07-03).
  EXPLICIT_REMEMBER  user asked to remember      -> archive + episodic + distill, always
  MEMORY_WORTHY      >=4 human msgs OR plan-mode OR >=2 files edited
                                                 -> archive + episodic + distill
  ARCHIVE_ONLY       2-3 human msgs AND (tool use OR >=10 min)
                                                 -> archive only (no distill, no episodic)
  EPHEMERAL          everything else             -> nothing at capture time; files already
                                                    in pending/ are still archived (records
                                                    are never deleted once captured)

"Human messages" = user entries with actual text — pure tool_result entries do not
count (the old gates counted every user-type entry, inflating the tally on
agent-heavy sessions; plan-mode and files-edited rules cover those).

Operates on the pending/archive session JSON shape that sync_claude_sessions.py writes
(lib/session_extract); archived captures from the retired SessionEnd hook share it.
Pure python — no chromadb, safe to import under any interpreter.
"""

import json
import re

EXPLICIT_REMEMBER = "explicit_remember"
MEMORY_WORTHY = "memory_worthy"
ARCHIVE_ONLY = "archive_only"
EPHEMERAL = "ephemeral"

# Tunable thresholds (kept as module constants so /rai sanity can assert on them)
MEMORY_WORTHY_MIN_HUMAN_MSGS = 4
MEMORY_WORTHY_MIN_FILES = 2
ARCHIVE_ONLY_MIN_HUMAN_MSGS = 2
ARCHIVE_ONLY_MIN_MINUTES = 10

# Native-transcript entrypoints that mean "not an interactive Rai session".
# Corpus survey 2026-07-03: only two values exist — "cli" (interactive) and
# "sdk-cli" (claude -p / SDK: 55% of all transcripts, all pipeline self-calls).
HEADLESS_ENTRYPOINTS = ("sdk-cli",)

# Remember-language, matched against USER text only. False positives are cheap
# (one extra distill); misses are not — keep the net wide but user-scoped.
_REMEMBER_RE = re.compile(
    r"(remember (this|that|it)|save this|add (this |that )?to memory|update (your )?memory"
    r"|don'?t forget|note this down"
    r"|تذكر|احفظ|لا تنسى)",
    re.IGNORECASE,
)


def message_text(entry: dict) -> str:
    """Plain text from a session-JSON message entry {type, message}."""
    m = entry.get("message")
    if isinstance(m, str):
        return m
    if isinstance(m, dict):
        c = m.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            return "\n".join(
                b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text"
            )
    return ""


# Harness-injected user entries (slash-command echoes, interrupts) — not human prompts.
_NON_HUMAN_PREFIXES = (
    "<local-command", "<command-name>", "<command-message>", "[Request interrupted",
    "<system-reminder>", "<task-notification", "Caveat: The messages below",
)


def _human_text(m: dict) -> str:
    """Real human prompt text of a user entry, '' when it's tool_result-only or
    harness-injected (command echoes count as user messages but aren't prompts)."""
    if m.get("type") != "user":
        return ""
    t = message_text(m).strip()
    if not t or t.startswith(_NON_HUMAN_PREFIXES):
        return ""
    return t


def human_msgs(session: dict) -> int:
    """User entries carrying real human text."""
    return sum(1 for m in session.get("messages", []) if _human_text(m))


def used_plan_mode(session: dict) -> bool:
    """Reliable signal = an ExitPlanMode/EnterPlanMode tool_use block (NOT a text match,
    which false-positives on transcripts that merely mention the tool name)."""
    for m in session.get("messages", []):
        msg = m.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("ExitPlanMode", "EnterPlanMode"):
                    return True
    return False


def files_edited(session: dict) -> int:
    """Distinct file paths edited. Prefers the captured metadata; derives from
    tool_use blocks when the field is absent (scanner-normalized sessions)."""
    files = session.get("files_modified")
    if isinstance(files, str):
        try:
            files = json.loads(files)
        except Exception:
            files = None
    if isinstance(files, list):
        return len(set(files))
    paths = set()
    for m in session.get("messages", []):
        msg = m.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("Edit", "Write", "NotebookEdit"):
                    fp = (b.get("input") or {}).get("file_path", "")
                    if fp:
                        paths.add(fp)
    return len(paths)


def has_tool_use(session: dict) -> bool:
    ts = session.get("tools_summary")
    if isinstance(ts, str):
        try:
            ts = json.loads(ts)
        except Exception:
            ts = None
    if isinstance(ts, dict) and ts:
        return True
    for m in session.get("messages", []):
        msg = m.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    return True
    return False


def asked_to_remember(session: dict) -> bool:
    for m in session.get("messages", []):
        t = _human_text(m)
        if t and _REMEMBER_RE.search(t):
            return True
    return False


def is_headless(session: dict) -> bool:
    """Pipeline self-call (claude -p / SDK), never an interactive Rai session.
    Sessions captured before the field existed have no entrypoint -> not headless."""
    return session.get("entrypoint") in HEADLESS_ENTRYPOINTS


def classify(session: dict) -> str:
    """First match wins, per the policy table."""
    # Headless BEFORE remember-language: -p prompts embed user transcripts, so the
    # regex matches quoted text and the pipeline re-ingests its own distill calls.
    if is_headless(session):
        return EPHEMERAL
    if asked_to_remember(session):
        return EXPLICIT_REMEMBER
    n = human_msgs(session)
    if (
        n >= MEMORY_WORTHY_MIN_HUMAN_MSGS
        or used_plan_mode(session)
        or files_edited(session) >= MEMORY_WORTHY_MIN_FILES
    ):
        return MEMORY_WORTHY
    duration = int(session.get("duration_minutes", 0) or 0)
    if ARCHIVE_ONLY_MIN_HUMAN_MSGS <= n and (has_tool_use(session) or duration >= ARCHIVE_ONLY_MIN_MINUTES):
        return ARCHIVE_ONLY
    return EPHEMERAL


def should_distill(cls: str) -> bool:
    return cls in (EXPLICIT_REMEMBER, MEMORY_WORTHY)


def should_episodic(cls: str) -> bool:
    return cls in (EXPLICIT_REMEMBER, MEMORY_WORTHY)


def should_archive(cls: str) -> bool:
    return cls != EPHEMERAL


if __name__ == "__main__":
    import sys
    from pathlib import Path

    for path in sys.argv[1:]:
        d = json.loads(Path(path).read_text())
        cls = classify(d)
        print(
            f"{Path(path).name}: {cls} "
            f"(human={human_msgs(d)}, plan={used_plan_mode(d)}, "
            f"files={files_edited(d)}, tools={has_tool_use(d)}, "
            f"mins={d.get('duration_minutes', 0)})"
        )
