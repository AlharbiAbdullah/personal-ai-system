"""Regional sales reports over the `sales` table (see salesdb.py)."""

from __future__ import annotations

import sqlite3


def region_running_totals(conn: sqlite3.Connection) -> list[tuple[str, str, int, int]]:
    raise NotImplementedError


def top_products(conn: sqlite3.Connection, k: int) -> list[tuple[str, str, int, int]]:
    raise NotImplementedError


def month_over_month(conn: sqlite3.Connection) -> list[tuple[str, int, int | None, float | None]]:
    raise NotImplementedError


def best_day_per_region(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    raise NotImplementedError
