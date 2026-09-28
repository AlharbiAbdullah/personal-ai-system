"""Vault, Skills and Agents checks."""

from conftest import st
from sanity_checks.core import FAIL, PASS, WARN

FOLDERS = ["00-landing", "01-inbox", "02-ana", "03-rai", "04-work", "05-projects", "06-learning",
           "07-reading", "08-bawaba", "09-ideas", "10-knowledge", "11-workflows", "12-system",
           "13-archive"]


def _skill(w, router, subs=(), name=None, sub_fm=None):
    """A router dir: SKILL.md named `name` (default: the dir) plus sub-skill files."""
    w.write(f"helm/03-rai/skills/{router}/SKILL.md",
            f"---\nname: {name or router}\ndescription: d\n---\n# {router}\n")
    for s in subs:
        fm = (sub_fm or {}).get(s, f"---\nname: {s}\ndescription: d\n---\n")
        w.write(f"helm/03-rai/skills/{router}/{s}.md", fm + f"# {s}\n")


# VAULT-1..3 ────────────────────────────────────────────────────────────────────
def test_vault_1_ok(w):
    for d in FOLDERS:
        w.mkdir(f"helm/{d}")
    assert st("VAULT-1").status == PASS


def test_vault_1_fault_folder_gone(w):
    for d in FOLDERS[:-1]:
        w.mkdir(f"helm/{d}")
    r = st("VAULT-1")
    assert r.status == FAIL and "13-archive" in r.evidence


def test_vault_2_ok(w):
    w.write("helm/12-system/templates/Topic Note.md", "---\ntype: topic\n---\n")
    assert st("VAULT-2").status == PASS


def test_vault_2_fault_template_without_frontmatter(w):
    w.write("helm/12-system/templates/Topic Note.md", "# no frontmatter\n")
    assert st("VAULT-2").status == FAIL


def test_vault_2_fault_dir_missing(w):
    assert st("VAULT-2").status == FAIL


def test_vault_3_ok(w):
    w.write("helm/AGENTS.md", "x")
    w.write("helm/.helm-index/helm-index.md", "x")
    assert st("VAULT-3").status == PASS


def test_vault_3_fault_index_missing(w):
    w.write("helm/AGENTS.md", "x")
    assert st("VAULT-3").status == FAIL


# SKILL-1 ───────────────────────────────────────────────────────────────────────
def test_skill_1_ok(w):
    _skill(w, "rai", subs=("sanity", "eval"))
    w.mkdir("helm/03-rai/skills/synced")  # harness bucket, not a router
    assert st("SKILL-1").status == PASS


def test_skill_1_ok_design_doc_is_not_a_subskill(w):
    """The 2026-09-26 false FAIL: a doc with its own frontmatter (title, status) and a YAML
    sample further down (`name: ci`) read as a mis-named sub-skill."""
    _skill(w, "project-init")
    w.write("helm/03-rai/skills/project-init/DESIGN.md",
            "---\ntitle: design\nstatus: shipped\n---\n# Design\n\n```yaml\nname: ci\non: push\n```\n")
    w.write("helm/03-rai/skills/project-init/v31-companion.md",
            "---\ntitle: \"v3.1\"\nstatus: built\n---\n# v3.1\n")
    r = st("SKILL-1")
    assert r.status == PASS, r.evidence


def test_skill_1_ok_subskill_without_frontmatter(w):
    _skill(w, "research")
    w.write("helm/03-rai/skills/research/academic.md", "# Academic\n")
    assert st("SKILL-1").status == PASS


def test_skill_1_fault_subskill_misnamed(w):
    _skill(w, "rai", subs=("sanity",), sub_fm={"sanity": "---\nname: healthcheck\ndescription: d\n---\n"})
    r = st("SKILL-1")
    assert r.status == FAIL and "name=healthcheck" in r.evidence


def test_skill_1_fault_router_misnamed(w):
    _skill(w, "rai", name="brain")
    assert st("SKILL-1").status == FAIL


def test_skill_1_fault_no_skill_md(w):
    w.write("helm/03-rai/skills/orphan/notes.md", "x")
    assert st("SKILL-1").status == FAIL


def test_skill_1_fault_name_only_in_body(w):
    """A router's name must come from its frontmatter, not from a line further down."""
    w.write("helm/03-rai/skills/rai/SKILL.md", "---\ndescription: d\n---\nname: rai\n")
    assert st("SKILL-1").status == FAIL


def test_skill_1_fault_router_sub_collision(w):
    _skill(w, "rai", subs=("rai",))
    assert st("SKILL-1").status == FAIL


# SKILL-2..3 ────────────────────────────────────────────────────────────────────
def _critical(w, skip=None):
    for rel in ("rai/sanity.md", "rai/process-sessions.md", "recall/history.md", "remember/SKILL.md"):
        if rel != skip:
            w.write(f"helm/03-rai/skills/{rel}", "x")
    w.link(".claude/skills", w.rai / "skills")


def test_skill_2_ok(w):
    _critical(w)
    assert st("SKILL-2").status == PASS


def test_skill_2_fault_unreachable(w):
    _critical(w, skip="recall/history.md")
    assert st("SKILL-2").status == FAIL


def test_skill_3_ok(w):
    w.write("helm/03-rai/skills/recall/history.md", "client.get_collection('rai-semantic')")
    assert st("SKILL-3").status == PASS


def test_skill_3_fault_dead_collection(w):
    w.write("helm/03-rai/skills/routine/today-prep.md", 'c.get_collection("memories")')
    r = st("SKILL-3")
    assert r.status == FAIL and "memories" in r.evidence


# AGENT-1 ───────────────────────────────────────────────────────────────────────
MAN = """# Agents Manifest

{n} agents. Every agent file sets `model: opus` and `effort: xhigh` in its frontmatter.

| Agent | Scope |
|-------|-------|
{rows}"""


def _agents(w, names=("sre", "writer"), listed=None, stated=None, fm=None):
    for n in names:
        w.write(f"helm/03-rai/agents/{n}.md", (fm or {}).get(n, f"---\nname: {n}\nmodel: opus\neffort: xhigh\n---\n"))
    listed = names if listed is None else listed
    w.write("helm/03-rai/agents/MANIFEST.md",
            MAN.format(n=stated or len(names), rows="".join(f"| `{n}` | x |\n" for n in listed)))


def test_agent_1_ok(w):
    _agents(w)
    r = st("AGENT-1")
    assert r.status == PASS, r.evidence


def test_agent_1_fault_misnamed(w):
    _agents(w, fm={"sre": "---\nname: ops\nmodel: opus\neffort: xhigh\n---\n"})
    assert st("AGENT-1").status == FAIL


def test_agent_1_fault_no_frontmatter(w):
    _agents(w, fm={"sre": "# SRE\nname: sre\n"})
    assert st("AGENT-1").status == FAIL


def test_agent_1_fault_manifest_misses_agent(w):
    _agents(w, listed=("sre",))
    r = st("AGENT-1")
    assert r.status == WARN and "manifest:writer" in r.evidence


def test_agent_1_fault_stated_count(w):
    _agents(w, stated=11)
    assert st("AGENT-1").status == WARN


def test_agent_1_fault_contract_broken(w):
    _agents(w, fm={"sre": "---\nname: sre\nmodel: sonnet\neffort: xhigh\n---\n"})
    r = st("AGENT-1")
    assert r.status == WARN and "sre:model=sonnet" in r.evidence
