# Nightly order load

`etl/` copies changed orders from the shop database (the source) into the warehouse (dw), one
increment per run. Both sides are SQLite databases opened with the stdlib `sqlite3` module. This
README is the contract.

## Source

Table `orders(id INTEGER PRIMARY KEY, customer TEXT, amount TEXT, status TEXT, updated_at TEXT)`.

- `amount` is a decimal string with at most two decimals: `"12.30"`, `"7"`, `"0.29"`.
- `updated_at` is UTC text `YYYY-MM-DDTHH:MM:SSZ`, set whenever a row is inserted or changed, so
  text order is time order.
- The shop commits slowly. A row can become visible after a load has already run, carrying an
  `updated_at` that is older than the time of that run, or equal to the newest `updated_at` the run
  saw. Such rows must still arrive in the next run.

## Warehouse

`fact_orders(id INTEGER PRIMARY KEY, customer TEXT NOT NULL, amount_cents INTEGER NOT NULL,
status TEXT NOT NULL, updated_at TEXT NOT NULL, first_loaded_at TEXT NOT NULL,
last_loaded_at TEXT NOT NULL)` and `etl_state(key TEXT PRIMARY KEY, value TEXT NOT NULL)`; the
watermark is stored under the key `orders_watermark`.

## Modules

- `etl.extract.fetch_changes(src, watermark)`: source rows with `updated_at >= watermark` (every row
  when the watermark is `None`), ordered by `updated_at`, then `id`, as dicts with the keys `id`,
  `customer`, `amount`, `status`, `updated_at`.
- `etl.transform.transform(row)`: the warehouse row `{id, customer, amount_cents, status, updated_at}`,
  or `None` for a test order. `customer` is stripped; `status` is stripped and lowercased; an order
  whose status is `test` in any letter case, with or without surrounding spaces, is a test order;
  `amount_cents` is the exact integer number of cents (`"0.29"` -> 29, `"7"` -> 700).
- `etl.load.ensure_schema(dw)`, `etl.load.get_watermark(dw) -> str | None`,
  `etl.load.set_watermark(dw, value)`.
- `etl.load.upsert(dw, rows, loaded_at) -> int`: for each row:
  - a new id is inserted with `first_loaded_at` and `last_loaded_at` set to `loaded_at`;
  - a row whose `updated_at` is older than the stored one is ignored;
  - a row identical to the stored one (same customer, amount_cents, status and updated_at) is left
    alone;
  - otherwise the stored row gets the new customer, amount_cents, status, updated_at and
    `last_loaded_at = loaded_at`; `first_loaded_at` never changes.
  Returns the number of rows inserted or changed.
- `etl.pipeline.run(src, dw, now) -> int`: one increment. Reads the watermark, fetches, transforms,
  upserts with `loaded_at = now`, and sets the new watermark to the largest `updated_at` among all
  fetched rows (test orders included); the watermark stays as it was when nothing was fetched. The
  load and the new watermark are committed together. Returns what `upsert` returned.
