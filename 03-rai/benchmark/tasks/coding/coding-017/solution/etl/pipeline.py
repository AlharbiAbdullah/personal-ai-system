from __future__ import annotations

import sqlite3

from etl.extract import fetch_changes
from etl.load import ensure_schema, get_watermark, set_watermark, upsert
from etl.transform import transform


def run(src: sqlite3.Connection, dw: sqlite3.Connection, now: str) -> int:
    ensure_schema(dw)
    rows = fetch_changes(src, get_watermark(dw))
    clean = [t for t in (transform(r) for r in rows) if t is not None]
    with dw:  # load and watermark commit together, or roll back together
        count = upsert(dw, clean, now)
        if rows:
            set_watermark(dw, max(r["updated_at"] for r in rows))
    return count
