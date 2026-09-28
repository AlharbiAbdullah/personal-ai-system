"""Harness: the thin edges each agent harness mounts into the vault. The vault is canonical and
every edge is deletable (doctrine 2026-07-05), so an absent harness SKIPs; a present one must
resolve into 03-rai exactly, and the bootstrap must be able to recreate every edge."""

import glob
import re
import sys

from . import core
from .config import claude_project_dir
from .core import FAIL, PASS, SKIP, WARN, P, check
from .hooks import _registered_hooks

# pi's edges: link under home -> target under helm (03-rai/harness/pi/README.md, Wiring)
PI_EDGES = {
    ".pi/agent/AGENTS.md": "03-rai/AGENTS.md",
    ".pi/agent/extensions/rai-bridge.ts": "03-rai/harness/pi/rai-bridge.ts",
    ".agents/skills": "03-rai/skills",
}
# hooks the bridge deliberately does not run: pi has no AskUserQuestion tool (README parity matrix)
PI_NOT_APPLICABLE = {"set-question-tab", "question-answered"}
BRIDGE = "03-rai/harness/pi/rai-bridge.ts"
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
                ("skills", "03-rai/skills"), ("CLAUDE.md", "03-rai/AGENTS.md"),
                ("settings.json", "03-rai/config/settings.json"))},
                mem: "03-rai/auto-memory", **PI_EDGES}
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
