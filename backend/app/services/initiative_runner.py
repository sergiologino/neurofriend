"""Запуск исходящей инициативы и sweep по профилям."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.datetimeutil import utc_naive_now
from app.models.neurofriend import IdentityCore, NeuroFriendProfile
from app.models.relationship_state import RelationshipModel
from app.models.tracked_event import TrackedEvent, TrackedEventReminder
from app.services import affect_lite, chat_thread_service, event_service, tracked_event_service
from app.services.conversation_prompt import build_recent_transcript_text
from app.services.initiative_queue import enqueue_initiative_candidate
from app.services.initiative_service import (
    EVENT_FOLLOWUP_INITIATIVE_OUT,
    INITIATIVE_MESSAGE_OUT,
    build_initiative_status,
    get_last_initiative_out_at,
)
from app.services.llm_orchestrator import generate_event_followup_ping, generate_initiative_ping
from app.services.language_adaptation_service import build_language_adaptation_context
from app.services.repair_initiative_service import try_send_repair_initiative
from app.services.semantic_memory import index_intro_only, retrieve_snippets

logger = logging.getLogger(__name__)


async def _list_neurofriend_ids(session: AsyncSession) -> list[uuid.UUID]:
    r = await session.execute(select(NeuroFriendProfile.id))
    return [row[0] for row in r.all()]


async def _send_tracked_reminder_initiative(
    session: AsyncSession,
    neurofriend_id: uuid.UUID,
    reminder_row: TrackedEventReminder,
) -> dict:
    """Исходящее напоминание по TrackedEventReminder."""
    st = await build_initiative_status(session, neurofriend_id)
    if st.get("in_quiet_hours"):
        return {"sent": False, "reason": "quiet_hours"}

    ev = await session.get(TrackedEvent, reminder_row.tracked_event_id)
    if not ev or ev.neurofriend_id != neurofriend_id or ev.status != "confirmed":
        return {"sent": False, "reason": "event_missing"}

    rnf = await session.execute(select(NeuroFriendProfile).where(NeuroFriendProfile.id == neurofriend_id))
    nf = rnf.scalar_one_or_none()
    if not nf:
        return {"sent": False, "reason": "not_found"}

    rcore = await session.execute(select(IdentityCore).where(IdentityCore.neurofriend_id == neurofriend_id))
    core = rcore.scalar_one_or_none()
    state = await affect_lite.get_latest_state(session, neurofriend_id)
    rrel = await session.execute(
        select(RelationshipModel).where(
            RelationshipModel.neurofriend_id == neurofriend_id,
            RelationshipModel.person_ref == "user_main",
        )
    )
    rel = rrel.scalar_one_or_none()
    transcript_ctx = await build_recent_transcript_text(session, neurofriend_id)
    memory_snippets = await retrieve_snippets(
        neurofriend_id=neurofriend_id,
        query_text=f"{ev.title} напоминание событие планы",
        session=session,
    )

    lang_adapt = await build_language_adaptation_context(
        session, neurofriend_id=nf.id, user_id=nf.user_id, rel=rel
    )

    text = await generate_event_followup_ping(
        nf=nf,
        core=core,
        state=state,
        rel=rel,
        event_title=ev.title,
        event_type=ev.event_type,
        reminder_hint=reminder_row.hint,
        memory_snippets=memory_snippets,
        conversation_transcript=transcript_ctx,
        language_adaptation_context=lang_adapt,
    )

    outbound = await event_service.log_event(
        session,
        neurofriend_id=nf.id,
        event_type=EVENT_FOLLOWUP_INITIATIVE_OUT,
        source="tracked_event_reminder",
        normalized={
            "text": text,
            "tracked_event_id": str(ev.id),
            "reminder_id": str(reminder_row.id),
        },
    )

    thread, _mid = await chat_thread_service.append_assistant_only(
        session,
        neurofriend_id=nf.id,
        assistant_text=text,
        source="tracked_event_reminder",
        message_kind="event_followup",
        outbound_event_id=outbound.id,
    )

    await tracked_event_service.mark_reminder_sent(session, reminder_row.id)

    await enqueue_initiative_candidate(
        neurofriend_id=nf.id,
        readiness_score=0.75,
        extra={"thread_id": str(thread.id), "event_id": str(outbound.id), "kind": "event_followup"},
    )

    await index_intro_only(
        neurofriend_id=nf.id,
        assistant_text=text,
        source="tracked_event_reminder",
        event_id=outbound.id,
    )

    logger.info(
        "event follow-up initiative neurofriend_id=%s thread_id=%s reminder_id=%s",
        nf.id,
        thread.id,
        reminder_row.id,
    )
    return {"sent": True, "thread_id": str(thread.id), "event_id": str(outbound.id), "kind": "event_followup"}


async def _try_send_generic_initiative(session: AsyncSession, neurofriend_id: uuid.UUID) -> dict:
    """Обычная инициатива после паузы (как раньше)."""
    data = await build_initiative_status(session, neurofriend_id)
    if not data["eligible_to_reach_out"]:
        return {"sent": False, "reason": "not_eligible"}

    rnf = await session.execute(select(NeuroFriendProfile).where(NeuroFriendProfile.id == neurofriend_id))
    nf = rnf.scalar_one_or_none()
    if not nf:
        return {"sent": False, "reason": "not_found"}

    rcore = await session.execute(select(IdentityCore).where(IdentityCore.neurofriend_id == neurofriend_id))
    core = rcore.scalar_one_or_none()

    state = await affect_lite.get_latest_state(session, neurofriend_id)
    rrel = await session.execute(
        select(RelationshipModel).where(
            RelationshipModel.neurofriend_id == neurofriend_id,
            RelationshipModel.person_ref == "user_main",
        )
    )
    rel = rrel.scalar_one_or_none()

    gap = data.get("gap_hours")
    gap_f = float(gap) if gap is not None else 0.0
    transcript_ctx = await build_recent_transcript_text(session, neurofriend_id)
    memory_snippets = await retrieve_snippets(
        neurofriend_id=neurofriend_id,
        query_text="настроение переживания что нового как дела",
        session=session,
    )

    lang_adapt = await build_language_adaptation_context(
        session, neurofriend_id=nf.id, user_id=nf.user_id, rel=rel
    )

    text = await generate_initiative_ping(
        nf=nf,
        core=core,
        state=state,
        rel=rel,
        gap_hours=gap_f,
        memory_snippets=memory_snippets,
        conversation_transcript=transcript_ctx,
        language_adaptation_context=lang_adapt,
    )

    outbound = await event_service.log_event(
        session,
        neurofriend_id=nf.id,
        event_type=INITIATIVE_MESSAGE_OUT,
        source="initiative",
        normalized={"text": text, "gap_hours": gap_f},
    )

    thread, _mid = await chat_thread_service.append_assistant_only(
        session,
        neurofriend_id=nf.id,
        assistant_text=text,
        source="initiative",
        message_kind="initiative",
        outbound_event_id=outbound.id,
    )

    await enqueue_initiative_candidate(
        neurofriend_id=nf.id,
        readiness_score=float(data["readiness_score"]),
        extra={"thread_id": str(thread.id), "event_id": str(outbound.id)},
    )

    await index_intro_only(
        neurofriend_id=nf.id,
        assistant_text=text,
        source="initiative",
        event_id=outbound.id,
    )

    logger.info("initiative sent neurofriend_id=%s thread_id=%s", nf.id, thread.id)
    return {"sent": True, "thread_id": str(thread.id), "event_id": str(outbound.id)}


async def try_send_initiative(session: AsyncSession, neurofriend_id: uuid.UUID) -> dict:
    """Одна попытка исходящего сообщения: напоминание по событию → repair → обычная инициатива."""
    settings = get_settings()

    last_out = await get_last_initiative_out_at(session, neurofriend_id)
    now = utc_naive_now()
    if last_out is not None:
        hours_since = (now - last_out).total_seconds() / 3600.0
        if hours_since < settings.initiative_cooldown_hours:
            return {
                "sent": False,
                "reason": "cooldown",
                "hours_since_last_initiative": round(hours_since, 2),
            }

    if settings.tracked_event_reminders_enabled:
        rem = await tracked_event_service.pop_next_due_reminder(session, neurofriend_id)
        if rem is not None:
            out = await _send_tracked_reminder_initiative(session, neurofriend_id, rem)
            if out.get("sent"):
                return out

    if settings.repair_initiative_enabled:
        rep = await try_send_repair_initiative(session, neurofriend_id)
        if rep.get("sent"):
            return rep

    return await _try_send_generic_initiative(session, neurofriend_id)


async def run_initiative_sweep(session: AsyncSession) -> dict:
    """Проходит всех нейродрузей; при успехе — commit на каждого отправителя."""
    settings = get_settings()
    if not settings.initiative_enabled:
        return {"skipped": True, "reason": "initiative_disabled", "results": []}

    ids = await _list_neurofriend_ids(session)
    results: list[dict] = []
    for nid in ids:
        try:
            res = await try_send_initiative(session, nid)
            await session.commit()
            results.append({"neurofriend_id": str(nid), **res})
        except Exception as e:
            await session.rollback()
            logger.exception("initiative sweep failed for %s", nid)
            results.append({"neurofriend_id": str(nid), "error": str(e), "sent": False})
    return {"neurofriends": len(ids), "results": results}
