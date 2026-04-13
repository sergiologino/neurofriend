"""UTC time as naive datetime — matches PostgreSQL TIMESTAMP WITHOUT TIME ZONE with asyncpg."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
