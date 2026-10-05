"""Project calendar helpers for Indian mutual-fund reporting dates."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

INDIA_TZ=ZoneInfo("Asia/Kolkata")


def india_today(now=None):
    """Return the calendar date in Asia/Kolkata for a timezone-aware instant."""
    current=now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current=current.replace(tzinfo=timezone.utc)
    return current.astimezone(INDIA_TZ).date()
