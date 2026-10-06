from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS fact_orders (
    id INTEGER PRIMARY KEY,
    customer TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    first_loaded_at TEXT NOT NULL,
    last_loaded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS etl_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""
WATERMARK_KEY = "orders_watermark"


def ensure_schema(dw: sqlite3.Connection) -> None:
    dw.executescript(SCHEMA)


def get_watermark(dw: sqlite3.Connection) -> str | None:
    row = dw.execute("SELECT value FROM etl_state WHERE key = ?", (WATERMARK_KEY,)).fetchone()
    return row[0] if row else None


def set_watermark(dw: sqlite3.Connection, value: str) -> None:
    dw.execute(
        "INSERT INTO etl_state (key, value) VALUES (?, ?) "
        "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        (WATERMARK_KEY, value),
    )


def upsert(dw: sqlite3.Connection, rows: list[dict], loaded_at: str) -> int:
    count = 0
    for r in rows:
        dw.execute(
            "INSERT OR REPLACE INTO fact_orders "
            "(id, customer, amount_cents, status, updated_at, first_loaded_at, last_loaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r["id"], r["customer"], r["amount_cents"], r["status"], r["updated_at"], loaded_at, loaded_at),
        )
        count += 1
    return count
