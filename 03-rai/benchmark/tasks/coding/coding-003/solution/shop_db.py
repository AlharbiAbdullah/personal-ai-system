"""Small order store on SQLite (stdlib sqlite3 only)."""

from __future__ import annotations

import sqlite3
from collections import Counter

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0)
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    placed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
"""


class DuplicateCustomer(Exception):
    """The email is already registered (in any letter case)."""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def add_customer(
    conn: sqlite3.Connection, email: str, name: str, created_at: str
) -> int:
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO customers (email, name, created_at) VALUES (?, ?, ?)",
                (email, name, created_at),
            )
    except sqlite3.IntegrityError as exc:
        raise DuplicateCustomer(email) from exc
    return int(cur.lastrowid)


def add_product(conn: sqlite3.Connection, sku: str, name: str, price_cents: int) -> int:
    with conn:
        cur = conn.execute(
            "INSERT INTO products (sku, name, price_cents) VALUES (?, ?, ?)",
            (sku, name, price_cents),
        )
    return int(cur.lastrowid)


def set_price(conn: sqlite3.Connection, sku: str, price_cents: int) -> None:
    with conn:
        cur = conn.execute(
            "UPDATE products SET price_cents = ? WHERE sku = ?", (price_cents, sku)
        )
    if cur.rowcount == 0:
        raise KeyError(sku)


def place_order(
    conn: sqlite3.Connection,
    customer_id: int,
    items: list[tuple[str, int]],
    placed_at: str,
) -> int:
    if not items:
        raise ValueError("an order needs at least one item")
    quantities: Counter[str] = Counter()
    for sku, quantity in items:
        if quantity < 1:
            raise ValueError(f"quantity must be at least 1: {sku}")
        quantities[sku] += quantity
    if (
        conn.execute("SELECT 1 FROM customers WHERE id = ?", (customer_id,)).fetchone()
        is None
    ):
        raise KeyError(customer_id)
    products = {}
    for sku in quantities:
        row = conn.execute(
            "SELECT id, price_cents FROM products WHERE sku = ?", (sku,)
        ).fetchone()
        if row is None:
            raise ValueError(f"unknown sku: {sku}")
        products[sku] = row
    with conn:
        order_id = conn.execute(
            "INSERT INTO orders (customer_id, placed_at) VALUES (?, ?)",
            (customer_id, placed_at),
        ).lastrowid
        conn.executemany(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) VALUES (?, ?, ?, ?)",
            [
                (order_id, pid, quantities[sku], price)
                for sku, (pid, price) in products.items()
            ],
        )
    return int(order_id)


def customer_totals(
    conn: sqlite3.Connection, since: str | None = None
) -> list[tuple[str, int, int]]:
    rows = conn.execute(
        """
        WITH order_totals AS (
            SELECT o.id, o.customer_id, SUM(i.quantity * i.unit_price_cents) AS total
            FROM orders o JOIN order_items i ON i.order_id = o.id
            WHERE ? IS NULL OR o.placed_at >= ?
            GROUP BY o.id
        )
        SELECT c.email, COUNT(t.id), COALESCE(SUM(t.total), 0) AS total
        FROM customers c LEFT JOIN order_totals t ON t.customer_id = c.id
        GROUP BY c.id
        ORDER BY total DESC, c.email COLLATE BINARY ASC
        """,
        (since, since),
    ).fetchall()
    return [(email, int(count), int(total)) for email, count, total in rows]


def top_products(conn: sqlite3.Connection, n: int) -> list[tuple[str, int]]:
    rows = conn.execute(
        """
        SELECT p.sku, SUM(i.quantity) AS units
        FROM order_items i JOIN products p ON p.id = i.product_id
        GROUP BY p.id
        ORDER BY units DESC, p.sku ASC
        LIMIT ?
        """,
        (n,),
    ).fetchall()
    return [(sku, int(units)) for sku, units in rows]
