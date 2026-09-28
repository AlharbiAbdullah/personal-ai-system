---
name: sql-patterns
description: >
  Tactical SQL patterns: window functions, CTEs, upserts, anti-joins,
  engine-specific tricks (Postgres, DuckDB, Spark SQL, Snowflake). USE WHEN
  the user is writing queries, not designing schemas.
---

# SQL Patterns

Concrete query recipes that come up often.

## Window functions

Ranking within groups:
```sql
SELECT user_id, event_at,
       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_at DESC) AS rn
FROM events
QUALIFY rn = 1;  -- BigQuery / DuckDB / Snowflake
-- (In Postgres, wrap in a subquery and filter WHERE rn = 1)
```

Running totals:
```sql
SELECT date, amount,
       SUM(amount) OVER (ORDER BY date ROWS UNBOUNDED PRECEDING) AS running_total
FROM sales;
```

Percent of total:
```sql
SELECT category, amount,
       amount * 100.0 / SUM(amount) OVER () AS pct_of_total
FROM orders;
```

## CTE chains

Break complex queries into named steps:
```sql
WITH raw AS (
    SELECT * FROM events WHERE event_at >= CURRENT_DATE - INTERVAL '7 days'
),
enriched AS (
    SELECT r.*, u.plan FROM raw r JOIN users u ON r.user_id = u.id
),
agg AS (
    SELECT plan, COUNT(*) AS events, COUNT(DISTINCT user_id) AS users
    FROM enriched GROUP BY plan
)
SELECT * FROM agg ORDER BY events DESC;
```

## Upsert patterns

Postgres:
```sql
INSERT INTO users (id, email, updated_at)
VALUES (%s, %s, NOW())
ON CONFLICT (id) DO UPDATE
    SET email = EXCLUDED.email, updated_at = EXCLUDED.updated_at;
```

Snowflake:
```sql
MERGE INTO users u
USING (SELECT %s AS id, %s AS email) s ON u.id = s.id
WHEN MATCHED THEN UPDATE SET email = s.email
WHEN NOT MATCHED THEN INSERT (id, email) VALUES (s.id, s.email);
```

## Anti-joins

Find rows in A not in B:
```sql
-- Preferred (most engines optimize well)
SELECT * FROM a
WHERE NOT EXISTS (SELECT 1 FROM b WHERE b.key = a.key);

-- LEFT JOIN version (works but uses extra memory)
SELECT a.* FROM a LEFT JOIN b ON b.key = a.key WHERE b.key IS NULL;
```

## Date bucketing

```sql
-- Postgres
SELECT DATE_TRUNC('week', event_at) AS week, COUNT(*)
FROM events GROUP BY 1;

-- DuckDB
SELECT TIME_BUCKET(INTERVAL '1 hour', event_at) AS hour, COUNT(*)
FROM events GROUP BY 1;

-- Snowflake
SELECT DATE_TRUNC(WEEK, event_at) AS week, COUNT(*)
FROM events GROUP BY 1;
```

## JSON access

Postgres:
```sql
SELECT metadata->>'source' AS source,        -- text
       (metadata->>'count')::int AS count    -- cast to int
FROM events
WHERE metadata->>'type' = 'signup';
```

DuckDB:
```sql
SELECT metadata->>'$.source' AS source,
       CAST(metadata->>'$.count' AS INTEGER) AS count
FROM events;
```

## Pivoting

```sql
-- Manual with CASE
SELECT user_id,
       SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END) AS clicks,
       SUM(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS views
FROM events GROUP BY user_id;

-- Snowflake / DuckDB have native PIVOT
SELECT * FROM events PIVOT (COUNT(*) FOR event_type IN ('click', 'view'))
```

## Gaps + islands

Find consecutive runs:
```sql
WITH numbered AS (
    SELECT user_id, login_date,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS rn
    FROM logins
),
grouped AS (
    SELECT user_id, login_date, login_date - INTERVAL '1 day' * rn AS streak_group
    FROM numbered
)
SELECT user_id, streak_group, COUNT(*) AS streak_length,
       MIN(login_date) AS streak_start, MAX(login_date) AS streak_end
FROM grouped GROUP BY user_id, streak_group;
```

## Engine-specific tips

### Postgres
- `EXPLAIN ANALYZE` liberally; read the plan backwards
- `CREATE INDEX CONCURRENTLY` to avoid locking
- `pg_stat_statements` for query performance baselines
- Partial indexes for filtered queries: `CREATE INDEX ... WHERE active = true`

### DuckDB
- Incredible for analytics on local files. `SELECT * FROM 'file.parquet'`
- Zero-copy Parquet scans
- Pandas/Arrow integration without materialization

### Spark SQL
- Partition pruning requires filter on partition column
- Broadcast small dimension tables with `BROADCAST(t)` hint
- Watch for shuffle-heavy operations; repartition before big joins

### Snowflake
- Zero-copy clone for dev datasets
- Time travel with `AT (TIMESTAMP => ...)`
- `RESULT_SCAN(LAST_QUERY_ID())` for debugging chains
- Stream + task for CDC-like flows inside Snowflake

## Anti-patterns

- `SELECT *` in production queries — names break on schema change silently
- Implicit type casts in join keys — prevent index use
- OR in WHERE across different columns — splits indexes; use UNION ALL
- `NOT IN` with nullable column — returns 0 rows because NULL semantics. Use `NOT EXISTS`.
- Correlated subqueries where a JOIN works — slower + harder to read

## Examples

- "Window function for running daily active users"
- "Upsert pattern for user profiles in Postgres"
- "Find gaps in date series"
- "Pivot event types into columns per user"
