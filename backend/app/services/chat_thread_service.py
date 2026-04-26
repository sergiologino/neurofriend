"""Chat threads are transcript mirrors — not source of truth. Rollover at N messages."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.datetimeutil import utc_naive_now
from app.models.conversation import ConversationThread, Message
from app.services.chat_policy import should_rollover_before_append


async def get_or_create_active_thread(session: AsyncSession, neurofriend_id: uuid.UUID) -> ConversationThread:
    stmt = (
        select(ConversationThread)
        .where(
            ConversationThread.neurofriend_id == neurofriend_id,
            ConversationThread.status == "active",
        )
        .limit(1)
    )
    res = await session.execute(stmt)
    thread = res.scalar_one_or_none()
    if thread:
        return thread
    thread = ConversationThread(neurofriend_id=neurofriend_id, status="active", message_count=0)
    session.add(thread)
    await session.flush()
    return thread


async def _copy_carryover(
    session: AsyncSession,
    *,
    from_thread: ConversationThread,
    to_thread: ConversationThread,
    carryover: int,
) -> None:
    stmt = (
        select(Message)
        .where(Message.thread_id == from_thread.id)
        .order_by(Message.created_at.desc())
        .limit(carryover)
    )
    res = await session.execute(stmt)
    rows = list(res.scalars().all())
    rows.reverse()
    for m in rows:
        meta = dict(m.metadata_json or {})
        meta["carryover"] = True
        meta["from_thread_id"] = str(from_thread.id)
        clone = Message(
            thread_id=to_thread.id,
            direction=m.direction,
            role=m.role,
            text=m.text,
            message_kind=m.message_kind,
            source=m.source,
            event_id=m.event_id,
            metadata_json=meta,
        )
        session.add(clone)
    await session.flush()
    to_thread.message_count = len(rows)


async def rollover_if_full(
    session: AsyncSession,
    thread: ConversationThread,
    incoming_messages: int = 2,
) -> ConversationThread:
    """Rollover when appending `incoming_messages` would exceed the per-thread cap (2 = пара, 1 = одна реплика)."""
    settings = get_settings()
    max_m = settings.chat_max_messages_per_thread
    carryover = settings.chat_carryover_messages
    if not should_rollover_before_append(
        message_count=thread.message_count, incoming_messages=incoming_messages, max_messages=max_m
    ):
        return thread

    thread.status = "archived"
    thread.archived_at = utc_naive_now()
    new_t = ConversationThread(neurofriend_id=thread.neurofriend_id, status="active", message_count=0)
    session.add(new_t)
    await session.flush()
    await _copy_carryover(session, from_thread=thread, to_thread=new_t, carryover=carryover)
    return new_t


async def append_transcript_pair(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    user_text: str,
    assistant_text: str,
    source: str,
    inbound_event_id: uuid.UUID,
    outbound_event_id: uuid.UUID,
    user_metadata: dict | None = None,
    assistant_metadata: dict | None = None,
) -> tuple[ConversationThread, uuid.UUID, uuid.UUID]:
    """Append user+assistant rows; rollover before append if at capacity."""
    thread = await get_or_create_active_thread(session, neurofriend_id)
    thread = await rollover_if_full(session, thread, incoming_messages=2)

    user_meta = {"paired_outbound_event_id": str(outbound_event_id), **(user_metadata or {})}
    assistant_meta = {"paired_inbound_event_id": str(inbound_event_id), **(assistant_metadata or {})}
    umsg = Message(
        thread_id=thread.id,
        direction="in",
        role="user",
        text=user_text,
        message_kind="transcript",
        source=source,
        event_id=inbound_event_id,
        metadata_json=user_meta,
    )
    amsg = Message(
        thread_id=thread.id,
        direction="out",
        role="assistant",
        text=assistant_text,
        message_kind="transcript",
        source=source,
        event_id=outbound_event_id,
        metadata_json=assistant_meta,
    )
    session.add(umsg)
    session.add(amsg)
    thread.message_count += 2
    await session.flush()
    return thread, umsg.id, amsg.id


async def append_assistant_only(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    assistant_text: str,
    source: str,
    message_kind: str,
    outbound_event_id: uuid.UUID,
) -> tuple[ConversationThread, uuid.UUID]:
    """Одна исходящая реплика (инициатива без пары user)."""
    thread = await get_or_create_active_thread(session, neurofriend_id)
    thread = await rollover_if_full(session, thread, incoming_messages=1)
    amsg = Message(
        thread_id=thread.id,
        direction="out",
        role="assistant",
        text=assistant_text,
        message_kind=message_kind,
        source=source,
        event_id=outbound_event_id,
        metadata_json={"kind": message_kind},
    )
    session.add(amsg)
    thread.message_count += 1
    await session.flush()
    return thread, amsg.id
