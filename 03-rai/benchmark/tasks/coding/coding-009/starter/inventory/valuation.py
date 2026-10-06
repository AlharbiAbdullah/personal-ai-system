from __future__ import annotations

from datetime import date
from decimal import Decimal

from inventory.ledger import Ledger


def average_cost(ledger: Ledger, sku: str, as_of: date) -> Decimal:
    costs = [
        float(m.unit_cost)
        for m in ledger.movements
        if m.sku == sku and m.kind == "in" and m.on <= as_of
    ]
    if not costs:
        raise KeyError(sku)
    return Decimal(str(round(sum(costs) / len(costs), 2)))


def stock_value(ledger: Ledger, sku: str, as_of: date) -> Decimal:
    on_hand = ledger.stock_on_hand(sku, as_of)
    if on_hand == 0:
        return Decimal("0.00")
    try:
        cost = average_cost(ledger, sku, as_of)
    except KeyError:
        return Decimal("0.00")
    return Decimal(str(round(float(cost) * on_hand, 2)))
