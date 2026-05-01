"""Запуск исходящей инициативы и sweep по профилям."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.datetimeutil import utc_naive_now
from app.models.neurofriend import IdentityCore, NeuroFriendProfile
from app.models.relationship_state import InternalStateSnapshot, RelationshipModel
from app.services import affect_lite, chat_thread_service, event_service
from app.services.conversation_prompt import build_recent_transcript_text
from app.services.initiative_queue import enqueue_initiative_candidate
from app.services.initiative_service import (
    INITIATIVE_MESSAGE_OUT,
    build_initiative_status,
    get_last_initiative_out_at,
)
from app.services.llm_orchestrator import generate_initiative_ping
from app.services.semantic_memory import index_intro_only, retrieve_snippets

logger = logging.getLogger(__name__)


async def _list_neurofriend_ids(session: AsyncSession) -> list[uuid.UUID]:
    r = await session.execute(select(NeuroFriendProfile.id))
    return [row[0] for row in r.all()]


async def try_send_initiative(session: AsyncSession, neurofriend_id: uuid.UUID) -> dict:
    """Одна попытка отправить инициативу; вызывающий делает commit/rollback."""
    settings = get_settings()
    data = await build_initiative_status(session, neurofriend_id)
    if not data["eligible_to_reach_out"]:
        return {"sent": False, "reason": "not_eligible"}

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

    text = await generate_initiative_ping(
        nf=nf,
        core=core,
        state=state,
        rel=rel,
        gap_hours=gap_f,
        memory_snippets=memory_snippets,
        conversation_transcript=transcript_ctx,
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
