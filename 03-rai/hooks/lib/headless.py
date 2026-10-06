"""
headless.py: is this hook running inside a `claude -p` run?

One copy of the check for every hook that must stay quiet in Rai's own plumbing
(news runs, maintenance, distill, observer calls). turn-capture.py skips capture there;
response-format-reminder.py skips the workflow line there.
"""

import os
import subprocess
from pathlib import Path


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
