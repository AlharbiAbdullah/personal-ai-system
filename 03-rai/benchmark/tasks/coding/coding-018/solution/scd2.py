"""Type 2 slowly changing dimension for customers, on SQLite (stdlib sqlite3)."""

from __future__ import annotations

import re
import sqlite3
from datetime import date

SCHEMA = """
CREATE TABLE IF NOT EXISTS dim_customer (
    sk INTEGER PRIMARY KEY,
    customer_id TEXT NOT NULL,
    name TEXT,
    city TEXT,
    tier TEXT,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    is_current INTEGER NOT NULL CHECK (is_current IN (0, 1))
);
CREATE UNIQUE INDEX IF NOT EXISTS dim_customer_one_current
    ON dim_customer (customer_id) WHERE is_current = 1;
"""
ATTRS = ("name", "city", "tier")
DAY_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _check_day(day: str) -> None:
    if not isinstance(day, str) or not DAY_RE.fullmatch(day):
        raise ValueError(f"not a YYYY-MM-DD date: {day!r}")
    date.fromisoformat(day)


def _latest_day(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT MAX(valid_from), MAX(valid_to) FROM dim_customer"
    ).fetchone()
    return max((v for v in row if v is not None), default=None)


def apply_snapshot(
    conn: sqlite3.Connection, rows: list[dict], as_of: str
) -> dict[str, int]:
    _check_day(as_of)
    ids = [row["customer_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate customer_id in snapshot")
    latest = _latest_day(conn)
    if latest is not None and as_of < latest:
        raise ValueError(f"as_of {as_of} is before the latest change {latest}")

    current = {
        cid: (sk, (name, city, tier))
        for sk, cid, name, city, tier in conn.execute(
            "SELECT sk, customer_id, name, city, tier FROM dim_customer WHERE is_current = 1"
        )
    }
    counts = dict.fromkeys(["inserted", "updated", "closed", "unchanged"], 0)

    def close(sk: int) -> None:
        conn.execute(
            "UPDATE dim_customer SET valid_to = ?, is_current = 0 WHERE sk = ?",
            (as_of, sk),
        )

    def insert(cid: str, values: tuple) -> None:
        conn.execute(
            "INSERT INTO dim_customer (customer_id, name, city, tier, valid_from, valid_to, is_current) "
            "VALUES (?, ?, ?, ?, ?, NULL, 1)",
            (cid, *values, as_of),
        )

    with conn:
        for row in rows:
            values = tuple(row.get(attr) for attr in ATTRS)
            existing = current.pop(row["customer_id"], None)
            if existing is None:
                insert(row["customer_id"], values)
                counts["inserted"] += 1
            elif existing[1] == values:
                counts["unchanged"] += 1
            else:
                close(existing[0])
                insert(row["customer_id"], values)
                counts["updated"] += 1
        for sk, _ in current.values():
            close(sk)
            counts["closed"] += 1
    return counts


def as_of_view(conn: sqlite3.Connection, day: str) -> list[tuple]:
    _check_day(day)
    return conn.execute(
        "SELECT customer_id, name, city, tier FROM dim_customer "
        "WHERE valid_from <= ? AND (valid_to IS NULL OR valid_to > ?) ORDER BY customer_id",
        (day, day),
    ).fetchall()


def history(conn: sqlite3.Connection, customer_id: str) -> list[tuple]:
    return conn.execute(
        "SELECT name, city, tier, valid_from, valid_to FROM dim_customer "
        "WHERE customer_id = ? ORDER BY valid_from, sk",
        (customer_id,),
    ).fetchall()
