"""Drift: read-only doc-drift detection. WARN only: a doc going stale is never BROKEN."""

import json
import re
import subprocess

from . import core
from .core import PASS, SKIP, WARN, P, check, frontmatter

_PLACEHOLDER_TOKEN = re.compile(r"\b(YYYY|MM|DD|NNN|Www|WWW)\b")
_BACKTICK = re.compile(r"`([^`]+)`")
_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
# Files whose backticked strings describe an EXTERNAL repo's layout, not helm's (a project-init
# scaffold template, a lesson's build-repo contract) — real paths there, just not vault-relative.
_DRIFT2_EXEMPT = {"03-rai/skills/project-init/templates/AGENTS.md", "06-learning/example-rebuild/AGENTS.md"}
# beside every AGENTS.md: the architecture docs, the manual map, the pi harness README
_DRIFT2_DOCS = ("ARCHITECTURE.md", "MEMORY-ARCHITECTURE.md", "SYNC-ARCHITECTURE.md",
                "harness/pi/README.md", "../12-system/manual/README.md")


_ROUTE_HEADING = re.compile(r"^#+\s.*rout", re.I)
_MD_CELL = re.compile(r"`([\w./-]+\.md)`")
NOT_SUBSKILLS = {"SKILL.md", "MANIFEST.md", "GAPS.md", "README.md"}


def skill_dirs() -> list:
    """Skill folders (synced/ is the harness-managed anthropic-skills bucket, not a skill)."""
    root = P.RAI / "skills"
    return sorted(d for d in root.iterdir() if d.is_dir() and d.name != "synced" and (d / "SKILL.md").exists())


def routing_refs(text: str) -> list:
    """Backticked .md files in the last cell of table rows under a routing heading. A SKILL.md
    with none is a leaf; with some, a router."""
    refs, in_route = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            in_route = bool(_ROUTE_HEADING.match(line))
        elif in_route and line.lstrip().startswith("|"):
            refs += _MD_CELL.findall(line.strip().strip("|").split("|")[-1])
    return refs


@check("DRIFT-1", "Drift")
def skill_manifest_parity():
    """skills/MANIFEST.md has one row per skill folder, marks routers R and leaves L as their
    SKILL.md tables say, and its stated counts match the folders."""
    kinds = {d.name: "R" if routing_refs((d / "SKILL.md").read_text(errors="replace")) else "L" for d in skill_dirs()}
    text = (P.RAI / "skills/MANIFEST.md").read_text(errors="replace")
    rows = dict((n, t) for t, n in re.findall(r"\|\s*([RL])\s*\|\s*\*\*([\w-]+)\*\*", text))
    diff = sorted(rows.keys() - kinds.keys()) + sorted(kinds.keys() - rows.keys())
    diff += [f"{n}:{rows[n]}->{k}" for n, k in sorted(kinds.items()) if n in rows and rows[n] != k]
    stated = re.search(r"(\d+) skills: (\d+) routers and (\d+) leaves", text)
    real = (len(kinds), sum(k == "R" for k in kinds.values()), sum(k == "L" for k in kinds.values()))
    if stated and tuple(map(int, stated.groups())) != real:
        diff.append(f"stated {stated.group(0)!r}, real {real[0]}/{real[1]}/{real[2]}")
    ev = f"{real[0]} skill dirs ({real[1]} routers, {real[2]} leaves), {len(rows)} MANIFEST rows"
    return (WARN, ev + f" mismatch={diff[:5]}", "Fix the MANIFEST row, its R/L type or its count line.") if diff else (PASS, ev, "")


@check("DRIFT-2", "Drift")
def agents_paths_resolve():
    """Backticked vault paths resolve in the docs Rai reads as truth: every AGENTS.md, the
    architecture docs, the auto-loaded identity files, the manual map and the pi README."""
    files = [p for p in P.HELM.rglob("AGENTS.md")
             if ".git" not in p.parts and str(p.relative_to(P.HELM)) not in _DRIFT2_EXEMPT]
    files += [p for p in (P.RAI / n for n in _DRIFT2_DOCS) if p.exists()]
    files += sorted((P.RAI / "identity").glob("*.md")) + sorted((P.HELM / "02-ana/identity").glob("*.md"))
    missing = []
    for f in files:
        for raw in _BACKTICK.findall(f.read_text(errors="replace")):
            s = raw.split("#")[0].split("^")[0].rstrip("/")
            if (not s or " " in s or raw[:1] in "~/" or raw.startswith(".claude/") or "://" in s
                    or any(c in s for c in "<>{}*?$()|:=") or "/" not in s or _PLACEHOLDER_TOKEN.search(s)):
                continue
            if not any((base / s).exists() for base in (f.parent, P.HELM, P.RAI)):
                missing.append(f"{f.relative_to(P.HELM)}:{s}")
    ev = f"{len(files)} docs scanned, {len(missing)} dead path(s)"
    return (WARN, ev + f" {missing[:5]}", "Fix the path, or add a genuine exception to _DRIFT2_EXEMPT.") if missing else (PASS, ev, "")


