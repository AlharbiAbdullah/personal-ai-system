"""Workflows checks: FLOW-1..7 over 11-workflows/."""

from conftest import st
from sanity_checks.core import FAIL, PASS, WARN

GOOD = """# Debugging

**Use when:** a bug in code.
**Not for:** a machine incident (25 incident).
**Done when:** the repro no longer triggers the bug.

Short intro.

## Steps

### 1. Reproduce

- [ ] Run `/testing → tdd` and `/git → commit`.
- [ ] Stuck: hand the diagnosis to the `debugger` agent.
- [ ] Next: [[05-code-review]].
"""

REVIEW = GOOD.replace("# Debugging", "# Code review").replace("[[05-code-review]]", "[[04-debugging]]")

TABLE = "| # | Workflow | Use when |\n|---|---|---|\n| 04 | debugging | x |\n| 05 | code review | x |\n"
INDEX = "# Helm\n\n## 11-workflows/\n\n" + TABLE + "\n## 12-system/\n"


def _world(w, files=None, table=TABLE, index=INDEX):
    """Two workflows, their skills and agent, the AGENTS.md table and the helm index."""
    files = files if files is not None else {"04-debugging.md": GOOD, "05-code-review.md": REVIEW}
    for name, text in files.items():
        w.write(f"helm/11-workflows/{name}", text)
    w.write("helm/11-workflows/AGENTS.md", "# 11-workflows\n\n" + table)
    w.write("helm/.helm-index/helm-index.md", index)
    for rel in ("testing/SKILL.md", "testing/tdd.md", "git/SKILL.md", "git/commit.md"):
        w.write(f"helm/03-rai/skills/{rel}", "---\nname: x\n---\n")
    w.write("helm/03-rai/agents/debugger.md", "---\nname: debugger\n---\n")
    w.write("helm/03-rai/agents/MANIFEST.md", "# Agents\n")


# FLOW-1 ────────────────────────────────────────────────────────────────────────
def test_flow_1_ok(w):
    _world(w)
    r = st("FLOW-1")
    assert r.status == PASS, r.evidence


def test_flow_1_ok_paths_and_external_skills_are_not_skill_refs(w):
    text = GOOD + "- [ ] Read `/home/john/helm/x.md`, run `/deep-research` and `/sdd`.\n"
    _world(w, files={"04-debugging.md": text, "05-code-review.md": REVIEW})
    r = st("FLOW-1")
    assert r.status == PASS, r.evidence


def test_flow_1_fault_unknown_router(w):
    _world(w, files={"04-debugging.md": GOOD + "- [ ] Run `/news day`.\n", "05-code-review.md": REVIEW})
    r = st("FLOW-1")
    assert r.status == FAIL and "/news" in r.evidence


def test_flow_1_fault_unknown_sub_skill(w):
    _world(w, files={"04-debugging.md": GOOD + "- [ ] Run `/git → rebase-all`.\n", "05-code-review.md": REVIEW})
    r = st("FLOW-1")
    assert r.status == FAIL and "rebase-all" in r.evidence


def test_flow_1_fault_no_workflows(w):
    w.mkdir("helm/11-workflows")
    assert st("FLOW-1").status == FAIL


# FLOW-2 ────────────────────────────────────────────────────────────────────────
def test_flow_2_ok(w):
    _world(w)
    r = st("FLOW-2")
    assert r.status == PASS and "1/1" in r.evidence, r.evidence


def test_flow_2_ok_builtin_type(w):
    text = GOOD + "- [ ] Fan out read-only lanes with the `Explore` agent.\n"
    _world(w, files={"04-debugging.md": text, "05-code-review.md": REVIEW})
    assert st("FLOW-2").status == PASS


def test_flow_2_ok_reports_unnamed_agents(w):
    _world(w)
    w.write("helm/03-rai/agents/sre.md", "---\nname: sre\n---\n")
    r = st("FLOW-2")
    assert r.status == PASS and "unnamed: sre" in r.evidence


