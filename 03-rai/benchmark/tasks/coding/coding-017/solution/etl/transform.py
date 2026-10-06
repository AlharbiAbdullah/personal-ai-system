from __future__ import annotations

from decimal import Decimal


def transform(row: dict) -> dict | None:
    status = row["status"].strip().lower()
    if status == "test":
        return None
    return {
        "id": row["id"],
        "customer": row["customer"].strip(),
        "amount_cents": int(Decimal(row["amount"].strip()) * 100),
        "status": status,
        "updated_at": row["updated_at"],
    }
