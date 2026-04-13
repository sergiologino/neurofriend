"""Lightweight affect updates — full SRS formulas come later."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetimeutil import utc_naive_now
from app.models.relationship_state import InternalStateSnapshot, RelationshipModel


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
    # naive sentiment hook
    t = user_text.lower()
    if any(x in t for x in ("спасибо", "люблю", "рад", "хорошо")):
        v = min(1.0, v + 0.08)
        att = min(1.0, att + 0.02)
    if any(x in t for x in ("злой", "бесит", "стоп", "отвали")):
        v = max(-1.0, v - 0.12)
        hurt = min(1.0, hurt + 0.05)

    snap = InternalStateSnapshot(
        neurofriend_id=neurofriend_id,
        valence=v,
        arousal=prev.arousal if prev else 0.3,
        trust_baseline=prev.trust_baseline if prev else 0.5,
        attachment=att,
        safety=prev.safety if prev else 0.6,
        curiosity=prev.curiosity if prev else 0.5,
        loneliness=lonely,
        hurt=hurt,
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
