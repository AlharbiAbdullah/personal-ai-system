"""Workflows: reference integrity of John's workflows in 11-workflows/.

A workflow is his way of doing one kind of work (11-workflows/AGENTS.md). These checks keep
its links to skills, agents and other workflows from rotting. A FAIL here makes the verdict
DEGRADED, never BROKEN: a stale link is a feature off, not data at risk.
"""

import re

from .core import FAIL, PASS, WARN, P, check

WORKFLOW_FILE = re.compile(r"^(\d{2})-[a-z0-9-]+\.md$")

# `/router` or `/router → sub` inside backticks. The lookahead refuses paths such as `/home/x`.
SKILL_REF = re.compile(r"`/([a-z][a-z0-9-]*)(?:\s*→\s*([a-z][a-z0-9-]*))?(?=[`\s])")
# Skills that live outside 03-rai/skills: each repo's own /sdd, and Claude Code built-ins.
EXTERNAL_SKILLS = {"sdd", "deep-research", "code-review", "simplify", "security-review",
                   "clear", "compact", "effort", "rewind"}

AGENT_REF = re.compile(r"\bthe `([a-z][a-z0-9-]*)` agent\b", re.I)
BUILTIN_AGENTS = {"general-purpose", "explore", "plan"}

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
LINE_CITE = re.compile(r"\b[\w./-]+\.(?:md|py|sh|json|jsonl|yaml|yml|toml|ts|js):\d+")
HEADER_KEYS = ("Use when", "Not for", "Done when")
GAP_BLOCK = re.compile(r"^>\s*\*\*GAP\s+Q\d+\.\d+", re.M)


def _workflows():
    d = P.HELM / "11-workflows"
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if WORKFLOW_FILE.match(p.name))


def _text(p):
    return p.read_text(errors="replace")


def _none_found(what):
    return FAIL, f"no workflow files in 11-workflows/ ({what})", "Restore 11-workflows/ from git."


@check("FLOW-1", "Workflows")
def skill_refs():
    """Every `/router` and `/router → sub-skill` a workflow names resolves to a live skill file."""
    files = _workflows()
    if not files:
        return _none_found("FLOW-1")
    skills = P.RAI / "skills"
    bad, seen = [], 0
    for p in files:
        for m in SKILL_REF.finditer(_text(p)):
            router, sub = m.group(1), m.group(2)
            seen += 1
            if router in EXTERNAL_SKILLS:
                continue
            if not (skills / router / "SKILL.md").exists():
                bad.append(f"{p.name}:/{router}")
            elif sub and not (skills / router / f"{sub}.md").exists():
                bad.append(f"{p.name}:/{router} → {sub}")
    ev = f"{seen} skill refs in {len(files)} workflows, {len(bad)} unresolved"
    if bad:
        return FAIL, ev + f" {sorted(set(bad))[:5]}", "Point the step at a live skill, or fix the skill name."
    return PASS, ev, ""


@check("FLOW-2", "Workflows")
def agent_refs():
    """Every "the `<name>` agent" a workflow names is a Rai agent or a built-in type."""
    files = _workflows()
    if not files:
        return _none_found("FLOW-2")
    agents = {p.stem for p in (P.RAI / "agents").glob("*.md") if p.name != "MANIFEST.md"}
    named, bad = set(), []
    for p in files:
        for m in AGENT_REF.finditer(_text(p)):
            name = m.group(1).lower()
            named.add(name)
            if name not in agents and name not in BUILTIN_AGENTS:
                bad.append(f"{p.name}:{name}")
    unnamed = sorted(agents - named)
    ev = f"{len(named & agents)}/{len(agents)} agents named by a workflow step"
    if unnamed:
        ev += f"; unnamed: {', '.join(unnamed)}"
    if bad:
        return FAIL, ev + f"; unknown {sorted(set(bad))[:5]}", "Name an agent that exists in 03-rai/agents/."
    return PASS, ev, ""


def _note_stems():
    """Every note stem and vault-relative path, the way Obsidian resolves [[links]]."""
    stems, rels = set(), set()
    for p in P.HELM.rglob("*.md"):
        parts = p.relative_to(P.HELM).parts
        if any(x.startswith(".") for x in parts[:-1]):
            continue
        stems.add(p.stem)
        rels.add(str(p.relative_to(P.HELM).with_suffix("")))
    return stems, rels


