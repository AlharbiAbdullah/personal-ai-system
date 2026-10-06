"""The attempt sandbox: bubblewrap with `~/helm` as an overlay of a vault snapshot.

What an attempt can and cannot reach:
- The snapshot is `git archive HEAD` of the live vault, scrubbed of the benchmark: the
  `03-rai/benchmark/` folder is removed, and archived sessions, memory lines and ChromaDB
  documents that mention the benchmark are dropped, so no attempt reads hidden tests, solutions,
  rubrics or expected answers, even through Rai's own memory.
- Each attempt writes into its own overlay upper dir; the live vault is never touched. The
  grader reads the result through FileView.
- ChromaDB is one scrubbed, writable copy per run, bound in, so memory reads cost no copy-up.
- `$HOME` is a throwaway overlay: stray config and cache writes are discarded. `~/.cache` is an
  empty tmpfs (the uv cache shows through a throwaway overlay), which hides the bench's own
  cache and any build scratch.
- `/run/user/$UID` and the session bus are hidden: no systemd --user, no desktop, no browser
  bridge, no 1Password socket. Rai's runtime state (XDG_STATE_HOME) goes to scratch.
- `~/.claude` stays live and writable, so an OAuth refresh inside a run persists; its session
  records (projects, history, sessions, backups...) are bound to scratch.
"""

import hashlib
import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import paths

# Claude Code session records under ~/.claude: bound to per-attempt scratch.
CLAUDE_SCRATCH = ("projects", "sessions", "session-env", "file-history", "shell-snapshots",
                  "todos", "paste-cache", "backups", "plans")
CLAUDE_SCRATCH_FILES = ("history.jsonl", "stats-cache.json")
CHROMA_REL = "03-rai/semantic-memory/chromadb"
# Writes the plumbing makes inside the vault, never counted as the agent's changes: the vector
# store, and the skills Claude Code syncs from claude.ai at startup (~/.claude/skills -> vault).
IGNORE_WRITES = (CHROMA_REL + "/", "03-rai/skills/synced/")
# Text that marks benchmark content. Anything in Rai's memory carrying it is scrubbed from the
# snapshot, so expected answers never reach an attempt through recall.
MARKERS = ("03-rai/benchmark", "bench_lib", "bench.py", "rai benchmark", "hidden_tests")
SCRUB_FILES = ("13-archive/historical-sessions",)                       # whole files dropped
SCRUB_LINES = ("03-rai/semantic-memory/daily", "03-rai/semantic-memory/index",
               "03-rai/auto-memory", "03-rai/identity")                  # matching lines dropped
UNREADABLE = b"\0<unreadable>\0"


def rmtree(p: Path) -> None:
    """Remove a sandbox tree. Overlayfs leaves its work dir at mode 000, so make every dir
    writable first, or a plain rmtree fails half-way."""
    if p.exists():
        subprocess.run(["chmod", "-R", "u+rwX", str(p)], capture_output=True)
        shutil.rmtree(p, ignore_errors=True)


def _read(p: Path) -> bytes | None:
    try:
        return p.read_bytes() if p.is_file() else None
    except OSError:
        return UNREADABLE


# ---------------------------------------------------------------- snapshot

def _has_marker(data: bytes) -> bool:
    low = data.lower()
    return any(m.encode() in low for m in MARKERS)


def scrub(snap: Path) -> dict:
    """Drop benchmark content from Rai's memory in the snapshot. Returns counts per kind."""
    out = {"files": 0, "lines": 0}
    shutil.rmtree(snap / "03-rai" / "benchmark", ignore_errors=True)
    for rel in SCRUB_FILES:
        for f in (snap / rel).rglob("*") if (snap / rel).is_dir() else []:
            if f.is_file() and _has_marker(f.read_bytes()):
                f.unlink()
                out["files"] += 1
    for rel in SCRUB_LINES:
        for f in (snap / rel).rglob("*") if (snap / rel).is_dir() else []:
            if not f.is_file():
                continue
            data = f.read_bytes()
            if not _has_marker(data):
                continue
            lines = data.split(b"\n")
            keep = [ln for ln in lines if not _has_marker(ln)]
            out["lines"] += len(lines) - len(keep)
            f.write_bytes(b"\n".join(keep))
    return out


