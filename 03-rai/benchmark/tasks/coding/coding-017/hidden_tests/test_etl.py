import sqlite3

import pytest
from etl import load, pipeline, transform

SRC_SCHEMA = "CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, amount TEXT, status TEXT, updated_at TEXT)"


def make_src(rows=()):
    src = sqlite3.connect(":memory:")
    src.execute(SRC_SCHEMA)
    add(src, *rows)
    return src


def add(src, *rows):
    src.executemany("INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?)", rows)
    src.commit()


def facts(dw):
    return dw.execute(
        "SELECT id, customer, amount_cents, status, updated_at, first_loaded_at, last_loaded_at FROM fact_orders ORDER BY id"
    ).fetchall()


BASE = [
    (1, " Ann ", "0.29", " Shipped ", "2026-03-01T08:00:00Z"),
    (2, "Bob", "7", "PAID", "2026-03-01T09:00:00Z"),
    (3, "Cy", "12.3", "Test", "2026-03-01T09:30:00Z"),
    (4, "Dee", "0.57", "paid", "2026-03-01T09:30:00Z"),
    (5, "QA", "1.00", " TEST ", "2026-03-01T10:00:00Z"),
]


@pytest.mark.parametrize(
    "amount,cents",
    [
        ("0.29", 29),
        ("0.57", 57),
        ("7", 700),
        ("12.3", 1230),
        ("1234.56", 123456),
        ("0.1", 10),
        ("19.99", 1999),
        ("4.35", 435),
    ],
)
def test_amount_is_exact_cents(amount, cents):
    out = transform.transform(
        {
            "id": 1,
            "customer": "x",
            "amount": amount,
            "status": "paid",
            "updated_at": "t",
        }
    )
    assert out["amount_cents"] == cents


@pytest.mark.parametrize(
    "status,expected",
    [
        (" Shipped ", "shipped"),
        ("PAID", "paid"),
        ("tested", "tested"),
        ("Test", None),
        (" TEST ", None),
        ("test", None),
    ],
)
def test_status_normalisation_and_test_orders(status, expected):
    out = transform.transform(
        {"id": 1, "customer": " c ", "amount": "1", "status": status, "updated_at": "t"}
    )
    if expected is None:
        assert out is None
    else:
        assert out["status"] == expected
        assert out["customer"] == "c"


def test_first_run_loads_clean_rows_and_sets_watermark():
    src, dw = make_src(BASE), sqlite3.connect(":memory:")
    assert pipeline.run(src, dw, "2026-03-02T00:00:00Z") == 3
    assert facts(dw) == [
        (
            1,
            "Ann",
            29,
            "shipped",
            "2026-03-01T08:00:00Z",
            "2026-03-02T00:00:00Z",
            "2026-03-02T00:00:00Z",
        ),
        (
            2,
            "Bob",
            700,
            "paid",
            "2026-03-01T09:00:00Z",
            "2026-03-02T00:00:00Z",
            "2026-03-02T00:00:00Z",
        ),
        (
            4,
            "Dee",
            57,
            "paid",
            "2026-03-01T09:30:00Z",
            "2026-03-02T00:00:00Z",
            "2026-03-02T00:00:00Z",
        ),
    ]
    assert load.get_watermark(dw) == "2026-03-01T10:00:00Z"


def test_rerun_without_changes_does_nothing():
    src, dw = make_src(BASE), sqlite3.connect(":memory:")
    pipeline.run(src, dw, "2026-03-02T00:00:00Z")
    before = facts(dw)
    assert pipeline.run(src, dw, "2026-03-03T00:00:00Z") == 0
    assert facts(dw) == before
    assert load.get_watermark(dw) == "2026-03-01T10:00:00Z"


def test_late_row_with_same_timestamp_as_watermark_arrives():
    src, dw = make_src(BASE), sqlite3.connect(":memory:")
    pipeline.run(src, dw, "2026-03-02T00:00:00Z")
    add(src, (6, "Eve", "3.50", "paid", "2026-03-01T10:00:00Z"))
    assert pipeline.run(src, dw, "2026-03-03T00:00:00Z") == 1
    assert facts(dw)[-1][:5] == (6, "Eve", 350, "paid", "2026-03-01T10:00:00Z")


