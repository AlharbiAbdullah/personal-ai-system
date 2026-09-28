#!/usr/bin/env python3
"""Orchestrator worker status hook.

Registered in the target repo's .claude/settings.local.json for
UserPromptSubmit / PreToolUse / Stop / Notification / SessionEnd, behind a
shell guard that exits unless ORCH_TASK is set. Writes one JSON status file
per worker into $ORCH_RUN_DIR/status/<task>.json. Always exits 0: a status
write must never block a worker.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STATUS_BY_EVENT = {
    "UserPromptSubmit": "working",
    "PreToolUse": "working",
    "Stop": "idle",
    "Notification": "waiting",
    "SessionEnd": "exited",
}


def main() -> None:
    task = os.environ.get("ORCH_TASK")
    run_dir = os.environ.get("ORCH_RUN_DIR")
    if not task or not run_dir:
        return
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    event = payload.get("hook_event_name", "unknown")
    record = {
        "task": task,
        "status": STATUS_BY_EVENT.get(event, "working"),
        "event": event,
        "session_id": payload.get("session_id", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if event == "Notification":
        record["message"] = str(payload.get("message", ""))[:500]
    status_dir = Path(run_dir) / "status"
    try:
        status_dir.mkdir(parents=True, exist_ok=True)
        tmp = status_dir / f".{task}.json.tmp"
        tmp.write_text(json.dumps(record) + "\n")
        tmp.replace(status_dir / f"{task}.json")
    except Exception:
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
