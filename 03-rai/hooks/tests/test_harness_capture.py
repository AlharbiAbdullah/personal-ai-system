"""
test_harness_capture.py: the brain side every harness adapter relies on.

- The batch scanner reads Claude Code's projects, pi's shadow transcripts, and one folder
  per harness adapter under ~/.local/share/rai/transcripts/ (each optional).
- turn-capture's detached worker finds the `claude` binary through claude_cli.claude_bin(),
  so it still runs when a harness starts hooks with a PATH that lacks `claude`.

Hermetic: every scanner path points into tmp_path, and the worker's model call is stubbed.

Run: uv run --with pytest pytest 03-rai/hooks/tests/test_harness_capture.py -q -p no:cacheprovider
"""

import importlib.util
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))  # bind `lib` to THIS checkout


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# scanner roots ──────────────────────────────────────────────────────────────────
@pytest.fixture
def scs(tmp_path, monkeypatch):
    mod = _load("sync_claude_sessions_t", HOOKS / "scripts" / "sync_claude_sessions.py")
    projects = tmp_path / ".claude" / "projects"
    pi = tmp_path / ".pi" / "agent" / "rai-transcripts"
    shadows = tmp_path / ".local" / "share" / "rai" / "transcripts"
    monkeypatch.setattr(mod, "CLAUDE_PROJECTS", projects)
    monkeypatch.setattr(mod, "PI_TRANSCRIPTS", pi)
    monkeypatch.setattr(mod, "TRANSCRIPT_ROOTS", (projects, pi))
    monkeypatch.setattr(mod, "SHADOW_ROOT", shadows)
    monkeypatch.setattr(mod, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(mod, "PENDING", tmp_path / "pending")
    monkeypatch.setattr(mod, "ARCHIVE", tmp_path / "archive")
    return mod


def test_roots_add_each_adapter_folder(scs):
    scs.CLAUDE_PROJECTS.mkdir(parents=True)
    for h in ("opencode", "agy"):
        (scs.SHADOW_ROOT / h).mkdir(parents=True)
    (scs.SHADOW_ROOT / "stray.jsonl").write_text("{}\n")  # a file is never a root
    assert scs.transcript_roots() == [
        scs.CLAUDE_PROJECTS, scs.SHADOW_ROOT / "agy", scs.SHADOW_ROOT / "opencode"]


def test_roots_all_optional(scs):
    assert scs.transcript_roots() == []
    scs.PI_TRANSCRIPTS.mkdir(parents=True)
    assert scs.transcript_roots() == [scs.PI_TRANSCRIPTS]


def _shadow(root: Path, entrypoint: str) -> str:
    sid = str(uuid.uuid4())
    f = root / "-home-x" / f"{sid}.jsonl"
    f.parent.mkdir(parents=True)
    rec = {"type": "user", "sessionId": sid, "cwd": "/home/x", "entrypoint": entrypoint,
           "timestamp": "2026-10-02T10:00:00.000Z",
           "message": {"role": "user", "content": [{"type": "text", "text": "hello"}]}}
    f.write_text(json.dumps(rec) + "\n")
    old = time.time() - 3600  # quiescent
    os.utime(f, (old, old))
    return sid


def test_scan_reads_adapter_shadows(scs, monkeypatch, capsys):
    (scs.LEDGER).write_text('{"session_id": "seed"}\n')  # skip first-run seeding
    sid = _shadow(scs.SHADOW_ROOT / "agy", "sdk-cli")
    monkeypatch.setattr(sys, "argv", ["sync_claude_sessions.py"])
    assert scs.main() == 0
    out = capsys.readouterr().out
    assert f"ephemeral {sid[:8]}" in out and "'ephemeral': 1" in out
    ledger = scs.LEDGER.read_text()
    assert sid in ledger and "skipped-ephemeral" in ledger


# turn-capture worker ────────────────────────────────────────────────────────────
def test_worker_calls_claude_bin(monkeypatch):
    tc = _load("turn_capture_t", HOOKS / "turn-capture.py")
    monkeypatch.setenv("RAI_HARNESS", "agy")  # the observer's own claude call is Claude Code's
    import lib.claude_cli as cli
    monkeypatch.setattr(cli, "claude_bin", lambda: "/opt/test/claude")
    monkeypatch.setattr(cli, "effort_args", lambda level="high": [])
    monkeypatch.setattr(tc, "last_turn_text", lambda p: "x" * (tc.MIN_TURN_CHARS + 1))
    monkeypatch.setattr(tc, "sdd_root", lambda cwd: None)
    calls = []

    def fake_run(argv, **kw):
        calls.append((argv, kw))
        return subprocess.CompletedProcess(argv, 1, "", "")  # a failed call writes nothing

    monkeypatch.setattr(tc.subprocess, "run", fake_run)
    tc.capture("/nonexistent.jsonl", "00000000-0000-4000-8000-000000000000", "/tmp")
    assert calls and calls[0][0][0] == "/opt/test/claude"
    assert calls[0][1]["env"]["RAI_HEADLESS"] == "1"
    assert "RAI_HARNESS" not in calls[0][1]["env"]
    _assert_isolated(calls[0][0], calls[0][1])


def _assert_isolated(argv, kw):
    """A pipeline claude -p loads none of his setup: no user hooks, CLAUDE.md, memory or MCP, no
    saved transcript, run from a neutral folder (no project settings)."""
    assert argv[argv.index("--setting-sources") + 1] == "project"
    assert "--strict-mcp-config" in argv and "--no-session-persistence" in argv
    assert kw["env"]["CLAUDE_CODE_DISABLE_CLAUDE_MDS"] == "1"
    assert kw["env"]["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"
    assert kw["cwd"] and not (Path(kw["cwd"]) / ".claude").exists()


def test_run_claude_is_isolated(monkeypatch):
    import lib.claude_cli as cli
    seen = []

    def fake_run(argv, **kw):
        seen.append((argv, kw))
        return subprocess.CompletedProcess(argv, 0, "out", "")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli, "claude_bin", lambda: "/opt/test/claude")
    assert cli.run_claude("prompt", model="opus") == "out"
    _assert_isolated(*seen[0])


def test_shadow_root_follows_xdg_data_home(tmp_path, monkeypatch):
    """The adapters write under $XDG_DATA_HOME (default ~/.local/share); the scanner reads there."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    mod = _load("scs_xdg", HOOKS / "scripts" / "sync_claude_sessions.py")
    assert mod.SHADOW_ROOT == tmp_path / "rai" / "transcripts"
    monkeypatch.delenv("XDG_DATA_HOME")
    mod = _load("scs_noxdg", HOOKS / "scripts" / "sync_claude_sessions.py")
    assert mod.SHADOW_ROOT == Path.home() / ".local" / "share" / "rai" / "transcripts"


def test_hook_timer_tags_the_harness(tmp_path, monkeypatch):
    """Adapters set RAI_HARNESS; Claude Code sets nothing, so it is the default."""
    import lib.hook_timer as ht
    monkeypatch.setattr(ht, "PERF_LOG", tmp_path / "perf.jsonl")
    monkeypatch.setenv("RAI_HARNESS", "agy")
    with ht.hook_timer("x"):
        pass
    monkeypatch.delenv("RAI_HARNESS")
    with ht.hook_timer("y"):
        pass
    rows = [json.loads(l) for l in (tmp_path / "perf.jsonl").read_text().splitlines()]
    assert [(r["hook"], r["harness"]) for r in rows] == [("x", "agy"), ("y", "claude-code")]


def test_run_claude_can_see_his_setup_when_asked(monkeypatch):
    """The eval's /recall smoke needs his skills, settings and CLAUDE.md."""
    import lib.claude_cli as cli
    seen = []
    monkeypatch.setattr(cli.subprocess, "run", lambda argv, **kw: seen.append((argv, kw)) or subprocess.CompletedProcess(argv, 0, "out", ""))
    monkeypatch.setattr(cli, "claude_bin", lambda: "/opt/test/claude")
    cli.run_claude("/recall x", model="sonnet", cwd="/home/x/helm", isolate=False)
    argv, kw = seen[0]
    assert "--setting-sources" not in argv and kw["cwd"] == "/home/x/helm"
    assert "CLAUDE_CODE_DISABLE_CLAUDE_MDS" not in kw["env"] and kw["env"]["RAI_HEADLESS"] == "1"
