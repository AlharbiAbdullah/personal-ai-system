import json
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
import scd2

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def path(tmp_path):
    return tmp_path / "dw.db"


@pytest.fixture
def conn(path):
    c = sqlite3.connect(path)
    scd2.init(c)
    yield c
    c.close()


def snap(name):
    return json.loads((ROOT / "data" / f"snapshot-{name}.json").read_text())


def count_rows(path):
    with sqlite3.connect(path) as other:
        return other.execute("SELECT COUNT(*) FROM dim_customer").fetchone()[0]


def c(cid, name="N", city="X", tier=None):
    return {"customer_id": cid, "name": name, "city": city, "tier": tier}


def test_init_is_idempotent_and_enforces_one_current_row(conn):
    scd2.init(conn)
    conn.execute(
        "INSERT INTO dim_customer (customer_id, valid_from, is_current) VALUES ('A', '2026-01-01', 1)"
    )
    conn.execute(
        "INSERT INTO dim_customer (customer_id, valid_from, valid_to, is_current) VALUES ('A', '2025-01-01', '2026-01-01', 0)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO dim_customer (customer_id, valid_from, is_current) VALUES ('A', '2026-02-01', 1)"
        )


def test_sample_snapshots(conn, path):
    assert scd2.apply_snapshot(conn, snap("2026-01-01"), "2026-01-01") == {
        "inserted": 3,
        "updated": 0,
        "closed": 0,
        "unchanged": 0,
    }
    assert scd2.apply_snapshot(conn, snap("2026-02-01"), "2026-02-01") == {
        "inserted": 1,
        "updated": 1,
        "closed": 1,
        "unchanged": 1,
    }
    assert scd2.history(conn, "C-001") == [
        ("Ann Lee", "Austin", "gold", "2026-01-01", "2026-02-01"),
        ("Ann Lee", "Dallas", "gold", "2026-02-01", None),
    ]
    assert scd2.history(conn, "C-003") == [
        ("Cy Moss", "Reno", "silver", "2026-01-01", "2026-02-01")
    ]
    assert scd2.history(conn, "C-404") == []
    assert scd2.as_of_view(conn, "2025-12-31") == []
    assert scd2.as_of_view(conn, "2026-01-15") == [
        ("C-001", "Ann Lee", "Austin", "gold"),
        ("C-002", "Bob Stone", "Denver", None),
        ("C-003", "Cy Moss", "Reno", "silver"),
    ]
    assert scd2.as_of_view(conn, "2026-02-01") == [
        ("C-001", "Ann Lee", "Dallas", "gold"),
        ("C-002", "Bob Stone", "Denver", None),
        ("C-004", "Dee Park", "Austin", "bronze"),
    ]
    assert count_rows(path) == 5


def test_rerun_same_snapshot_same_day_changes_nothing(conn, path):
    scd2.apply_snapshot(conn, snap("2026-01-01"), "2026-01-01")
    scd2.apply_snapshot(conn, snap("2026-02-01"), "2026-02-01")
    assert scd2.apply_snapshot(conn, snap("2026-02-01"), "2026-02-01") == {
        "inserted": 0,
        "updated": 0,
        "closed": 0,
        "unchanged": 3,
    }
    assert count_rows(path) == 5


def test_customer_can_come_back(conn):
    scd2.apply_snapshot(conn, [c("A"), c("B")], "2026-01-01")
    scd2.apply_snapshot(conn, [c("B")], "2026-02-01")
    assert scd2.apply_snapshot(conn, [c("A", city="Y"), c("B")], "2026-03-01") == {
        "inserted": 1,
        "updated": 0,
        "closed": 0,
        "unchanged": 1,
    }
    assert scd2.history(conn, "A") == [
        ("N", "X", None, "2026-01-01", "2026-02-01"),
        ("N", "Y", None, "2026-03-01", None),
    ]
    assert [r[0] for r in scd2.as_of_view(conn, "2026-02-15")] == ["B"]


def test_null_and_empty_string_are_different(conn):
    scd2.apply_snapshot(conn, [c("A", tier=None), c("B", tier="")], "2026-01-01")
    assert (
        scd2.apply_snapshot(conn, [c("A", tier=None), c("B", tier="")], "2026-01-02")[
            "unchanged"
        ]
        == 2
    )
    assert (
        scd2.apply_snapshot(conn, [c("A", tier=""), c("B", tier=None)], "2026-01-03")[
            "updated"
        ]
        == 2
    )
    assert scd2.as_of_view(conn, "2026-01-03") == [
        ("A", "N", "X", ""),
        ("B", "N", "X", None),
    ]