CHROMA_SCRUB = """
import sys, chromadb
c = chromadb.PersistentClient(path=sys.argv[1])
n = 0
for col in c.list_collections():
    col = c.get_collection(getattr(col, "name", col))
    for m in sys.argv[2:]:
        got = col.get(where_document={"$contains": m}, include=[])
        if got["ids"]:
            col.delete(ids=got["ids"])
            n += len(got["ids"])
print(n)
"""


def build_snapshot(dest: Path, helm: Path | None = None) -> Path:
    """dest/helm: the vault at HEAD, scrubbed; dest/chroma: a scrubbed copy of the vector store.
    Idempotent: a finished snapshot carries dest/.done and is reused."""
    helm = helm or paths.helm()
    snap = dest / "helm"
    if (dest / ".done").exists():
        return snap
    rmtree(dest)
    snap.mkdir(parents=True)
    head = subprocess.run(["git", "-C", str(helm), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    arch = subprocess.Popen(["git", "-C", str(helm), "archive", "--format=tar", head], stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(snap)], stdin=arch.stdout, check=True)
    arch.stdout.close()
    if arch.wait() != 0:
        raise RuntimeError("git archive failed")
    counts = scrub(snap)
    (snap / CHROMA_REL).mkdir(parents=True, exist_ok=True)          # mount point for the copy
    chroma = helm / CHROMA_REL
    if chroma.is_dir():
        subprocess.run(["cp", "-a", "--reflink=auto", str(chroma), str(dest / "chroma")], check=True)
        wrapper = helm / "03-rai" / "semantic-memory" / "scripts" / "py-chroma.sh"
        script = dest / "chroma-scrub.py"
        script.write_text(CHROMA_SCRUB)
        r = subprocess.run([str(wrapper), str(script), str(dest / "chroma"), *MARKERS],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(f"ChromaDB scrub failed: {r.stderr.strip()[-300:]}")
        counts["chroma_docs"] = int((r.stdout.strip().splitlines() or ["0"])[-1])
    (dest / ".done").write_text(f"{head}\n{counts}\n")
    return snap


# ---------------------------------------------------------------- attempt layout

@dataclass
class Attempt:
    root: Path              # ~/.cache/rai-bench/runs/<run>/att/<key>
    snapshot: Path          # the run's snapshot helm/
    cwd_kind: str           # helm | work
    seeded: dict = field(default_factory=dict)    # rel -> bytes planted before the run
    chroma: Path | None = None                    # the run's writable ChromaDB copy

    @property
    def upper(self) -> Path:
        return self.root / "upper"

    @property
    def ovwork(self) -> Path:
        return self.root / "ovwork"

    @property
    def work(self) -> Path:
        return self.root / "work"

    @property
    def scratch(self) -> Path:
        return self.root / "scratch"

    @property
    def cwd(self) -> Path:
        """The attempt's working folder as the harness sees it."""
        return paths.home() / "helm" if self.cwd_kind == "helm" else self.work

    def cwd_root(self) -> Path:
        """Where seeded files land on disk before the run."""
        return self.upper if self.cwd_kind == "helm" else self.work


def project_slug(p: Path) -> str:
    """Claude Code's folder name for a project path under ~/.claude/projects."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(p))


def prepare(root: Path, snapshot: Path, task, extra_files: dict | None = None) -> Attempt:
    """Fresh attempt dirs; plant setup files, the coding starter, and any harness context file."""
    rmtree(root)
    chroma = snapshot.parent / "chroma"
    att = Attempt(root, snapshot, task.cwd, chroma=chroma if chroma.is_dir() else None)
    for d in (att.upper, att.ovwork, att.work, att.scratch / "state"):
        d.mkdir(parents=True)
    for name in CLAUDE_SCRATCH:
        (att.scratch / "claude" / name).mkdir(parents=True)
    for name in CLAUDE_SCRATCH_FILES:
        (att.scratch / "claude" / name).touch()
    # his auto-memory, as Claude Code mounts it for the vault project
    mem = att.scratch / "claude" / "projects" / project_slug(paths.home() / "helm") / "memory"
    mem.parent.mkdir(parents=True)
    mem.symlink_to(paths.home() / "helm" / "03-rai" / "auto-memory")
    if task.dir and (task.dir / "starter").is_dir():
        shutil.copytree(task.dir / "starter", att.work, dirs_exist_ok=True)
    plant = dict((task.setup or {}).get("files", {}))
    plant.update(extra_files or {})
    for rel, text in plant.items():
        p = att.cwd_root() / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        data = text.encode() if isinstance(text, str) else text
        p.write_bytes(data)
        att.seeded[rel] = data
    if att.cwd_kind == "work":
        att.seeded = {**_manifest(att.work), **att.seeded}
    return att


def _manifest(d: Path) -> dict:
    return {str(p.relative_to(d)): _read(p) for p in d.rglob("*") if p.is_file() and not p.is_symlink()}


# ---------------------------------------------------------------- bubblewrap

def bwrap_argv(att: Attempt, harness: str, argv: list, net: bool = True) -> list:
    """The full command line that runs `argv` inside the attempt's sandbox. Order matters:
    later mounts sit on top of earlier ones."""
    h = paths.home()
    uid = os.getuid()
    # own PID namespace: when the harness exits, every process it left behind dies with it
    a = ["bwrap", "--die-with-parent", "--unshare-pid", "--ro-bind", "/", "/", "--dev", "/dev",
         "--proc", "/proc", "--tmpfs", "/tmp"]
    for private in (Path(f"/run/user/{uid}"), Path("/run/dbus")):
        if private.is_dir():
            a += ["--tmpfs", str(private)]
    a += ["--overlay-src", str(h), "--tmp-overlay", str(h)]
    a += ["--overlay-src", str(att.snapshot), "--overlay", str(att.upper), str(att.ovwork), str(h / "helm")]
    if att.chroma:
        a += ["--bind", str(att.chroma), str(h / "helm" / CHROMA_REL)]
    a += ["--tmpfs", str(h / ".cache")]
    if (h / ".cache" / "uv").is_dir():
        a += ["--overlay-src", str(h / ".cache" / "uv"), "--tmp-overlay", str(h / ".cache" / "uv")]
    a += ["--bind", str(att.root), str(att.root)]
    for hidden in _hidden_paths():
        a += ["--tmpfs", str(hidden)]
    a += ["--setenv", "XDG_STATE_HOME", str(att.scratch / "state"), "--setenv", "RAI_BENCH", "1",
          "--setenv", "PYTHONDONTWRITEBYTECODE", "1"]
    for var in ("DBUS_SESSION_BUS_ADDRESS", "WAYLAND_DISPLAY", "DISPLAY", "SSH_AUTH_SOCK"):
        a += ["--unsetenv", var]
    if harness == "claude-code":
        a += ["--bind", str(h / ".claude"), str(h / ".claude")]
        for name in CLAUDE_SCRATCH:
            a += ["--bind", str(att.scratch / "claude" / name), str(h / ".claude" / name)]
        for name in CLAUDE_SCRATCH_FILES:
            if (h / ".claude" / name).exists():
                a += ["--bind", str(att.scratch / "claude" / name), str(h / ".claude" / name)]
    elif harness == "pi":
        a += ["--bind", str(h / ".pi"), str(h / ".pi")]
        for sub in ("sessions", "rai-transcripts"):
            p = h / ".pi" / "agent" / sub
            if p.exists():
                (att.scratch / "pi" / sub).mkdir(parents=True, exist_ok=True)
                a += ["--bind", str(att.scratch / "pi" / sub), str(p)]
    elif harness == "opencode":
        for p in (h / ".local" / "share" / "opencode", h / ".config" / "opencode"):
            if p.exists():
                a += ["--bind", str(p), str(p)]
    if not net:
        a += ["--unshare-net"]
    a += ["--chdir", str(att.cwd), "--"]
    return a + list(argv)


def _hidden_paths() -> list:
    """Checkouts of the vault outside ~/helm and ~/.cache (build worktrees): an attempt must not
    read the benchmark folder through them."""
    out = []
    try:
        r = subprocess.run(["git", "-C", str(paths.helm()), "worktree", "list", "--porcelain"],
                           capture_output=True, text=True, timeout=10)
        cache = paths.home() / ".cache"
        for line in r.stdout.splitlines():
            if line.startswith("worktree "):
                p = Path(line.split(" ", 1)[1])
                if p != paths.helm() and p.exists() and cache not in p.parents:
                    out.append(p)
    except (OSError, subprocess.SubprocessError):
        pass
    return out


# ---------------------------------------------------------------- what the run changed

def _is_whiteout(p: Path) -> bool:
    try:
        st = p.lstat()
    except OSError:
        return False
    return stat.S_ISCHR(st.st_mode) and st.st_rdev == 0


def _is_opaque(p: Path) -> bool:
    """A dir the agent deleted and recreated: overlayfs hides the lower dir's content under it."""
    for attr in ("user.overlay.opaque", "trusted.overlay.opaque"):
        try:
            if os.getxattr(p, attr, follow_symlinks=False) == b"y":
                return True
        except OSError:
            continue
    return False


def _ignored(rel: str) -> bool:
    return rel.startswith(IGNORE_WRITES) or "__pycache__" in Path(rel).parts


class FileView:
    """The files after the run, the files before it, and what changed, relative to the cwd root."""

    def __init__(self, att: Attempt):
        self.att = att

    def before(self, rel: str) -> bytes | None:
        if rel in self.att.seeded:
            return self.att.seeded[rel]
        return _read(self.att.snapshot / rel) if self.att.cwd_kind == "helm" else None

    def after(self, rel: str) -> bytes | None:
        if self.att.cwd_kind == "work":
            return _read(self.att.work / rel)
        lower_hidden = False
        for par in reversed(Path(rel).parents):
            if str(par) == ".":
                continue
            up = self.att.upper / par
            if _is_whiteout(up):
                return None
            if up.is_dir() and _is_opaque(up):
                lower_hidden = True
        up = self.att.upper / rel
        if _is_whiteout(up):
            return None
        if up.is_file():
            return _read(up)
        return None if lower_hidden else _read(self.att.snapshot / rel)

    def exists(self, rel: str) -> bool:
        return self.after(rel) is not None

    def changes(self) -> list:
        """Files created, modified or deleted by the run (Rai's plumbing writes excluded)."""
        out = set()
        if self.att.cwd_kind == "work":
            now = _manifest(self.att.work)
            for rel in set(now) | set(self.att.seeded):
                if not _ignored(rel) and now.get(rel) != self.att.seeded.get(rel):
                    out.add(rel)
            return sorted(out)
        for p in self.att.upper.rglob("*"):
            rel = str(p.relative_to(self.att.upper))
            if _ignored(rel):
                continue
            if _is_whiteout(p):
                low = self.att.snapshot / rel
                if low.is_file() or rel in self.att.seeded:
                    out.add(rel)
                elif low.is_dir():
                    out |= {str(f.relative_to(self.att.snapshot)) for f in low.rglob("*") if f.is_file()}
            elif p.is_dir() and _is_opaque(p):
                low = self.att.snapshot / rel
                for f in low.rglob("*") if low.is_dir() else []:
                    frel = str(f.relative_to(self.att.snapshot))
                    if f.is_file() and not (self.att.upper / frel).is_file():
                        out.add(frel)
            elif p.is_file() and not p.is_symlink() and self.before(rel) != self.after(rel):
                out.add(rel)
        out |= {rel for rel in self.att.seeded if self.before(rel) != self.after(rel)}
        return sorted(r for r in out if not _ignored(r))


def digest(data: bytes | None) -> str:
    return "-" if data is None else hashlib.sha256(data).hexdigest()[:12]
