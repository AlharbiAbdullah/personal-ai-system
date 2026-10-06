"""
core.py: the registry, result type, roles, paths and shared helpers every check module uses.

Checks read the filesystem only through `P` (one Paths object, mutated in place), so the test
suite can point the whole harness at a fixture home with `set_home()` and nothing else changes.
"""

import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

# ── status + role constants ────────────────────────────────────────────────────
PASS, WARN, FAIL, SKIP = "PASS", "WARN", "FAIL", "SKIP"
PRODUCER, CONSUMER, SHARED = "producer", "consumer", "shared"

# A FAIL in one of these subsystems means the brain is BROKEN (load-bearing: data safety,
# runtime, storage, the producing pipeline, self-evolve, retrieval, hook execution, the coverage
# gate). A FAIL anywhere else is DEGRADED — a feature is off but data is safe.
BROKEN_SUBSYSTEMS = {
    "Data safety", "Environment", "Stores", "Pipeline",
    "Self-evolve", "Retrieval", "Hooks", "Self-test",
}

# Report order. A subsystem missing here sorts last, so a new one still prints.
SUBSYSTEM_ORDER = [
    "Data safety", "Environment", "Stores", "Pipeline", "Live capture", "Self-evolve",
    "Retrieval", "Hooks", "Identity", "Eval", "Config", "Harness", "Vault", "Code",
    "Auto-memory", "Skills", "Agents", "Workflows", "Jobs", "Drift", "External", "Self-test",
]


# ── component coverage maps (the coverage gate reads these) ─────────────────────
ASSERTED_COLLECTIONS = {"rai-semantic", "rai-episodic", "rai-daily", "rai-preferences"}
# v3 derived stores (rai-daily = live-capture index, rai-preferences = self-evolve dedup)
# may legitimately be empty on a fresh rebuild — only the CORE pair must hold data.
CORE_COLLECTIONS = {"rai-semantic", "rai-episodic"}
# Legacy/empty husks we KNOW about and have deliberately decided to leave (or drop). Anything live
# that is neither asserted nor tombstoned trips the coverage gate — that is how a silently-added
# store gets caught instead of rotting unwatched.
TOMBSTONED_COLLECTIONS = {"memories", "session_memory", "session_summaries"}
# STORE-3's permanent write probe. Kept (empty) between runs — never dropped (see store_roundtrip).
PROBE_COLLECTION = "sanity-probe"  # chromadb requires names start/end alphanumeric (no leading _)


class Paths:
    """Every filesystem root a check reads. `set()` re-derives them all from one home."""

    def __init__(self, home: Path):
        self.set(home)

    def set(self, home: Path):
        home = Path(home)
        real = home == Path.home()
        self.HOME = home
        self.HELM = home / "helm"
        self.RAI = self.HELM / "03-rai"
        self.SM = self.RAI / "semantic-memory"
        self.CHROMADB_DIR = self.SM / "chromadb"
        self.HOOKS = self.RAI / "hooks"
        self.WRAP = self.SM / "scripts" / "py-chroma.sh"
        self.BASELINE = self.RAI / ".sanity-baseline.json"
        self.STATUS_FILE = self.RAI / "memory" / "learning" / "system" / "sanity-last.json"
        self.DCLAUDE = home / ".claude"
        self.STATE = home / ".local" / "state"
        # hooks/lib/paths.py honours XDG_STATE_HOME for rai/runtime + rai/telemetry; mirror it
        # on the real home only, so a fixture home never reads the live machine's state
        xdg = os.environ.get("XDG_STATE_HOME") if real else None
        rai_state = (Path(xdg) if xdg else self.STATE) / "rai"
        self.RUNTIME = rai_state / "runtime"      # per-session hook runtime state
        self.TELEMETRY = rai_state / "telemetry"  # hook-perf.jsonl + counts-history.jsonl
        self.COORD_LOGS = self.STATE / "rai-maintenance" / "logs"
        self.BACKUP_STATUS = self.STATE / "backup-drive" / "status"
        self.SYSTEMD_USER = home / ".config" / "systemd" / "user"
        self.OPENCODE = home / ".config" / "opencode"
        self.PI = home / ".pi" / "agent"
        self.GEMINI = home / ".gemini"
        # the harness adapters write under XDG_DATA_HOME; mirror it on the real home only
        xdg_data = os.environ.get("XDG_DATA_HOME") if real else None
        data = Path(xdg_data) if xdg_data else home / ".local" / "share"
        self.SHADOWS = data / "rai" / "transcripts"   # one folder per adapter (opencode, agy)
        self.OPENCODE_DB = data / "opencode" / "opencode.db"
        self.DEVENV = home / "dev-env"
        self.TESTS = Path(__file__).resolve().parent.parent / "tests"


