"""API v4.4: tracked events + активный конфликт."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.neurofriend import NeuroFriendProfile
from app.models.relationship_state import RelationshipModel
from app.models.tracked_event import TrackedEvent
from app.schemas.v44_tracked import (
    ActiveConflictRead,
    TrackedEventCreate,
    TrackedEventPatch,
    TrackedEventRead,
)
from app.services import tracked_event_service

router = APIRouter()


async def _nf_or_404(session: AsyncSession, neurofriend_id: uuid.UUID) -> NeuroFriendProfile:
    r = await session.execute(select(NeuroFriendProfile).where(NeuroFriendProfile.id == neurofriend_id))
    nf = r.scalar_one_or_none()
    if not nf:
        raise HTTPException(status_code=404, detail="NeuroFriend not found")
    return nf


@router.get("/{neurofriend_id}/conflicts/active", response_model=ActiveConflictRead)
async def get_active_conflict(
    neurofriend_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ActiveConflictRead:
    await _nf_or_404(session, neurofriend_id)
    rrel = await session.execute(
        select(RelationshipModel).where(
            RelationshipModel.neurofriend_id == neurofriend_id,
            RelationshipModel.person_ref == "user_main",
        )
    )
    rel = rrel.scalar_one_or_none()
    if not rel:
        return ActiveConflictRead(unresolved_conflict=False)
    return ActiveConflictRead(
        unresolved_conflict=bool(rel.unresolved_conflict),
        last_conflict_at=rel.last_conflict_at,
        repair_attempt_count=int(rel.repair_attempt_count or 0),
        last_repair_attempt_at=rel.last_repair_attempt_at,
        repair_success_rate=float(rel.repair_success_rate or 0.5),
        conflict_memory_score=float(rel.conflict_memory_score or 0.0),
        boundary_safety_score=float(rel.boundary_safety_score or 0.7),
    )


@router.get("/{neurofriend_id}/tracked-events", response_model=list[TrackedEventRead])
async def list_tracked_events_route(
    neurofriend_id: uuid.UUID,
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[TrackedEventRead]:
    await _nf_or_404(session, neurofriend_id)
    rows = await tracked_event_service.list_tracked_events(session, neurofriend_id, status=status)
    return [TrackedEventRead.model_validate(x) for x in rows]


@router.post("/{neurofriend_id}/tracked-events", response_model=TrackedEventRead)
async def create_tracked_event_route(
    neurofriend_id: uuid.UUID,
    body: TrackedEventCreate,
    session: AsyncSession = Depends(get_session),
) -> TrackedEventRead:
    nf = await _nf_or_404(session, neurofriend_id)
    mf = body.missing_fields_json if body.missing_fields_json is not None else []
    row = TrackedEvent(
        user_id=nf.user_id,
        neurofriend_id=neurofriend_id,
        event_type=body.event_type.strip().lower()[:48],
        title=body.title.strip()[:320],
        subject_person=(body.subject_person.strip()[:200] if body.subject_person else None),
        description=body.description,
        event_time=body.event_time,
        time_precision=(body.time_precision or "unknown")[:24],
        status=(body.status or "draft")[:24],
        needs_clarification=body.needs_clarification,
        missing_fields_json=mf,
        importance_score=body.importance_score,
        follow_up_strategy=(body.follow_up_strategy or "soft_check_in")[:48],
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    if row.status == "confirmed":
        await tracked_event_service.schedule_reminders_for_event(session, row)
        await session.commit()
        await session.refresh(row)
    return TrackedEventRead.model_validate(row)


@router.patch("/{neurofriend_id}/tracked-events/{event_id}", response_model=TrackedEventRead)
async def patch_tracked_event_route(
    neurofriend_id: uuid.UUID,
    event_id: uuid.UUID,
    body: TrackedEventPatch,
    session: AsyncSession = Depends(get_session),
) -> TrackedEventRead:
    await _nf_or_404(session, neurofriend_id)
    ev = await tracked_event_service.get_tracked_event(session, neurofriend_id, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Tracked event not found")
    data = body.model_dump(exclude_unset=True)
    prev_status = ev.status
    for k, v in data.items():
        setattr(ev, k, v)
    await session.flush()
    await session.commit()
    await session.refresh(ev)
    if ev.status == "confirmed" and prev_status != "confirmed":
        await tracked_event_service.schedule_reminders_for_event(session, ev)
        await session.commit()
        await session.refresh(ev)
    return TrackedEventRead.model_validate(ev)


@router.post("/{neurofriend_id}/tracked-events/{event_id}/complete")
async def complete_tracked_event_route(
    neurofriend_id: uuid.UUID,
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await _nf_or_404(session, neurofriend_id)
    ok = await tracked_event_service.mark_event_completed(session, neurofriend_id, event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tracked event not found")
    await session.commit()
    return {"ok": True}


@router.post("/{neurofriend_id}/tracked-events/{event_id}/reminders")
async def reschedule_tracked_event_reminders_route(
    neurofriend_id: uuid.UUID,
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await _nf_or_404(session, neurofriend_id)
    ok = await tracked_event_service.reschedule_reminders(session, neurofriend_id, event_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tracked event not found")
    await session.commit()
    return {"ok": True}
