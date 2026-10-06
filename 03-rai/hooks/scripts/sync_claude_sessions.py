#!/usr/bin/env python3
"""
sync_claude_sessions.py — Memory v3 batch scanner: session capture, decoupled from live
hooks.

Scans native transcripts from every harness root — Claude Code (~/.claude/projects/
**/<uuid>.jsonl), pi via the rai-bridge shadow (~/.pi/agent/rai-transcripts/
**/<uuid>.jsonl, same Claude shape), and one folder per other harness adapter under
$XDG_DATA_HOME/rai/transcripts/<harness>/ (default ~/.local/share; shadows in the same
shape) — finds sessions
not yet processed, normalizes
them to the pending shape (lib/session_extract), classifies via THE one gate
(lib/session_gate), and routes:

  explicit_remember / memory_worthy -> semantic-memory/pending/   (drain distills later)
  archive_only                      -> 13-archive/historical-sessions/  (no distill)
  ephemeral                         -> nothing (native JSONL stays the only record)

Dedup ledger: semantic-memory/processed-sessions.jsonl (append-only, merge=union — both
machines run this and their entries merge). First run seeds it from the existing archive
+ pending queue so history is never re-ingested.

Skips transcripts modified in the last QUIESCENT_MINUTES (live sessions) and non-UUID
files. Idempotent; no AI calls. This is the only capture path: the coordinator runs it
before process-sessions (4 runs a day), and capture_mac runs it on the Mac. A session whose
JSON is already in pending/ is ledgered as hook-captured and not queued again.

Run: python3 sync_claude_sessions.py [--dry-run]
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "helm" / "03-rai"
sys.path.insert(0, str(ROOT / "hooks"))

from lib.session_extract import normalize_transcript  # noqa: E402
from lib.session_gate import classify, should_distill, should_archive  # noqa: E402

CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
PI_TRANSCRIPTS = Path.home() / ".pi" / "agent" / "rai-transcripts"
TRANSCRIPT_ROOTS = (CLAUDE_PROJECTS, PI_TRANSCRIPTS)  # each optional; either harness may be absent
# one folder per harness adapter, under $XDG_DATA_HOME as the adapters write it
SHADOW_ROOT = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "rai" / "transcripts"
PENDING = ROOT / "semantic-memory" / "pending"
ARCHIVE = Path.home() / "helm" / "13-archive" / "historical-sessions"
LEDGER = ROOT / "semantic-memory" / "processed-sessions.jsonl"

QUIESCENT_MINUTES = 15
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SID_RE = re.compile(r'"session_id":\s*"([^"]+)"')


def log(msg: str):
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def ledger_sids() -> set:
    sids = set()
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                sids.add(json.loads(line)["session_id"])
            except Exception:
                pass
    return sids


def ledger_append(entries: list[dict]):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a") as f:
        for e in entries:
            f.write(json.dumps({**e, "ts": datetime.now().isoformat(timespec="seconds")}) + "\n")


def _sid_from_json_head(path: Path) -> str:
    """session_id from the first KB of a pending/archive JSON (every session JSON carries
    it as the first key — no need to parse multi-MB files)."""
    try:
        with open(path, errors="replace") as f:
            m = SID_RE.search(f.read(1024))
        return m.group(1) if m else ""
    except OSError:
        return ""


def seed_ledger() -> int:
    """First run: register every already-captured session so history isn't re-ingested."""
    entries = []
    for d, status in ((ARCHIVE, "seed-archive"), (PENDING, "seed-pending")):
        if not d.exists():
            continue
        for f in sorted(d.glob("session_*.json")):
            if f.name.endswith(".distill.json"):
                continue  # preserved distill artifacts (M1), not sessions
            sid = _sid_from_json_head(f)
            if sid:
                entries.append({"session_id": sid, "status": status, "source": f.name})
    ledger_append(entries)
    return len(entries)


def pending_sids() -> set:
    out = set()
    if PENDING.exists():
        for f in PENDING.glob("session_*.json"):
            if f.name.endswith(".distill.json"):
                continue  # preserved distill artifacts (M1), not sessions
            sid = _sid_from_json_head(f)
            if sid:
                out.add(sid)
    return out


def transcript_roots() -> list[Path]:
    """Every root that exists: Claude Code, pi, then each adapter folder under SHADOW_ROOT."""
    shadows = sorted(d for d in SHADOW_ROOT.iterdir() if d.is_dir()) if SHADOW_ROOT.is_dir() else []
    return [r for r in (*TRANSCRIPT_ROOTS, *shadows) if r.exists()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    roots = transcript_roots()
    if not roots:
        log("no transcript roots (~/.claude/projects, ~/.pi/agent/rai-transcripts, "
            "~/.local/share/rai/transcripts/*) — nothing to scan")
        return 0

    seen = ledger_sids()
    if not seen:
        n = seed_ledger()
        log(f"seeded ledger with {n} already-captured sessions (archive + pending)")
        seen = ledger_sids()

    in_pending = pending_sids()
    now = datetime.now().timestamp()
    agg = {"queued": 0, "archived": 0, "ephemeral": 0, "hook_captured": 0, "live": 0, "fail": 0}
    new_entries = []

    for f in sorted(f for r in roots for f in r.glob("*/*.jsonl")):
        if not UUID_RE.match(f.stem):
            continue
        sid = f.stem
        if sid in seen:
            continue
        try:
            if (now - f.stat().st_mtime) < QUIESCENT_MINUTES * 60:
                agg["live"] += 1
                continue
        except OSError:
            continue
        if sid in in_pending:
            new_entries.append({"session_id": sid, "status": "hook-captured", "source": f.name})
            agg["hook_captured"] += 1
            continue

        try:
            d = normalize_transcript(f, session_id=sid)
        except Exception as e:
            log(f"FAIL normalize {sid}: {e}")
            agg["fail"] += 1
            continue
        cls = classify(d)

        if not should_archive(cls):
            log(f"ephemeral {sid[:8]} ({d.get('context')}, {d.get('duration_minutes')}m) -> skip")
            if not a.dry_run:
                new_entries.append({"session_id": sid, "status": "skipped-ephemeral", "source": f.name})
            agg["ephemeral"] += 1
            continue

        ts = d.get("timestamp", "")
        try:
            stamp = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y%m%d_%H%M%S")
        except Exception:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"session_{stamp}.json"

        if should_distill(cls):
            dest, status, key = PENDING / name, "queued", "queued"
        else:  # archive_only
            dest, status, key = ARCHIVE / name, "archived-no-distill", "archived"
        log(f"{cls} {sid[:8]} ({d.get('context')}, {d.get('duration_minutes')}m) -> {dest.parent.name}/{name}")
        if not a.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(d, indent=2))
            new_entries.append({"session_id": sid, "status": status, "source": name})
        agg[key] += 1

    if not a.dry_run and new_entries:
        ledger_append(new_entries)
    log(f"DONE{' (dry-run)' if a.dry_run else ''}: {agg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
