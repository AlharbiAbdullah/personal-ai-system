#!/usr/bin/env python3
"""
SessionStart Hook - Load Rai identity files + the frozen memory snapshot.

Memory v3 (Phase C): needs NO ChromaDB — the memory block is pre-rendered to
memory/state/memory-block.md by the drain (render_memory_block.py), and the live
layer's daily-log tail is a plain file read. Injection order is stable
(identity → helm-index → codemap → memory block → daily tail → status) so the
cacheable prefix is maximal. Warns when the identity surface exceeds its budget
(4KB/file, 44KB total) — advisory only, never truncates.

Emits a compact status line at the end so slow hooks / pending backlog are visible.
Graceful: missing files are skipped. Timeout: 8s.
"""

import json
import os
import re
import signal
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.hook_errors import log_error
from lib.hook_timer import hook_timer
from lib.paths import get_runtime_dir


def timeout_handler(signum, frame):
    print("Rai identity load timed out (8s)")
    sys.exit(0)


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(8)

PAI_DIR = Path.home() / "helm" / "03-rai"
IDENTITY_DIR = PAI_DIR / "identity"
SKILLS_DIR = PAI_DIR / "skills"
BRAIN_DIR = Path.home() / "helm"
TELOS_DIR = BRAIN_DIR / "02-ana"
CHROMADB_PATH = BRAIN_DIR / "03-rai" / "semantic-memory" / "chromadb"
PENDING_DIR = BRAIN_DIR / "03-rai" / "semantic-memory" / "pending"
IDENTITY_CACHE = get_runtime_dir() / "identity-cache.json"

PENDING_WARN = 20
CODEMAP_MAX_BYTES = 20_000
CODEMAP_MAX_WALKS = 3
HELM_INDEX_PATH = BRAIN_DIR / ".helm-index" / "helm-index.md"
HELM_INDEX_MAX_BYTES = 20_000

IDENTITY_DIRS = [IDENTITY_DIR, TELOS_DIR / "identity"]

MEMORY_BLOCK = PAI_DIR / "memory" / "state" / "memory-block.md"
DAILY_DIR = PAI_DIR / "semantic-memory" / "daily"
DAILY_TAIL_LINES = 60
IDENTITY_FILE_BUDGET = 4_096   # advisory per-file cap (bytes)
IDENTITY_TOTAL_BUDGET = 45056  # raised 40->44KB 2026-09-21 (deliberate identity growth); 32->40KB 2026-07-03 (M5); per-file 4KB stays strict


