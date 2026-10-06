from __future__ import annotations


def transform(row: dict) -> dict | None:
    if row["status"] == "test":
        return None
    return {
        "id": row["id"],
        "customer": row["customer"].strip(),
        "amount_cents": int(float(row["amount"]) * 100),
        "status": row["status"].strip().lower(),
        "updated_at": row["updated_at"],
    }
