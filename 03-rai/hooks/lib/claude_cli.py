#!/usr/bin/env python3
"""
claude_cli.py — single owner of headless `claude -p` invocation for Rai pipeline code.

Owns: binary resolution, model + effort args (flag support detected once, cached),
RAI_HEADLESS env (belt to session_gate's sdk-cli suspender — the memory system must
never ingest its own plumbing), stdin piping, timeout.

Used by: the eval harness judge (skills/rai/scripts/eval.py), the distill chunk-reduce
(distill_session.py), and turn-capture.py (claude_bin and effort_args — its call stays its own).
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from .paths import get_runtime_dir

FLAG_CACHE = get_runtime_dir() / "claude-cli-flags.json"


# A pipeline call is a machine call with a self-contained prompt. It loads none of his setup:
# no user hooks or settings, no CLAUDE.md (which imports the whole identity), no auto-memory,
# no MCP servers, no saved transcript, and no project settings (a neutral folder).
ISOLATION_ARGS = ["--setting-sources", "project", "--strict-mcp-config", "--no-session-persistence"]
ISOLATION_ENV = {"RAI_HEADLESS": "1", "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}


def isolated_env() -> dict:
    env = {**os.environ, **ISOLATION_ENV}
    env.pop("RAI_HARNESS", None)  # its hooks would run in Claude Code, whichever harness asked
    return env


def neutral_cwd() -> str:
    d = get_runtime_dir() / "claude-p"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def claude_bin() -> str:
    return shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")


def effort_args(level: str = "high") -> list:
    """`["--effort", level]` when the installed CLI supports the flag, else [].

    Support is detected once per binary path and cached (a dot-state file, not memory).
    """
    bin_path = claude_bin()
    try:
        cached = json.loads(FLAG_CACHE.read_text())
        if cached.get("bin") == bin_path:
            return ["--effort", level] if cached.get("has_effort") else []
    except Exception:
        pass
    has_effort = False
    try:
        help_text = subprocess.run(
            [bin_path, "--help"], capture_output=True, text=True, timeout=15
        ).stdout
        has_effort = "--effort" in help_text
    except Exception:
        pass
    try:
        FLAG_CACHE.parent.mkdir(parents=True, exist_ok=True)
        FLAG_CACHE.write_text(json.dumps({"bin": bin_path, "has_effort": has_effort}))
    except Exception:
        pass
    return ["--effort", level] if has_effort else []


def run_claude(prompt: str, model: str = "opus", timeout: int = 300,
               effort: str = None, cwd: str = None, isolate: bool = True) -> str:
    """Run `claude -p` headless, prompt on stdin; return stdout.

    `effort=None` keeps the CLI default; pass "high"/"xhigh" to raise it.
    The call is isolated (ISOLATION_ARGS, isolated_env); `cwd` defaults to a neutral folder.
    `isolate=False` is for a call that must see his real setup (the eval's /recall smokes):
    his settings, skills, CLAUDE.md and hooks, from `cwd`.
    Raises subprocess.TimeoutExpired or CalledProcessError — callers decide retry policy.
    """
    extra = effort_args(effort) if effort else []
    if isolate:
        argv, env, cwd = [claude_bin(), "-p", "--model", model, *extra, *ISOLATION_ARGS], isolated_env(), cwd or neutral_cwd()
    else:
        argv, env = [claude_bin(), "-p", "--model", model, *extra], dict(os.environ, RAI_HEADLESS="1")
    r = subprocess.run(argv, input=prompt, capture_output=True, text=True, timeout=timeout, env=env, cwd=cwd)
    if r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, "claude -p", r.stdout, r.stderr)
    return r.stdout
