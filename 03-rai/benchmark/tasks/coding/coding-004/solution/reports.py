"""Regional sales reports over the `sales` table (see salesdb.py)."""

from __future__ import annotations

import sqlite3

RUNNING_TOTALS = """
WITH daily AS (
    SELECT region, sale_date, SUM(amount_cents) AS day_total
    FROM sales
    GROUP BY region, sale_date
)
SELECT region, sale_date, day_total,
       SUM(day_total) OVER (PARTITION BY region ORDER BY sale_date
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM daily
ORDER BY region, sale_date
"""

TOP_PRODUCTS = """
WITH monthly AS (
    SELECT substr(sale_date, 1, 7) AS month, product, SUM(amount_cents) AS total
    FROM sales
    GROUP BY month, product
), ranked AS (
    SELECT month, product, total,
           DENSE_RANK() OVER (PARTITION BY month ORDER BY total DESC) AS rnk
    FROM monthly
)
SELECT month, product, total, rnk
FROM ranked
WHERE rnk <= ?
ORDER BY month, rnk, product
"""

MONTH_OVER_MONTH = """
WITH monthly AS (
    SELECT substr(sale_date, 1, 7) AS month, SUM(amount_cents) AS total
    FROM sales
    GROUP BY month
), lagged AS (
    SELECT month, total, LAG(total) OVER (ORDER BY month) AS prev
    FROM monthly
)
SELECT month, total, prev,
       CASE WHEN prev IS NULL OR prev = 0 THEN NULL
            ELSE ROUND((total - prev) * 100.0 / prev, 1) END AS pct_change
FROM lagged
ORDER BY month
"""

BEST_DAY = """
WITH daily AS (
    SELECT region, sale_date, SUM(amount_cents) AS day_total
    FROM sales
    GROUP BY region, sale_date
), ranked AS (
    SELECT region, sale_date, day_total,
           ROW_NUMBER() OVER (PARTITION BY region ORDER BY day_total DESC, sale_date ASC) AS rn
    FROM daily
)
SELECT region, sale_date, day_total FROM ranked WHERE rn = 1 ORDER BY region
"""


def region_running_totals(conn: sqlite3.Connection) -> list[tuple[str, str, int, int]]:
    return conn.execute(RUNNING_TOTALS).fetchall()


def top_products(conn: sqlite3.Connection, k: int) -> list[tuple[str, str, int, int]]:
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")
    return conn.execute(TOP_PRODUCTS, (k,)).fetchall()


def month_over_month(
    conn: sqlite3.Connection,
) -> list[tuple[str, int, int | None, float | None]]:
    return conn.execute(MONTH_OVER_MONTH).fetchall()


def best_day_per_region(conn: sqlite3.Connection) -> list[tuple[str, str, int]]:
    return conn.execute(BEST_DAY).fetchall()
