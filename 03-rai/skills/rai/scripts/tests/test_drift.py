"""Drift checks: docs that must keep matching the filesystem."""

from conftest import st
from sanity_checks.core import PASS, WARN

MANIFEST = "helm/03-rai/skills/MANIFEST.md"


def _skills(w, *names, routers=()):
    """Leaves by default; a router gets a routing table naming one sub-skill file."""
    for n in names:
        body = f"---\nname: {n}\n---\n"
        if n in routers:
            body += "## Routing table\n\n| Task | Sub-skill | File |\n|---|---|---|\n| x | sub | `sub.md` |\n"
            w.write(f"helm/03-rai/skills/{n}/sub.md", "---\nname: sub\n---\n")
        w.write(f"helm/03-rai/skills/{n}/SKILL.md", body)


def _manifest_rows(*rows, stated=None):
    head = f"{stated}\n\n" if stated else ""
    return head + "| Type | Skill |\n|---|---|\n" + "".join(f"| {t} | **{n}** | x |\n" for t, n in rows)


# DRIFT-1 ───────────────────────────────────────────────────────────────────────
def test_drift_1_ok(w):
    _skills(w, "rai", "remember", routers=("rai",))
    w.write(MANIFEST, _manifest_rows(("R", "rai"), ("L", "remember"), stated="2 skills: 1 routers and 1 leaves"))
    r = st("DRIFT-1")
    assert r.status == PASS, r.evidence


def test_drift_1_fault_row_missing(w):
    _skills(w, "rai", "recall", "fusion")
    w.write(MANIFEST, _manifest_rows(("L", "rai"), ("L", "recall")))
    r = st("DRIFT-1")
    assert r.status == WARN and "fusion" in r.evidence


def test_drift_1_fault_row_for_deleted_skill(w):
    _skills(w, "rai")
    w.write(MANIFEST, _manifest_rows(("L", "rai"), ("L", "ghost")))
    assert st("DRIFT-1").status == WARN


def test_drift_1_fault_wrong_type(w):
    _skills(w, "rai", routers=("rai",))
    w.write(MANIFEST, _manifest_rows(("L", "rai")))
    r = st("DRIFT-1")
    assert r.status == WARN and "rai:L->R" in r.evidence


def test_drift_1_fault_stated_count_stale(w):
    _skills(w, "rai", "remember", routers=("rai",))
    w.write(MANIFEST, _manifest_rows(("R", "rai"), ("L", "remember"), stated="3 skills: 2 routers and 1 leaves"))
    r = st("DRIFT-1")
    assert r.status == WARN and "stated" in r.evidence


# DRIFT-2 ───────────────────────────────────────────────────────────────────────
def test_drift_2_ok(w):
    w.write("helm/03-rai/hooks/session-start.py", "x")
    w.write("helm/AGENTS.md", "See `03-rai/hooks/session-start.py` and `~/elsewhere/x.md`.")
    assert st("DRIFT-2").status == PASS


def test_drift_2_fault_dead_path(w):
    w.write("helm/AGENTS.md", "See `03-rai/hooks/save-memory.py`.")
    r = st("DRIFT-2")
    assert r.status == WARN and "save-memory.py" in r.evidence


def test_drift_2_ok_rai_relative_paths(w):
    w.write("helm/03-rai/hooks/scripts/sync_claude_sessions.py", "x")
    w.write("helm/03-rai/harness/pi/README.md", "The scanner is `hooks/scripts/sync_claude_sessions.py`.")
    assert st("DRIFT-2").status == PASS


def test_drift_2_fault_identity_dead_route(w):
    w.write("helm/03-rai/identity/definitions.md", "Telos lives in `02-ana/telos.md`.")
    r = st("DRIFT-2")
    assert r.status == WARN and "telos.md" in r.evidence


def test_drift_2_ok_exempt_external_layout(w):
    w.write("helm/06-learning/example-rebuild/AGENTS.md", "The build repo has `src/example/app.py`.")
    assert st("DRIFT-2").status == PASS


# DRIFT-3 ───────────────────────────────────────────────────────────────────────
def test_drift_3_ok(w):
    w.write("helm/10-knowledge/Docker.md", "x")
    w.write("helm/.helm-index/helm-index.md", "[[Docker]] [[10-knowledge/Docker|alias]]")
    assert st("DRIFT-3").status == PASS


def test_drift_3_fault_dead_link(w):
    w.write("helm/.helm-index/helm-index.md", "[[Retired Course]]")
    r = st("DRIFT-3")
    assert r.status == WARN and "Retired Course" in r.evidence


def test_drift_3_fault_index_missing(w):
    assert st("DRIFT-3").status == WARN


# DRIFT-4: curated wikilinks ────────────────────────────────────────────────────
def test_drift_4_ok(w):
    w.write("helm/10-knowledge/Docker.md", "x")
    w.write("helm/02-ana/financial/investment/AGENTS.md", "rules")
    w.write("helm/10-knowledge/Build.md", "[[Docker|containers]] [[02-ana/financial/investment/AGENTS|AGENTS]] "
                                         "![[Docker.md]] `[[not a link]]`\n```\n[[also not]]\n```\n")
    w.write("helm/13-archive/old.md", "[[Long Gone]]")                          # a record
    w.write("helm/03-rai/semantic-memory/daily/2026-07-01.md", "[[project_x]]")   # a record
    w.write("helm/12-system/templates/Topic Note.md", "[[topic]]")                # a placeholder
    assert st("DRIFT-4").status == PASS


