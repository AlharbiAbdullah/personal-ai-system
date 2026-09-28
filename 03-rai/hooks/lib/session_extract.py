#!/usr/bin/env python3
"""
session_extract.py — normalize a native Claude Code transcript (~/.claude/projects/
<slug>/<uuid>.jsonl) into the pending session-JSON shape Memory v3 consumes.

The batch scanner (scripts/sync_claude_sessions.py) and eval_sections.py call it. Pure
python, no chromadb.
"""

import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

from .transcript_parse import iter_assistant_tool_uses

CONTEXT_MAPPING_FILE = Path(__file__).resolve().parents[1] / "context_mapping.json"


def load_context_mapping() -> dict:
    if CONTEXT_MAPPING_FILE.exists():
        try:
            return json.loads(CONTEXT_MAPPING_FILE.read_text())
        except Exception:
            pass
    return {}


def detect_project_name(cwd: str) -> str:
    """Project name from .git remote, pyproject.toml, package.json, or folder."""
    cwd_path = Path(cwd)
    if (cwd_path / ".git").exists():
        try:
            result = subprocess.run(
                ["git", "-C", cwd, "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                m = re.search(r"/([^/]+?)(?:\.git)?$", result.stdout.strip())
                if m:
                    return m.group(1)
        except Exception:
            pass
    pyproject = cwd_path / "pyproject.toml"
    if pyproject.exists():
        try:
            m = re.search(r'^\s*name\s*=\s*["\']([^"\']+)["\']', pyproject.read_text(), re.MULTILINE)
            if m:
                return m.group(1)
        except Exception:
            pass
    package_json = cwd_path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())
            if data.get("name"):
                return data["name"]
        except Exception:
            pass
    return cwd_path.name


def apply_context_mapping(cwd: str) -> str:
    mapping = load_context_mapping()
    cwd_expanded = str(Path(cwd).expanduser().resolve())
    for pattern, context_name in mapping.items():
        pattern_expanded = str(Path(pattern).expanduser().resolve())
        if "*" in pattern_expanded:
            base_pattern = pattern_expanded.rstrip("/*")
            if cwd_expanded.startswith(base_pattern):
                return detect_project_name(cwd) if context_name == "auto-detect" else context_name
        if cwd_expanded == pattern_expanded or cwd_expanded.startswith(pattern_expanded + "/"):
            return detect_project_name(cwd) if context_name == "auto-detect" else context_name
    return detect_project_name(cwd)


def _iter_entries(transcript_path: Path):
    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def extract_tool_usage(transcript_path: Path) -> tuple[dict, list[str]]:
    """Tool counts + unique Edit/Write file paths."""
    tools_counter: Counter = Counter()
    files_modified: set[str] = set()
    for tool_use in iter_assistant_tool_uses(str(transcript_path)):
        name = tool_use.get("name", "")
        if name:
            tools_counter[name] += 1
        if name in ("Edit", "Write", "NotebookEdit"):
            fp = tool_use.get("input", {}).get("file_path", "")
            if fp:
                files_modified.add(fp)
    return dict(tools_counter), sorted(files_modified)


def normalize_transcript(transcript_path: Path, session_id: str = "") -> dict:
    """One pass over the native JSONL -> the pending session-JSON shape
    (session_id, timestamp, context, cwd, project metadata, messages[])."""
    messages, first_ts, last_ts, cwd, entrypoint = [], None, None, "", ""
    for entry in _iter_entries(transcript_path):
        if not cwd and entry.get("cwd"):
            cwd = entry["cwd"]
        if not entrypoint and entry.get("entrypoint"):
            entrypoint = entry["entrypoint"]
        ts = entry.get("timestamp")
        if ts:
            first_ts = first_ts or ts
            last_ts = ts
        if entry.get("type") in ("user", "assistant"):
            messages.append({"type": entry["type"], "message": entry.get("message", "")})
            if not session_id and entry.get("sessionId"):
                session_id = entry["sessionId"]

    duration = 0
    if first_ts and last_ts:
        try:
            first = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            last = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            duration = max(0, int((last - first).total_seconds() / 60))
        except Exception:
            pass

    tools_summary, files_modified = extract_tool_usage(transcript_path)
    return {
        "session_id": session_id or transcript_path.stem,
        "timestamp": first_ts or datetime.now().isoformat(),
        "context": apply_context_mapping(cwd) if cwd else "brainstorm",
        "transcript_path": str(transcript_path),
        "cwd": cwd,
        "entrypoint": entrypoint,  # "cli" interactive / "sdk-cli" headless (gate: ephemeral)
        "project_name": detect_project_name(cwd) if cwd else "unknown",
        "duration_minutes": duration,
        "tools_summary": tools_summary,
        "files_modified": files_modified,
        "messages": messages,
    }