@check("FLOW-3", "Workflows")
def wikilinks():
    """Every [[link]] in a workflow resolves to a note in the vault."""
    files = _workflows()
    if not files:
        return _none_found("FLOW-3")
    stems, rels = _note_stems()
    bad, seen = [], 0
    for p in files:
        for m in WIKILINK.finditer(_text(p)):
            target = m.group(1).strip()
            seen += 1
            if target not in stems and target not in rels:
                bad.append(f"{p.name}:[[{target}]]")
    ev = f"{seen} links, {len(bad)} unresolved"
    if bad:
        return FAIL, ev + f" {sorted(set(bad))[:5]}", "Fix the link target or restore the note."
    return PASS, ev, ""


def _table_numbers(text):
    return set(re.findall(r"^\|\s*(\d{2})\s*\|", text, re.M))


@check("FLOW-4", "Workflows")
def indexed():
    """Every workflow is in the 11-workflows/AGENTS.md table and the helm index, and every
    numbered row in the AGENTS.md table has a file."""
    files = _workflows()
    if not files:
        return _none_found("FLOW-4")
    nums = {WORKFLOW_FILE.match(p.name).group(1) for p in files}
    agents_md = P.HELM / "11-workflows" / "AGENTS.md"
    index = P.HELM / ".helm-index" / "helm-index.md"
    in_table = _table_numbers(_text(agents_md)) if agents_md.exists() else set()
    idx_text = _text(index) if index.exists() else ""
    section = idx_text.split("## 11-workflows/", 1)[1].split("\n## ", 1)[0] if "## 11-workflows/" in idx_text else ""
    in_index = _table_numbers(section)
    probs = [f"AGENTS.md lacks {n}" for n in sorted(nums - in_table)]
    probs += [f"AGENTS.md row {n} has no file" for n in sorted(in_table - nums)]
    probs += [f"helm index lacks {n}" for n in sorted(nums - in_index)]
    ev = f"{len(nums)} workflows; {len(probs)} index gaps"
    if probs:
        return FAIL, ev + f" {probs[:5]}", "Update the 11-workflows/AGENTS.md table, then run /map-updater."
    return PASS, ev, ""


@check("FLOW-5", "Workflows")
def no_line_citations():
    """No workflow cites `file.md:NN`: line numbers rot, a file name does not."""
    files = _workflows()
    if not files:
        return _none_found("FLOW-5")
    hits = [f"{p.name}:{m.group(0)}" for p in files for m in LINE_CITE.finditer(_text(p))]
    ev = f"{len(hits)} line citations"
    if hits:
        return FAIL, ev + f" {hits[:5]}", "Name the file without a line number."
    return PASS, ev, ""


@check("FLOW-6", "Workflows")
def headers():
    """Each workflow opens with a # title and exactly one Use when, Not for and Done when line,
    the lines the menu, the router and the per-prompt reminder read."""
    files = _workflows()
    if not files:
        return _none_found("FLOW-6")
    probs = []
    for p in files:
        text = _text(p)
        head = text.split("\n## ", 1)[0]
        if not text.startswith("# "):
            probs.append(f"{p.name}:no title")
        for key in HEADER_KEYS:
            n = len(re.findall(rf"^\*\*{key}:\*\*", head, re.M))
            if n != 1:
                probs.append(f"{p.name}:{key} x{n}")
    ev = f"{len(files)} workflows, {len(probs)} header problems"
    if probs:
        return FAIL, ev + f" {probs[:5]}", "Give the workflow its header lines (see 11-workflows/AGENTS.md)."
    return PASS, ev, ""


@check("FLOW-7", "Workflows")
def open_gaps():
    """Open GAP blocks: questions a draft still owes John. A WARN, never a FAIL."""
    files = _workflows()
    if not files:
        return _none_found("FLOW-7")
    open_ = {p.name: len(GAP_BLOCK.findall(_text(p))) for p in files}
    open_ = {k: v for k, v in open_.items() if v}
    total = sum(open_.values())
    ev = f"{total} open GAP blocks" + (f" in {sorted(open_)[:6]}" if open_ else "")
    if total:
        return WARN, ev, "Ask John the GAP questions, then write his answers into the steps."
    return PASS, ev, ""
