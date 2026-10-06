"""Invoice assembly: usage totals, plan charges, discount and tax."""

from __future__ import annotations

from billing.discounts import discount_cents
from billing.plans import get_plan
from billing.tax import tax_rate

METRICS = ("api_calls", "storage_gb")


def _usage_totals(usage: list[dict]) -> dict[str, int]:
    totals = dict.fromkeys(METRICS, 0)
    for record in usage:
        if record["metric"] not in totals:
            raise ValueError("unknown metric: " + str(record["metric"]))
        totals[record["metric"]] += record["quantity"]
    return totals


def compute_invoice(customer: dict, usage: list[dict], period: str) -> dict:
    totals = _usage_totals(usage)
    plan = get_plan(customer["plan"])
    api_charge, storage_charge = plan.charges(totals["api_calls"], totals["storage_gb"])

    lines = [{"item": "base", "cents": plan.base_cents}]
    if api_charge:
        lines.append({"item": "api_calls", "cents": api_charge})
    if storage_charge:
        lines.append({"item": "storage", "cents": storage_charge})
    subtotal = plan.base_cents + api_charge + storage_charge

    discount = discount_cents(customer.get("discount_code"), plan.name, subtotal)
    taxable = subtotal - discount
    tax = round(taxable * tax_rate(customer.get("country", "")))
    return {
        "customer": customer["id"],
        "period": period,
        "lines": lines,
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": taxable + tax,
    }
