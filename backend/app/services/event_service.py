from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_log import EventLog


async def log_event(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    event_type: str,
    source: str = "api",
    normalized: dict[str, Any] | None = None,
    raw: dict[str, Any] | None = None,
    importance: float | None = None,
) -> EventLog:
    ev = EventLog(
        neurofriend_id=neurofriend_id,
        event_type=event_type,
        source=source,
        normalized_payload_json=normalized,
        raw_payload_json=raw,
        importance_score=importance,
    )
    session.add(ev)
    await session.flush()
    return ev
