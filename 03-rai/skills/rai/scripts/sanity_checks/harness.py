"""Harness: the thin edges each agent harness mounts into the vault. The vault is canonical and
every edge is deletable (doctrine 2026-07-05), so an absent harness SKIPs; a present one must
resolve into 03-rai exactly, and the bootstrap must be able to recreate every edge."""

import glob
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from . import core
from .config import claude_project_dir
from .core import FAIL, PASS, SKIP, WARN, P, check
from .hooks import _registered_hooks

# pi's edges: link under home -> target under helm (03-rai/harness/pi/README.md, Wiring)
PI_EDGES = {
    ".pi/agent/AGENTS.md": "03-rai/AGENTS.md",
    ".pi/agent/extensions/rai-bridge.ts": "03-rai/harness/pi/rai-bridge.ts",
    ".pi/agent/prompts": "03-rai/harness/pi/prompts",
    ".agents/skills": "03-rai/skills",
}
# hooks the bridge deliberately does not run: pi has no AskUserQuestion tool (README parity matrix)
PI_NOT_APPLICABLE = {"set-question-tab", "question-answered"}
BRIDGE = "03-rai/harness/pi/rai-bridge.ts"
# opencode and agy: the same two, plus stop-orchestrator, which only resets a terminal tab
# these harnesses own (each README's parity matrix)
ADAPTER_NOT_APPLICABLE = PI_NOT_APPLICABLE | {"stop-orchestrator"}
OPENCODE_EDGES = {
    ".config/opencode/plugin/rai.ts": "03-rai/harness/opencode/rai.ts",
    ".config/opencode/AGENTS.md": "03-rai/AGENTS.md",
}
OPENCODE_PLUGIN = "03-rai/harness/opencode/rai.ts"
AGY_EDGES = {
    ".gemini/GEMINI.md": "03-rai/AGENTS.md",
    ".gemini/config/plugins/rai/plugin.json": "03-rai/harness/agy/plugin.json",
    ".gemini/config/plugins/rai/hooks.json": "03-rai/harness/agy/hooks.json",
    ".gemini/config/plugins/rai/skills": "03-rai/skills",
}
AGY_HOOK = "03-rai/harness/agy/agy-hook.py"
AGY_RULES = ".gemini/config/plugins/rai/rules"
AGY_RULE_CAP = 24000      # agy cuts each rules file here, after its includes expand
AGY_RULES_BUDGET = 60000  # bytes of global plus plugin rules, about 17k of agy's 20k-token rules budget
INCLUDE_RE = re.compile(r"@\[[^\]]*\]\(([^)]+)\)")
CAPTURE_GRACE_H = 6  # a session this much newer than the newest shadow: the adapter stopped capturing
BOOTSTRAP = "linux/omarchy/claude-config.sh"


@check("HARN-1", "Harness")
def pi_mounts():
    """pi's three edges resolve into the vault (SKIP when pi is not installed)."""
    if not P.PI.exists():
        return SKIP, "pi not installed (no ~/.pi/agent)", ""
    probs = [f"~/{rel}: {state}" for rel, target in PI_EDGES.items()
             if (state := core.link_state(P.HOME / rel, P.HELM / target)) != "ok"]
    if probs:
        return FAIL, f"{len(PI_EDGES) - len(probs)}/{len(PI_EDGES)} edges resolve; {probs}", \
            "Re-run dev-env linux/omarchy/claude-config.sh, or the three ln -s lines in 03-rai/harness/pi/README.md."
    return PASS, f"{len(PI_EDGES)}/{len(PI_EDGES)} edges resolve", ""


@check("HARN-2", "Harness")
def pi_hook_parity():
    """The pi bridge runs every hook settings.json registers, minus the two AskUserQuestion hooks
    pi has no tool for, and nothing settings.json no longer registers."""
    bridge = P.HELM / BRIDGE
    if not bridge.exists() and not P.PI.exists():
        return SKIP, "pi not installed (no ~/.pi/agent) and no bridge in this vault", ""
    if not bridge.exists():
        return FAIL, f"{BRIDGE} missing", "Restore the bridge from git; pi sessions run with no hooks."
    called = set(re.findall(r"[\"']([\w-]+)\.py[\"']", bridge.read_text(errors="replace")))
    reg = _registered_hooks()
    missing = sorted(reg - PI_NOT_APPLICABLE - called)
    extra = sorted(called - reg)
    ev = f"bridge runs {len(called)}, settings.json registers {len(reg)} ({len(PI_NOT_APPLICABLE)} not applicable to pi)"
    if missing or extra:
        return WARN, ev + (f", bridge lacks {missing}" if missing else "") + (f", bridge runs unregistered {extra}" if extra else ""), \
            "Wire the hook in rai-bridge.ts (and the README parity matrix), or drop the stale call."
    return PASS, ev, ""


