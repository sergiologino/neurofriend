"""Поиск релевантных фрагментов в SQL `memory_items` (рядом с Qdrant semantic_memory)."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory_item import MemoryItem

_STOPWORDS = frozenset(
    {
        "и",
        "в",
        "во",
        "не",
        "на",
        "но",
        "что",
        "как",
        "а",
        "то",
        "это",
        "от",
        "до",
        "за",
        "по",
        "из",
        "у",
        "мы",
        "вы",
        "они",
        "он",
        "она",
        "его",
        "ли",
        "же",
        "бы",
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "to",
        "of",
        "in",
        "on",
        "for",
        "and",
        "or",
        "it",
        "that",
        "this",
        "with",
    }
)
_WORD_RE = re.compile(r"[0-9a-zа-яё]{2,}", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower().replace("ё", "е") for m in _WORD_RE.finditer(text)} - _STOPWORDS


def _overlap_score(query_tokens: set[str], content: str) -> float:
    if not query_tokens:
        return 0.0
    ct = _tokens(content)
    if not ct:
        return 0.0
    hit = len(query_tokens & ct)
    return hit / max(1, len(query_tokens))


async def retrieve_sql_memory_snippets(
    session: AsyncSession,
    neurofriend_id: uuid.UUID,
    query_text: str,
    *,
    limit: int,
    candidate_pool: int = 120,
) -> list[str]:
    """
    Эвристический отбор: базовый ранг из importance × access × (1−decay), усиление пересечением слов с запросом.
    """
    if limit <= 0:
        return []

    rank_expr = MemoryItem.importance_score * MemoryItem.access_score * (1.0 - MemoryItem.decay_score)
    stmt = (
        select(MemoryItem)
        .where(MemoryItem.neurofriend_id == neurofriend_id)
        .order_by(rank_expr.desc())
        .limit(max(candidate_pool, limit * 8))
    )
    result = await session.execute(stmt)
    items = result.scalars().all()
    if not items:
        return []

    qtok = _tokens(query_text or "")
    scored: list[tuple[float, MemoryItem]] = []
    for item in items:
        base = float(item.importance_score or 0.0) * float(item.access_score or 0.0) * max(
            0.12, 1.0 - float(item.decay_score or 0.0)
        )
        ov = _overlap_score(qtok, item.content_text or "")
        scored.append((base * (1.0 + 0.45 * ov), item))

    scored.sort(key=lambda x: x[0], reverse=True)

    out: list[str] = []
    seen: set[str] = set()
    for _, item in scored:
        text = (item.content_text or "").strip()
        if len(text) < 4:
            continue
        clip = text[:320]
        key = clip.lower()[:140]
        if key in seen:
            continue
        seen.add(key)
        out.append(clip)
        if len(out) >= limit:
            break
    return out


def merge_vector_and_sql_snippets(
    vector_snippets: list[str],
    sql_snippets: list[str],
    *,
    max_total: int,
) -> list[str]:
    """Дедупликация по префиксу; сначала векторные попадания, затем SQL."""
    out: list[str] = []
    seen: set[str] = set()

    def take(batch: list[str]) -> None:
        for s in batch:
            t = s.strip()
            if len(t) < 3:
                continue
            key = t.lower()[:140]
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
            if len(out) >= max_total:
                return

    take(vector_snippets)
    take(sql_snippets)
    return out
