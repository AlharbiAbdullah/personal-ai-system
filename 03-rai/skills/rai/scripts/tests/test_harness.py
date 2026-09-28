"""Harness edges (pi, OpenCode, the dev-env bootstrap) and the code-parse checks."""

import re

import pytest

from conftest import hook_cmd, st
from sanity_checks import core
from sanity_checks.core import FAIL, PASS, SKIP, WARN
from sanity_checks.harness import PI_EDGES

SETTINGS_HOOKS = ["session-start", "memory-injection", "turn-capture", "set-question-tab", "question-answered"]
BRIDGE = "helm/03-rai/harness/pi/rai-bridge.ts"


def _pi(w, skip=None):
    for rel, target in PI_EDGES.items():
        w.write(f"helm/{target}", "x") if not target.endswith("skills") else w.mkdir(f"helm/{target}")
        if rel != skip:
            w.link(rel, w.helm / target)


# HARN-1 ────────────────────────────────────────────────────────────────────────
def test_harn_1_ok(w):
    _pi(w)
    assert st("HARN-1").status == PASS


def test_harn_1_skips_without_pi(w):
    assert st("HARN-1").status == SKIP


def test_harn_1_fault_edge_missing(w):
    _pi(w, skip=".agents/skills")
    r = st("HARN-1")
    assert r.status == FAIL and ".agents/skills: missing" in r.evidence


def test_harn_1_fault_edge_points_outside_vault(w):
    _pi(w)
    w.write("old/CLAUDE.md", "stale")
    w.link(".pi/agent/AGENTS.md", w.path("old/CLAUDE.md"))
    assert st("HARN-1").status == FAIL


# HARN-2 ────────────────────────────────────────────────────────────────────────
def _bridge(w, hooks):
    calls = "\n".join(f'await runHook("{h}.py", base, opts);' for h in hooks)
    w.write(BRIDGE, "/* session_start -> session-start.py (comment, not a call) */\n" + calls)
    w.settings({"Stop": [hook_cmd(w, h) for h in SETTINGS_HOOKS]})


def test_harn_2_ok(w):
    _bridge(w, ["session-start", "memory-injection", "turn-capture"])
    assert st("HARN-2").status == PASS


def test_harn_2_fault_new_hook_not_bridged(w):
    _bridge(w, ["session-start", "memory-injection"])
    r = st("HARN-2")
    assert r.status == WARN and "bridge lacks ['turn-capture']" in r.evidence


def test_harn_2_fault_bridge_calls_retired_hook(w):
    _bridge(w, ["session-start", "memory-injection", "turn-capture", "save-memory"])
    r = st("HARN-2")
    assert r.status == WARN and "save-memory" in r.evidence


def test_harn_2_fault_bridge_missing(w):
    w.write(".pi/agent/.keep", "")
    w.settings({"Stop": [hook_cmd(w, "turn-capture")]})
    assert st("HARN-2").status == FAIL


def test_harn_2_skip_no_pi(w):
    w.settings({"Stop": [hook_cmd(w, "turn-capture")]})
    assert st("HARN-2").status == SKIP


# HARN-3 ────────────────────────────────────────────────────────────────────────
def _slug(w):
    return re.sub(r"[^A-Za-z0-9]", "-", str(w.helm))


BOOT = """#!/usr/bin/env bash
CLAUDE="$HOME/.claude"
RAI="$HOME/helm/03-rai"
link_skills() {{ ln -sfn "$RAI/skills" "$1"; }}
ln -sfn "$RAI/agents"                 "$CLAUDE/agents"
ln -sfn "$RAI/hooks"                  "$CLAUDE/hooks"
link_skills "$CLAUDE/skills"
ln -sfn "$RAI/{claude_md}"              "$CLAUDE/CLAUDE.md"
ln -sfn "$RAI/config/settings.json"   "$CLAUDE/settings.json"
MEM="$CLAUDE/projects/{slug}/memory"
ln -sfn "$RAI/auto-memory" "$MEM"
ln -sfn "$RAI/AGENTS.md"                "$HOME/.pi/agent/AGENTS.md"
ln -sfn "$RAI/harness/pi/rai-bridge.ts" "$HOME/.pi/agent/extensions/rai-bridge.ts"
link_skills "$HOME/.agents/skills"
"""


def _vault_targets(w):
    for rel in ("agents", "hooks", "skills", "auto-memory"):
        w.mkdir(f"helm/03-rai/{rel}")
    for rel in ("AGENTS.md", "config/settings.json", "harness/pi/rai-bridge.ts", "identity/a.md"):
        w.write(f"helm/03-rai/{rel}", "x")


def _boot(w, claude_md="AGENTS.md", drop=None):
    text = BOOT.format(claude_md=claude_md, slug=_slug(w))
    if drop:
        text = "\n".join(l for l in text.splitlines() if drop not in l)
    w.write("dev-env/linux/omarchy/claude-config.sh", text)


