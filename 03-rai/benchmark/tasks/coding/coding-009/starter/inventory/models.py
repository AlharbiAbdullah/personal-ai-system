from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Item:
    sku: str
    name: str


@dataclass(frozen=True)
class Movement:
    sku: str
    qty: int
    kind: str  # "in" or "out"
    on: date
    unit_cost: Decimal | None = None
