"""Исходящая repair-инициатива после конфликта (v4.4)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.datetimeutil import utc_naive_now
from app.models.neurofriend import IdentityCore, NeuroFriendProfile
from app.models.relationship_state import RelationshipModel
from app.services import affect_lite, chat_thread_service, event_service
from app.services.conversation_prompt import build_recent_transcript_text
from app.services.initiative_queue import enqueue_initiative_candidate
from app.services.initiative_service import (
    REPAIR_INITIATIVE_OUT,
    build_initiative_status,
    get_last_initiative_out_at,
    get_last_user_inbound_at,
)
from app.services.llm_orchestrator import generate_repair_ping
from app.services.language_adaptation_service import build_language_adaptation_context
from app.services.repair_state import cooldown_hours_for_peak
from app.services.semantic_memory import index_intro_only, retrieve_snippets

logger = logging.getLogger(__name__)


def compute_repair_readiness_now(
    *,
    rel: RelationshipModel,
    conflict_peak: float,
) -> float:
    if not rel.unresolved_conflict or rel.last_conflict_at is None:
        return 0.0
    now = utc_naive_now()
    hours_conflict = max(0.0, (now - rel.last_conflict_at).total_seconds() / 3600.0)
    cool = cooldown_hours_for_peak(conflict_peak)
    base = min(1.0, hours_conflict / max(cool, 0.01))
    attempts = int(rel.repair_attempt_count or 0)
    penalty = max(0.35, 1.0 - 0.18 * attempts)
    return min(1.0, base * penalty)


async def should_send_repair_initiative(session: AsyncSession, neurofriend_id: uuid.UUID) -> dict:
    settings = get_settings()
    out: dict = {"eligible": False}
    if not settings.repair_initiative_enabled or not settings.initiative_enabled:
        return out

    rrel = await session.execute(
        select(RelationshipModel).where(
            RelationshipModel.neurofriend_id == neurofriend_id,
            RelationshipModel.person_ref == "user_main",
        )
    )
    rel = rrel.scalar_one_or_none()
    if not rel or not rel.unresolved_conflict or rel.last_conflict_at is None:
        return out

    attempts = int(rel.repair_attempt_count or 0)
    if attempts >= settings.repair_attempt_max:
        return {**out, "reason": "max_attempts"}

    last_repair = rel.last_repair_attempt_at
    if last_repair is not None:
        hrs = (utc_naive_now() - last_repair).total_seconds() / 3600.0
        if hrs < settings.repair_attempt_gap_hours:
            return {**out, "reason": "repair_cooldown", "hours_since_repair": hrs}

    state = await affect_lite.get_latest_state(session, neurofriend_id)
    peak = float(state.conflict_peak) if state else 0.45
    readiness = compute_repair_readiness_now(rel=rel, conflict_peak=peak)
    if readiness < settings.repair_readiness_threshold:
        return {**out, "reason": "readiness_low", "readiness": readiness}

    last_user = await get_last_user_inbound_at(session, neurofriend_id)
    now = utc_naive_now()
    gap_hours = None
    if last_user is not None:
        gap_hours = max(0.0, (now - last_user).total_seconds() / 3600.0)

    required_pause = max(settings.repair_initiative_gap_hours_min, cooldown_hours_for_peak(peak) * 0.92)
    if gap_hours is None or gap_hours < required_pause:
        return {**out, "reason": "user_recent_or_no_gap", "gap_hours": gap_hours, "required_pause": required_pause}

    last_out = await get_last_initiative_out_at(session, neurofriend_id)
    if last_out is not None:
        since_out = (now - last_out).total_seconds() / 3600.0
        if since_out < settings.initiative_cooldown_hours:
            return {**out, "reason": "initiative_cooldown"}

    status = await build_initiative_status(session, neurofriend_id)
    if status.get("in_quiet_hours"):
        return {**out, "reason": "quiet_hours"}

    return {
        "eligible": True,
        "readiness": readiness,
        "conflict_peak": peak,
        "gap_hours": gap_hours,
        "meta": status.get("meta"),
    }


async def try_send_repair_initiative(session: AsyncSession, neurofriend_id: uuid.UUID) -> dict:
    gate = await should_send_repair_initiative(session, neurofriend_id)
    if not gate.get("eligible"):
        return {"sent": False, **gate}

    rnf = await session.execute(select(NeuroFriendProfile).where(NeuroFriendProfile.id == neurofriend_id))
    nf = rnf.scalar_one_or_none()
    if not nf:
        return {"sent": False, "reason": "not_found"}

    rcore = await session.execute(select(IdentityCore).where(IdentityCore.neurofriend_id == neurofriend_id))
    core = rcore.scalar_one_or_none()

    rrel = await session.execute(
        select(RelationshipModel).where(
            RelationshipModel.neurofriend_id == neurofriend_id,
            RelationshipModel.person_ref == "user_main",
        )
    )
    rel = rrel.scalar_one_or_none()
    state = await affect_lite.get_latest_state(session, neurofriend_id)

    transcript_ctx = await build_recent_transcript_text(session, neurofriend_id)
    memory_snippets = await retrieve_snippets(
        neurofriend_id=neurofriend_id,
        query_text="примирение разговор поддержка что было непросто",
        session=session,
    )

    gap_f = float(gate.get("gap_hours") or 0.0)
    lang_adapt = await build_language_adaptation_context(
        session, neurofriend_id=nf.id, user_id=nf.user_id, rel=rel
    )
    text = await generate_repair_ping(
        nf=nf,
        core=core,
        state=state,
        rel=rel,
        gap_hours=gap_f,
        memory_snippets=memory_snippets,
        conversation_transcript=transcript_ctx,
        conflict_peak=float(gate.get("conflict_peak") or 0.0),
        readiness=float(gate.get("readiness") or 0.0),
        language_adaptation_context=lang_adapt,
    )

    outbound = await event_service.log_event(
        session,
        neurofriend_id=nf.id,
        event_type=REPAIR_INITIATIVE_OUT,
        source="repair_initiative",
        normalized={
            "text": text,
            "gap_hours": gap_f,
            "readiness": gate.get("readiness"),
            "conflict_peak": gate.get("conflict_peak"),
        },
    )

    if rel:
        rel.repair_attempt_count = int(rel.repair_attempt_count or 0) + 1
        rel.last_repair_attempt_at = utc_naive_now()

    thread, _mid = await chat_thread_service.append_assistant_only(
        session,
        neurofriend_id=nf.id,
        assistant_text=text,
        source="repair_initiative",
        message_kind="repair_initiative",
        outbound_event_id=outbound.id,
    )

    await enqueue_initiative_candidate(
        neurofriend_id=nf.id,
        readiness_score=float(gate.get("readiness") or 0.7),
        extra={"thread_id": str(thread.id), "event_id": str(outbound.id), "kind": "repair"},
    )

    await index_intro_only(
        neurofriend_id=nf.id,
        assistant_text=text,
        source="repair_initiative",
        event_id=outbound.id,
    )

    logger.info("repair initiative sent neurofriend_id=%s thread_id=%s", nf.id, thread.id)
    return {"sent": True, "thread_id": str(thread.id), "event_id": str(outbound.id)}


# re-export for initiative_service typing
assert REPAIR_INITIATIVE_OUT
