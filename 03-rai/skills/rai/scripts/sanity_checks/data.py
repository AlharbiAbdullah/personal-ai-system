"""Data safety: the git backup target, the coordinator heartbeat, loss tripwires, merge rules."""

import json
import re
import subprocess
import time
from pathlib import Path

from . import core
from .core import FAIL, PASS, PRODUCER, SKIP, WARN, P, check

# Sanity is step 3.5 and push is step 4, so every cycle that commits anything is *guaranteed* to
# look unpushed here. Only an unpushed commit older than a full cycle means the push actually
# failed. Cadence is 6h (04/10/16/22), +1h slack for a long run.
UNPUSHED_GRACE_H = 7
HEARTBEAT_WARN_H = 30       # last origin commit (coordinator runs 4x/day)
HEARTBEAT_FAIL_H = 72

# Paths the live hooks rewrite on every turn. A dirty tree here is the system working, not a
# backup risk — the maintenance cycle sweeps them into a commit 4x/day. Counted separately so
# DATA-1's evidence line shows real uncommitted work instead of a permanent floor of noise.
CHURN_PATHS = (
    ".obsidian/",
    "03-rai/memory/learning/",
    "03-rai/memory/state/",
    "03-rai/semantic-memory/pending/",
    "03-rai/semantic-memory/daily/",
)


def _is_churn(path: str) -> bool:
    # rename entries are "old -> new"; classify on the destination
    path = path.split(" -> ")[-1].strip().strip('"')
    return any(path.startswith(c) for c in CHURN_PATHS)


def _origin_idle_h(upstream: str) -> float:
    """Hours since the upstream tracking ref last moved (a push, or a fetch that brought
    commits), read from its reflog; without a reflog, the oldest unpushed commit's age."""
    line = core._git("reflog", "show", "--date=unix", "-n", "1", f"refs/remotes/{upstream}")
    m = re.search(r"@\{(\d+)\}", line)
    if m:
        return (time.time() - int(m.group(1))) / 3600
    epochs = [int(x) for x in core._git("log", "--format=%ct", "@{u}..HEAD").split() if x.isdigit()]
    return (time.time() - min(epochs)) / 3600 if epochs else 0.0


@check("DATA-1", "Data safety")
def git_backup():
    """origin is reachable, the branch tracks it, and pushes keep landing while we are ahead."""
    dirty = [l for l in core._git("status", "--porcelain").splitlines() if l]
    churn = [l for l in dirty if _is_churn(l[3:].strip().strip('"'))]
    real = len(dirty) - len(churn)
    # without an upstream `@{u}..HEAD` errors to empty stdout, which read as "nothing unpushed"
    upstream = core._git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    unpushed_lines = [l for l in core._git("log", "--oneline", "@{u}..HEAD").splitlines() if l]
    unpushed = len(unpushed_lines)
    remote_ok = subprocess.run(["git", "-C", str(P.HELM), "ls-remote", "--exit-code", "origin", "HEAD"],
                               capture_output=True).returncode == 0
    # How long origin has sat still while we are ahead tells a failed push from a mid-cycle one.
    # Commit dates cannot: a merged branch brings day-old commits that are only minutes unpushed.
    idle_h = _origin_idle_h(upstream) if unpushed else 0.0
    ev = (f"uncommitted={real} (+{len(churn)} churn), unpushed={unpushed}"
          f"{f' (origin idle {idle_h:.1f}h)' if unpushed else ''}, remote={'yes' if remote_ok else 'NO'}")
    if not remote_ok:
        return FAIL, ev, "Check network / `git remote -v` — no backup target reachable."
    if not upstream:
        return WARN, ev + ", no upstream", "The branch tracks nothing, so pushes go nowhere: `git branch -u origin/main`."
    if unpushed > 0 and core.detect_role() == PRODUCER and idle_h > UNPUSHED_GRACE_H:
        return WARN, ev, "Coordinator has unpushed commits older than one cycle — `cd ~/helm && git push`."
    return PASS, ev, ""


@check("DATA-2", "Data safety")
def heartbeat():
    """Coordinator pulse: origin should move every cycle (4x/day). A frozen HEAD = the whole
    pipeline stopped — the exact silent death we are guarding against."""
    epoch = core._git("log", "-1", "--format=%ct")
    if not epoch:
        return FAIL, "no commits", "Repo has no history — wrong directory?"
    age_h = (time.time() - int(epoch)) / 3600
    ev = f"last commit {age_h:.0f}h ago"
    if age_h > HEARTBEAT_FAIL_H:
        return FAIL, ev, "Coordinator likely DOWN >3d. Check systemd `rai-maintenance.timer` on Ubuntu."
    if age_h > HEARTBEAT_WARN_H:
        return WARN, ev, "No commit in >30h — coordinator may have missed cycles."
    return PASS, ev, ""


def md_count() -> int:
    return sum(1 for _ in P.HELM.rglob("*.md")
               if ".git/" not in str(_) and "node_modules/" not in str(_))