@check("DRIFT-3", "Drift")
def helm_index_links_resolve():
    """Every wikilink in the session-injected helm-index resolves."""
    idx = P.HELM / ".helm-index/helm-index.md"
    if not idx.exists():
        return WARN, "helm-index.md missing", "Run /map-updater."
    stems = {p.stem for p in P.HELM.rglob("*.md") if ".git" not in p.parts}
    missing = []
    for raw in _WIKILINK.findall(idx.read_text(errors="replace")):
        t = raw.split("\\|")[0].split("|")[0].split("#")[0].split("^")[0].strip()
        if t and t.rsplit("/", 1)[-1] not in stems:
            missing.append(t)
    ev = f"{len(missing)} unresolved link(s)"
    return (WARN, ev + f" {missing[:5]}", "Fix the link, or run /map-updater to regenerate.") if missing else (PASS, ev, "")


# ── DRIFT-4: curated wikilinks ──────────────────────────────────────────────────
_WIKI_SKIP_TOP = ("13-archive", "08-bawaba")     # records keep the links they were written with
_WIKI_SKIP_PREFIX = ("03-rai/semantic-memory/", "03-rai/memory/", "12-system/templates/")
_WIKI_EXAMPLES = {"10-knowledge/AGENTS.md", "03-rai/skills/knowledge/insight.md"}  # teach the syntax
_FENCE = re.compile(r"```.*?```", re.S)
_INLINE_CODE = re.compile(r"`[^`\n]*`")


@check("DRIFT-4", "Drift")
def curated_wikilinks():
    """Wikilinks in curated notes resolve. Records (the archive, daily logs, digests, memory
    state) keep the links they were written with; templates hold placeholders."""
    files = core.vault_files("*")
    names = {p.name for p in files} | {p.stem for p in files}
    rels = {str(p.relative_to(P.HELM)) for p in files}
    rels |= {r.rsplit(".", 1)[0] for r in rels}
    dead, scanned = [], 0
    for p in files:
        rel = str(p.relative_to(P.HELM))
        if (p.suffix != ".md" or rel.split("/")[0] in _WIKI_SKIP_TOP
                or rel.startswith(_WIKI_SKIP_PREFIX) or rel in _WIKI_EXAMPLES):
            continue
        scanned += 1
        text = _INLINE_CODE.sub("", _FENCE.sub("", p.read_text(errors="replace")))
        for raw in _WIKILINK.findall(text):
            t = raw.split("|")[0].split("#")[0].split("^")[0].strip().rstrip("\\")
            if t and t.rsplit("/", 1)[-1] not in names and t not in rels:
                dead.append(f"{rel}: [[{t}]]")
    ev = f"{scanned} curated notes, {len(dead)} dead wikilink(s)"
    return (WARN, ev + f" {dead[:4]}", "Relink to the note's current name, or delink it.") if dead else (PASS, ev, "")


# ── DRIFT-5: router tables ──────────────────────────────────────────────────────
@check("DRIFT-5", "Drift")
def router_tables():
    """Router tables route both ways: every file a table names exists, and every sub-skill file
    in the folder is named by its table (an unrouted sub-skill is unreachable)."""
    dead, unrouted, routers = [], [], 0
    for rd in skill_dirs():
        refs = routing_refs((rd / "SKILL.md").read_text(errors="replace"))
        if not refs:
            continue  # a leaf: its sibling .md files are references, not sub-skills
        routers += 1
        dead += [f"{rd.name}: {r}" for r in refs if "/" not in r and not (rd / r).exists()]
        for sub in sorted(rd.glob("*.md")):
            fm = frontmatter(sub.read_text(errors="replace"))
            is_doc = fm is not None and "name" not in fm and "description" not in fm
            if sub.name not in NOT_SUBSKILLS and not is_doc and sub.name not in refs:
                unrouted.append(f"{rd.name}/{sub.name}")
    ev = f"{routers} router tables, {len(dead)} dead row(s), {len(unrouted)} unrouted sub-skill(s)"
    if dead or unrouted:
        return WARN, ev + f" {(dead + unrouted)[:4]}", "Add the sub-skill's row to its router table, or fix the row's file."
    return PASS, ev, ""


