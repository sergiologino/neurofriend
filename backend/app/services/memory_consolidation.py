"""Заготовка под ночную консолидацию памяти (сводки, decay, слияние дублей).

Реализация: воркер по Redis/Celery или отдельный процесс — см. ROADMAP этап 6–7.
"""

from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)


async def run_consolidation_for_neurofriend(_neurofriend_id: uuid.UUID) -> None:
    """Плейсхолдер: сюда попадут правила SRS (importance/decay, ежедневные сводки)."""
    logger.debug("memory_consolidation: no-op stub")
