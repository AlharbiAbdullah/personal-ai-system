from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from inventory.models import Movement

KINDS = ("in", "out")


class InsufficientStock(Exception):
    """An outgoing movement is larger than the stock on hand."""


class Ledger:
    def __init__(self, movements: Iterable[Movement] | None = None) -> None:
        self.movements: list[Movement] = (
            list(movements) if movements is not None else []
        )

    def record(self, movement: Movement) -> None:
        if movement.qty <= 0:
            raise ValueError(f"qty must be positive: {movement.qty}")
        if movement.kind not in KINDS:
            raise ValueError(f"unknown kind: {movement.kind}")
        if movement.kind == "in" and movement.unit_cost is None:
            raise ValueError("an incoming movement needs a unit_cost")
        if movement.kind == "out":
            available = self.stock_on_hand(movement.sku, movement.on)
            if movement.qty > available:
                raise InsufficientStock(
                    f"{movement.sku}: need {movement.qty}, have {available}"
                )
        self.movements.append(movement)

    def stock_on_hand(self, sku: str, as_of: date) -> int:
        total = 0
        for m in self.movements:
            if m.sku == sku and m.on <= as_of:
                total += m.qty if m.kind == "in" else -m.qty
        return total

    def movements_between(self, start: date, end: date) -> list[Movement]:
        return [m for m in self.movements if start <= m.on <= end]
