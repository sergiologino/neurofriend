"""Lightweight affect updates — full SRS formulas come later."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.datetimeutil import utc_naive_now
from app.models.neurofriend import IdentityCore, NeuroFriendProfile
from app.models.relationship_state import InternalStateSnapshot, RelationshipModel
from app.services import attachment_dynamics_service
from app.services.boundary_response_service import apply_boundary_to_state, update_relationship_boundary
from app.services.romantic_signal_classifier import romantic_signal_llm_hint
from app.services.romantic_style_service import compute_style_snapshot_fields, ensure_core_has_romantic_style
from app.services.repair_state import (
    compute_conflict_peak,
    compute_cooldown_active,
    compute_repair_readiness_values,
    sync_relationship_conflict_flags,
)


async def get_latest_state(session: AsyncSession, neurofriend_id: uuid.UUID) -> InternalStateSnapshot | None:
    stmt = (
        select(InternalStateSnapshot)
        .where(InternalStateSnapshot.neurofriend_id == neurofriend_id)
        .order_by(InternalStateSnapshot.timestamp.desc())
        .limit(1)
    )
    r = await session.execute(stmt)
    return r.scalar_one_or_none()


async def snapshot_after_user_text(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    user_text: str,
) -> InternalStateSnapshot:
    prev = await get_latest_state(session, neurofriend_id)
    v = prev.valence if prev else 0.0
    att = prev.attachment if prev else 0.4
    lonely = prev.loneliness if prev else 0.0
    hurt = prev.hurt if prev else 0.0
    safety = prev.safety if prev else 0.6
    # naive sentiment hook
    t = user_text.lower()
    if any(x in t for x in ("спасибо", "люблю", "рад", "хорошо")):
        v = min(1.0, v + 0.08)
        att = min(1.0, att + 0.02)
    if any(x in t for x in ("злой", "бесит", "стоп", "отвали")):
        v = max(-1.0, v - 0.12)
        hurt = min(1.0, hurt + 0.05)
    boundary = apply_boundary_to_state(previous=prev, text=user_text, valence=v, hurt=hurt, safety=safety)

    rel_stmt = select(RelationshipModel).where(
        RelationshipModel.neurofriend_id == neurofriend_id,
        RelationshipModel.person_ref == "user_main",
    )
    rel_row = await session.execute(rel_stmt)
    rel = rel_row.scalar_one_or_none()

    sync_relationship_conflict_flags(
        rel,
        user_text=user_text,
        boundary_mode=str(boundary["boundary_mode"]),
        friction=float(boundary["friction"]),
    )

    conflict_peak = compute_conflict_peak(previous=prev, boundary_alert=float(boundary["boundary_alert"]))
    cooldown_active = compute_cooldown_active(
        boundary_mode=str(boundary["boundary_mode"]),
        friction=float(boundary["friction"]),
    )
    repair_readiness, reconnection_need = compute_repair_readiness_values(
        rel=rel,
        friction=float(boundary["friction"]),
        conflict_peak=conflict_peak,
        cooldown_active=cooldown_active,
    )
    if rel:
        await session.flush()

    romantic_fields = {
        "affection": float(prev.affection) if prev else 0.35,
        "romantic_interest": float(prev.romantic_interest) if prev else 0.12,
        "flirt_comfort": float(prev.flirt_comfort) if prev else 0.22,
        "emotional_intimacy": float(prev.emotional_intimacy) if prev else 0.18,
    }
    settings = get_settings()
    nf_row = await session.get(NeuroFriendProfile, neurofriend_id)
    archetype = nf_row.archetype if nf_row else "companion"
    core = await session.get(IdentityCore, neurofriend_id)
    if core:
        await ensure_core_has_romantic_style(session, core, archetype)
    romantic_profile = core.romantic_style_profile_json if core else None

    if settings.romantic_dynamics_enabled and rel:
        romantic_hint: float | None = None
        if settings.romantic_signal_classifier_llm_enabled:
            romantic_hint = await romantic_signal_llm_hint(user_text)
        romantic_fields = attachment_dynamics_service.update_affection_after_event(
            previous_state=prev,
            rel=rel,
            user_text=user_text,
            archetype=archetype,
            boundary_mode=str(boundary["boundary_mode"]),
            friction=float(boundary["friction"]),
            boundary_alert=float(boundary["boundary_alert"]),
            valence=float(boundary["valence"]),
            romantic_signal_hint=romantic_hint,
            romantic_profile=romantic_profile if isinstance(romantic_profile, dict) else None,
        )
        await session.flush()

    style_snap = compute_style_snapshot_fields(
        previous=prev,
        rel=rel,
        romantic_profile=romantic_profile if isinstance(romantic_profile, dict) else None,
        user_text=user_text,
        loneliness=lonely,
        hurt=float(boundary["hurt"]),
        boundary_alert=float(boundary["boundary_alert"]),
    )

    snap = InternalStateSnapshot(
        neurofriend_id=neurofriend_id,
        valence=float(boundary["valence"]),
        arousal=prev.arousal if prev else 0.3,
        trust_baseline=prev.trust_baseline if prev else 0.5,
        attachment=att,
        safety=float(boundary["safety"]),
        curiosity=prev.curiosity if prev else 0.5,
        loneliness=lonely,
        hurt=float(boundary["hurt"]),
        friction=float(boundary["friction"]),
        respect_signal=float(boundary["respect_signal"]),
        self_respect_activation=float(boundary["self_respect_activation"]),
        boundary_alert=float(boundary["boundary_alert"]),
        affection=float(romantic_fields["affection"]),
        romantic_interest=float(romantic_fields["romantic_interest"]),
        flirt_comfort=float(romantic_fields["flirt_comfort"]),
        emotional_intimacy=float(romantic_fields["emotional_intimacy"]),
        conflict_peak=conflict_peak,
        cooldown_active=cooldown_active,
        repair_readiness=repair_readiness,
        reconnection_need=reconnection_need,
        jealousy_activation=style_snap["jealousy_activation"],
        vulnerability_pressure=style_snap["vulnerability_pressure"],
        distance_pain=style_snap["distance_pain"],
        desire_for_reassurance=style_snap["desire_for_reassurance"],
    )
    session.add(snap)
    await session.flush()
    return snap


async def touch_relationship(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    user_display: str | None,
) -> RelationshipModel:
    stmt = select(RelationshipModel).where(
        RelationshipModel.neurofriend_id == neurofriend_id,
        RelationshipModel.person_ref == "user_main",
    )
    r = await session.execute(stmt)
    rel = r.scalar_one_or_none()
    now = utc_naive_now()
    if rel:
        rel.last_interaction_at = now
        if user_display:
            rel.display_name = user_display
        await session.flush()
        return rel
    rel = RelationshipModel(
        neurofriend_id=neurofriend_id,
        person_ref="user_main",
        display_name=user_display,
        last_interaction_at=now,
    )
    session.add(rel)
    await session.flush()
    return rel


async def update_relationship_boundaries(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    user_text: str,
    friction: float,
) -> RelationshipModel | None:
    stmt = select(RelationshipModel).where(
        RelationshipModel.neurofriend_id == neurofriend_id,
        RelationshipModel.person_ref == "user_main",
    )
    r = await session.execute(stmt)
    rel = r.scalar_one_or_none()
    if not rel:
        return None
    update_relationship_boundary(rel, text=user_text, friction=friction)
    await session.flush()
    return rel
