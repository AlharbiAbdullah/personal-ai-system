"""Clean the raw order export: one file of clean rows, one file of rejects with reasons."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

FIELDS = ["order_id", "customer_email", "amount", "currency", "order_date", "status"]
REJECT_FIELDS = ["row", "order_id", "reason"]
ORDER_ID_RE = re.compile(r"ORD-[0-9]{5}")
AMOUNT_RE = re.compile(r"-?[0-9]+(\.[0-9]+)?")
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%b %d, %Y")
CURRENCIES = {"USD", "EUR", "GBP"}
STATUSES = {
    "completed": "completed",
    "complete": "completed",
    "done": "completed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "pending": "pending",
    "refunded": "refunded",
}
CENT = Decimal("0.01")


def _order_id(raw: str) -> str:
    value = raw.strip().upper()
    if not ORDER_ID_RE.fullmatch(value):
        raise ValueError("bad order_id")
    return value


def _email(raw: str) -> str:
    value = raw.strip().lower()
    if value.count("@") != 1 or any(ch.isspace() for ch in value):
        raise ValueError("bad email")
    local, domain = value.split("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("bad email")
    return value


def _amount(raw: str) -> str:
    value = raw.strip()
    value = value.removeprefix("$")
    value = value.replace(",", "")
    if not AMOUNT_RE.fullmatch(value):
        raise ValueError("bad amount")
    amount = Decimal(value)
    if amount < 0:
        raise ValueError("negative amount")
    return str(amount.quantize(CENT, rounding=ROUND_HALF_UP))


def _currency(raw: str) -> str:
    value = raw.strip().upper() or "USD"
    if value not in CURRENCIES:
        raise ValueError("bad currency")
    return value


def _date(raw: str) -> str:
    value = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date().isoformat()  # noqa: DTZ007 - a date, no zone
        except ValueError:
            continue
    raise ValueError("bad date")


def _status(raw: str) -> str:
    value = raw.strip().lower()
    if value not in STATUSES:
        raise ValueError("bad status")
    return STATUSES[value]


def clean_row(row: dict[str, str]) -> dict[str, str]:
    """Return the cleaned row, or raise ValueError naming the first broken rule."""
    get = lambda key: row.get(key) or ""
    return {
        "order_id": _order_id(get("order_id")),
        "customer_email": _email(get("customer_email")),
        "amount": _amount(get("amount")),
        "currency": _currency(get("currency")),
        "order_date": _date(get("order_date")),
        "status": _status(get("status")),
    }


def clean_file(
    src: str | Path, out: str | Path, rejects: str | Path
) -> tuple[int, int]:
    """Clean SRC into OUT and REJECTS; return (clean_count, rejected_count)."""
    seen: set[str] = set()
    clean_count = rejected_count = 0
    with (
        open(src, newline="", encoding="utf-8") as src_fh,
        open(out, "w", newline="", encoding="utf-8") as out_fh,
        open(rejects, "w", newline="", encoding="utf-8") as rej_fh,
    ):
        clean_writer = csv.DictWriter(out_fh, fieldnames=FIELDS)
        reject_writer = csv.writer(rej_fh)
        clean_writer.writeheader()
        reject_writer.writerow(REJECT_FIELDS)
        for number, row in enumerate(csv.DictReader(src_fh), start=1):
            raw_id = (row.get("order_id") or "").strip()
            try:
                cleaned = clean_row(row)
                if cleaned["order_id"] in seen:
                    raise ValueError("duplicate order_id")
            except ValueError as exc:
                reject_writer.writerow([number, raw_id, str(exc)])
                rejected_count += 1
                continue
            seen.add(cleaned["order_id"])
            clean_writer.writerow(cleaned)
            clean_count += 1
    return clean_count, rejected_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rejects", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.src.is_file():
        print(f"error: no such file: {args.src}", file=sys.stderr)
        return 1
    clean_count, rejected_count = clean_file(args.src, args.out, args.rejects)
    print(f"clean={clean_count} rejected={rejected_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