def test_drift_4_fault_dead_link(w):
    """ANA-07: the AGENTS.md rename left [[CLAUDE]] links pointing at nothing."""
    w.write("helm/03-rai/skills/investment/convene.md", "- [[CLAUDE]] · [[investment-moc]]")
    w.write("helm/02-ana/financial/investment/investment-moc.md", "x")
    r = st("DRIFT-4")
    assert r.status == WARN and "[[CLAUDE]]" in r.evidence


# DRIFT-5: router tables ────────────────────────────────────────────────────────
ROUTER = "---\nname: research\n---\n## Routing table\n\n| Task | Sub-skill | File to Read |\n|---|---|---|\n{rows}"


def _router(w, rows, files):
    w.write("helm/03-rai/skills/research/SKILL.md",
            ROUTER.format(rows="".join(f"| task, see progress.md | {r[:-3]} | `{r}` |\n" for r in rows)))
    for f in files:
        w.write(f"helm/03-rai/skills/research/{f}", f"# {f}\n")


def test_drift_5_ok(w):
    _router(w, ["web.md", "academic.md"], ["web.md", "academic.md"])
    w.write("helm/03-rai/skills/research/DESIGN.md", "---\ntitle: notes\n---\n")    # a doc, not a sub-skill
    w.write("helm/03-rai/skills/news-digest/SKILL.md", "---\nname: news-digest\n---\n")  # a leaf
    w.write("helm/03-rai/skills/news-digest/weekly_style.md", "# style reference\n")
    assert st("DRIFT-5").status == PASS


def test_drift_5_fault_unrouted_subskill(w):
    """SKILLS-15: research had 5 sub-skill files its table never routed to."""
    _router(w, ["web.md"], ["web.md", "academic.md"])
    r = st("DRIFT-5")
    assert r.status == WARN and "research/academic.md" in r.evidence


def test_drift_5_fault_dead_row(w):
    _router(w, ["web.md", "market.md"], ["web.md"])
    r = st("DRIFT-5")
    assert r.status == WARN and "market.md" in r.evidence


# DRIFT-6: Obsidian folders ─────────────────────────────────────────────────────
def _obsidian(w, templates="12-system/templates", attach="12-system/media"):
    w.mkdir("helm/12-system/templates")
    w.mkdir("helm/12-system/media")
    w.mkdir("helm/00-landing")
    w.json("helm/.obsidian/app.json", {"attachmentFolderPath": attach, "newFileFolderPath": "00-landing"})
    w.json("helm/.obsidian/templates.json", {"folder": templates})
    w.json("helm/.obsidian/plugins/templater-obsidian/data.json", {"templates_folder": templates})


def test_drift_6_ok(w):
    _obsidian(w)
    assert st("DRIFT-6").status == PASS


def test_drift_6_ok_relative_attachments(w):
    _obsidian(w, attach="./")
    assert st("DRIFT-6").status == PASS


def test_drift_6_skips_without_obsidian(w):
    from sanity_checks.core import SKIP
    assert st("DRIFT-6").status == SKIP


def test_drift_6_fault_renumbered_folder(w):
    """KNOW-V01/ROOT-04: templates pointed at '006 Extras/Templates' after the renumber."""
    _obsidian(w, templates="006 Extras/Templates")
    r = st("DRIFT-6")
    assert r.status == WARN and "006 Extras" in r.evidence


# DRIFT-7: cited check IDs ──────────────────────────────────────────────────────
def test_drift_7_ok(w):
    w.write("helm/12-system/tools/harnesses/settings.md",
            "Sanity CFG-1 checks the registration; cleanup DRIFT-28 and DRIFT-01 are audit findings.\n")
    w.write("helm/03-rai/skills/rai/scheduled/run.sh", '# sanity writes COORD-0 on abort\n')
    assert st("DRIFT-7").status == PASS


def test_drift_7_fault_retired_check_cited(w):
    """MEMRT-V03: docs kept citing sanity checks long after they were retired."""
    w.write("helm/03-rai/skills/GAPS.md", "Sanity HOOK-9 checks reality and surfaces doc drift.\n")
    r = st("DRIFT-7")
    assert r.status == WARN and "HOOK-9" in r.evidence


# DRIFT-8: tracked but ignored ──────────────────────────────────────────────────
def test_drift_8_ok(w):
    w.git_repo()
    w.write("helm/.gitignore", "scratch/\n")
    w.write("helm/scratch/x.txt", "x")
    assert st("DRIFT-8").status == PASS


def test_drift_8_fault_ignored_but_tracked(w):
    """GIT-03: workspace.json was gitignored but never untracked."""
    w.git_repo()
    w.write("helm/.obsidian/workspace.json", "{}")
    w.git("add", "-A")
    w.git("commit", "-q", "-m", "ws")
    w.write("helm/.gitignore", ".obsidian/workspace.json\n")
    r = st("DRIFT-8")
    assert r.status == WARN and "workspace.json" in r.evidence
