"""Small order store on SQLite (stdlib sqlite3 only)."""

from __future__ import annotations

import sqlite3


class DuplicateCustomer(Exception):
    """The email is already registered (in any letter case)."""


def connect(path: str) -> sqlite3.Connection:
    raise NotImplementedError


def init_schema(conn: sqlite3.Connection) -> None:
    raise NotImplementedError


def add_customer(conn: sqlite3.Connection, email: str, name: str, created_at: str) -> int:
    raise NotImplementedError


def add_product(conn: sqlite3.Connection, sku: str, name: str, price_cents: int) -> int:
    raise NotImplementedError


def set_price(conn: sqlite3.Connection, sku: str, price_cents: int) -> None:
    raise NotImplementedError


def place_order(
    conn: sqlite3.Connection, customer_id: int, items: list[tuple[str, int]], placed_at: str
) -> int:
    raise NotImplementedError


def customer_totals(conn: sqlite3.Connection, since: str | None = None) -> list[tuple[str, int, int]]:
    raise NotImplementedError


def top_products(conn: sqlite3.Connection, n: int) -> list[tuple[str, int]]:
    raise NotImplementedError
