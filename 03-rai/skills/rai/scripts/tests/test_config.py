"""Config, Auto-memory and External checks."""

import re


from conftest import st
from sanity_checks.core import FAIL, PASS, SKIP, WARN

EDGE = {"agents": "agents", "hooks": "hooks", "skills": "skills", "CLAUDE.md": "AGENTS.md",
        "settings.json": "config/settings.json"}


def _edge(w):
    for rel in ("agents", "hooks", "skills"):
        w.mkdir(f"helm/03-rai/{rel}")
    w.write("helm/03-rai/AGENTS.md", "# Rai")
    w.settings({})
    for name, target in EDGE.items():
        w.link(f".claude/{name}", w.rai / target)


# CFG-1 ─────────────────────────────────────────────────────────────────────────
def _mcp(w, servers):
    w.json(".claude.json", {"mcpServers": servers})


def test_cfg_1_ok(w):
    _edge(w)
    _mcp(w, {"context7": {"command": "npx"}})
    assert st("CFG-1").status == PASS


def test_cfg_1_fault_context7_unregistered(w):
    _edge(w)
    _mcp(w, {})
    r = st("CFG-1")
    assert r.status == FAIL and "context7:not-registered" in r.evidence


def test_cfg_1_fault_settings_broken(w):
    _edge(w)
    _mcp(w, {"context7": {}})
    w.write("helm/03-rai/config/settings.json", "{not json")
    assert st("CFG-1").status == FAIL


# CFG-2 ─────────────────────────────────────────────────────────────────────────
def test_cfg_2_ok(w):
    _edge(w)
    assert st("CFG-2").status == PASS


def test_cfg_2_fault_wrong_target(w):
    _edge(w)
    w.write("elsewhere/CLAUDE.md", "stale copy")
    w.link(".claude/CLAUDE.md", w.path("elsewhere/CLAUDE.md"))
    r = st("CFG-2")
    assert r.status == FAIL and "CLAUDE.md:wrong" in r.evidence


def test_cfg_2_fault_missing(w):
    _edge(w)
    w.path(".claude/hooks").unlink()
    assert st("CFG-2").status == FAIL


# CFG-3 ─────────────────────────────────────────────────────────────────────────
def test_cfg_3_ok(w):
    w.write("helm/real.md", "x")
    w.link("helm/alias.md", w.helm / "real.md")
    assert st("CFG-3").status == PASS


def test_cfg_3_fault_dangling(w):
    w.link("helm/stale.md", "/Users/someone/helm/gone.md")
    assert st("CFG-3").status == WARN


def test_cfg_3_fault_widespread(w):
    for i in range(4):
        w.link(f"helm/stale{i}.md", f"/nowhere/{i}")
    assert st("CFG-3").status == FAIL


# MEM-1: helm's own auto-memory, mounted from the vault ──────────────────────────
def _slug(w):
    return re.sub(r"[^A-Za-z0-9]", "-", str(w.helm))


def _memory(w, lines=5, mount=True, dead_ref=False):
    notes = [f"n{i}.md" for i in range(3)]
    for n in notes:
        w.write(f"helm/03-rai/auto-memory/{n}", "---\nname: n\n---\n")
    idx = ["# Memory Index", ""] + [f"- [N](n{i % 3}.md) — hook" for i in range(lines - 2)]
    if dead_ref:
        idx.append("- [Gone](gone.md) — deleted note")
    w.write("helm/03-rai/auto-memory/MEMORY.md", "\n".join(idx) + "\n")
    if mount:
        w.link(f".claude/projects/{_slug(w)}/memory", w.rai / "auto-memory")


def test_mem_1_ok(w):
    _memory(w)
    r = st("MEM-1")
    assert r.status == PASS, r.evidence


def test_mem_1_fault_reads_the_wrong_project(w):
    """The original bug: the first MEMORY.md under ~/.claude/projects won, so a small index in some
    other project hid helm's over-limit one."""
    _memory(w, lines=210)
    for i in range(8):  # created after helm's, so a directory scan meets them first on tmpfs
        w.write(f".claude/projects/-home-x-proj{i}/memory/MEMORY.md", "- [a](a.md)\n")
        w.write(f".claude/projects/-home-x-proj{i}/memory/a.md", "x")
    r = st("MEM-1")
    assert r.status == FAIL and "210" in r.evidence


def test_mem_1_fault_near_the_cut(w):
    _memory(w, lines=160)
    assert st("MEM-1").status == WARN


def test_mem_1_fault_dead_ref(w):
    _memory(w, dead_ref=True)
    assert st("MEM-1").status == FAIL


def test_mem_1_fault_not_mounted(w):
    _memory(w, mount=False)
    w.write(f".claude/projects/{_slug(w)}/memory/MEMORY.md", "- local notes outside git\n")
    r = st("MEM-1")
    assert r.status == FAIL and "mount" in r.evidence


def test_mem_1_fault_not_mounted_consumer_warns(w, monkeypatch):
    monkeypatch.setenv("RAI_ROLE", "consumer")
    _memory(w, mount=False)
    assert st("MEM-1", role="consumer").status == WARN


def test_mem_1_fault_store_missing(w):
    w.write("helm/03-rai/auto-memory/.keep", "")
    assert st("MEM-1").status == FAIL


def test_mem_1_skip_no_store(w):
    assert st("MEM-1").status == SKIP


# EXT-1 ─────────────────────────────────────────────────────────────────────────
HUD = ".claude/plugins/cache/claude-hud/claude-hud/0.8.0/dist/index.js"


def _statusline(w, cmd="node ~/.claude/plugins/cache/claude-hud/x/dist/index.js"):
    w.settings({}, extra={"statusLine": {"type": "command", "command": cmd}})


def test_ext_1_ok(w, monkeypatch):
    import sanity_checks.config as cfg
    monkeypatch.setattr(cfg.shutil, "which", lambda n: "/usr/bin/node")
    _statusline(w)
    w.write(HUD, "")
    assert st("EXT-1").status == PASS


def test_ext_1_fault_not_claude_hud(w):
    _statusline(w, cmd="bash statusline.sh")
    assert st("EXT-1").status == WARN


def test_ext_1_fault_plugin_missing(w, monkeypatch):
    import sanity_checks.config as cfg
    monkeypatch.setattr(cfg.shutil, "which", lambda n: "/usr/bin/node")
    _statusline(w)
    assert st("EXT-1").status == FAIL


def test_ext_1_fault_no_node(w, monkeypatch):
    import sanity_checks.config as cfg
    monkeypatch.setattr(cfg.shutil, "which", lambda n: None)
    _statusline(w)
    w.write(HUD, "")
    r = st("EXT-1")
    assert r.status == FAIL and "node" in r.evidence