def test_late_row_older_than_run_time_arrives():
    src, dw = make_src(BASE), sqlite3.connect(":memory:")
    pipeline.run(src, dw, "2026-03-02T00:00:00Z")
    add(src, (7, "Fay", "2", "paid", "2026-03-01T12:00:00Z"))
    assert pipeline.run(src, dw, "2026-03-03T00:00:00Z") == 1
    assert [r[0] for r in facts(dw)] == [1, 2, 4, 7]
    assert load.get_watermark(dw) == "2026-03-01T12:00:00Z"


def test_update_keeps_first_loaded_at():
    src, dw = make_src(BASE), sqlite3.connect(":memory:")
    pipeline.run(src, dw, "2026-03-02T00:00:00Z")
    add(src, (2, "Bob", "7", "refunded", "2026-03-02T11:00:00Z"))
    assert pipeline.run(src, dw, "2026-03-03T00:00:00Z") == 1
    row = next(r for r in facts(dw) if r[0] == 2)
    assert row == (
        2,
        "Bob",
        700,
        "refunded",
        "2026-03-02T11:00:00Z",
        "2026-03-02T00:00:00Z",
        "2026-03-03T00:00:00Z",
    )
    untouched = next(r for r in facts(dw) if r[0] == 1)
    assert untouched[6] == "2026-03-02T00:00:00Z"


def test_order_turning_into_test_order_moves_watermark_only():
    src, dw = make_src(BASE[:2]), sqlite3.connect(":memory:")
    pipeline.run(src, dw, "2026-03-02T00:00:00Z")
    add(src, (8, "Tmp", "1", "TEST", "2026-03-04T00:00:00Z"))
    assert pipeline.run(src, dw, "2026-03-05T00:00:00Z") == 0
    assert load.get_watermark(dw) == "2026-03-04T00:00:00Z"
    assert [r[0] for r in facts(dw)] == [1, 2]


def test_empty_source_keeps_watermark_unset():
    src, dw = make_src(), sqlite3.connect(":memory:")
    assert pipeline.run(src, dw, "2026-03-02T00:00:00Z") == 0
    assert load.get_watermark(dw) is None
    add(src, *BASE[:1])
    assert pipeline.run(src, dw, "2026-03-03T00:00:00Z") == 1


def test_upsert_rules_directly():
    dw = sqlite3.connect(":memory:")
    load.ensure_schema(dw)
    newer = {
        "id": 9,
        "customer": "Gil",
        "amount_cents": 100,
        "status": "paid",
        "updated_at": "2026-03-05T00:00:00Z",
    }
    older = {**newer, "status": "pending", "updated_at": "2026-03-04T00:00:00Z"}
    assert load.upsert(dw, [newer], "L1") == 1
    assert load.upsert(dw, [older], "L2") == 0
    assert load.upsert(dw, [dict(newer)], "L3") == 0
    assert facts(dw) == [(9, "Gil", 100, "paid", "2026-03-05T00:00:00Z", "L1", "L1")]
    same_time_new_value = {**newer, "amount_cents": 150}
    assert load.upsert(dw, [same_time_new_value], "L4") == 1
    assert facts(dw) == [(9, "Gil", 150, "paid", "2026-03-05T00:00:00Z", "L1", "L4")]


def test_load_and_watermark_are_committed(tmp_path):
    src = make_src(BASE)
    path = tmp_path / "dw.db"
    dw = sqlite3.connect(path)
    pipeline.run(src, dw, "2026-03-02T00:00:00Z")
    other = sqlite3.connect(path)
    assert other.execute("SELECT COUNT(*) FROM fact_orders").fetchone() == (3,)
    assert other.execute(
        "SELECT value FROM etl_state WHERE key = 'orders_watermark'"
    ).fetchone() == ("2026-03-01T10:00:00Z",)
