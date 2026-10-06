"""Price plans: base fee, included usage and overage pricing."""

from __future__ import annotations

from dataclasses import dataclass

CALLS_PER_BLOCK = 1000


def _started_blocks(units: int, per: int) -> int:
    return (units + per - 1) // per


@dataclass(frozen=True)
class Plan:
    name: str
    base_cents: int
    included_calls: int
    # Overage tiers over started blocks of 1000 calls: (blocks in tier, or None for the rest; cents per block).
    call_tiers: tuple[tuple[int | None, int], ...]
    included_storage_gb: int
    cents_per_gb: int
    hard_call_limit: bool = False

    def charges(self, api_calls: int, storage_gb: int) -> tuple[int, int]:
        """Return (api_charge, storage_charge) in cents for one month's usage."""
        if self.hard_call_limit and api_calls > self.included_calls:
            raise ValueError(f"{self.name} plan limit exceeded")
        storage = max(0, storage_gb - self.included_storage_gb) * self.cents_per_gb
        return self._api_charge(api_calls), storage

    def _api_charge(self, api_calls: int) -> int:
        blocks = _started_blocks(
            max(0, api_calls - self.included_calls), CALLS_PER_BLOCK
        )
        total = 0
        for size, cents in self.call_tiers:
            taken = blocks if size is None else min(blocks, size)
            total += taken * cents
            blocks -= taken
        return total


PLANS: dict[str, Plan] = {
    plan.name: plan
    for plan in (
        Plan("free", 0, 1000, (), 1, 25, hard_call_limit=True),
        Plan("starter", 900, 10_000, ((None, 40),), 10, 20),
        Plan("pro", 4900, 100_000, ((400, 30), (None, 20)), 100, 15),
        Plan("enterprise", 25_000, 1_000_000, ((None, 10),), 500, 10),
    )
}


def get_plan(name: str) -> Plan:
    try:
        return PLANS[name]
    except (KeyError, TypeError):
        raise ValueError("unknown plan: " + str(name)) from None
