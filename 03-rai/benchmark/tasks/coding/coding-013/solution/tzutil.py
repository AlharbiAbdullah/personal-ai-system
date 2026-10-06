"""Local wall time <-> instant conversions that survive DST transitions (stdlib zoneinfo)."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

HHMM_RE = re.compile(r"[0-9]{2}:[0-9]{2}")
AMBIGUOUS_POLICIES = ("earlier", "later", "raise")


class NonexistentTimeError(ValueError):
    """The wall time is skipped by a DST jump in that zone."""


class AmbiguousTimeError(ValueError):
    """The wall time happens twice in that zone (clocks moved back)."""


def _exists(naive: datetime, tz: ZoneInfo) -> bool:
    round_trip = (
        naive.replace(tzinfo=tz, fold=0).astimezone(timezone.utc).astimezone(tz)
    )
    return round_trip.replace(tzinfo=None) == naive


def localize(naive: datetime, tz_name: str, ambiguous: str = "earlier") -> datetime:
    if ambiguous not in AMBIGUOUS_POLICIES:
        raise ValueError(
            f"ambiguous must be one of {AMBIGUOUS_POLICIES}, not {ambiguous!r}"
        )
    if naive.tzinfo is not None:
        raise ValueError("localize() needs a naive datetime")
    tz = ZoneInfo(tz_name)
    naive = naive.replace(fold=0)
    if not _exists(naive, tz):
        raise NonexistentTimeError(f"{naive} does not exist in {tz_name}")
    first, second = naive.replace(tzinfo=tz, fold=0), naive.replace(tzinfo=tz, fold=1)
    if first.utcoffset() == second.utcoffset():
        return first
    if ambiguous == "raise":
        raise AmbiguousTimeError(f"{naive} happens twice in {tz_name}")
    return first if ambiguous == "earlier" else second


def daily_at(hhmm: str, tz_name: str, start: date, days: int) -> list[datetime]:
    if not HHMM_RE.fullmatch(hhmm):
        raise ValueError(f"expected HH:MM, got {hhmm!r}")
    wall = time(int(hhmm[:2]), int(hhmm[3:]))
    if days < 0:
        raise ValueError("days must be >= 0")
    tz = ZoneInfo(tz_name)
    # fold=0 maps a skipped wall time with the pre-jump offset, i.e. shifted forward by the gap,
    # and an ambiguous one to its earlier occurrence.
    return [
        datetime.combine(start + timedelta(days=i), wall)
        .replace(tzinfo=tz, fold=0)
        .astimezone(timezone.utc)
        for i in range(days)
    ]


def elapsed(start: datetime, end: datetime, tz_name: str) -> timedelta:
    first = localize(start, tz_name).astimezone(timezone.utc)
    last = localize(end, tz_name).astimezone(timezone.utc)
    return last - first


def format_local(instant: datetime, tz_name: str) -> str:
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("format_local() needs an aware datetime")
    return instant.astimezone(ZoneInfo(tz_name)).isoformat(timespec="seconds")