@check("DATA-3", "Data safety")
def baseline_drift():
    """The .md count and the chromadb size have not dropped against the baseline (the loss tripwire)."""
    md = md_count()
    chroma_kb = int(_git_du(P.CHROMADB_DIR) / 1024)
    cur = {"md_count": md, "chromadb_kb": chroma_kb}
    if not P.BASELINE.exists():
        return WARN, f"md={md}, chromadb={chroma_kb//1024}MB (no baseline)", "Run `/sanity --baseline` to set one."
    base = json.loads(P.BASELINE.read_text())
    worst, detail = 0.0, []
    for k, v in cur.items():
        old = base.get(k, 0)
        if not old:
            continue
        pct = (v - old) / old * 100
        detail.append(f"{k} {pct:+.0f}%")
        if pct < worst:
            worst = pct
    ev = ", ".join(detail) or "no comparable metrics"
    # Heuristic tripwire, not proof: catastrophic drop screams (data-loss guard the user demands),
    # smaller drops advise. Real loss also shows in DATA-1/git. Reset with --baseline after surgery.
    if worst < -40:
        return FAIL, ev, "Catastrophic drop — investigate `git status` + trash; reset baseline only once explained."
    if worst < -10:
        return WARN, ev, "Notable drop — possible accidental deletion, or expected post-cleanup (reset baseline)."
    return PASS, ev, ""


def _git_du(p: Path) -> int:
    total = 0
    for f in p.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


@check("DATA-4", "Data safety")
def gitattributes_union():
    """The append-only files both machines write must merge with union, or a Mac merge can
    silently clobber one side's entries (daily logs, scanner ledger, memory jsonl)."""
    ga = P.HELM / ".gitattributes"
    if not ga.exists():
        return WARN, ".gitattributes missing", "Restore it — append-only logs lose merge protection without it."
    txt = ga.read_text()
    required = [
        "03-rai/memory/**/*.jsonl",
        "03-rai/semantic-memory/daily/*.md",
        "03-rai/semantic-memory/processed-sessions.jsonl",
    ]
    missing = [r for r in required if r not in txt]
    ev = f"{len(required)-len(missing)}/{len(required)} union rules" + (f" — missing {missing}" if missing else "")
    return (WARN, ev, "Re-add the merge=union line — next two-sided merge may clobber entries.") if missing else (PASS, ev, "")


BACKUP_WARN_D = 8    # weekly: one missed run
BACKUP_FAIL_D = 15   # two missed runs


@check("DATA-5", "Data safety", role=PRODUCER)
def offsite_backup():
    """The weekly offsite backup of the vault and the home folders: the status line its
    runner writes says OK and is recent, and its timer still fires."""
    from .jobs import timer_health
    hard, soft = timer_health("backup-drive")
    if not P.BACKUP_STATUS.exists() and any("not installed" in h for h in hard):
        return SKIP, "no offsite backup set up (backup-drive timer not installed)", ""
    if not P.BACKUP_STATUS.exists():
        return FAIL, "no backup status on record", "Run ~/.local/bin/backup-drive once; see its log in ~/.local/state/backup-drive."
    day, _, outcome = P.BACKUP_STATUS.read_text().strip().partition(" ")
    age = core._days_old(day)
    ev = f"last backup {day} ({age}d ago) {outcome.split()[0] if outcome else '?'}"
    if hard or soft:
        ev += "; " + "; ".join(hard + soft)
    fix = "Rerun ~/.local/bin/backup-drive and read ~/.local/state/backup-drive/last-run.log."
    if outcome.startswith("FAIL") or age > BACKUP_FAIL_D:
        return FAIL, ev + (f": {outcome[5:80]}" if outcome.startswith("FAIL") else ""), fix
    if age > BACKUP_WARN_D or hard or soft:
        return WARN, ev, fix
    return PASS, ev, ""


BIG_WARN_MB = 50    # GitHub warns on push
BIG_FAIL_MB = 100   # GitHub rejects the push: every later backup push fails with it


@check("DATA-6", "Data safety")
def tracked_file_sizes():
    """No tracked file near GitHub's per-file limits. One file over 100 MB blocks every push, so
    origin stops being a backup without anything else looking wrong."""
    r = subprocess.run(["git", "-C", str(P.HELM), "ls-files", "-z"], capture_output=True, timeout=60)
    big = []
    for rel in filter(None, r.stdout.decode(errors="replace").split("\0")):
        try:
            size = (P.HELM / rel).lstat().st_size
        except OSError:
            continue
        if size >= BIG_WARN_MB * 1024 * 1024:
            big.append((size, rel))
    big.sort(reverse=True)
    top = [f"{rel} {size / 2**20:.0f}MB" for size, rel in big[:3]]
    if big and big[0][0] >= BIG_FAIL_MB * 1024 * 1024:
        return FAIL, f"{len(big)} file(s) >= {BIG_WARN_MB}MB: {top}", "Untrack it (git rm --cached + .gitignore) before the next push; history too if already committed."
    if big:
        return WARN, f"{len(big)} file(s) >= {BIG_WARN_MB}MB: {top}", "Move it out of git (Syncthing or ~/work) before it grows past 100MB."
    return PASS, f"no tracked file >= {BIG_WARN_MB}MB", ""


# `git pull --rebase` (or -r) as a command, optionally with -C <dir> / -c k=v before `pull`
_REBASE_PULL = re.compile(r"\bgit\b(?:\s+-[Cc]\s+\S+)*\s+pull\b[^\n;&|]*?(?:\s--rebase\b|\s-r\b)")


@check("DATA-7", "Data safety")
def no_rebase_pull():
    """No unattended runner does `git pull --rebase`. On the sole-writer hub a news job did, and
    half-rebased the vault (cleanup GIT-V01). Every script under skills/*/scheduled/ is read."""
    hits = []
    for f in sorted(P.RAI.glob("skills/*/scheduled/*.sh")):
        for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            if not line.lstrip().startswith("#") and _REBASE_PULL.search(line):
                hits.append(f"{f.relative_to(P.HELM)}:{n}")
    if hits:
        return FAIL, f"pull --rebase in {hits[:4]}", "Use fetch + merge --ff-only; only the commit skill rebases, and only when behind."
    return PASS, "no unattended pull --rebase", ""
