from __future__ import annotations

from datetime import date

from inventory.ledger import Ledger
from inventory.models import Item


def low_stock(ledger: Ledger, items: list[Item], threshold: int, as_of: date) -> list[tuple[str, int]]:
    out = []
    for item in items:
        on_hand = ledger.stock_on_hand(item.sku, as_of)
        if on_hand < threshold:
            out.append((item.sku, on_hand))
    return sorted(out)


def movement_summary(ledger: Ledger, start: date, end: date) -> dict[str, tuple[int, int]]:
    summary: dict[str, tuple[int, int]] = {}
    for m in ledger.movements:
        if start <= m.on < end:
            total_in, total_out = summary.get(m.sku, (0, 0))
            if m.kind == "in":
                total_in += m.qty
            else:
                total_out += m.qty
            summary[m.sku] = (total_in, total_out)
    return summary
