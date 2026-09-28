"""Config, Auto-memory and External: the harness contract parses, the ~/.claude edge resolves into
the vault, no link dangles, the auto-memory index loads whole, the status line runs."""

import json
import re
import shutil
import time
from pathlib import Path

from . import core
from .core import FAIL, PASS, PRODUCER, SKIP, WARN, P, check


def _user_mcp_servers() -> dict | None:
    """mcpServers from ~/.claude.json (user scope), or None when unreadable. Claude Code rewrites
    the file while it runs, so a parse error gets one retry."""
    for attempt in (0, 1):
        try:
            return json.loads((P.HOME / ".claude.json").read_text()).get("mcpServers") or {}
        except Exception:
            if attempt == 0:
                time.sleep(0.5)
    return None


@check("CFG-1", "Config")
def json_configs_valid():
    """The harness contract parses, and Context7 is registered at user scope in ~/.claude.json
    (dev-env claude-config.sh registers it with `claude mcp add --scope user`)."""
    targets = [P.DCLAUDE / "settings.json", P.RAI / "config/settings.json"]
    bad = []
    for p in targets:
        if not p.exists():
            bad.append(f"{p.name}:MISSING"); continue
        try:
            json.loads(p.read_text())
        except Exception as e:
            bad.append(f"{p.name}:{str(e)[:30]}")
    servers = _user_mcp_servers()
    if servers is None:
        bad.append("~/.claude.json:unreadable")
    elif not servers.get("context7"):
        bad.append("context7:not-registered")
    ev = f"{len(targets)} settings files checked, context7 at user scope"
    fix = ("Restore a broken settings.json from git history. Register Context7: claude mcp add "
           "--scope user context7 -- npx -y @upstash/context7-mcp@latest")
    return (FAIL, f"{bad}", fix) if bad else (PASS, ev, "")


@check("CFG-2", "Config")
def claude_symlinks():
    """The five ~/.claude links (agents, hooks, skills, CLAUDE.md, settings.json) resolve into 03-rai."""
    expect = {
        "agents": P.RAI / "agents", "hooks": P.RAI / "hooks", "skills": P.RAI / "skills",
        "CLAUDE.md": P.RAI / "AGENTS.md", "settings.json": P.RAI / "config/settings.json",
    }
    probs = []
    for name, want in expect.items():
        link = P.DCLAUDE / name
        if not link.exists():
            probs.append(f"{name}:missing"); continue
        try:
            if link.resolve() != want.resolve():
                probs.append(f"{name}:wrong->{link.resolve().name}")
        except Exception:
            probs.append(f"{name}:broken")
    ev = f"{len(expect)-len(probs)}/{len(expect)} resolve"
    return (FAIL, ev + f" {probs}", "ln -sfn ~/helm/03-rai/<target> ~/.claude/<name>.") if probs else (PASS, ev, "")


@check("CFG-3", "Config", slow=True)
def broken_symlinks():
    """No symlink inside helm dangles (typically a cross-machine path left behind)."""
    bad = []
    for p in P.HELM.rglob("*"):
        s = str(p)
        if "/.git" in s or "/chromadb" in s or "/node_modules" in s:
            continue
        if p.is_symlink() and not p.exists():
            bad.append(p.name)
            if len(bad) > 10:
                break
    ev = f"{len(bad)} dangling"
    if len(bad) > 3:
        return FAIL, ev + f" {bad[:5]}", "Widespread broken links — investigate."
    if bad:
        return WARN, ev + f" {bad}", "Delete dangling links (often cross-machine paths)."
    return PASS, ev, ""


# ════════════════════════════════════════════════════════════════════════════════
# AUTO-MEMORY
# ════════════════════════════════════════════════════════════════════════════════
MEMORY_CUT = 200     # the loader drops MEMORY.md past this line
MEMORY_WARN = 150


def claude_project_dir(path) -> Path:
    """Claude Code keys per-project state by the absolute path with every character that is not
    a letter or digit turned into '-': /home/john/helm -> -home-john-helm."""
    return P.DCLAUDE / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(path))


@check("MEM-1", "Auto-memory")
def memory_md():
    """Helm's own auto-memory: the Claude Code slot is mounted from 03-rai/auto-memory, the index
    stays under the loader's cut, and every index link resolves."""
    store = P.RAI / "auto-memory"
    idx = store / "MEMORY.md"
    if not store.exists():
        return SKIP, "no 03-rai/auto-memory store in this vault (optional)", ""
    if not idx.exists():
        return FAIL, "03-rai/auto-memory/MEMORY.md missing", "Restore the vault store from git."
    # Before 2026-09-26 this read the FIRST MEMORY.md under ~/.claude/projects, which was the
    # home-dir project's 13-line index: helm's own was never checked.
    mount = core.link_state(claude_project_dir(P.HELM) / "memory", store)
    txt = idx.read_text()
    lines = len(txt.splitlines())
    refs = re.findall(r"\]\(([^)]+\.md)\)", txt)
    missing = [r for r in refs if not (store / r).exists()]
    ev = f"{lines}/{MEMORY_CUT} lines, {len(refs)} refs, {len(missing)} missing, mount {mount}"
    if lines > MEMORY_CUT or missing:
        return FAIL, ev, "Past line 200 is truncated by the loader; fix missing refs."
    if mount != "ok":
        fix = ("Claude Code reads and writes memories outside the vault: link "
               "~/.claude/projects/<helm slug>/memory -> ~/helm/03-rai/auto-memory (dev-env claude-config.sh).")
        return (FAIL if core.detect_role() == PRODUCER else WARN), ev, fix
    if lines > MEMORY_WARN:
        return WARN, ev, "Approaching the 200-line truncation limit: fold resolved lines into their notes."
    return PASS, ev, ""


# ════════════════════════════════════════════════════════════════════════════════
# EXTERNAL
# ════════════════════════════════════════════════════════════════════════════════
@check("EXT-1", "External")
def statusline_resolves():
    """settings.json `statusLine` runs the claude-hud plugin with node: the plugin's
    dist/index.js must be installed and node must be on PATH."""
    try:
        cmd = (json.loads((P.RAI / "config/settings.json").read_text()).get("statusLine") or {}).get("command", "")
    except Exception as e:
        return FAIL, f"settings.json unreadable: {str(e)[:30]}", "Restore settings.json from git history."
    if "claude-hud" not in cmd:
        return WARN, "statusLine does not run claude-hud", "Point statusLine back at the claude-hud plugin."
    probs = []
    entries = list((P.DCLAUDE / "plugins/cache/claude-hud/claude-hud").glob("*/dist/index.js"))
    if not entries:
        probs.append("claude-hud:not-installed")
    if not shutil.which("node"):
        probs.append("node:not-on-PATH")
    if probs:
        return FAIL, f"{probs}", "Reinstall the claude-hud plugin (/plugin) and make node resolvable (mise)."
    newest = max(entries, key=lambda p: [int(x) if x.isdigit() else 0 for x in p.parents[1].name.split(".")])
    return PASS, f"claude-hud {newest.parents[1].name}, node on PATH", ""