P = Paths(Path.home())


def set_home(home: Path):
    """Repoint every path at `home` (the test suite's fixture tree)."""
    P.set(home)


# the live hook modules (lib.*, route_preferences, index_daily, sync_claude_sessions) always come
# from the real vault, even when P points at a fixture
sys.path.insert(0, str(P.HOOKS))
sys.path.insert(0, str(P.HOOKS / "scripts"))


@dataclass
class R:
    id: str
    subsystem: str
    role: str
    status: str
    evidence: str = ""
    fix: str = ""


CHECKS = []  # (id, subsystem, role, slow, fn)


def check(id, subsystem, role=SHARED, slow=False):
    def deco(fn):
        CHECKS.append((id, subsystem, role, slow, fn))
        return fn
    return deco


# ── helpers ─────────────────────────────────────────────────────────────────────
def _client():
    import chromadb
    return chromadb.PersistentClient(path=str(P.CHROMADB_DIR))


def _collections():
    """name -> count for every live collection."""
    return {c.name: c.count() for c in _client().list_collections()}


def _age_hours(p: Path) -> float:
    return (time.time() - p.stat().st_mtime) / 3600


def _git(*args) -> str:
    r = subprocess.run(["git", "-C", str(P.HELM), *args], capture_output=True, text=True)
    return r.stdout.strip()


def _days_old(date_str: str) -> int:
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return (date.today() - d).days
    except Exception:
        return 9999


def systemctl_show(unit: str, *props: str) -> dict:
    """`systemctl --user show` as {prop: value}; timestamps come back as '@<epoch>' or ''.
    A unit systemd does not know reports UnitFileState=''. No bus at all raises."""
    r = subprocess.run(["systemctl", "--user", "show", unit, "--timestamp=unix",
                        *[f"--property={p}" for p in props]],
                       capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        raise RuntimeError(f"systemctl --user show {unit}: {r.stderr.strip()[:80]}")
    return dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)


def epoch_of(value: str) -> float | None:
    """'@1790380819' -> 1790380819.0; '' or 'n/a' -> None."""
    return float(value[1:]) if value and value.startswith("@") and value[1:].isdigit() else None


def link_state(link: Path, target: Path) -> str:
    """'ok' when `link` is a symlink resolving to `target`, else what it is instead."""
    if link.is_symlink():
        return "ok" if link.resolve() == target.resolve() else f"-> {link.resolve()}"
    return "real path" if link.exists() else "missing"


# the interpreter settings.json registers the hooks with, and the coordinator runs scripts with
SYSTEM_PYTHON = "python3"

_COMPILE_PROBE = """
import json, sys
bad = []
for f in sys.argv[1:]:
    try:
        compile(open(f, "rb").read(), f, "exec")
    except SyntaxError as e:
        bad.append(f"{f}:{e.lineno}")
print(json.dumps(bad))
"""


def compile_with(python: str, files: list) -> list:
    """Compile `files` under another interpreter; returns ['path:line', ...] for syntax errors.
    An interpreter that cannot run at all reports itself as the one bad entry."""
    if not files:
        return []
    r = subprocess.run([python, "-c", _COMPILE_PROBE, *map(str, files)],
                       capture_output=True, text=True, timeout=120)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        return [f"{python}:{(r.stderr.strip().splitlines() or ['did not run'])[-1][:60]}"]


# never scanned: VCS internals, virtualenvs, caches, the vector store, Obsidian's own state
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "chromadb", ".obsidian", ".trash"}


def vault_files(pattern: str, skip_top=()) -> list:
    """Files under helm matching `pattern`, outside SKIP_DIRS and the top folders in `skip_top`."""
    out = []
    for p in P.HELM.rglob(pattern):
        parts = p.relative_to(P.HELM).parts
        if parts[0] in skip_top or SKIP_DIRS & set(parts[:-1]) or not p.is_file():
            continue
        out.append(p)
    return out


_FM_KEY = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")


def frontmatter(text: str) -> dict | None:
    """The leading `---` block's top-level keys as {key: value}, or None when there is no block.
    Only the block counts: a `name:` further down (a YAML sample in a doc) is body text."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    out = {}
    for line in text[3:end].splitlines():
        m = _FM_KEY.match(line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("'\"")
    return out


def detect_role() -> str:
    env = os.environ.get("RAI_ROLE", "").strip().lower()
    if env in (PRODUCER, CONSUMER):
        return env
    return CONSUMER if platform.system() == "Darwin" else PRODUCER