def test_ids_are_case_sensitive(conn):
    assert scd2.apply_snapshot(conn, [c("c1"), c("C1")], "2026-01-01")["inserted"] == 2


def test_missing_attribute_keys_mean_null(conn):
    scd2.apply_snapshot(conn, [{"customer_id": "A", "name": "Ann"}], "2026-01-01")
    assert scd2.as_of_view(conn, "2026-01-01") == [("A", "Ann", None, None)]


def test_empty_snapshot_closes_everyone(conn):
    scd2.apply_snapshot(conn, [c("A"), c("B")], "2026-01-01")
    assert scd2.apply_snapshot(conn, [], "2026-02-01") == {
        "inserted": 0,
        "updated": 0,
        "closed": 2,
        "unchanged": 0,
    }
    assert scd2.as_of_view(conn, "2026-02-01") == []


@pytest.mark.parametrize(
    "bad_day", ["2026-02-30", "2026/03/01", "20260301", "", "2026-3-1"]
)
def test_bad_as_of(conn, bad_day):
    with pytest.raises(ValueError):
        scd2.apply_snapshot(conn, [c("A")], bad_day)


def test_going_back_in_time_is_refused_and_writes_nothing(conn, path):
    scd2.apply_snapshot(conn, [c("A"), c("B")], "2026-01-01")
    scd2.apply_snapshot(conn, [c("A")], "2026-03-01")
    with pytest.raises(ValueError):
        scd2.apply_snapshot(conn, [c("A", city="Z")], "2026-02-01")
    assert count_rows(path) == 2
    assert scd2.as_of_view(conn, "2026-03-01") == [("A", "N", "X", None)]


def test_duplicate_ids_are_refused_and_write_nothing(conn, path):
    scd2.apply_snapshot(conn, [c("A")], "2026-01-01")
    with pytest.raises(ValueError):
        scd2.apply_snapshot(conn, [c("B"), c("A", city="Q"), c("B")], "2026-02-01")
    assert count_rows(path) == 1
    assert scd2.as_of_view(conn, "2026-02-01") == [("A", "N", "X", None)]


def test_changes_are_committed(conn, path):
    scd2.apply_snapshot(conn, [c("A")], "2026-01-01")
    with sqlite3.connect(path) as other:
        assert other.execute(
            "SELECT customer_id, is_current, valid_to FROM dim_customer"
        ).fetchall() == [("A", 1, None)]


@pytest.mark.parametrize("seed", [4, 99])
def test_generated_history_reproduces_every_snapshot(conn, seed):
    rng = random.Random(seed)
    population = {
        f"K{n:03d}": {
            "name": f"Name {n}",
            "city": rng.choice(["A", "B", "C"]),
            "tier": rng.choice([None, "gold", "silver"]),
        }
        for n in range(40)
    }
    day = date(2026, 1, 1)
    applied = []
    previous = {}
    for _ in range(12):
        snapshot = {}
        for cid, attrs in population.items():
            if rng.random() < 0.8:
                attrs = dict(attrs)
                if rng.random() < 0.25:
                    attrs[rng.choice(["name", "city", "tier"])] = rng.choice(
                        [None, "", "A", "B", "gold", f"v{rng.randrange(5)}"]
                    )
                    population[cid] = attrs
                snapshot[cid] = attrs
        rows = [{"customer_id": cid, **attrs} for cid, attrs in snapshot.items()]
        rng.shuffle(rows)
        expected = {
            "inserted": sum(cid not in previous for cid in snapshot),
            "updated": sum(
                cid in previous and previous[cid] != snapshot[cid] for cid in snapshot
            ),
            "closed": sum(cid not in snapshot for cid in previous),
            "unchanged": sum(
                cid in previous and previous[cid] == snapshot[cid] for cid in snapshot
            ),
        }
        assert scd2.apply_snapshot(conn, rows, day.isoformat()) == expected
        applied.append((day, snapshot))
        previous = snapshot
        day += timedelta(days=rng.randrange(1, 40))
    for i, (when, snapshot) in enumerate(applied):
        view = [
            (cid, a["name"], a["city"], a["tier"])
            for cid, a in sorted(snapshot.items())
        ]
        assert scd2.as_of_view(conn, when.isoformat()) == view
        until = applied[i + 1][0] if i + 1 < len(applied) else when + timedelta(days=30)
        assert scd2.as_of_view(conn, (until - timedelta(days=1)).isoformat()) == view
    assert scd2.as_of_view(conn, (applied[0][0] - timedelta(days=1)).isoformat()) == []
    current = conn.execute(
        "SELECT customer_id, COUNT(*) FROM dim_customer WHERE is_current = 1 GROUP BY customer_id HAVING COUNT(*) > 1"
    ).fetchall()
    assert current == []