def _opencode_problems() -> list:
    cfg = next((p for p in (P.OPENCODE / "opencode.jsonc", P.OPENCODE / "opencode.json") if p.exists()), None)
    if not cfg:
        return []
    m = re.search(r'"instructions"\s*:\s*\[(.*?)\]', cfg.read_text(errors="replace"), re.S)
    probs = []
    for entry in re.findall(r'"([^"]+)"', m.group(1)) if m else []:
        pattern = str(P.HOME) + entry[1:] if entry.startswith("~") else entry
        if not glob.glob(pattern):
            probs.append(f"opencode instruction {entry} matches nothing")
    return probs


def _bootstrap_links(text: str) -> dict:
    """claude-config.sh -> {link path relative to home: target relative to helm}. Expands the
    script's own VAR="..." assignments; link_skills DEST links DEST to $RAI/skills."""
    env = {"HOME": "~"}
    for name, val in re.findall(r'^\s*(\w+)="([^"]*)"', text, re.M):
        env[name] = re.sub(r"\$\{?(\w+)\}?", lambda v: env.get(v.group(1), v.group(0)), val)

    def expand(s):
        return re.sub(r"\$\{?(\w+)\}?", lambda v: env.get(v.group(1), v.group(0)), s)

    pairs = re.findall(r'ln -sfn\s+"([^"]+)"\s+"([^"]+)"', text)
    pairs += [("$RAI/skills", dest) for dest in re.findall(r'^\s*link_skills\s+"([^"]+)"', text, re.M)]
    out = {}
    for target, link in pairs:
        t, l = expand(target), expand(link)
        if t.startswith("~/helm/") and l.startswith("~/"):
            out[l[2:]] = t[len("~/helm/"):]
    return out


def _bootstrap_problems() -> list:
    script = P.DEVENV / BOOTSTRAP
    if not script.exists() or not sys.platform.startswith("linux"):
        return []  # the Linux bootstrap; the Mac has its own setup
    links = _bootstrap_links(script.read_text(errors="replace"))
    if not links:
        return [f"{BOOTSTRAP}: no vault links parsed (script reshaped? this check went blind)"]
    probs = [f"bootstrap links ~/{l} to missing {t}" for l, t in links.items() if not (P.HELM / t).exists()]
    mem = str((claude_project_dir(P.HELM) / "memory").relative_to(P.HOME))
    required = {**{f".claude/{n}": t for n, t in (("agents", "03-rai/agents"), ("hooks", "03-rai/hooks"),
                ("skills", "03-rai/skills"), ("CLAUDE.md", "03-rai/harness/claude-code/user-instructions.md"),
                ("settings.json", "03-rai/config/settings.json"))},
                mem: "03-rai/auto-memory", **PI_EDGES, **OPENCODE_EDGES, **AGY_EDGES}
    probs += [f"a fresh install would not recreate ~/{l}" for l, t in required.items() if links.get(l) != t]
    return probs


@check("HARN-3", "Harness")
def harness_edges():
    """OpenCode's instruction globs and the dev-env bootstrap point at files that exist, and the
    bootstrap still recreates every edge sanity asserts (CFG-2, MEM-1, HARN-1)."""
    have_oc = (P.OPENCODE / "opencode.jsonc").exists() or (P.OPENCODE / "opencode.json").exists()
    have_boot = (P.DEVENV / BOOTSTRAP).exists() and sys.platform.startswith("linux")
    if not have_oc and not have_boot:
        return SKIP, "no OpenCode config and no dev-env bootstrap on this machine", ""
    probs = _opencode_problems() + _bootstrap_problems()
    ev = f"opencode={'yes' if have_oc else 'absent'}, bootstrap={'yes' if have_boot else 'absent'}"
    if probs:
        return WARN, ev + f"; {probs[:4]}", "Point the edge at today's vault path (dev-env repo), then re-run it."
    return PASS, ev + ", every edge resolves", ""


def _edge_problems(edges: dict) -> list:
    return [f"~/{rel}: {state}" for rel, target in edges.items()
            if (state := core.link_state(P.HOME / rel, P.HELM / target)) != "ok"]


def _parity(adapter: str) -> tuple:
    """(hooks the adapter runs, registered hooks it lacks, hooks it runs that are not registered)."""
    called = set(re.findall(r"[\"']([\w-]+)\.py[\"']", (P.HELM / adapter).read_text(errors="replace")))
    reg = _registered_hooks()
    return called, sorted(reg - ADAPTER_NOT_APPLICABLE - called), sorted(called - reg)


