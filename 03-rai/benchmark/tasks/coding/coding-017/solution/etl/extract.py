from __future__ import annotations

import sqlite3

COLUMNS = "id, customer, amount, status, updated_at"


def fetch_changes(src: sqlite3.Connection, watermark: str | None) -> list[dict]:
    # >= on purpose: rows committed late with the same updated_at as the watermark must not be
    # lost; re-fetched rows are harmless because upsert skips identical rows.
    if watermark is None:
        cur = src.execute(f"SELECT {COLUMNS} FROM orders ORDER BY updated_at, id")
    else:
        cur = src.execute(
            f"SELECT {COLUMNS} FROM orders WHERE updated_at >= ? ORDER BY updated_at, id",
            (watermark,),
        )
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]