# ── DRIFT-6: the folders Obsidian writes into ───────────────────────────────────
_OBSIDIAN_FOLDERS = (
    ("app.json", "attachmentFolderPath"), ("app.json", "newFileFolderPath"),
    ("templates.json", "folder"), ("plugins/templater-obsidian/data.json", "templates_folder"),
    ("plugins/obsidian-excalidraw-plugin/data.json", "folder"),
)


@check("DRIFT-6", "Drift")
def obsidian_folders():
    """The folders Obsidian writes into exist: attachments, new notes, templates (core and
    Templater), Excalidraw. A renumbered folder sends new files to the vault root."""
    ob = P.HELM / ".obsidian"
    if not ob.is_dir():
        return SKIP, "no .obsidian config", ""
    dead, seen = [], 0
    for rel, key in _OBSIDIAN_FOLDERS:
        f = ob / rel
        try:
            val = json.loads(f.read_text()).get(key) if f.exists() else None
        except ValueError:
            dead.append(f"{rel} unparseable")
            continue
        if not isinstance(val, str) or not val or val.startswith("./") or val == "/":
            continue  # unset, or relative to the current note
        seen += 1
        if not (P.HELM / val).is_dir():
            dead.append(f"{rel} {key}={val!r}")
    ev = f"{seen} folder settings, {len(dead)} dead"
    return (WARN, ev + f" {dead}", "Point the setting at today's folder, with Obsidian closed (it rewrites its json on exit).") if dead else (PASS, ev, "")


# ── DRIFT-7: sanity check IDs cited in docs ─────────────────────────────────────
RESERVED_IDS = {"COORD-0"}   # written by the coordinator's abort path, not a registered check
_CHECK_ID = re.compile(r"\b([A-Z]{2,7})-(\d+)\b")
_ID_SKIP = ("03-rai/semantic-memory/", "03-rai/memory/", "03-rai/skills/rai/scripts/")


@check("DRIFT-7", "Drift")
def cited_check_ids():
    """Every sanity check ID cited on a line that mentions sanity exists. A doc citing a retired
    check reads as coverage that is not there (cleanup MEMRT-V03: K1, K2, I2)."""
    ids = {e[0] for e in core.CHECKS} | RESERVED_IDS
    # a family's IDs run 1..N. Audit findings share some family names but are zero-padded or run
    # past N (the cleanup's DRIFT-01..DRIFT-32), so a token counts only if it could be a check.
    top = {}
    for i in ids:
        fam, num = i.rsplit("-", 1)
        top[fam] = max(top.get(fam, 0), int(num))

    def could_be_check(fam, num):
        return fam in top and not num.startswith("0") and int(num) <= top[fam] + 5
    files = core.vault_files("*.md", skip_top=("13-archive",))
    files += [p for ext in ("*.py", "*.sh", "*.ts") for p in core.vault_files(ext, skip_top=("13-archive",))]
    bad = []
    for p in files:
        rel = str(p.relative_to(P.HELM))
        if rel.startswith(_ID_SKIP):
            continue
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if "sanity" in line.lower():
                bad += [f"{rel}:{n} {m.group(0)}" for m in _CHECK_ID.finditer(line)
                        if could_be_check(m.group(1), m.group(2)) and m.group(0) not in ids]
    ev = f"{len(files)} files, {len(bad)} citation(s) of a check that does not exist"
    return (WARN, ev + f" {bad[:4]}", "Cite the check that does the job today (sanity.py --list), or drop the claim.") if bad else (PASS, ev, "")


# ── DRIFT-8: tracked files the ignore rules exclude ─────────────────────────────
@check("DRIFT-8", "Drift")
def tracked_but_ignored():
    """No tracked file matches .gitignore. A rule added without `git rm --cached` keeps the file
    in every commit (cleanup GIT-03: workspace.json in 1 of 4 commits)."""
    r = subprocess.run(["git", "-C", str(P.HELM), "ls-files", "-ci", "--exclude-standard"],
                       capture_output=True, text=True, timeout=60)
    files = [l for l in r.stdout.splitlines() if l]
    if files:
        return WARN, f"{len(files)} tracked file(s) match .gitignore: {files[:4]}", "git rm --cached <file> (the ignore rule then holds)."
    return PASS, "no tracked file matches .gitignore", ""
