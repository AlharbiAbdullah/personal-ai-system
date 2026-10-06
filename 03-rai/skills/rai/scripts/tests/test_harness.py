"""Harness edges (pi, OpenCode, the dev-env bootstrap) and the code-parse checks."""

import re

import pytest

from conftest import hook_cmd, st
from sanity_checks import core
from sanity_checks.core import FAIL, PASS, SKIP, WARN
from sanity_checks.harness import AGY_EDGES, OPENCODE_EDGES, PI_EDGES

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
ln -sfn "$RAI/harness/pi/prompts"      "$HOME/.pi/agent/prompts"
link_skills "$HOME/.agents/skills"
ln -sfn "$RAI/AGENTS.md"                "$HOME/.config/opencode/AGENTS.md"
ln -sfn "$RAI/harness/opencode/rai.ts"  "$HOME/.config/opencode/plugin/rai.ts"
AGY_PLUGIN="$HOME/.gemini/config/plugins/rai"
ln -sfn "$RAI/AGENTS.md"                "$HOME/.gemini/GEMINI.md"
ln -sfn "$RAI/harness/agy/plugin.json"  "$AGY_PLUGIN/plugin.json"
ln -sfn "$RAI/harness/agy/hooks.json"   "$AGY_PLUGIN/hooks.json"
ln -sfn "$RAI/skills"                   "$AGY_PLUGIN/skills"
"""


def _vault_targets(w):
    for rel in ("agents", "hooks", "skills", "auto-memory", "harness/pi/prompts"):
        w.mkdir(f"helm/03-rai/{rel}")
    for rel in ("AGENTS.md", "config/settings.json", "harness/pi/rai-bridge.ts", "identity/a.md",
                "harness/claude-code/user-instructions.md",
                "harness/opencode/rai.ts", "harness/agy/plugin.json", "harness/agy/hooks.json"):
        w.write(f"helm/03-rai/{rel}", "x")


def _boot(w, claude_md="harness/claude-code/user-instructions.md", drop=None):
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


def test_harn_3_fault_bootstrap_drops_an_adapter_edge(w):
    _vault_targets(w)
    _boot(w, drop="plugin/rai.ts")
    r = st("HARN-3")
    assert r.status == WARN and ".config/opencode/plugin/rai.ts" in r.evidence


# HARN-4 (opencode) and HARN-5 (agy) ─────────────────────────────────────────────
ADAPTER_HOOKS = ["session-start", "memory-injection", "turn-capture"]


def _registered(w):
    w.settings({"Stop": [hook_cmd(w, h) for h in SETTINGS_HOOKS + ["stop-orchestrator"]]})


def _oc(w, hooks=ADAPTER_HOOKS, skip=None):
    w.write("helm/03-rai/AGENTS.md", "x")
    w.write("helm/03-rai/harness/opencode/rai.ts", "\n".join(f'runHook("{h}.py", base, opts);' for h in hooks))
    for rel, target in OPENCODE_EDGES.items():
        if rel != skip:
            w.link(rel, w.helm / target)
    _registered(w)


def test_harn_4_ok(w):
    _oc(w)
    r = st("HARN-4")
    assert r.status == PASS, r.evidence


def test_harn_4_skips_without_opencode(w):
    assert st("HARN-4").status == SKIP


def test_harn_4_fault_plugin_unmounted(w):
    _oc(w, skip=".config/opencode/plugin/rai.ts")
    r = st("HARN-4")
    assert r.status == FAIL and "plugin/rai.ts: missing" in r.evidence


def test_harn_4_fault_new_hook_not_wired(w):
    _oc(w, hooks=["session-start", "memory-injection"])
    r = st("HARN-4")
    assert r.status == WARN and "lacks ['turn-capture']" in r.evidence


def _agy(w, hooks=ADAPTER_HOOKS, skip=None, rules=True, drop=None, spill=False, agents=True):
    w.write("helm/03-rai/AGENTS.md", "x")
    w.mkdir("helm/03-rai/skills")
    w.write("helm/03-rai/harness/agy/plugin.json", "{}")
    w.write("helm/03-rai/harness/agy/hooks.json", "{}")
    w.write("helm/03-rai/harness/agy/agy-hook.py", "\n".join(f'run("{h}.py", env)' for h in hooks))
    ident = [w.write("helm/03-rai/identity/a.md", "a"), w.write("helm/02-ana/identity/b.md", "b")]
    for rel, target in AGY_EDGES.items():
        if rel != skip:
            w.link(rel, w.helm / target)
    w.write("helm/03-rai/agents/reviewer.md", "---\nname: reviewer\ndescription: d\n---\nbody\n")
    w.write("helm/03-rai/agents/MANIFEST.md", "# agents")
    if agents:
        w.write(".gemini/config/plugins/rai/agents/reviewer.md", "---\nname: reviewer\n---\n")
    if rules:
        inc = [f for f in ident if f.name != drop]
        w.write(".gemini/config/plugins/rai/rules/AGENTS.md", "\n".join(f"@[{f.name}]({f})" for f in inc))
        w.write(".gemini/config/plugins/rai/rules/GEMINI.md",
                "Identity files that did not fit, read them at the start of a task:\n- /x/c.md\n" if spill else "")
    _registered(w)


def test_harn_5_ok(w):
    _agy(w)
    r = st("HARN-5")
    assert r.status == PASS, r.evidence


def test_harn_5_skips_without_agy(w):
    assert st("HARN-5").status == SKIP


def test_harn_5_fault_global_rules_unmounted(w):
    _agy(w, skip=".gemini/GEMINI.md")
    r = st("HARN-5")
    assert r.status == FAIL and ".gemini/GEMINI.md: missing" in r.evidence


def test_harn_5_fault_rules_never_rendered(w):
    _agy(w, rules=False)
    r = st("HARN-5")
    assert r.status == WARN and "rules" in r.evidence


def test_harn_5_fault_identity_file_not_included(w):
    _agy(w, drop="b.md")
    r = st("HARN-5")
    assert r.status == WARN and "b.md" in r.evidence


def test_harn_5_fault_identity_over_the_rules_cap(w):
    _agy(w, spill=True)
    r = st("HARN-5")
    assert r.status == WARN and "cap" in r.evidence


def test_harn_5_fault_new_hook_not_wired(w):
    _agy(w, hooks=["session-start", "turn-capture"])
    r = st("HARN-5")
    assert r.status == WARN and "lacks ['memory-injection']" in r.evidence


# HARN-6 (adapters keep writing shadows) ───────────────────────────────────────
def _mount(w, rel, age_h):
    import os, time
    w.write("helm/03-rai/x", "x")
    w.link(rel, w.helm / "03-rai/x")
    t = time.time() - age_h * 3600
    os.utime(w.path(rel), (t, t), follow_symlinks=False)


def _oc_db(w, age_h):
    import sqlite3, time
    db = w.path(".local/share/opencode/opencode.db")
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.execute("create table session (id text, parent_id text, time_updated integer)")
    con.execute("insert into session values ('ses_1', null, ?)", (int((time.time() - age_h * 3600) * 1000),))
    con.execute("insert into session values ('ses_2', 'ses_1', ?)", (int(time.time() * 1000),))  # a child: ignored
    con.commit()
    con.close()


def test_harn_6_skips_without_adapters(w):
    assert st("HARN-6").status == SKIP


def test_harn_6_ok(w):
    _mount(w, ".config/opencode/plugin/rai.ts", 48)
    _oc_db(w, 2)
    w.write(".local/share/rai/transcripts/opencode/-h/s.jsonl", "{}", age_h=1)
    r = st("HARN-6")
    assert r.status == PASS, r.evidence


def test_harn_6_ignores_sessions_from_before_the_mount(w):
    _mount(w, ".config/opencode/plugin/rai.ts", 1)
    _oc_db(w, 24)
    assert st("HARN-6").status == PASS


def test_harn_6_fault_opencode_stopped_capturing(w):
    _mount(w, ".config/opencode/plugin/rai.ts", 72)
    _oc_db(w, 1)
    w.write(".local/share/rai/transcripts/opencode/-h/s.jsonl", "{}", age_h=60)
    r = st("HARN-6")
    assert r.status == WARN and "opencode" in r.evidence


def test_harn_6_fault_agy_never_captured(w):
    _mount(w, ".gemini/config/plugins/rai/hooks.json", 72)
    w.write(".gemini/antigravity-cli/brain/c1/.system_generated/logs/transcript_full.jsonl", "{}", age_h=1)
    r = st("HARN-6")
    assert r.status == WARN and "agy" in r.evidence


def test_harn_5_fault_rules_file_over_agys_cap(w):
    _agy(w)
    w.write("helm/03-rai/identity/a.md", "x" * 25000)
    r = st("HARN-5")
    assert r.status == WARN and "24,000" in r.evidence


def test_harn_5_fault_rules_near_agys_token_budget(w):
    _agy(w)
    w.write("helm/03-rai/identity/a.md", "x" * 20000)
    w.write("helm/02-ana/identity/b.md", "x" * 20000)
    w.write("helm/03-rai/AGENTS.md", "x" * 22000)  # the global rules file
    r = st("HARN-5")
    assert r.status == WARN and "budget" in r.evidence


def test_harn_6_skips_a_disabled_agy_plugin(w):
    _mount(w, ".gemini/config/plugins/rai/hooks.json", 72)
    w.write(".gemini/antigravity-cli/brain/c1/.system_generated/logs/transcript_full.jsonl", "{}", age_h=1)
    w.write(".gemini/config/config.json", '{"plugins": {"rai": {"enabled": false}}}')
    assert st("HARN-6").status == SKIP


# HARN-7 (Claude Code loads identity through CLAUDE.md imports) ─────────────────
def _cc(w, edge=True, listed=("a.md", "b.md"), imports=True):
    a = w.write("helm/03-rai/identity/a.md", "a")
    b = w.write("helm/02-ana/identity/b.md", "b")
    if edge:
        w.write("helm/03-rai/harness/claude-code/user-instructions.md",
                "@~/helm/03-rai/AGENTS.md\n@~/helm/03-rai/harness/claude-code/identity-imports.md\n")
    if imports:
        paths = {"a.md": "~/helm/03-rai/identity/a.md", "b.md": "~/helm/02-ana/identity/b.md"}
        w.write("helm/03-rai/harness/claude-code/identity-imports.md",
                "# Rai identity\n" + "".join(f"@{paths[n]}\n" for n in listed))
    return a, b


def test_harn_7_ok(w):
    _cc(w)
    r = st("HARN-7")
    assert r.status == PASS, r.evidence


def test_harn_7_fault_imports_file_missing(w):
    _cc(w, imports=False)
    r = st("HARN-7")
    assert r.status == FAIL and "identity-imports.md" in r.evidence


def test_harn_7_fault_edge_does_not_import(w):
    _cc(w)
    w.write("helm/03-rai/harness/claude-code/user-instructions.md", "@~/helm/03-rai/AGENTS.md\n")
    r = st("HARN-7")
    assert r.status == FAIL and "imports" in r.evidence


def test_harn_7_fault_identity_file_not_listed(w):
    _cc(w, listed=("a.md",))
    r = st("HARN-7")
    assert r.status == WARN and "b.md" in r.evidence


def test_harn_5_fault_agents_not_rendered(w):
    _agy(w, agents=False)
    r = st("HARN-5")
    assert r.status == WARN and "agents miss ['reviewer']" in r.evidence
