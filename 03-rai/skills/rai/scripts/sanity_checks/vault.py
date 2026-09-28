"""Vault, Skills and Agents: the folder skeleton, templates, root files, skill structure and
reachability, live collection refs, agent frontmatter."""

import re

from .core import ASSERTED_COLLECTIONS, FAIL, PASS, WARN, P, check, frontmatter

# ════════════════════════════════════════════════════════════════════════════════
# VAULT
# ════════════════════════════════════════════════════════════════════════════════
@check("VAULT-1", "Vault")
def folders():
    """The 14 top-level vault folders exist."""
    expect = ["00-landing", "01-inbox", "02-ana", "03-rai", "04-work", "05-projects",
              "06-learning", "07-reading", "08-bawaba", "09-ideas", "10-knowledge",
              "11-workflows", "12-system", "13-archive"]
    missing = [d for d in expect if not (P.HELM / d).is_dir()]
    ev = f"{len(expect)-len(missing)}/{len(expect)}"
    return (FAIL, ev + f" missing {missing}", "Restore structural folders from git.") if missing else (PASS, ev, "")


@check("VAULT-2", "Vault")
def templates():
    """Every template in 12-system/templates starts with frontmatter."""
    td = P.HELM / "12-system/templates"
    if not td.is_dir():
        return FAIL, "templates dir missing", "Restore 12-system/templates."
    mds = list(td.glob("*.md"))
    nofm = [p.name for p in mds if not p.read_text(errors="replace").startswith("---")]
    ev = f"{len(mds)} templates, {len(nofm)} without frontmatter"
    return (FAIL, ev + f" {nofm[:5]}", "Every template must start with --- frontmatter.") if nofm else (PASS, ev, "")


@check("VAULT-3", "Vault")
def root_files():
    """The root AGENTS.md and the helm-index exist."""
    ok = (P.HELM / "AGENTS.md").exists()
    idx = (P.HELM / ".helm-index/helm-index.md").exists()
    ev = f"AGENTS.md={'y' if ok else 'N'}, helm-index={'y' if idx else 'N'}"
    return (PASS, ev, "") if ok and idx else (FAIL, ev, "Restore AGENTS.md / run /map-updater for the index.")


# ════════════════════════════════════════════════════════════════════════════════
# SKILLS
# ════════════════════════════════════════════════════════════════════════════════
@check("SKILL-1", "Skills")
def skills_structure():
    """Each SKILL.md names its folder, sub-skills with a name are named for their file, and none shares its router's name."""
    root = P.RAI / "skills"
    EXC = {"SKILL.md", "MANIFEST.md", "GAPS.md", "README.md"}
    rprob, sprob, collide = [], [], []

    def name_of(p):
        fm = frontmatter(p.read_text(errors="replace"))
        if fm is None:
            return None, "no frontmatter"
        if "name" not in fm and "description" not in fm:
            return None, "document"  # a design doc or companion note, not a sub-skill
        return (fm["name"], None) if fm.get("name") else (None, "no name")

    # synced/ is the harness-managed anthropic-skills bucket, not a router
    HARNESS_DIRS = {"synced"}
    routers = 0
    for rd in sorted(d for d in root.iterdir() if d.is_dir() and d.name not in HARNESS_DIRS):
        sm = rd / "SKILL.md"
        if not sm.exists():
            rprob.append(f"{rd.name}:no SKILL.md"); continue
        routers += 1
        nm, err = name_of(sm)
        if err:
            rprob.append(f"{rd.name}:{err}")
        elif nm != rd.name:
            rprob.append(f"{rd.name}:name={nm}")
        for sub in rd.glob("*.md"):
            if sub.name in EXC:
                continue
            snm, serr = name_of(sub)
            if serr in ("no frontmatter", "document"):  # frontmatter is optional (MANIFEST rule)
                continue
            if serr:
                sprob.append(f"{rd.name}/{sub.name}:{serr}")
            elif snm != sub.stem:
                sprob.append(f"{rd.name}/{sub.name}:name={snm}")
            if snm == rd.name:
                collide.append(f"{rd.name}/{sub.name}")
    ev = f"{routers} routers; router_probs={len(rprob)}, sub_probs={len(sprob)}, collisions={len(collide)}"
    if rprob or sprob or collide:
        return FAIL, ev + f" {(rprob+sprob+collide)[:4]}", "Each SKILL.md name must match folder; no router/sub name collision."
    return PASS, ev, ""


