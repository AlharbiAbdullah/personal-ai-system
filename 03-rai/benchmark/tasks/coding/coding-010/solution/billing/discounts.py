"""Discount codes."""

from __future__ import annotations

# code -> (rate, plans it applies to; None = every plan). round() on a float is kept on purpose:
# invoices already issued used exactly this rounding.
PERCENT_CODES: dict[str, tuple[float, frozenset[str] | None]] = {
    "WELCOME10": (0.10, None),
    "PRO20": (0.2, frozenset({"pro", "enterprise"})),
}


def discount_cents(code: str | None, plan_name: str, subtotal: int) -> int:
    if not code:
        return 0
    code = code.strip().upper()
    if code in PERCENT_CODES:
        rate, plans = PERCENT_CODES[code]
        if plans is not None and plan_name not in plans:
            return 0
        return round(subtotal * rate)
    if code.startswith("FLAT") and code[4:].isdigit():
        return min(subtotal, int(code[4:]) * 100)
    raise ValueError("unknown discount code: " + code)
