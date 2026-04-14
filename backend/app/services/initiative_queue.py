"""Очередь Redis для будущих исходящих инициатив (воркер — отдельный процесс)."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

INITIATIVE_QUEUE_KEY = "nf:initiative:candidates"


async def enqueue_initiative_candidate(
    *,
    neurofriend_id: uuid.UUID,
    readiness_score: float,
    extra: dict[str, Any] | None = None,
) -> bool:
    """Кладёт задачу в Redis LIST; False если Redis недоступен."""
    r = await get_redis()
    if r is None:
        logger.debug("initiative_queue: redis unavailable, skip enqueue")
        return False
    payload = {
        "neurofriend_id": str(neurofriend_id),
        "readiness_score": readiness_score,
        "extra": extra or {},
    }
    try:
        await r.rpush(INITIATIVE_QUEUE_KEY, json.dumps(payload, ensure_ascii=False))
        return True
    except Exception as e:
        logger.warning("initiative_queue enqueue failed: %s", e)
        return False