def test_flow_2_fault_unknown_agent(w):
    text = GOOD + "- [ ] Hand it to the `wizard` agent.\n"
    _world(w, files={"04-debugging.md": text, "05-code-review.md": REVIEW})
    r = st("FLOW-2")
    assert r.status == FAIL and "wizard" in r.evidence


# FLOW-3 ────────────────────────────────────────────────────────────────────────
def test_flow_3_ok(w):
    _world(w)
    w.write("helm/12-system/templates/Seed.md", "---\nx: y\n---\n")
    text = GOOD + "- [ ] Capture a [[Seed]], see [[11-workflows/AGENTS|the rules]] and [[05-code-review#Steps]].\n"
    w.write("helm/11-workflows/04-debugging.md", text)
    r = st("FLOW-3")
    assert r.status == PASS, r.evidence


def test_flow_3_fault_dead_link(w):
    _world(w, files={"04-debugging.md": GOOD + "- [ ] See [[03-kitchen]].\n", "05-code-review.md": REVIEW})
    r = st("FLOW-3")
    assert r.status == FAIL and "03-kitchen" in r.evidence


# FLOW-4 ────────────────────────────────────────────────────────────────────────
def test_flow_4_ok(w):
    _world(w)
    r = st("FLOW-4")
    assert r.status == PASS, r.evidence


def test_flow_4_fault_missing_from_table(w):
    _world(w, table="| 04 | debugging | x |\n")
    r = st("FLOW-4")
    assert r.status == FAIL and "AGENTS.md lacks 05" in r.evidence


def test_flow_4_fault_row_without_file(w):
    _world(w, table=TABLE + "| 19 | bot go-live | x |\n")
    r = st("FLOW-4")
    assert r.status == FAIL and "row 19 has no file" in r.evidence


def test_flow_4_fault_missing_from_helm_index(w):
    _world(w, index="# Helm\n\n## 11-workflows/\n\n| 04 | debugging | x |\n\n## 12-system/\n")
    r = st("FLOW-4")
    assert r.status == FAIL and "helm index lacks 05" in r.evidence


# FLOW-5 ────────────────────────────────────────────────────────────────────────
def test_flow_5_ok(w):
    _world(w)
    assert st("FLOW-5").status == PASS


def test_flow_5_fault_line_citation(w):
    text = GOOD + "- [ ] The rule sits at `plan.md:43`.\n"
    _world(w, files={"04-debugging.md": text, "05-code-review.md": REVIEW})
    r = st("FLOW-5")
    assert r.status == FAIL and "plan.md:43" in r.evidence


# FLOW-6 ────────────────────────────────────────────────────────────────────────
def test_flow_6_ok(w):
    _world(w)
    r = st("FLOW-6")
    assert r.status == PASS, r.evidence


def test_flow_6_fault_old_header(w):
    old = GOOD.replace("**Use when:** a bug in code.", "**Triggered by:** \"let's debug this\"")
    _world(w, files={"04-debugging.md": old, "05-code-review.md": REVIEW})
    r = st("FLOW-6")
    assert r.status == FAIL and "Use when x0" in r.evidence


def test_flow_6_fault_duplicate_header_line(w):
    dup = GOOD.replace("**Done when:**", "**Done when:** a.\n**Done when:**")
    _world(w, files={"04-debugging.md": dup, "05-code-review.md": REVIEW})
    r = st("FLOW-6")
    assert r.status == FAIL and "Done when x2" in r.evidence


def test_flow_6_fault_no_title(w):
    _world(w, files={"04-debugging.md": "\n" + GOOD, "05-code-review.md": REVIEW})
    r = st("FLOW-6")
    assert r.status == FAIL and "no title" in r.evidence


# FLOW-7 ────────────────────────────────────────────────────────────────────────
def test_flow_7_ok(w):
    _world(w)
    assert st("FLOW-7").status == PASS


def test_flow_7_fault_open_gap_block(w):
    gap = GOOD + "\n> **GAP Q04.1:** who drives the diagnosis?\n"
    _world(w, files={"04-debugging.md": gap, "05-code-review.md": REVIEW})
    r = st("FLOW-7")
    assert r.status == WARN and "1 open GAP" in r.evidence