def _opencode(w, entries):
    body = ",\n".join(f'    "{e}"' for e in entries)
    w.write(".config/opencode/opencode.jsonc", '{\n  // comment with a url https://x.y\n  "instructions": [\n' + body + "\n  ]\n}\n")


def test_harn_3_ok(w):
    _vault_targets(w)
    _boot(w)
    _opencode(w, [f"{w.rai}/identity/*.md", "~/helm/03-rai/AGENTS.md"])
    r = st("HARN-3")
    assert r.status == PASS, r.evidence


def test_harn_3_skips_without_edges(w):
    assert st("HARN-3").status == SKIP


def test_harn_3_fault_bootstrap_links_deleted_file(w):
    """CRITIC-01: after the AGENTS.md rename the bootstrap still linked $RAI/CLAUDE.md."""
    _vault_targets(w)
    _boot(w, claude_md="CLAUDE.md")
    r = st("HARN-3")
    assert r.status == WARN and "03-rai/CLAUDE.md" in r.evidence


def test_harn_3_fault_bootstrap_drops_an_edge(w):
    _vault_targets(w)
    _boot(w, drop='"$MEM"')
    r = st("HARN-3")
    assert r.status == WARN and "would not recreate" in r.evidence


def test_harn_3_fault_bootstrap_unparseable(w):
    _vault_targets(w)
    w.write("dev-env/linux/omarchy/claude-config.sh", "#!/bin/sh\ncp -r stuff ~/.claude\n")
    r = st("HARN-3")
    assert r.status == WARN and "blind" in r.evidence


def test_harn_3_skips_linux_bootstrap_on_the_mac(w, monkeypatch):
    import sanity_checks.harness as h
    monkeypatch.setattr(h.sys, "platform", "darwin")
    _vault_targets(w)
    _boot(w, claude_md="CLAUDE.md")  # broken, but not the Mac's bootstrap
    assert st("HARN-3").status == SKIP


def test_harn_3_fault_opencode_glob_dead(w):
    _vault_targets(w)
    _opencode(w, [f"{w.helm}/05-rai/identity/*.md"])
    r = st("HARN-3")
    assert r.status == WARN and "05-rai" in r.evidence


# CODE-1 and the dual-interpreter parse behind HOOK-3 / PIPE-2 ──────────────────
def test_code_1_ok(w):
    w.write("helm/02-ana/financial/investment/paper-portfolio/portfolio.py", "x = 1\n")
    w.write("helm/03-rai/skills/rai/scheduled/run.sh", "#!/bin/bash\nif true; then echo ok; fi\n")
    w.write("helm/13-archive/old/broken.py", "def f(:\n")          # the archive never runs
    w.write("helm/proj/.venv/lib/site.py", "def f(:\n")           # nor does a virtualenv
    assert st("CODE-1").status == PASS


def test_code_1_fault_python_syntax(w):
    w.write("helm/03-rai/skills/news-digest/_collect.py", "def f(:\n")
    r = st("CODE-1")
    assert r.status == FAIL and "_collect.py" in r.evidence


def test_code_1_fault_shell_syntax(w):
    w.write("helm/03-rai/skills/rai/scheduled/run.sh", "#!/bin/bash\nif true; then echo ok\n")
    r = st("CODE-1")
    assert r.status == FAIL and "run.sh" in r.evidence


@pytest.fixture
def fake_system_python(w, monkeypatch):
    """A system python3 that rejects every file, standing in for a version-only syntax break."""
    fake = w.write("bin/python3", "#!/bin/sh\necho '[\"/x/turn-capture.py:1\"]'\n", mode=0o755)
    monkeypatch.setattr(core, "SYSTEM_PYTHON", str(fake))


def test_hook_3_fault_breaks_only_under_system_python(w, fake_system_python):
    w.write("helm/03-rai/hooks/turn-capture.py", "x = 1\n")
    r = st("HOOK-3")
    assert r.status == FAIL and "turn-capture (python3)" in r.evidence


def test_pipe_2_fault_breaks_only_under_system_python(w, fake_system_python):
    from sanity_checks.pipeline import REQUIRED_SCRIPTS
    for n in REQUIRED_SCRIPTS:
        w.write(f"helm/03-rai/hooks/scripts/{n}.py", "x = 1\n")
    r = st("PIPE-2")
    assert r.status == FAIL and "(python3)" in r.evidence


def test_code_1_fault_system_python_missing(w, monkeypatch):
    monkeypatch.setattr(core, "SYSTEM_PYTHON", str(w.path("nope/python3")))
    w.write("helm/03-rai/skills/x/y.py", "x = 1\n")
    with pytest.raises(FileNotFoundError):
        core.compile_with(core.SYSTEM_PYTHON, [w.path("helm/03-rai/skills/x/y.py")])
    assert st("CODE-1").status == FAIL  # the runner turns the raise into a FAIL row
