"""Shared time utilities for Rai hooks."""

from datetime import datetime, timezone


def get_iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
