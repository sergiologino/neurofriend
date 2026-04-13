"""Формирование недавнего диалога для контекста LLM (транскрипт чата — зеркало событий)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationThread, Message


async def build_recent_transcript_text(
    session: AsyncSession,
    neurofriend_id: uuid.UUID,
    *,
    max_messages: int = 24,
    max_chars: int = 8000,
) -> str:
    """
    Последние реплики активного треда, хронологически.
    Текущая реплика пользователя в БД ещё не записана — в контексте только прошлое + она придёт отдельным user message.
    """
    r = await session.execute(
        select(ConversationThread)
        .where(
            ConversationThread.neurofriend_id == neurofriend_id,
            ConversationThread.status == "active",
        )
        .limit(1)
    )
    thread = r.scalar_one_or_none()
    if not thread:
        return ""

    r2 = await session.execute(
        select(Message).where(Message.thread_id == thread.id).order_by(Message.created_at.asc())
    )
    rows = list(r2.scalars().all())
    if len(rows) > max_messages:
        rows = rows[-max_messages:]

    lines: list[str] = []
    for m in rows:
        t = (m.text or "").strip()
        if not t:
            continue
        t = " ".join(t.split())
        if m.direction == "in" and m.role == "user":
            lines.append(f"Пользователь: {t}")
        else:
            lines.append(f"Ты (нейродруг): {t}")

    out = "\n".join(lines)
    if len(out) > max_chars:
        out = "…\n" + out[-(max_chars - 2) :]
    return out