def _parity_note(name: str, adapter: str) -> tuple:
    called, missing, extra = _parity(adapter)
    note = f"{name} runs {len(called)} hooks ({len(ADAPTER_NOT_APPLICABLE)} not applicable)"
    bad = (f", {name} lacks {missing}" if missing else "") + (f", {name} runs unregistered {extra}" if extra else "")
    return note, bad


@check("HARN-4", "Harness")
def opencode_adapter():
    """opencode's plugin and global AGENTS.md resolve into the vault, and the plugin runs every
    hook settings.json registers, minus the three its README marks not applicable."""
    if not P.OPENCODE.exists():
        return SKIP, "opencode not installed (no ~/.config/opencode)", ""
    if not (P.HELM / OPENCODE_PLUGIN).exists():
        return FAIL, f"{OPENCODE_PLUGIN} missing", "Restore the plugin from git; opencode runs with no Rai."
    probs = _edge_problems(OPENCODE_EDGES)
    if probs:
        return FAIL, f"{len(OPENCODE_EDGES) - len(probs)}/{len(OPENCODE_EDGES)} edges resolve; {probs}", \
            "Re-run dev-env linux/omarchy/claude-config.sh, or the ln lines in 03-rai/harness/opencode/README.md."
    note, bad = _parity_note("plugin", OPENCODE_PLUGIN)
    ev = f"{len(OPENCODE_EDGES)}/{len(OPENCODE_EDGES)} edges resolve, {note}"
    if bad:
        return WARN, ev + bad, "Wire the hook in rai.ts (and the README parity matrix), or drop the stale call."
    return PASS, ev, ""


def _identity_files() -> list:
    files = [f for d in (P.RAI / "identity", P.HELM / "02-ana" / "identity") for f in sorted(d.glob("*.md"))]
    block = P.RAI / "memory" / "state" / "memory-block.md"
    return files + ([block] if block.exists() else [])


@check("HARN-5", "Harness")
def agy_adapter():
    """agy's global rules, plugin and skills resolve into the vault; its rules files name every
    identity file within agy's size cap; every Rai agent has its agy version; and the hook runs
    every registered hook bar three."""
    if not P.GEMINI.exists():
        return SKIP, "agy not installed (no ~/.gemini)", ""
    if not (P.HELM / AGY_HOOK).exists():
        return FAIL, f"{AGY_HOOK} missing", "Restore the agy adapter from git; agy runs with no Rai."
    probs = _edge_problems(AGY_EDGES)
    if probs:
        return FAIL, f"{len(AGY_EDGES) - len(probs)}/{len(AGY_EDGES)} edges resolve; {probs}", \
            "Re-run dev-env linux/omarchy/claude-config.sh, or the lines in 03-rai/harness/agy/README.md."
    rules = P.HOME / AGY_RULES
    parts = {n: (rules / n).read_text(errors="replace") for n in ("AGENTS.md", "GEMINI.md") if (rules / n).exists()}
    text = "".join(parts.values())
    issues = []
    if not text:
        issues.append("rules never rendered")
    else:
        absent = [f.name for f in _identity_files() if str(f) not in text]
        if absent:
            issues.append(f"rules miss {absent}")
        if "did not fit" in text:
            issues.append("identity is over agy's rules cap, the rest is named as pointers")
        sizes = {n: _expanded(body) for n, body in parts.items()}
        over = [f"rules/{n} expands to {b:,} bytes" for n, b in sizes.items() if b > AGY_RULE_CAP]
        if over:
            issues.append(f"{over}, over agy's {AGY_RULE_CAP:,}-byte cap: its end is cut")
        glob_rules = P.HOME / ".gemini" / "GEMINI.md"
        total = sum(sizes.values()) + (glob_rules.stat().st_size if glob_rules.exists() else 0)
        if total > AGY_RULES_BUDGET:
            issues.append(f"rules total {total:,} bytes, near agy's 20k-token rules budget")
    rendered = {p.stem for p in (P.GEMINI / "config/plugins/rai/agents").glob("*.md")}
    agents = sorted(p.stem for p in (P.RAI / "agents").glob("*.md")
                    if p.name != "MANIFEST.md" and p.read_text(errors="replace").startswith("---"))
    if missing_agents := [a for a in agents if a not in rendered]:
        issues.append(f"agents miss {missing_agents}")
    note, bad = _parity_note("hook", AGY_HOOK)
    ev = f"{len(AGY_EDGES)}/{len(AGY_EDGES)} edges resolve, {note}"
    if issues or bad:
        return WARN, ev + (f", {'; '.join(issues)}" if issues else "") + bad, \
            "Run `03-rai/harness/agy/agy-hook.py render-rules`, trim identity under 46 KB, or wire the hook in agy-hook.py."
    return PASS, ev + f", rules include every identity file, {len(agents)} agents rendered", ""


