#!/usr/bin/env python3
"""
turn-capture.py — Stop hook (Memory v3, Phase B). LIVE capture layer.

After each completed turn in an INTERACTIVE session, has Sonnet at high effort
(subscription, `claude -p --model sonnet`, CAPTURE_MODEL) write 2-10 third-person observer
bullets about the exchange and appends them to semantic-memory/daily/YYYY-MM-DD.md under a
`### HH:MM (session:xxxxxxxx)` heading. MemSearch's capture pattern, Rai-native.

This deliberately reverses Memory v2's batch-only invariant (John's call,
2026-07-03; see 03-rai/MEMORY-ARCHITECTURE.md). The narrower rule it obeys:
live writes append to TEXT only; ChromaDB indexing of these logs stays with the
batch coordinator (index_daily.py).

Guardrails (all of them, always):
- recursion guard  : stop_hook_active payload flag + RAI_HEADLESS env on own claude calls
- headless skip    : any ancestor `claude -p/--print` process (news runs, maintenance,
                     distill, this hook's own model call) -> no capture
- debounce         : >=60s between captures per session (state-file mtime)
- min length       : turns under 300 chars of real text -> no capture
- non-blocking     : parent re-spawns itself detached (--capture) and exits immediately
- fail-open        : every failure path exits 0 silently; errors -> hook-errors.jsonl
- repo rule (H27)  : a turn whose cwd sits in a project-init repo (`.project.toml`, see
                     lib/sdd_repo.py) keeps only preferences John states himself,
                     cross-project lessons and one "worked in <repo>: <what>" pointer bullet,
                     written by the session's first captured block only (the daily log is
                     the ledger); bullets naming a repo scenario ID or file path are dropped

The parent dispatch logs to hook-perf as "turn-capture" (proof of firing); the
detached worker logs as "turn-capture-bg" with the real duration.
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.daily_log import blocks_for_session
from lib.hook_errors import log_error
from lib.hook_timer import hook_timer
from lib.paths import get_runtime_dir
from lib.sdd_repo import (
    POINTER_RE,
    has_pointer,
    leak_check,
    pointer_line,
    repo_name,
    routing_rule,
    sdd_root,
)

DAILY_DIR = Path.home() / "helm" / "03-rai" / "semantic-memory" / "daily"
DEBOUNCE_DIR = get_runtime_dir() / "turn-capture"
DEBOUNCE_SECONDS = 60
MIN_TURN_CHARS = 300
MAX_TURN_CHARS = 8000
CLAUDE_TIMEOUT = 180  # thinking headroom for Sonnet at high effort
# Sonnet at high effort (John's call 2026-07-03, M4): the baseline eval measured 7
# hallucinated bullets across 10 sampled turns on the smaller model.
CAPTURE_MODEL = "sonnet"

OBSERVER_PROMPT = """You are an external observer writing memory notes about ONE exchange in John's AI-assistant (Rai) session. Read the exchange below. Output 2-10 terse third-person bullets capturing what is durable: decisions WITH their why, state changes (built / fixed / changed / broken / blocked), discoveries, standing rules John establishes, and open threads. Keep names, numbers, and file paths verbatim. Claim ONLY what the exchange actually shows — never embellish or infer beyond the text. No preamble, no headers — only lines starting with "- ". If the exchange contains nothing durable (small talk, pure navigation, tool noise), output exactly: SKIP
"""


def build_prompt(turn: str, repo: str = "") -> str:
    """Observer prompt for one exchange. A turn inside a project-init repo (H27) gets the
    routing addendum; every other turn gets today's prompt, byte for byte."""
    addendum = (f"\n{routing_rule(repo)} This rule replaces the list above, including its"
                f' 2-bullet minimum: put the pointer first, as "- worked in {repo}: ...", and for'
                " an exchange that finished work a lone pointer bullet is a complete answer. Repo"
                " facts are not durable here: when the exchange finished no work (only questions,"
                " diagnosis, plans or reading) and nothing else qualifies to keep, output exactly:"
                " SKIP\n") if repo else ""
    return OBSERVER_PROMPT + addendum + "\nEXCHANGE:\n" + turn


def pointer_written(session_id: str, repo: str) -> bool:
    """True when an earlier daily-log block of this session already holds the repo's
    pointer (H27: one pointer per session, not one per captured turn)."""
    try:
        return any(has_pointer(text, repo)
                   for _, _, text in blocks_for_session(session_id, DAILY_DIR))
    except (OSError, ValueError):  # unreadable or undecodable daily file
        return False  # fail-open: a second pointer beats a lost one


def route_bullets(bullets: list[str], repo: str, pointer_done: bool = False,
                  leaks=None) -> list[str]:
    """H27 guard on a project-init turn's bullets: the model's kept bullets minus any that
    `leaks` flags (a repo scenario ID or file path), led by one pointer bullet (the model's
    own, re-stamped with the repo name) unless this session already wrote it. May return []
    (nothing left to append)."""
    pointers = [b for b in bullets if POINTER_RE.match(b)]
    rest = [b for b in bullets if not POINTER_RE.match(b) and not (leaks and leaks(b))][:9]
    if pointer_done:
        return rest
    return ["- " + pointer_line(repo, pointers[0] if pointers else "", leaks)] + rest


def _proc_cmdline(pid: int) -> list[str]:
    """Command tokens for a pid. /proc on Linux, ps fallback on macOS."""
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return [t for t in raw.decode(errors="replace").split("\0") if t]
    except OSError:
        try:
            out = subprocess.run(
                ["ps", "-o", "command=", "-p", str(pid)],
                capture_output=True, text=True, timeout=2,
            ).stdout.strip()
            return out.split() if out else []
        except Exception:
            return []


