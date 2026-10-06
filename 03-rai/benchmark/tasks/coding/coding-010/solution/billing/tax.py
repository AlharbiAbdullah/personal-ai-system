"""Sales tax by customer country."""

from __future__ import annotations

RATES = {"DE": 0.19, "FR": 0.20, "GB": 0.20, "NL": 0.21, "SA": 0.15}


def tax_rate(country: str) -> float:
    return RATES.get(country.strip().upper(), 0.0)
