#!/usr/bin/env python3
"""
process_pending.py — the Memory v3 drain (producer). Drains semantic-memory/pending/*.json
into the stores via the distill pipeline, then archives. Invoked by /rai process-sessions and
the maintenance coordinator.

Gating = the shared policy in hooks/lib/session_gate.py (Memory v3 Phase A — one gate
everywhere). Sessions classed explicit_remember/memory_worthy: distill via SUBSCRIPTION Opus
(distill_session.py) -> store episodic + semantic + route preferences -> move the file to
13-archive/historical-sessions/. archive_only/ephemeral pending files are archived WITHOUT
distillation (once captured, records are never deleted — ephemeral means "don't capture",
which is the scanner's job, not the drain's).
Idempotent (episodic upserts, semantic dedups). Refreshes the committed jsonl source at the
end so the gitignored chromadb stays rebuildable.

Run: python3 process_pending.py [--dry-run]
"""

import argparse
import glob
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "helm" / "03-rai"
PENDING = ROOT / "semantic-memory" / "pending"
ARCHIVE = Path.home() / "helm" / "13-archive" / "historical-sessions"
SCRIPTS = ROOT / "hooks" / "scripts"
WRAP = ROOT / "semantic-memory" / "scripts" / "py-chroma.sh"
LEDGER = ROOT / "semantic-memory" / "processed-sessions.jsonl"


def ledger_sids() -> set:
    out = set()
    try:
        for line in LEDGER.read_text().splitlines():
            try:
                out.add(json.loads(line).get("session_id"))
            except Exception:
                pass
    except OSError:
        pass
    return out


def ledger_drained(seen: set, sid: str, archive_name: str):
    """Ledger the sid at archive time if it has no row. A session JSON that reached
    pending/ without the scanner (a re-drained archive capture from the retired SessionEnd
    hook) carries no ledger row, and once drained out of pending/ the scanner can't see it
    there anymore, so its next pass would re-classify the native transcript and re-queue an
    already-distilled session (double distill). Scanner-queued sessions already have their
    'queued' row; for those this writes nothing."""
    if sid in seen:
        return
    try:
        with open(LEDGER, "a") as fh:
            fh.write(json.dumps({
                "session_id": sid, "status": "drained-archive", "source": archive_name,
                "ts": datetime.now().isoformat(timespec="seconds"),
            }) + "\n")
        seen.add(sid)
    except OSError:
        pass

sys.path.insert(0, str(ROOT / "hooks"))
from lib.daily_log import blocks_for_session  # noqa: E402
from lib.session_gate import classify, human_msgs, should_distill  # noqa: E402


def backfill_entrypoint(d: dict):
    """Back-fill the native-transcript `entrypoint` for hook-captured sessions.

    Archived captures from the retired SessionEnd hook lack the field, which blinds the
    gate's headless-FIRST rule when one is re-drained: a headless `claude -p` run
    (news digest, maintenance) with >=2 files edited classifies memory_worthy and
    gets distilled into the stores — the exact self-ingest loop the 2026-07-03
    purge closed on the scanner path. Read the field from the native transcript
    head; missing transcript (30d auto-clean) leaves the session unchanged."""
    if "entrypoint" in d:
        return
    tp = d.get("transcript_path", "")
    if not tp or not Path(tp).exists():
        return
    try:
        with open(tp) as fh:
            for i, line in enumerate(fh):
                if i > 200:
                    break
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("entrypoint"):
                    d["entrypoint"] = e["entrypoint"]
                    return
    except OSError:
        pass


