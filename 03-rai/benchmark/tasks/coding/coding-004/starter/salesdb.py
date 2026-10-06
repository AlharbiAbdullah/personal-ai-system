"""The sales table: one row per sale line. amount_cents is negative for returns."""

from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY,
    sale_date TEXT NOT NULL,      -- 'YYYY-MM-DD'
    region TEXT NOT NULL,
    product TEXT NOT NULL,
    amount_cents INTEGER NOT NULL -- negative for a return
);
"""


def create(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def load(conn: sqlite3.Connection, rows: list[tuple[str, str, str, int]]) -> None:
    """rows: (sale_date, region, product, amount_cents)."""
    conn.executemany(
        "INSERT INTO sales (sale_date, region, product, amount_cents) VALUES (?, ?, ?, ?)", rows
    )


def demo_rows(seed: int = 7, n: int = 200) -> list[tuple[str, str, str, int]]:
    rng = random.Random(seed)
    start = date(2026, 1, 1)
    rows = []
    for _ in range(n):
        day = start + timedelta(days=rng.randrange(0, 120))
        amount = rng.randrange(100, 5000) * (-1 if rng.random() < 0.05 else 1)
        rows.append((day.isoformat(), rng.choice(["north", "south", "east"]), rng.choice(["tea", "mug", "jam", "bag"]), amount))
    return rows
