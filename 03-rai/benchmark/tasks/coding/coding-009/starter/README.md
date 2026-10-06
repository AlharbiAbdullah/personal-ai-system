# inventory

Stock ledger for the warehouse. Movements are recorded per SKU; stock levels, valuation and
reports are derived from them. This README is the contract.

## Model (`inventory/models.py`)

- `Item(sku, name)`
- `Movement(sku, qty, kind, on, unit_cost=None)`: `qty` is a positive int, `kind` is `"in"`
  (delivery) or `"out"` (shipment), `on` is a `datetime.date`, `unit_cost` is a `Decimal` and
  is required for `"in"` movements.

## Ledger (`inventory/ledger.py`)

- `Ledger(movements=None)`: a new ledger. It takes a copy of the optional initial movements; the
  caller's list is never modified, and two ledgers never share movements.
- `Ledger.record(movement)`: validates and appends. Raises `ValueError` for a non-positive qty, an
  unknown kind, or an `"in"` without `unit_cost`. Raises `InsufficientStock` when an `"out"`
  movement is larger than the stock on hand at the end of its own date.
- `Ledger.stock_on_hand(sku, as_of)`: ins minus outs over all movements of that SKU dated on or
  before `as_of` (movements dated `as_of` itself count).
- `Ledger.movements_between(start, end)`: movements with `start <= on <= end`, in recorded order.

## Valuation (`inventory/valuation.py`)

- `average_cost(ledger, sku, as_of)`: weighted average unit cost of the `"in"` movements of that
  SKU dated on or before `as_of`: sum(qty * unit_cost) / sum(qty), computed in `Decimal` and
  quantized to exactly two decimal places with ROUND_HALF_UP (2.675 -> `Decimal("2.68")`,
  2 -> `Decimal("2.00")`). Raises `KeyError` when there is no such delivery.
- `stock_value(ledger, sku, as_of)`: `stock_on_hand * average_cost`, a `Decimal` quantized the same
  way. `Decimal("0.00")` when the stock on hand is 0 or there was never a delivery.

## Reports (`inventory/report.py`)

- `low_stock(ledger, items, threshold, as_of)`: `(sku, on_hand)` for every item whose stock on hand
  is at or below `threshold`, sorted by on_hand ascending, then sku.
- `movement_summary(ledger, start, end)`: `{sku: (total_in, total_out)}` over the movements dated
  from `start` to `end`, both inclusive. SKUs without movements in the window are absent.