def log(msg: str):
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="show what would happen; no writes/archive")
    a = p.parse_args()

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    files = [f for f in sorted(glob.glob(str(PENDING / "*.json")))
             if not f.endswith(".distill.json")]  # preserved distill artifacts are not sessions
    if not files:
        log("pending queue empty — nothing to do")
        return 0

    agg = {"distilled": 0, "archived_trivial": 0, "fail": 0, "store_failed": 0}
    seen_sids = ledger_sids()
    for f in files:
        try:
            d = json.load(open(f))
        except Exception as e:
            log(f"SKIP unreadable {Path(f).name}: {e}")
            agg["fail"] += 1
            continue
        sid = d.get("session_id") or Path(f).stem
        backfill_entrypoint(d)
        cls = classify(d)

        if not should_distill(cls):
            log(f"{cls} {sid} ({human_msgs(d)} human msgs) -> archive without distill")
            if not a.dry_run:
                Path(f).rename(ARCHIVE / Path(f).name)
                ledger_drained(seen_sids, sid, Path(f).name)
            agg["archived_trivial"] += 1
            continue

        if a.dry_run:
            log(f"WOULD distill+store+archive {sid} ({cls}, {human_msgs(d)} human msgs)")
            continue

        # Per-session distill artifact (M1): the Opus distill is the ONLY non-rebuildable
        # artifact in the pipeline — preserve it next to the session and reuse on retry
        # instead of re-running Opus.
        art = Path(f).with_suffix(".distill.json")
        reused = art.exists()
        if reused:
            try:
                json.load(open(art))
            except Exception:
                art.unlink()
                reused = False
        if reused:
            log(f"reused distill for {sid} ({art.name})")
        else:
            # Coupling A (M4): the session's live observer bullets ride along as the
            # distiller's turn-by-turn map. Optional — pre-live-capture sessions have none.
            bullets_arg, bf = [], None
            blocks = blocks_for_session(sid)
            if blocks:
                bf = Path(f).with_suffix(".bullets.txt")
                bf.write_text("\n\n".join(f"[{dd} {tt}]\n{txt}" for dd, tt, txt in blocks))
                bullets_arg = ["--bullets-file", str(bf)]
            r = subprocess.run(
                ["python3", str(SCRIPTS / "distill_session.py"), "--session-json", f,
                 "--out", str(art), *bullets_arg],
                capture_output=True, text=True,
            )
            if bf:
                bf.unlink(missing_ok=True)
            if r.returncode == 2:
                # distill's own thin-content gate (transcript < 200 chars): a terminal verdict,
                # not an error — archive it or it retries forever on every run.
                log(f"too-thin {sid} -> archive without distill")
                art.unlink(missing_ok=True)
                Path(f).rename(ARCHIVE / Path(f).name)
                ledger_drained(seen_sids, sid, Path(f).name)
                agg["archived_trivial"] += 1
                continue
            if r.returncode != 0:
                log(f"DISTILL-FAIL {sid}: {r.stderr.strip()[:160]} (left in pending for retry)")
                agg["fail"] += 1
                continue
        stores_ok = True
        for step in (
            ["bash", str(WRAP), str(SCRIPTS / "store_episodic.py"), "--session-json", f],
            ["bash", str(WRAP), str(SCRIPTS / "store_semantic.py"), "--distill-json", str(art)],
            # under WRAP since v3: preference re-confirmation is semantic (needs chromadb)
            ["bash", str(WRAP), str(SCRIPTS / "route_preferences.py"), "--distill-json", str(art)],
        ):
            rr = subprocess.run(step, capture_output=True, text=True)
            name = Path(step[2]).name
            if rr.returncode != 0:
                log(f"STORE-FAIL {name} rc={rr.returncode} {sid}: {rr.stderr.strip()[-200:]}")
                stores_ok = False
            elif rr.stdout.strip():
                log(f"{name}: {rr.stdout.strip()[:200]}")
        if not stores_ok:
            # Leave the session in pending WITH its distill artifact: the next drain reuses
            # the Opus output. Never archive on partial success — archiving counts as done.
            agg["store_failed"] += 1
            log(f"left in pending with preserved distill: {art.name}")
            continue
        art.unlink(missing_ok=True)
        Path(f).rename(ARCHIVE / Path(f).name)
        ledger_drained(seen_sids, sid, Path(f).name)
        agg["distilled"] += 1
        log(f"distilled+archived {sid}")

    if not a.dry_run and agg["distilled"]:
        subprocess.run(["bash", str(WRAP), str(SCRIPTS / "export_index.py")])  # refresh committed source
        # freeze the SessionStart memory block (Memory v3 — session-start reads the file,
        # never ChromaDB) so new sessions see the just-distilled facts
        subprocess.run(["bash", str(WRAP), str(SCRIPTS / "render_memory_block.py")])
    if not a.dry_run:
        # index the live-capture daily logs (v3 invariant: live writes are text-only;
        # this batch step is ChromaDB's only writer for them). Runs even with zero
        # distills — the logs accrue every turn.
        subprocess.run(["bash", str(WRAP), str(SCRIPTS / "index_daily.py")])
    log(f"DONE: {agg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
