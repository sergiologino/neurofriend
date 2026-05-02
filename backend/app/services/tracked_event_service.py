"""CRUD и ingest для TrackedEvent + напоминания (v4.4)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.datetimeutil import utc_naive_now
from app.models.neurofriend import NeuroFriendProfile
from app.models.tracked_event import TrackedEvent, TrackedEventReminder
from app.services.tracked_event_detection import detect_tracked_event_candidates


def _parse_iso(dt_str: str | None) -> datetime | None:
    if not dt_str or not str(dt_str).strip():
        return None
    s = str(dt_str).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _missing_fields_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw if x is not None][:24]
    return []


async def ingest_from_user_message(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    user_text: str,
    source_event_id: uuid.UUID | None,
) -> list[TrackedEvent]:
    """Детектит события LLM и сохраняет черновики; не коммитит."""
    settings = get_settings()
    if not settings.tracked_events_enabled:
        return []

    nf = await session.get(NeuroFriendProfile, neurofriend_id)
    if not nf:
        return []

    candidates = await detect_tracked_event_candidates(user_text)
    created: list[TrackedEvent] = []
    for c in candidates:
        title = str(c.get("title") or "").strip()[:320]
        if not title:
            continue
        et = str(c.get("event_type") or "").strip().lower()
        dup = await _find_recent_duplicate(session, neurofriend_id=neurofriend_id, event_type=et, title=title)
        if dup:
            continue

        event_time = _parse_iso(c.get("event_time_iso"))
        time_prec = str(c.get("time_precision") or "unknown").strip()[:24]
        needs = bool(c.get("needs_clarification", True))
        if event_time is not None and time_prec in {"exact", "day_only"}:
            needs = needs and bool(c.get("needs_clarification", False))

        row = TrackedEvent(
            user_id=nf.user_id,
            neurofriend_id=neurofriend_id,
            event_type=et,
            title=title,
            subject_person=(str(c.get("subject_person")).strip()[:200] if c.get("subject_person") else None),
            description=(str(c.get("description")).strip() if c.get("description") else None),
            event_time=event_time,
            time_precision=time_prec if time_prec else "unknown",
            status="draft",
            source_event_id=source_event_id,
            needs_clarification=needs,
            missing_fields_json=_missing_fields_list(c.get("missing_fields")),
            importance_score=max(0.0, min(1.0, float(c.get("importance_score") or 0.5))),
            follow_up_strategy=str(c.get("follow_up_strategy") or "soft_check_in").strip()[:48],
        )
        if not row.needs_clarification and row.event_time is None:
            row.needs_clarification = True
            row.missing_fields_json = list(set((row.missing_fields_json or []) + ["event_time"]))

        session.add(row)
        created.append(row)
    await session.flush()
    return created


async def _find_recent_duplicate(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    event_type: str,
    title: str,
) -> bool:
    since = utc_naive_now() - timedelta(days=7)
    stmt = (
        select(TrackedEvent.id)
        .where(
            TrackedEvent.neurofriend_id == neurofriend_id,
            TrackedEvent.event_type == event_type,
            TrackedEvent.title == title,
            TrackedEvent.created_at >= since,
        )
        .limit(1)
    )
    r = await session.execute(stmt)
    return r.scalar_one_or_none() is not None


async def build_orchestrator_context(session: AsyncSession, neurofriend_id: uuid.UUID) -> str:
    """Текст для system prompt: черновики и ближайшие подтверждённые события."""
    settings = get_settings()
    if not settings.tracked_events_enabled:
        return ""

    now = utc_naive_now()
    lines: list[str] = []

    stmt_draft = (
        select(TrackedEvent)
        .where(
            TrackedEvent.neurofriend_id == neurofriend_id,
            TrackedEvent.status == "draft",
            TrackedEvent.needs_clarification.is_(True),
        )
        .order_by(TrackedEvent.created_at.desc())
        .limit(6)
    )
    r1 = await session.execute(stmt_draft)
    drafts = list(r1.scalars().all())
    if drafts and settings.event_clarification_enabled:
        lines.append("Отслеживаемые события (нужно аккуратно уточнить недостающее в диалоге, без допроса):")
        for ev in drafts:
            mf = ev.missing_fields_json if isinstance(ev.missing_fields_json, list) else []
            lines.append(
                f"- [{ev.event_type}] {ev.title}"
                + (f"; не хватает: {', '.join(str(x) for x in mf[:6])}" if mf else "")
            )

    until = now + timedelta(days=21)
    stmt_up = (
        select(TrackedEvent)
        .where(
            TrackedEvent.neurofriend_id == neurofriend_id,
            TrackedEvent.status == "confirmed",
            TrackedEvent.event_time.is_not(None),
            TrackedEvent.event_time >= now,
            TrackedEvent.event_time <= until,
        )
        .order_by(TrackedEvent.event_time.asc())
        .limit(8)
    )
    r2 = await session.execute(stmt_up)
    upcoming = list(r2.scalars().all())
    if upcoming:
        lines.append("Предстоящие подтверждённые события пользователя (можно естественно учитывать):")
        for ev in upcoming:
            et = ev.event_time.strftime("%Y-%m-%d %H:%M") if ev.event_time else "?"
            lines.append(f"- [{ev.event_type}] {ev.title} ≈ {et}")

    return "\n".join(lines) if lines else ""


async def list_tracked_events(
    session: AsyncSession,
    neurofriend_id: uuid.UUID,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[TrackedEvent]:
    stmt = select(TrackedEvent).where(TrackedEvent.neurofriend_id == neurofriend_id)
    if status:
        stmt = stmt.where(TrackedEvent.status == status)
    stmt = stmt.order_by(TrackedEvent.created_at.desc()).limit(min(limit, 200))
    r = await session.execute(stmt)
    return list(r.scalars().all())


async def get_tracked_event(
    session: AsyncSession,
    neurofriend_id: uuid.UUID,
    event_id: uuid.UUID,
) -> TrackedEvent | None:
    stmt = select(TrackedEvent).where(
        TrackedEvent.id == event_id,
        TrackedEvent.neurofriend_id == neurofriend_id,
    )
    r = await session.execute(stmt)
    return r.scalar_one_or_none()


async def schedule_reminders_for_event(session: AsyncSession, ev: TrackedEvent) -> None:
    """Создаёт напоминания для подтверждённого события с известным временем."""
    settings = get_settings()
    if not settings.tracked_event_reminders_enabled or ev.event_time is None:
        return
    if ev.status != "confirmed":
        return

    await session.execute(delete(TrackedEventReminder).where(TrackedEventReminder.tracked_event_id == ev.id))

    et = ev.event_time
    strat = (ev.follow_up_strategy or "").lower()
    hints: list[tuple[datetime, str]] = []

    if ev.event_type == "birthday":
        hints.append((et - timedelta(days=7), "Заранее про подготовку к дню рождения"))
        hints.append((et - timedelta(days=1), "Напоминание накануне"))
    elif ev.event_type == "flight":
        hints.append((et - timedelta(hours=24), "Завтра вылет — можно напомнить про сборы"))
        hints.append((et - timedelta(hours=3), "Скоро вылет — проверить документы и сборы"))
    elif ev.event_type in {"deadline", "submission"}:
        hints.append((et - timedelta(days=2), "Дедлайн близко"))
        hints.append((et - timedelta(hours=6), "Скоро срок"))
    elif strat == "multiple_reminders":
        hints.append((max(utc_naive_now(), et - timedelta(days=3)), "Мягкое напоминание"))
        hints.append((et - timedelta(hours=12), "Финальное напоминание"))
    else:
        hints.append((max(utc_naive_now(), et - timedelta(days=1)), "Мягкая проверка готовности"))

    now = utc_naive_now()
    for when, hint in hints:
        if when < now:
            continue
        session.add(
            TrackedEventReminder(
                tracked_event_id=ev.id,
                remind_at=when,
                status="pending",
                hint=hint[:400],
            )
        )
    await session.flush()


async def pop_next_due_reminder(
    session: AsyncSession,
    neurofriend_id: uuid.UUID,
) -> TrackedEventReminder | None:
    """Блокирует очередность на уровне приложения: одна due-запись для sweep."""
    now = utc_naive_now()
    stmt = (
        select(TrackedEventReminder)
        .join(TrackedEvent, TrackedEventReminder.tracked_event_id == TrackedEvent.id)
        .where(
            TrackedEvent.neurofriend_id == neurofriend_id,
            TrackedEvent.status == "confirmed",
            TrackedEventReminder.status == "pending",
            TrackedEventReminder.remind_at <= now,
        )
        .order_by(TrackedEventReminder.remind_at.asc())
        .limit(1)
    )
    r = await session.execute(stmt)
    row = r.scalar_one_or_none()
    return row


async def mark_reminder_sent(session: AsyncSession, reminder_id: uuid.UUID) -> None:
    row = await session.get(TrackedEventReminder, reminder_id)
    if row:
        row.status = "sent"
        await session.flush()


async def mark_event_completed(session: AsyncSession, neurofriend_id: uuid.UUID, event_id: uuid.UUID) -> bool:
    ev = await get_tracked_event(session, neurofriend_id, event_id)
    if not ev:
        return False
    ev.status = "completed"
    ev.needs_clarification = False
    await session.execute(delete(TrackedEventReminder).where(TrackedEventReminder.tracked_event_id == ev.id))
    await session.flush()
    return True


async def reschedule_reminders(session: AsyncSession, neurofriend_id: uuid.UUID, event_id: uuid.UUID) -> bool:
    ev = await get_tracked_event(session, neurofriend_id, event_id)
    if not ev:
        return False
    await schedule_reminders_for_event(session, ev)
    return True
