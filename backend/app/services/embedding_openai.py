"""Текстовые эмбеддинги через OpenAI (семантическая память)."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.services.openai_client import get_openai_client

logger = logging.getLogger(__name__)

# Запас относительно лимита токенов модели эмбеддингов
_MAX_CHARS = 12000


def _clip(text: str) -> str:
    t = text.strip()
    if len(t) > _MAX_CHARS:
        return t[:_MAX_CHARS]
    return t


async def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Один батч-запрос; возвращает None, если нет клиента или пустой ввод."""
    clipped = [_clip(t) for t in texts if t and t.strip()]
    if not clipped:
        return None
    client = get_openai_client()
    if not client:
        return None
    settings = get_settings()
    try:
        resp = await client.embeddings.create(
            model=settings.embedding_model,
            input=clipped,
        )
        # Порядок соответствует входу
        return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
    except Exception as e:
        logger.warning("embed_texts failed: %s", e)
        return None


async def embed_query(text: str) -> list[float] | None:
    vecs = await embed_texts([text])
    if not vecs:
        return None
    return vecs[0]
