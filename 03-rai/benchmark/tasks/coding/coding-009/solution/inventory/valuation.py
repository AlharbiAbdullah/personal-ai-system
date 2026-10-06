from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from inventory.ledger import Ledger

CENT = Decimal("0.01")


def average_cost(ledger: Ledger, sku: str, as_of: date) -> Decimal:
    deliveries = [
        m for m in ledger.movements if m.sku == sku and m.kind == "in" and m.on <= as_of
    ]
    if not deliveries:
        raise KeyError(sku)
    total_cost = sum((Decimal(m.qty) * m.unit_cost for m in deliveries), Decimal(0))
    total_qty = sum(m.qty for m in deliveries)
    return (total_cost / total_qty).quantize(CENT, rounding=ROUND_HALF_UP)


def stock_value(ledger: Ledger, sku: str, as_of: date) -> Decimal:
    on_hand = ledger.stock_on_hand(sku, as_of)
    if on_hand == 0:
        return Decimal("0.00")
    try:
        cost = average_cost(ledger, sku, as_of)
    except KeyError:
        return Decimal("0.00")
    return (cost * on_hand).quantize(CENT, rounding=ROUND_HALF_UP)