def _expanded(body: str) -> int:
    """A rules file's size once agy expands its @[label](path) includes."""
    size = len(INCLUDE_RE.sub("", body).encode())
    for path in INCLUDE_RE.findall(body):
        try:
            size += (P.HOME / path[2:] if path.startswith("~/") else Path(path)).stat().st_size
        except OSError:
            pass
    return size


def _agy_plugin_enabled() -> bool:
    """`agy plugin disable rai` records the choice in ~/.gemini/config/config.json."""
    try:
        cfg = json.loads((P.GEMINI / "config" / "config.json").read_text())
        return cfg.get("plugins", {}).get("rai", {}).get("enabled", True) is not False
    except (OSError, ValueError, AttributeError):
        return True


def _newest(paths) -> float:
    return max((p.stat().st_mtime for p in paths), default=0.0)


def _opencode_last_session() -> float:
    if not P.OPENCODE_DB.exists():
        return 0.0
    try:
        con = sqlite3.connect(f"file:{P.OPENCODE_DB}?mode=ro", uri=True, timeout=2)
        try:
            row = con.execute("select max(time_updated) from session where parent_id is null").fetchone()
        finally:
            con.close()
        return (row[0] or 0) / 1000
    except sqlite3.Error:
        return 0.0


def _agy_last_session() -> float:
    return _newest(P.GEMINI.glob("antigravity-cli/brain/*/.system_generated/logs/transcript_full.jsonl"))


@check("HARN-6", "Harness")
def adapter_capture():
    """Each mounted adapter keeps writing shadows: a native opencode or agy session newer than
    the mount and more than 6 hours newer than the newest shadow means capture stopped."""
    seen, probs = [], []
    for name, edge, last in (("opencode", ".config/opencode/plugin/rai.ts", _opencode_last_session),
                             ("agy", ".gemini/config/plugins/rai/hooks.json", _agy_last_session)):
        link = P.HOME / edge
        if not link.is_symlink() or (name == "agy" and not _agy_plugin_enabled()):
            continue
        seen.append(name)
        native, shadow = last(), _newest((P.SHADOWS / name).glob("*/*.jsonl"))
        if native > link.lstat().st_mtime and native - shadow > CAPTURE_GRACE_H * 3600:
            when = datetime.fromtimestamp(native).strftime("%m-%d %H:%M")
            newest = datetime.fromtimestamp(shadow).strftime("%m-%d %H:%M") if shadow else "none"
            probs.append(f"{name} session at {when}, newest shadow {newest}")
    if not seen:
        return SKIP, "no opencode or agy adapter mounted", ""
    if probs:
        return WARN, "; ".join(probs), \
            "The adapter stopped writing shadows: read $XDG_STATE_HOME/rai/<harness>-adapter.log and the harness README."
    return PASS, f"{', '.join(seen)}: shadows keep up with sessions", ""


CC_EDGE = "03-rai/harness/claude-code/user-instructions.md"
CC_IMPORTS = "03-rai/harness/claude-code/identity-imports.md"


def _imported(text: str) -> set:
    return {str(P.HOME / l[3:]) if l.startswith("@~/") else l[1:]
            for l in (x.strip() for x in text.splitlines()) if l.startswith("@")}


@check("HARN-7", "Harness")
def claude_identity_imports():
    """Claude Code inlines a SessionStart output only up to 10,000 characters, so its identity loads
    through ~/.claude/CLAUDE.md: the edge file imports AGENTS.md and identity-imports.md, which
    session-start keeps listing every identity file, the memory block and the helm index."""
    edge, imports = P.HELM / CC_EDGE, P.HELM / CC_IMPORTS
    if not edge.exists() or not imports.exists():
        missing = [str(p.relative_to(P.HELM)) for p in (edge, imports) if not p.exists()]
        return FAIL, f"missing {missing}", "Restore the edge from git; session-start re-renders identity-imports.md."
    want = {str(P.RAI / "AGENTS.md"), str(imports)}
    if not want <= _imported(edge.read_text(errors="replace")):
        return FAIL, f"{CC_EDGE} imports {sorted(_imported(edge.read_text(errors='replace')))}", \
            "The edge file must import AGENTS.md and identity-imports.md."
    listed = _imported(imports.read_text(errors="replace"))
    index = P.HELM / ".helm-index" / "helm-index.md"
    expected = _identity_files() + ([index] if index.exists() else [])
    absent = [f.name for f in expected if str(f) not in listed]
    if absent:
        return WARN, f"identity-imports.md lacks {absent}", "Start a Claude Code session (session-start re-renders it), then re-run."
    return PASS, f"CLAUDE.md imports AGENTS.md and {len(listed)} identity files", ""