def _proc_ppid(pid: int) -> int:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        return int(stat.rsplit(")", 1)[1].split()[1])
    except OSError:
        try:
            out = subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(pid)],
                capture_output=True, text=True, timeout=2,
            ).stdout.strip()
            return int(out) if out else 0
        except Exception:
            return 0


def invoked_from_headless() -> bool:
    """True when this hook fired inside a `claude -p` run (never capture those:
    they are Rai's own plumbing — news, maintenance, distill, observer calls)."""
    if os.environ.get("RAI_HEADLESS"):
        return True
    pid = os.getppid()
    for _ in range(8):
        if pid <= 1:
            return False
        tokens = _proc_cmdline(pid)
        if tokens and "claude" in Path(tokens[0]).name.lower() or any(
            Path(t).name.lower() == "claude" for t in tokens[:2]
        ):
            if "-p" in tokens or "--print" in tokens:
                return True
            return False  # the owning claude is interactive — capture
        pid = _proc_ppid(pid)
    return False


def message_text(entry: dict) -> str:
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


def last_turn_text(transcript_path: Path) -> str:
    """USER + ASSISTANT text of the final exchange (from the last real user
    message to the end of the transcript)."""
    entries = []
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("type") in ("user", "assistant"):
                    entries.append(e)
    except OSError:
        return ""

    last_user = None
    for i in range(len(entries) - 1, -1, -1):
        if entries[i].get("type") == "user" and message_text(entries[i]).strip():
            last_user = i
            break
    if last_user is None:
        return ""

    parts = []
    for e in entries[last_user:]:
        t = message_text(e).strip()
        if t:
            parts.append(f"{e.get('type', '').upper()}: {t}")
    turn = "\n\n".join(parts)
    if len(turn) > MAX_TURN_CHARS:
        turn = turn[:MAX_TURN_CHARS // 2] + "\n[...]\n" + turn[-MAX_TURN_CHARS // 2:]
    return turn


def debounced(session_id: str) -> bool:
    """True if a SUCCESSFUL capture ran for this session within DEBOUNCE_SECONDS.
    Read-only — the stamp is touched by the worker only after it actually appends
    bullets, so a skipped thin turn can never suppress the next substantial one."""
    stamp = DEBOUNCE_DIR / session_id
    try:
        return stamp.exists() and (time.time() - stamp.stat().st_mtime) < DEBOUNCE_SECONDS
    except OSError:
        return False


def mark_captured(session_id: str):
    try:
        DEBOUNCE_DIR.mkdir(parents=True, exist_ok=True)
        (DEBOUNCE_DIR / session_id).touch()
    except OSError:
        pass


def capture(transcript_path: str, session_id: str, cwd: str = ""):
    """The detached worker: summarize the last turn, append to the daily log."""
    turn = last_turn_text(Path(transcript_path))
    if len(turn) < MIN_TURN_CHARS:
        return
    root = sdd_root(cwd)  # H27: None outside a project-init repo -> today's behaviour
    repo = repo_name(root) if root else ""

    env = dict(os.environ, RAI_HEADLESS="1")  # our own claude call must never capture itself
    try:
        from lib.claude_cli import effort_args  # detection lives in the lib (M4)
        extra = effort_args("high")
    except Exception:
        extra = []
    try:
        r = subprocess.run(
            ["claude", "-p", "--model", CAPTURE_MODEL, *extra],
            input=build_prompt(turn, repo),
            capture_output=True, text=True, timeout=CLAUDE_TIMEOUT, env=env,
        )
    except subprocess.TimeoutExpired:
        return
    if r.returncode != 0:
        return

    out = r.stdout.strip()
    if not out or out.upper().startswith("SKIP"):
        return
    bullets = [l.rstrip() for l in out.splitlines() if re.match(r"^\s*-\s+\S", l)][:10]
    if not bullets:
        return
    if repo:
        bullets = route_bullets(bullets, repo, pointer_written(session_id, repo),
                                leak_check(root))
        if not bullets:
            return

    now = datetime.now()
    day_file = DAILY_DIR / f"{now.strftime('%Y-%m-%d')}.md"
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    header = "" if day_file.exists() else f"# Daily log — {now.strftime('%Y-%m-%d')}\n"
    block = (
        f"{header}\n### {now.strftime('%H:%M')} (session:{session_id[:8]})\n"
        + "\n".join(bullets) + "\n"
    )
    # single O_APPEND write — atomic enough for concurrent sessions
    with open(day_file, "a") as f:
        f.write(block)
    mark_captured(session_id)  # debounce arms only on a real append


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        return
    if data.get("stop_hook_active"):
        return
    session_id = data.get("session_id", "")
    transcript_path = data.get("transcript_path", "")
    if not session_id or not transcript_path or not Path(transcript_path).exists():
        return
    if invoked_from_headless():
        return
    if debounced(session_id):
        return
    cwd = data.get("cwd") or os.getcwd()  # the repo rule (H27) keys on where the turn ran

    # hand off to a detached worker so the turn never waits on the model call
    subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--capture", transcript_path, session_id, cwd],
        start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--capture":
        with hook_timer("turn-capture-bg"):
            try:
                capture(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
            except Exception as e:
                log_error("turn-capture", e, "worker")
    else:
        with hook_timer("turn-capture"):
            try:
                main()
            except Exception as e:
                log_error("turn-capture", e, "dispatch")