def _label_from_path(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()


def _discover_identity_files() -> list[tuple[str, Path]]:
    """Scan identity directories for *.md files. Returns sorted (label, path) pairs.

    Contract: anything in `03-rai/identity/` and `02-ana/identity/` auto-loads.
    Non-.md files (YAML or JSON kept there for one hook or skill) are skipped.
    """
    files: list[tuple[str, Path]] = []
    for d in IDENTITY_DIRS:
        if not d.exists():
            continue
        for path in sorted(d.glob("*.md")):
            files.append((_label_from_path(path), path))
    return files


def _sweep_orphans_safe() -> dict:
    """Clean orphan state files from crashed sessions. Never fail identity load."""
    try:
        from lib.state_sweep import sweep_orphans

        session_id = ""
        try:
            raw = sys.stdin.read() if not sys.stdin.isatty() else ""
            if raw:
                session_id = json.loads(raw).get("session_id", "")
        except (json.JSONDecodeError, OSError):
            pass
        return sweep_orphans(session_id, get_runtime_dir())
    except Exception as e:
        log_error("session-start", e, "orphan sweep")
        return {}


def _sources_max_mtime(files: list[tuple[str, Path]]) -> float:
    m = 0.0
    for _, path in files:
        try:
            if path.exists():
                m = max(m, path.stat().st_mtime)
        except OSError:
            pass
    return m


def _load_identity_cached() -> tuple[list[str], bool]:
    """Return (sections, was_cached). mtime-invalidated."""
    files = _discover_identity_files()
    max_mtime = _sources_max_mtime(files)
    cache_key = [str(p) for _, p in files]
    try:
        if IDENTITY_CACHE.exists():
            cache = json.loads(IDENTITY_CACHE.read_text())
            if (
                isinstance(cache, dict)
                and cache.get("max_mtime", 0.0) >= max_mtime
                and cache.get("files") == cache_key
                and isinstance(cache.get("sections"), list)
            ):
                return cache["sections"], True
    except Exception:
        pass

    sections: list[str] = []
    for label, path in files:
        try:
            text = path.read_text().strip()
        except Exception:
            text = ""
        if text:
            sections.append(f"## {label}\n{text}")

    try:
        IDENTITY_CACHE.parent.mkdir(parents=True, exist_ok=True)
        IDENTITY_CACHE.write_text(json.dumps({
            "max_mtime": max_mtime,
            "files": cache_key,
            "sections": sections,
        }))
    except Exception as e:
        log_error("session-start", e, "identity cache write")

    return sections, False


def _validate_skills() -> list[str]:
    """Return list of malformed-skill issues. Empty = all clean.

    Lightweight regex check (no yaml dep): each skill folder must hold a
    SKILL.md with --- frontmatter containing name: and description: fields.
    Catches the failure mode where a stricter Claude Code skill loader would
    reject the file and surface a transient "N skills didn't load" at launch.
    """
    issues: list[str] = []
    if not SKILLS_DIR.exists():
        return issues
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            issues.append(f"{skill_dir.name}: missing SKILL.md")
            continue
        try:
            txt = skill_md.read_text()
        except OSError:
            issues.append(f"{skill_dir.name}: unreadable SKILL.md")
            continue
        m = re.match(r"^---\n(.*?)\n---", txt, re.DOTALL)
        if not m:
            issues.append(f"{skill_dir.name}: no frontmatter")
            continue
        fm = m.group(1)
        if not re.search(r"^name:\s*\S", fm, re.MULTILINE):
            issues.append(f"{skill_dir.name}: missing 'name' field")
        if not re.search(r"^description:\s*[\|>]?\s*\S", fm, re.MULTILINE):
            issues.append(f"{skill_dir.name}: missing 'description' field")
    return issues


def _count_pending() -> int:
    if not PENDING_DIR.exists():
        return 0
    try:
        return sum(1 for _ in PENDING_DIR.glob("session_*.json"))
    except OSError:
        return 0


# Per-file budget exemptions (M5, John 2026-07-03): operational RULE files whose every
# line changes behavior — they don't digest without losing behavior. Still counted in TOTAL.
IDENTITY_BUDGET_EXEMPT = {"coding-format.md"}


def _identity_overbudget() -> list[str]:
    """Advisory budget check on the always-injected identity surface. Returns
    'name:bytes' offenders (per-file > IDENTITY_FILE_BUDGET) and a total marker
    when the sum exceeds IDENTITY_TOTAL_BUDGET. Never truncates anything."""
    offenders: list[str] = []
    total = 0
    for _, path in _discover_identity_files():
        try:
            size = path.stat().st_size
        except OSError:
            continue
        total += size
        if size > IDENTITY_FILE_BUDGET and path.name not in IDENTITY_BUDGET_EXEMPT:
            offenders.append(f"{path.name}:{size}")
    if total > IDENTITY_TOTAL_BUDGET:
        offenders.append(f"TOTAL:{total}")
    return offenders


def _daily_tail() -> str:
    """Tail of today's live-capture log (+ yesterday's when today is thin) —
    the Hermes 'daily log in the snapshot' pattern."""
    from datetime import date, timedelta

    parts: list[str] = []
    today = DAILY_DIR / f"{date.today().isoformat()}.md"
    yesterday = DAILY_DIR / f"{(date.today() - timedelta(days=1)).isoformat()}.md"
    today_lines: list[str] = []
    if today.exists():
        try:
            today_lines = today.read_text().strip().splitlines()
        except OSError:
            pass
    if len([l for l in today_lines if l.strip()]) < 5 and yesterday.exists():
        try:
            y = yesterday.read_text().strip().splitlines()[-DAILY_TAIL_LINES:]
            parts.append(f"_{yesterday.stem} (yesterday):_\n" + "\n".join(y))
        except OSError:
            pass
    if today_lines:
        parts.append("\n".join(today_lines[-DAILY_TAIL_LINES:]))
    if not parts:
        return ""
    return "## Live log (turn-capture)\n" + "\n\n".join(parts)


def find_codemap(cwd: Path) -> Path | None:
    """Walk up from cwd looking for .codemap/codemap.md. Checks cwd + up to CODEMAP_MAX_WALKS parents."""
    try:
        cur = cwd.resolve()
    except OSError:
        return None
    for _ in range(CODEMAP_MAX_WALKS + 1):
        candidate = cur / ".codemap" / "codemap.md"
        try:
            if candidate.is_file() and candidate.stat().st_size <= CODEMAP_MAX_BYTES:
                return candidate
        except OSError:
            pass
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def find_helm_index() -> Path | None:
    try:
        if HELM_INDEX_PATH.is_file() and HELM_INDEX_PATH.stat().st_size <= HELM_INDEX_MAX_BYTES:
            return HELM_INDEX_PATH
    except OSError:
        pass
    return None


def main():
    sweep_counts = _sweep_orphans_safe()

    if not PAI_DIR.exists():
        sys.exit(0)

    sections, was_cached = _load_identity_cached()

    cwd = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    helm_index_path = find_helm_index()
    if helm_index_path:
        try:
            helm_index_text = helm_index_path.read_text().strip()
            if helm_index_text:
                sections.append(f"## Helm Index\n{helm_index_text}")
        except OSError as e:
            log_error("session-start", e, "helm-index load")

    codemap_path = find_codemap(cwd)
    if codemap_path:
        try:
            codemap_text = codemap_path.read_text().strip()
            if codemap_text:
                sections.append(f"## Codemap ({codemap_path.parent.parent})\n{codemap_text}")
        except OSError as e:
            log_error("session-start", e, "codemap load")

    # Frozen memory snapshot (Memory v3): pre-rendered by the drain, plain file read.
    mem_block = ""
    try:
        if MEMORY_BLOCK.exists():
            mem_block = MEMORY_BLOCK.read_text().strip()
    except OSError as e:
        log_error("session-start", e, "memory block read")
    if mem_block:
        sections.append(mem_block)

    try:
        daily = _daily_tail()
    except Exception as e:
        log_error("session-start", e, "daily tail")
        daily = ""
    if daily:
        sections.append(daily)

    # Surface the last /sanity verdict (written by the Ubuntu coordinator's post-run check and
    # synced here). A sick brain the producer caught becomes the FIRST thing seen at session start
    # — the direct cure for "the brain was sick for months and I didn't know."
    sanity_verdict = None
    try:
        import json as _json
        sp = PAI_DIR / "memory" / "learning" / "system" / "sanity-last.json"
        if sp.exists():
            s = _json.loads(sp.read_text())
            sanity_verdict = s.get("verdict")
            # A verdict's age is part of the verdict. The coordinator rewrites this file
            # every cycle (4x/day); past 30h (DATA-2's missed-cycle floor) it has stopped
            # running, and a HEALTHY written days ago says nothing about today. Sep 2026:
            # the runner died at step 0 for 2.5 days and this file said HEALTHY throughout.
            try:
                age_h = (datetime.now() - datetime.fromisoformat(s.get("ts", ""))).total_seconds() / 3600
            except (TypeError, ValueError):
                age_h = None
            stale = age_h is not None and age_h > 30
            if stale and sanity_verdict == "HEALTHY":
                sanity_verdict = "STALE"
            if sanity_verdict and sanity_verdict != "HEALTHY":
                fails = s.get("fails", [])
                warns = s.get("warns", [])
                rows = [f"  ✗ {f.get('id')} [{f.get('subsystem')}]: {f.get('evidence', '')}" for f in fails[:6]]
                rows += [f"  ⚠ {w.get('id')} [{w.get('subsystem')}]: {w.get('evidence', '')}" for w in warns[:6]]
                if stale:
                    rows.insert(0, f"  ✗ STALE [Coordinator]: last written {s.get('ts', '?')}, "
                                   f"{age_h:.0f}h ago; the maintenance runner has missed cycles "
                                   f"(check `systemctl --user status rai-maintenance.service` on Linux)")
                counts = s.get("counts", {})
                banner = (
                    f"## ⚠️ BRAIN SANITY: {sanity_verdict} "
                    f"({counts.get('FAIL', 0)} FAIL · {counts.get('WARN', 0)} WARN · "
                    f"checked {s.get('ts', '?')} on {s.get('role', '?')})\n"
                    + "\n".join(rows)
                    + "\nRun `/sanity` for the full report and fixes."
                )
                sections.insert(0, banner)
    except Exception as e:
        log_error("session-start", e, "sanity banner")

    pending = _count_pending()

    if sections:
        tag = "cached" if was_cached else "fresh"
        print(f"=== Rai Identity Loaded ({tag}) ===\n")
        print("\n\n".join(sections))
        print("\n=== End Rai Identity ===")

    skill_issues = _validate_skills()
    if skill_issues:
        print("\n[skill-validator] Malformed SKILL.md files:")
        for issue in skill_issues:
            print(f"  - {issue}")

    swept = sum(sweep_counts.values()) if sweep_counts else 0
    status_bits = [f"memory={'v3-frozen' if mem_block else 'no-block(run /process-sessions)'}",
                   f"identity={tag if sections else 'none'}"]
    overbudget = _identity_overbudget()
    if overbudget:
        status_bits.append(f"WARN identity_overbudget={','.join(overbudget)}")
    if sanity_verdict and sanity_verdict != "HEALTHY":
        status_bits.append(f"SANITY={sanity_verdict}")
    if swept:
        status_bits.append(f"orphans_swept={swept}")
    if pending:
        status_bits.append(f"pending={pending}")
        if pending >= PENDING_WARN:
            status_bits.append("WARN: run /process-sessions")
    if skill_issues:
        status_bits.append(f"skills_bad={len(skill_issues)}")
    print(f"[rai] {' '.join(status_bits)}")

    _warm_embeddings()


def _warm_embeddings():
    """Detached warmup so memory-injection's FIRST prompt query finds the embedding
    model page-cached instead of dying on its 2s alarm (M3 cold-start fix). Fire and
    forget — session start itself stays ChromaDB-free."""
    wrap = PAI_DIR / "semantic-memory" / "scripts" / "py-chroma.sh"
    if not wrap.exists():
        return
    code = ("import sys; sys.path.insert(0, str(__import__('pathlib').Path.home()/'helm'/'03-rai'/'hooks'));"
            "from lib.memory_retrieval import query_semantic; query_semantic('warmup', top_k=1)")
    try:
        subprocess.Popen(
            ["bash", str(wrap), "-c", code],
            start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
        )
    except Exception as e:
        log_error("session-start", e, "embedding warmup")


if __name__ == "__main__":
    with hook_timer("session-start"):
        try:
            main()
        except Exception as e:
            log_error("session-start", e, "main")
