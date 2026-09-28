"""Per-hook latency tracker. Append-only jsonl at ~/.local/state/rai/telemetry/hook-perf.jsonl."""

import json
import time
from contextlib import contextmanager

from .paths import get_telemetry_dir
from .time_utils import get_iso_timestamp

PERF_LOG = get_telemetry_dir() / "hook-perf.jsonl"


@contextmanager
def hook_timer(name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        try:
            PERF_LOG.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "hook": name,
                "ms": round(elapsed_ms, 2),
                "ts": get_iso_timestamp(),
            }
            with PERF_LOG.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
