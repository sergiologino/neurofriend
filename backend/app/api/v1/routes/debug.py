import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.event_log import EventLog
from app.models.relationship_state import RelationshipModel
from app.schemas.debug import EventTimelineItem, RelationshipRead

router = APIRouter()


@router.get("/neurofriends/{neurofriend_id}/debug/events", response_model=list[EventTimelineItem])
async def debug_event_timeline(
    neurofriend_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    before: datetime | None = None,
) -> list[EventTimelineItem]:
    stmt = select(EventLog).where(EventLog.neurofriend_id == neurofriend_id).order_by(EventLog.timestamp.desc()).limit(limit)
    if before is not None:
        stmt = (
            select(EventLog)
            .where(EventLog.neurofriend_id == neurofriend_id, EventLog.timestamp < before)
            .order_by(EventLog.timestamp.desc())
            .limit(limit)
        )
    r = await session.execute(stmt)
    rows = r.scalars().all()
    return [
        EventTimelineItem(
            id=e.id,
            timestamp=e.timestamp,
            event_type=e.event_type,
            source=e.source,
            importance_score=e.importance_score,
            normalized_payload_json=e.normalized_payload_json,
        )
        for e in rows
    ]


@router.get("/neurofriends/{neurofriend_id}/debug/relationships/primary", response_model=RelationshipRead)
async def debug_primary_relationship(
    neurofriend_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> RelationshipRead:
    r = await session.execute(
        select(RelationshipModel).where(
            RelationshipModel.neurofriend_id == neurofriend_id,
            RelationshipModel.person_ref == "user_main",
        )
    )
    rel = r.scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return RelationshipRead(
        id=rel.id,
        person_ref=rel.person_ref,
        display_name=rel.display_name,
        trust=rel.trust,
        attachment=rel.attachment,
        warmth=rel.warmth,
        last_interaction_at=rel.last_interaction_at,
        active_topics_json=rel.active_topics_json if isinstance(rel.active_topics_json, list) else [],
    )
