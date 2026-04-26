"""Инициатива и gap: эвристики до полной модели SRS."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.datetimeutil import utc_naive_now
from app.models.event_log import EventLog
from app.models.neurofriend import NeuroFriendProfile
from app.models.relationship_state import RelationshipModel
from app.models.user import User

USER_INBOUND_TYPES = frozenset(
    {
        "voice_message_in",
        "text_message_in",
    }
)

INITIATIVE_MESSAGE_OUT = "initiative_message_out"


def _aware_utc_from_naive(ts: datetime) -> datetime:
    if ts.tzinfo is not None:
        return ts.astimezone(timezone.utc)
    return ts.replace(tzinfo=timezone.utc)


def in_quiet_hours_utc(now_utc: datetime, *, start_hour: int, end_hour: int) -> bool:
    """Тихие часы по UTC (MVP). Если start > end — интервал через полночь."""
    h = now_utc.hour
    if start_hour <= end_hour:
        return start_hour <= h < end_hour
    return h >= start_hour or h < end_hour


def in_quiet_hours_for_timezone(
    now_utc: datetime,
    *,
    timezone_name: str,
    start_hour: int,
    end_hour: int,
) -> bool:
    try:
        local_now = now_utc.astimezone(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError:
        fallback_offsets = {
            "Europe/Moscow": 3,
            "UTC": 0,
        }
        offset = fallback_offsets.get(timezone_name, 0)
        local_now = now_utc.astimezone(timezone(timedelta(hours=offset)))
    return in_quiet_hours_utc(local_now, start_hour=start_hour, end_hour=end_hour)


async def get_user_timezone(session: AsyncSession, neurofriend_id: uuid.UUID) -> str:
    stmt = (
        select(User.timezone)
        .join(NeuroFriendProfile, NeuroFriendProfile.user_id == User.id)
        .where(NeuroFriendProfile.id == neurofriend_id)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() or "UTC"


async def get_last_initiative_out_at(session: AsyncSession, neurofriend_id: uuid.UUID) -> datetime | None:
    stmt = (
        select(EventLog.timestamp)
        .where(
            EventLog.neurofriend_id == neurofriend_id,
            EventLog.event_type == INITIATIVE_MESSAGE_OUT,
        )
        .order_by(EventLog.timestamp.desc())
        .limit(1)
    )
    r = await session.execute(stmt)
    return r.scalar_one_or_none()


async def get_last_user_inbound_at(session: AsyncSession, neurofriend_id: uuid.UUID) -> datetime | None:
    stmt = (
        select(EventLog.timestamp)
        .where(
            EventLog.neurofriend_id == neurofriend_id,
            EventLog.event_type.in_(USER_INBOUND_TYPES),
        )
        .order_by(EventLog.timestamp.desc())
        .limit(1)
    )
    r = await session.execute(stmt)
    return r.scalar_one_or_none()


async def get_primary_warmth(session: AsyncSession, neurofriend_id: uuid.UUID) -> float:
    stmt = select(RelationshipModel.warmth).where(
        RelationshipModel.neurofriend_id == neurofriend_id,
        RelationshipModel.person_ref == "user_main",
    )
    r = await session.execute(stmt)
    w = r.scalar_one_or_none()
    return float(w) if w is not None else 0.5


async def get_boundary_cooldown_factor(session: AsyncSession, neurofriend_id: uuid.UUID) -> float:
    stmt = select(RelationshipModel.conflict_memory_score, RelationshipModel.boundary_safety_score).where(
        RelationshipModel.neurofriend_id == neurofriend_id,
        RelationshipModel.person_ref == "user_main",
    )
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return 1.0
    conflict, safety = float(row[0] or 0.0), float(row[1] or 0.7)
    if conflict >= 0.55 or safety <= 0.35:
        return 0.0
    if conflict >= 0.25 or safety <= 0.55:
        return 0.45
    return 1.0


def compute_readiness(
    *,
    gap_hours: float | None,
    warmth: float,
    in_quiet: bool,
    min_gap_h: float,
    strong_gap_h: float,
) -> float:
    if in_quiet:
        return 0.0
    if gap_hours is None:
        return 0.0
    if gap_hours < min_gap_h:
        return 0.0
    span = max(strong_gap_h - min_gap_h, 1e-6)
    g = min(1.0, (gap_hours - min_gap_h) / span)
    return max(0.0, min(1.0, g * (0.45 + 0.55 * warmth)))


async def build_initiative_status(session: AsyncSession, neurofriend_id: uuid.UUID) -> dict:
    settings = get_settings()
    enabled = settings.initiative_enabled
    last_at = await get_last_user_inbound_at(session, neurofriend_id)
    now = utc_naive_now()
    gap_hours: float | None
    if last_at is None:
        gap_hours = None
    else:
        delta = now - last_at
        gap_hours = max(0.0, delta.total_seconds() / 3600.0)

    now_utc = datetime.now(timezone.utc)
    user_timezone = await get_user_timezone(session, neurofriend_id)
    quiet = in_quiet_hours_for_timezone(
        now_utc,
        timezone_name=user_timezone,
        start_hour=settings.initiative_quiet_hours_start_utc,
        end_hour=settings.initiative_quiet_hours_end_utc,
    )
    warmth = await get_primary_warmth(session, neurofriend_id)
    boundary_factor = await get_boundary_cooldown_factor(session, neurofriend_id)
    score = compute_readiness(
        gap_hours=gap_hours,
        warmth=warmth,
        in_quiet=quiet,
        min_gap_h=settings.initiative_gap_hours_min,
        strong_gap_h=settings.initiative_gap_hours_strong,
    )
    score = score * boundary_factor
    threshold = settings.initiative_readiness_threshold
    eligible = bool(enabled and score >= threshold and not quiet)

    meta = {
        "threshold": threshold,
        "gap_hours_min": settings.initiative_gap_hours_min,
        "gap_hours_strong": settings.initiative_gap_hours_strong,
        "warmth": warmth,
        "boundary_cooldown_factor": boundary_factor,
        "quiet_hours_local": [settings.initiative_quiet_hours_start_utc, settings.initiative_quiet_hours_end_utc],
        "user_timezone": user_timezone,
    }
    return {
        "last_user_message_at": last_at,
        "gap_hours": gap_hours,
        "in_quiet_hours": quiet,
        "readiness_score": round(score, 4),
        "eligible_to_reach_out": eligible,
        "initiative_enabled": enabled,
        "meta": meta,
    }
