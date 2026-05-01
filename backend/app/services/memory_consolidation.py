"""SQL memory consolidation: first practical layer over EventLog + Qdrant retrieval."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetimeutil import utc_naive_now
from app.models.event_log import EventLog
from app.models.memory_item import MemoryItem

EMOTIONAL_WORDS = ("люблю", "ненавижу", "страшно", "грустно", "рад", "важно", "больно", "спасибо")
IDENTITY_WORDS = ("я ", "меня", "мне", "мой", "моя", "помни", "запомни", "важно")


def score_event_importance(text: str, *, event_type: str) -> float:
    t = text.lower()
    emotional = 1.0 if any(word in t for word in EMOTIONAL_WORDS) else 0.25
    identity = 1.0 if any(word in t for word in IDENTITY_WORDS) else 0.25
    novelty = 0.6 if len(t) > 80 else 0.35
    relation = 0.7 if event_type.endswith("_in") else 0.35
    score = 0.22 * novelty + 0.22 * emotional + 0.18 * 0.4 + 0.14 * identity + 0.14 * relation + 0.10 * 0.4
    return round(max(0.0, min(1.0, score)), 4)


def _event_text(event: EventLog) -> str:
    payload = event.normalized_payload_json or {}
    text = payload.get("text")
    return text.strip() if isinstance(text, str) else ""


async def create_memory_from_event(session: AsyncSession, event: EventLog) -> MemoryItem | None:
    text = _event_text(event)
    if not text:
        return None
    score = event.importance_score if event.importance_score is not None else score_event_importance(text, event_type=event.event_type)
    memory_type = "fast" if score >= 0.62 else "episodic"
    item = MemoryItem(
        neurofriend_id=event.neurofriend_id,
        memory_type=memory_type,
        content_text=text,
        content_structured_json={"event_type": event.event_type, "source": event.source},
        source_event_ids_json=[str(event.id)],
        importance_score=score,
        access_score=1.0,
        decay_score=0.0,
        person_refs_json=["user_main"] if event.event_type.endswith("_in") else [],
        emotion_tags_json=[],
        topic_tags_json=[],
    )
    session.add(item)
    event.importance_score = score
    await session.flush()
    return item


async def apply_decay(session: AsyncSession, neurofriend_id: uuid.UUID, *, now: datetime | None = None) -> int:
    current = now or utc_naive_now()
    result = await session.execute(select(MemoryItem).where(MemoryItem.neurofriend_id == neurofriend_id))
    rows = result.scalars().all()
    for item in rows:
        age_days = max(0.0, (current - item.created_at).total_seconds() / 86400.0)
        decay = min(1.0, age_days * 0.015 * (1.2 - min(item.importance_score, 1.0)))
        item.decay_score = round(decay, 4)
        item.access_score = round(max(0.05, item.importance_score * (1.0 - decay)), 4)
    await session.flush()
    return len(rows)


async def create_daily_summary(
    session: AsyncSession,
    neurofriend_id: uuid.UUID,
    *,
    since: datetime,
) -> MemoryItem | None:
    result = await session.execute(
        select(MemoryItem)
        .where(
            MemoryItem.neurofriend_id == neurofriend_id,
            MemoryItem.created_at >= since,
            MemoryItem.memory_type.in_(["fast", "episodic"]),
        )
        .order_by(MemoryItem.importance_score.desc())
        .limit(8)
    )
    items = result.scalars().all()
    if not items:
        return None
    text = "Daily summary: " + " / ".join(item.content_text[:180] for item in items)
    summary = MemoryItem(
        neurofriend_id=neurofriend_id,
        memory_type="semantic_summary",
        content_text=text,
        content_structured_json={"kind": "daily_consolidation", "source_count": len(items)},
        source_event_ids_json=[
            event_id
            for item in items
            for event_id in (item.source_event_ids_json or [])
        ],
        importance_score=max(item.importance_score for item in items),
        access_score=1.0,
        decay_score=0.0,
        person_refs_json=["user_main"],
        emotion_tags_json=[],
        topic_tags_json=["daily_summary"],
    )
    session.add(summary)
    await session.flush()
    return summary


async def run_consolidation_for_neurofriend(session: AsyncSession, neurofriend_id: uuid.UUID) -> dict:
    since = utc_naive_now() - timedelta(days=1)
    events_result = await session.execute(
        select(EventLog)
        .where(
            EventLog.neurofriend_id == neurofriend_id,
            EventLog.timestamp >= since,
            EventLog.event_type.in_(["text_message_in", "voice_message_in", "text_message_out", "voice_message_out"]),
        )
        .order_by(EventLog.timestamp.asc())
    )
    events = events_result.scalars().all()
    created = 0
    existing_memories_result = await session.execute(select(MemoryItem).where(MemoryItem.neurofriend_id == neurofriend_id))
    seen_event_ids = {
        str(event_id)
        for item in existing_memories_result.scalars().all()
        for event_id in (item.source_event_ids_json or [])
    }
    for event in events:
        if str(event.id) in seen_event_ids:
            continue
        if await create_memory_from_event(session, event):
            created += 1
            seen_event_ids.add(str(event.id))
    decayed = await apply_decay(session, neurofriend_id)
    summary = await create_daily_summary(session, neurofriend_id, since=since)
    return {
        "created_memory_items": created,
        "decayed_memory_items": decayed,
        "created_summary": summary is not None,
    }
