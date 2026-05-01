"""Семантическая память: Qdrant + эмбеддинги OpenAI (этап 6 ROADMAP)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.embedding_openai import embed_query, embed_texts

logger = logging.getLogger(__name__)

_qdrant: AsyncQdrantClient | None = None


def semantic_memory_ready() -> bool:
    s = get_settings()
    url = (s.qdrant_url or "").strip()
    return bool(s.semantic_memory_enabled and url and s.openai_api_key)


def get_qdrant() -> AsyncQdrantClient | None:
    global _qdrant
    if not semantic_memory_ready():
        return None
    if _qdrant is None:
        s = get_settings()
        _qdrant = AsyncQdrantClient(
            url=s.qdrant_url,
            api_key=s.qdrant_api_key,
            timeout=30.0,
        )
    return _qdrant


async def shutdown_semantic_memory() -> None:
    global _qdrant
    if _qdrant is not None:
        try:
            await _qdrant.close()
        except Exception as e:
            logger.debug("qdrant close: %s", e)
        _qdrant = None


async def init_semantic_collection() -> None:
    """Создаёт коллекцию при старте, если Qdrant доступен."""
    client = get_qdrant()
    if not client:
        logger.info("Semantic memory: disabled (no Qdrant URL or OpenAI key or flag).")
        return
    settings = get_settings()
    name = settings.qdrant_collection_semantic
    try:
        cols = await client.get_collections()
        names = {c.name for c in cols.collections}
        if name in names:
            return
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=settings.embedding_vector_size, distance=Distance.COSINE),
        )
        logger.info("Semantic memory: created Qdrant collection %r", name)
    except Exception as e:
        logger.warning("Semantic memory: init failed (continuing without vectors): %s", e)


async def retrieve_snippets(
    *,
    neurofriend_id: uuid.UUID,
    query_text: str,
    session: AsyncSession | None = None,
) -> list[str]:
    """
    Семантика (Qdrant) + при наличии сессии — фрагменты из SQL memory_items.
    """
    settings = get_settings()
    vector_part = await _retrieve_qdrant_snippets(neurofriend_id=neurofriend_id, query_text=query_text)
    sql_part: list[str] = []
    if session is not None and settings.sql_memory_retrieval_enabled:
        from app.services.sql_memory_retrieval import merge_vector_and_sql_snippets, retrieve_sql_memory_snippets

        sql_part = await retrieve_sql_memory_snippets(
            session,
            neurofriend_id,
            query_text,
            limit=settings.sql_memory_top_k,
            candidate_pool=settings.sql_memory_candidate_pool,
        )
        cap = min(24, settings.semantic_memory_top_k + settings.sql_memory_top_k)
        return merge_vector_and_sql_snippets(vector_part, sql_part, max_total=cap)
    return vector_part


async def _retrieve_qdrant_snippets(*, neurofriend_id: uuid.UUID, query_text: str) -> list[str]:
    """Top-k по косинусной близости, только точки данного нейродруга."""
    if not semantic_memory_ready() or not query_text.strip():
        return []
    client = get_qdrant()
    if not client:
        return []
    settings = get_settings()
    vec = await embed_query(query_text)
    if not vec:
        return []
    try:
        hits = await client.search(
            collection_name=settings.qdrant_collection_semantic,
            query_vector=vec,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="neurofriend_id",
                        match=MatchValue(value=str(neurofriend_id)),
                    )
                ]
            ),
            limit=settings.semantic_memory_top_k,
            with_payload=True,
        )
        out: list[str] = []
        for h in hits:
            pl = h.payload or {}
            t = pl.get("text")
            if isinstance(t, str) and t.strip():
                out.append(t.strip())
        return out
    except Exception as e:
        logger.warning("_retrieve_qdrant_snippets failed: %s", e)
        return []


def _payload(
    *,
    neurofriend_id: uuid.UUID,
    text: str,
    role: str,
    source: str,
    event_id: uuid.UUID | None,
) -> dict[str, Any]:
    return {
        "neurofriend_id": str(neurofriend_id),
        "text": text,
        "role": role,
        "source": source,
        "event_id": str(event_id) if event_id else "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def index_dialogue_turn(
    *,
    neurofriend_id: uuid.UUID,
    user_text: str,
    assistant_text: str,
    source: str,
    user_event_id: uuid.UUID,
    assistant_event_id: uuid.UUID,
) -> None:
    if not semantic_memory_ready():
        return
    client = get_qdrant()
    if not client:
        return
    settings = get_settings()
    ut = user_text.strip()
    at = assistant_text.strip()
    if not ut and not at:
        return
    texts: list[str] = []
    metas: list[tuple[str, str, uuid.UUID]] = []
    if ut:
        texts.append(ut)
        metas.append(("user", source, user_event_id))
    if at:
        texts.append(at)
        metas.append(("assistant", source, assistant_event_id))
    vectors = await embed_texts(texts)
    if not vectors or len(vectors) != len(texts):
        return
    points: list[PointStruct] = []
    for i, (vec, meta) in enumerate(zip(vectors, metas, strict=True)):
        role, src, ev = meta
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload=_payload(
                    neurofriend_id=neurofriend_id,
                    text=texts[i],
                    role=role,
                    source=src,
                    event_id=ev,
                ),
            )
        )
    try:
        await client.upsert(collection_name=settings.qdrant_collection_semantic, points=points)
    except Exception as e:
        logger.warning("index_dialogue_turn upsert failed: %s", e)


async def index_intro_only(
    *,
    neurofriend_id: uuid.UUID,
    assistant_text: str,
    source: str,
    event_id: uuid.UUID,
) -> None:
    """Первое сообщение при создании (только реплика ассистента)."""
    if not semantic_memory_ready():
        return
    client = get_qdrant()
    if not client:
        return
    at = assistant_text.strip()
    if not at:
        return
    settings = get_settings()
    vectors = await embed_texts([at])
    if not vectors:
        return
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=vectors[0],
        payload=_payload(
            neurofriend_id=neurofriend_id,
            text=at,
            role="assistant",
            source=source,
            event_id=event_id,
        ),
    )
    try:
        await client.upsert(collection_name=settings.qdrant_collection_semantic, points=[point])
    except Exception as e:
        logger.warning("index_intro_only failed: %s", e)
