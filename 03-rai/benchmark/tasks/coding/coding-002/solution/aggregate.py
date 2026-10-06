"""Daily and per-user summary of the app event stream (JSON Lines)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

EVENT_TYPES = {"view", "click", "purchase", "refund"}
SIGN = {"purchase": 1, "refund": -1}
CENT = Decimal("0.01")
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True)
class Event:
    event_id: str
    user_id: str
    type: str
    when: datetime  # UTC
    amount: Decimal  # signed revenue contribution


@dataclass
class DayStats:
    events: int = 0
    users: set[str] = field(default_factory=set)
    purchases: int = 0
    refunds: int = 0
    revenue: Decimal = Decimal(0)


@dataclass
class UserStats:
    events: int = 0
    revenue: Decimal = Decimal(0)
    first_seen: datetime | None = None
    last_seen: datetime | None = None


def _non_empty_str(value: object) -> bool:
    return isinstance(value, str) and value != ""


def parse_event(line: str) -> Event | None:
    """Return the event on this line, or None when the line breaks any rule."""
    try:
        data = json.loads(line, parse_float=Decimal)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    event_id, user_id, typ, ts = (
        data.get(k) for k in ("event_id", "user_id", "type", "ts")
    )
    if not (_non_empty_str(event_id) and _non_empty_str(user_id)):
        return None
    if not isinstance(typ, str) or typ not in EVENT_TYPES or not isinstance(ts, str):
        return None
    try:
        when = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if when.utcoffset() is None:
        return None
    amount = Decimal(0)
    if typ in SIGN:
        raw = data.get("amount")
        if isinstance(raw, bool) or not isinstance(raw, (int, Decimal)):
            return None
        amount = Decimal(raw)
        if not amount.is_finite() or amount <= 0:
            return None
        amount *= SIGN[typ]
    return Event(event_id, user_id, typ, when.astimezone(timezone.utc), amount)


def _money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def aggregate(lines: Iterable[str]) -> dict:
    days: dict[str, DayStats] = {}
    users: dict[str, UserStats] = {}
    seen: set[str] = set()
    invalid = duplicates = 0
    for line in lines:
        if not line.strip():
            continue
        event = parse_event(line)
        if event is None:
            invalid += 1
            continue
        if event.event_id in seen:
            duplicates += 1
            continue
        seen.add(event.event_id)
        day = days.setdefault(event.when.date().isoformat(), DayStats())
        day.events += 1
        day.users.add(event.user_id)
        day.purchases += event.type == "purchase"
        day.refunds += event.type == "refund"
        day.revenue += event.amount
        user = users.setdefault(event.user_id, UserStats())
        user.events += 1
        user.revenue += event.amount
        user.first_seen = (
            event.when if user.first_seen is None else min(user.first_seen, event.when)
        )
        user.last_seen = (
            event.when if user.last_seen is None else max(user.last_seen, event.when)
        )
    return {
        "days": {
            key: {
                "events": d.events,
                "users": len(d.users),
                "purchases": d.purchases,
                "refunds": d.refunds,
                "revenue": _money(d.revenue),
            }
            for key, d in days.items()
        },
        "users": {
            key: {
                "events": u.events,
                "revenue": _money(u.revenue),
                "first_seen": u.first_seen.strftime(TIME_FORMAT),
                "last_seen": u.last_seen.strftime(TIME_FORMAT),
            }
            for key, u in users.items()
            if u.first_seen and u.last_seen
        },
        "invalid_lines": invalid,
        "duplicates": duplicates,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    with open(args.input, encoding="utf-8") as fh:
        result = aggregate(fh)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
    events = sum(day["events"] for day in result["days"].values())
    print(
        f"events={events} invalid={result['invalid_lines']} duplicates={result['duplicates']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
