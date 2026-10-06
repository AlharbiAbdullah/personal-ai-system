import random
import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from fractions import Fraction

import pytest
import reports
import salesdb


def make_conn(rows):
    conn = sqlite3.connect(":memory:")
    salesdb.create(conn)
    salesdb.load(conn, rows)
    conn.commit()
    return conn


def random_rows(seed, n=300):
    rng = random.Random(seed)
    start = date(2025, 11, 1)
    rows = []
    for _ in range(n):
        day = start + timedelta(days=rng.randrange(0, 150))
        amount = rng.randrange(1, 60) * 100 * (-1 if rng.random() < 0.08 else 1)
        rows.append(
            (
                day.isoformat(),
                rng.choice(["north", "south", "east", "west"]),
                rng.choice(["tea", "mug", "jam", "bag", "pen"]),
                amount,
            )
        )
    return rows


def ref_running(rows):
    by_day = defaultdict(int)
    for d, region, _, amount in rows:
        by_day[(region, d)] += amount
    out, running, last_region = [], 0, None
    for region, d in sorted(by_day):
        if region != last_region:
            running, last_region = 0, region
        running += by_day[(region, d)]
        out.append((region, d, by_day[(region, d)], running))
    return out


def ref_top(rows, k):
    totals = defaultdict(int)
    for d, _, product, amount in rows:
        totals[(d[:7], product)] += amount
    out = []
    for month in sorted({m for m, _ in totals}):
        items = [(p, t) for (m, p), t in totals.items() if m == month]
        distinct = sorted({t for _, t in items}, reverse=True)
        for p, t in items:
            rank = distinct.index(t) + 1
            if rank <= k:
                out.append((month, p, t, rank))
    return sorted(out, key=lambda r: (r[0], r[3], r[1]))


def ref_mom(rows):
    totals = defaultdict(int)
    for d, _, _, amount in rows:
        totals[d[:7]] += amount
    out, prev = [], None
    for month in sorted(totals):
        total = totals[month]
        pct = None if not prev else Fraction(total - prev, prev) * 100
        out.append((month, total, prev, pct))
        prev = total
    return out


def ref_best_day(rows):
    by_day = defaultdict(int)
    for d, region, _, amount in rows:
        by_day[(region, d)] += amount
    best = {}
    for (region, d), total in sorted(by_day.items()):
        if region not in best or total > best[region][1]:
            best[region] = (d, total)
    return [(region, d, t) for region, (d, t) in sorted(best.items())]


def assert_mom(got, expected):
    assert len(got) == len(expected)
    for g, e in zip(got, expected):
        assert tuple(g[:3]) == e[:3]
        if e[3] is None:
            assert g[3] is None
        else:
            assert isinstance(g[3], float)
            assert abs(Fraction(g[3]) - e[3]) <= Fraction(1, 20) + Fraction(1, 10**9)
            assert round(g[3], 1) == g[3]


SEEDS = [1, 42, 2026]


@pytest.mark.parametrize("seed", SEEDS)
def test_region_running_totals_random(seed):
    rows = random_rows(seed)
    assert [
        tuple(r) for r in reports.region_running_totals(make_conn(rows))
    ] == ref_running(rows)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("k", [1, 2, 3])
def test_top_products_random(seed, k):
    rows = random_rows(seed)
    assert [tuple(r) for r in reports.top_products(make_conn(rows), k)] == ref_top(
        rows, k
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_month_over_month_random(seed):
    rows = random_rows(seed)
    assert_mom(reports.month_over_month(make_conn(rows)), ref_mom(rows))


@pytest.mark.parametrize("seed", SEEDS)
def test_best_day_per_region_random(seed):
    rows = random_rows(seed)
    assert [
        tuple(r) for r in reports.best_day_per_region(make_conn(rows))
    ] == ref_best_day(rows)


def test_running_totals_collapse_same_day_rows():
    rows = [
        ("2026-01-02", "north", "tea", 500),
        ("2026-01-02", "north", "mug", 300),
        ("2026-01-01", "north", "tea", 100),
        ("2026-01-03", "north", "tea", -200),
        ("2026-01-01", "east", "jam", 50),
    ]
    assert [tuple(r) for r in reports.region_running_totals(make_conn(rows))] == [
        ("east", "2026-01-01", 50, 50),
        ("north", "2026-01-01", 100, 100),
        ("north", "2026-01-02", 800, 900),
        ("north", "2026-01-03", -200, 700),
    ]


def test_top_products_dense_rank_with_ties():
    rows = [
        ("2026-02-01", "north", "tea", 900),
        ("2026-02-03", "south", "mug", 900),
        ("2026-02-04", "south", "jam", 400),
        ("2026-02-05", "east", "bag", 400),
        ("2026-02-06", "east", "pen", 100),
        ("2026-03-01", "east", "pen", 700),
        ("2026-03-02", "east", "tea", 200),
        ("2026-03-09", "east", "tea", 300),
    ]
    conn = make_conn(rows)
    assert [tuple(r) for r in reports.top_products(conn, 2)] == [
        ("2026-02", "mug", 900, 1),
        ("2026-02", "tea", 900, 1),
        ("2026-02", "bag", 400, 2),
        ("2026-02", "jam", 400, 2),
        ("2026-03", "pen", 700, 1),
        ("2026-03", "tea", 500, 2),
    ]
    assert [tuple(r) for r in reports.top_products(conn, 1)] == [
        ("2026-02", "mug", 900, 1),
        ("2026-02", "tea", 900, 1),
        ("2026-03", "pen", 700, 1),
    ]


def test_month_over_month_handles_zero_and_gaps():
    rows = [
        ("2026-01-05", "north", "tea", 1000),
        ("2026-02-05", "north", "tea", 500),
        ("2026-02-06", "north", "tea", -500),
        ("2026-03-05", "north", "tea", 300),
        ("2026-05-01", "north", "tea", 400),
        ("2026-06-01", "north", "tea", 1000),
    ]
    got = reports.month_over_month(make_conn(rows))
    assert [tuple(r[:3]) for r in got] == [
        ("2026-01", 1000, None),
        ("2026-02", 0, 1000),
        ("2026-03", 300, 0),
        ("2026-05", 400, 300),
        ("2026-06", 1000, 400),
    ]
    assert got[0][3] is None
    assert got[1][3] == -100.0
    assert got[2][3] is None
    assert got[3][3] == pytest.approx(33.3)
    assert got[4][3] == 150.0


def test_best_day_tie_takes_earliest_date():
    rows = [
        ("2026-01-03", "west", "tea", 700),
        ("2026-01-01", "west", "tea", 300),
        ("2026-01-01", "west", "mug", 400),
        ("2026-01-02", "west", "tea", 100),
        ("2026-01-02", "south", "tea", -100),
    ]
    assert [tuple(r) for r in reports.best_day_per_region(make_conn(rows))] == [
        ("south", "2026-01-02", -100),
        ("west", "2026-01-01", 700),
    ]


@pytest.mark.parametrize("k", [0, -1])
def test_top_products_rejects_k_below_one(k):
    with pytest.raises(ValueError):
        reports.top_products(make_conn(random_rows(5, n=20)), k)


def test_empty_table():
    conn = make_conn([])
    assert list(reports.region_running_totals(conn)) == []
    assert list(reports.top_products(conn, 3)) == []
    assert list(reports.month_over_month(conn)) == []
    assert list(reports.best_day_per_region(conn)) == []