@check("SKILL-2", "Skills")
def critical_skills():
    """The four critical skills are reachable through ~/.claude/skills."""
    crit = ["rai/sanity.md", "rai/process-sessions.md", "recall/history.md", "remember/SKILL.md"]
    have = sum(1 for c in crit if (P.DCLAUDE / "skills" / c).exists())
    ev = f"{have}/{len(crit)} critical reachable"
    return (PASS, ev, "") if have == len(crit) else (FAIL, ev, "A critical skill is unreachable via ~/.claude/skills.")


@check("SKILL-3", "Skills")
def skill_collection_refs():
    """Every get_collection('X') embedded in a skill file must name a LIVE collection.
    This is the exact original disease — /recall queried the dead `memories` collection
    for days and nothing caught it. Never again."""
    bad = []
    for p in (P.RAI / "skills").rglob("*.md"):
        try:
            txt = p.read_text(errors="replace")
        except OSError:
            continue
        for m in re.finditer(r"get_collection\(\s*['\"]([\w-]+)['\"]", txt):
            name = m.group(1)
            if name not in ASSERTED_COLLECTIONS:
                bad.append(f"{p.relative_to(P.RAI / 'skills')}:{name}")
    ev = f"{len(bad)} dead collection refs" + (f" — {bad[:4]}" if bad else "")
    return (FAIL, ev, "A skill queries a collection that isn't live — rewrite it onto the v3 stores.") if bad else (PASS, ev, "")


# ════════════════════════════════════════════════════════════════════════════════
# AGENTS
# ════════════════════════════════════════════════════════════════════════════════
def _manifest_drift(d, fms: dict) -> list:
    """What agents/MANIFEST.md claims that the agent files contradict: its tables, its count
    sentence, and the frontmatter contract it states (`model: X` and `effort: Y`)."""
    man = d / "MANIFEST.md"
    if not man.exists():
        return ["MANIFEST.md missing"]
    text = man.read_text(errors="replace")
    listed = set(re.findall(r"^\|\s*`([\w-]+)`\s*\|", text, re.M))
    drift = [f"manifest:{n}" for n in sorted(listed ^ fms.keys())]
    count = re.search(r"^(\d+) agents\b", text, re.M)
    if count and int(count.group(1)) != len(fms):
        drift.append(f"manifest says {count.group(1)} agents, {len(fms)} exist")
    contract = re.search(r"sets `model: ([\w.-]+)` and `effort: ([\w-]+)`", text)
    if contract:
        model, effort = contract.groups()
        drift += [f"{n}:model={fm.get('model')},effort={fm.get('effort')}" for n, fm in sorted(fms.items())
                  if (fm.get("model"), fm.get("effort")) != (model, effort)]
    return drift


@check("AGENT-1", "Agents")
def agents_frontmatter():
    """Each agent's frontmatter names it; agents/MANIFEST.md lists exactly these agents, states
    their count, and every agent honours the model/effort contract it states."""
    d = P.RAI / "agents"
    fms = {p.stem: frontmatter(p.read_text(errors="replace")) or {} for p in sorted(d.glob("*.md"))
           if p.name != "MANIFEST.md"}
    probs = [f"{s}:no name" if not fm.get("name") else f"{s}:name={fm['name']}"
             for s, fm in fms.items() if fm.get("name") != s]
    drift = _manifest_drift(d, fms)
    ev = f"{len(fms)} agents, {len(probs)} problems, {len(drift)} manifest drift"
    if probs:
        return FAIL, ev + f" {probs}", "Each agents/*.md needs --- + name: matching filename."
    if drift:
        return WARN, ev + f" {drift[:4]}", "Bring agents/MANIFEST.md (tables, count, contract) or the agent file in line."
    return PASS, ev, ""
