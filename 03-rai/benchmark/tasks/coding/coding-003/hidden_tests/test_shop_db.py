import sqlite3

import pytest
import shop_db as db


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "shop.db")


@pytest.fixture
def conn(path):
    c = db.connect(path)
    db.init_schema(c)
    yield c
    c.close()


def other(path):
    """A second, independent connection: sees only committed data."""
    return sqlite3.connect(path)


def seed(conn):
    ids = {
        "ann": db.add_customer(conn, "ann@example.com", "Ann", "2026-01-01"),
        "bob": db.add_customer(conn, "Bob@Example.com", "Bob", "2026-01-02"),
        "cy": db.add_customer(conn, "cy@example.com", "Cy", "2026-01-03"),
    }
    db.add_product(conn, "TEA", "Green tea", 450)
    db.add_product(conn, "MUG", "Mug", 1200)
    db.add_product(conn, "JAM", "Fig jam", 700)
    return ids


def test_init_schema_is_idempotent(conn):
    db.init_schema(conn)
    names = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"customers", "products", "orders", "order_items"} <= names


def test_foreign_keys_are_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO orders (customer_id, placed_at) VALUES (999, '2026-01-01')"
        )


def test_check_constraints(conn):
    with pytest.raises(sqlite3.IntegrityError):
        db.add_product(conn, "BAD", "Bad", -1)
    cid = db.add_customer(conn, "a@example.com", "A", "2026-01-01")
    db.add_product(conn, "OK", "Ok", 100)
    db.add_product(conn, "OK2", "Ok too", 100)
    oid = db.place_order(conn, cid, [("OK", 1)], "2026-01-02")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) "
            "SELECT ?, id, 0, 1 FROM products WHERE sku = 'OK2'",
            (oid,),
        )


def test_deleting_an_order_cascades_to_items(conn):
    ids = seed(conn)
    oid = db.place_order(conn, ids["ann"], [("TEA", 2), ("MUG", 1)], "2026-02-01")
    conn.execute("DELETE FROM orders WHERE id = ?", (oid,))
    assert conn.execute("SELECT COUNT(*) FROM order_items").fetchone()[0] == 0


def test_add_customer_returns_ids_and_commits(conn, path):
    a = db.add_customer(conn, "x@example.com", "X", "2026-01-01")
    b = db.add_customer(conn, "y@example.com", "Y", "2026-01-01")
    assert isinstance(a, int) and isinstance(b, int) and a != b
    assert other(path).execute(
        "SELECT email FROM customers ORDER BY id"
    ).fetchall() == [
        ("x@example.com",),
        ("y@example.com",),
    ]


def test_duplicate_email_any_case(conn, path):
    db.add_customer(conn, "Ann@Example.com", "Ann", "2026-01-01")
    with pytest.raises(db.DuplicateCustomer):
        db.add_customer(conn, "ann@example.COM", "Ann again", "2026-01-02")
    assert other(path).execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 1
    assert (
        other(path).execute("SELECT email FROM customers").fetchone()[0]
        == "Ann@Example.com"
    )


def test_place_order_merges_skus_and_snapshots_prices(conn, path):
    ids = seed(conn)
    oid = db.place_order(
        conn, ids["ann"], [("TEA", 2), ("MUG", 1), ("TEA", 3)], "2026-02-01"
    )
    rows = (
        other(path)
        .execute(
            "SELECT p.sku, i.quantity, i.unit_price_cents FROM order_items i "
            "JOIN products p ON p.id = i.product_id WHERE i.order_id = ? ORDER BY p.sku",
            (oid,),
        )
        .fetchall()
    )
    assert rows == [("MUG", 1, 1200), ("TEA", 5, 450)]
    db.set_price(conn, "TEA", 999)
    assert db.customer_totals(conn)[0] == ("ann@example.com", 1, 5 * 450 + 1200)
    assert other(path).execute(
        "SELECT price_cents FROM products WHERE sku = 'TEA'"
    ).fetchone() == (999,)


def test_set_price_unknown_sku(conn):
    with pytest.raises(KeyError):
        db.set_price(conn, "NOPE", 10)


@pytest.mark.parametrize(
    "items,error",
    [
        ([("TEA", 1), ("NOPE", 1)], ValueError),
        ([("TEA", 1), ("MUG", 0)], ValueError),
        ([("TEA", -2)], ValueError),
        ([], ValueError),
    ],
)
def test_place_order_is_all_or_nothing(conn, path, items, error):
    ids = seed(conn)
    with pytest.raises(error):
        db.place_order(conn, ids["bob"], items, "2026-02-01")
    check = other(path)
    assert check.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert check.execute("SELECT COUNT(*) FROM order_items").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_place_order_unknown_customer(conn, path):
    seed(conn)
    with pytest.raises(KeyError):
        db.place_order(conn, 4242, [("TEA", 1)], "2026-02-01")
    assert other(path).execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_customer_totals_counts_orders_not_lines(conn):
    ids = seed(conn)
    db.place_order(conn, ids["bob"], [("TEA", 1), ("MUG", 2), ("JAM", 1)], "2026-02-01")
    db.place_order(conn, ids["ann"], [("MUG", 1)], "2026-02-02")
    db.place_order(conn, ids["ann"], [("JAM", 1)], "2026-02-03")
    assert db.customer_totals(conn) == [
        ("Bob@Example.com", 1, 450 + 2400 + 700),
        ("ann@example.com", 2, 1900),
        ("cy@example.com", 0, 0),
    ]


def test_customer_totals_since_keeps_everyone(conn):
    ids = seed(conn)
    db.place_order(conn, ids["ann"], [("MUG", 1)], "2026-01-15")
    db.place_order(conn, ids["ann"], [("TEA", 1)], "2026-02-15")
    db.place_order(conn, ids["bob"], [("JAM", 3)], "2026-01-20")
    db.place_order(conn, ids["cy"], [("TEA", 2)], "2026-02-01")
    assert db.customer_totals(conn, since="2026-02-01") == [
        ("cy@example.com", 1, 900),
        ("ann@example.com", 1, 450),
        ("Bob@Example.com", 0, 0),
    ]
    assert db.customer_totals(conn, since="2027-01-01") == [
        ("Bob@Example.com", 0, 0),
        ("ann@example.com", 0, 0),
        ("cy@example.com", 0, 0),
    ]


def test_customer_totals_ties_sort_by_email(conn):
    ids = seed(conn)
    db.place_order(conn, ids["cy"], [("TEA", 2)], "2026-02-01")
    db.place_order(conn, ids["ann"], [("TEA", 2)], "2026-02-01")
    got = db.customer_totals(conn)
    assert got[:2] == [("ann@example.com", 1, 900), ("cy@example.com", 1, 900)]


def test_top_products(conn):
    ids = seed(conn)
    db.add_product(conn, "BAG", "Bag", 300)
    db.place_order(conn, ids["ann"], [("TEA", 2), ("JAM", 4)], "2026-02-01")
    db.place_order(conn, ids["bob"], [("TEA", 2), ("MUG", 1)], "2026-02-02")
    db.place_order(conn, ids["cy"], [("MUG", 3)], "2026-02-03")
    assert db.top_products(conn, 10) == [("JAM", 4), ("MUG", 4), ("TEA", 4)]
    db.place_order(conn, ids["cy"], [("TEA", 1)], "2026-02-04")
    assert db.top_products(conn, 2) == [("TEA", 5), ("JAM", 4)]
    assert db.top_products(conn, 0) == []
