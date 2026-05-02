from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.datetimeutil import utc_naive_now
from app.core.types import jsonb_type


class TrackedEvent(Base):
    __tablename__ = "tracked_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    neurofriend_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("neurofriend_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    title: Mapped[str] = mapped_column(String(320))
    subject_person: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    time_precision: Mapped[str] = mapped_column(String(24), default="unknown")
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    needs_clarification: Mapped[bool] = mapped_column(Boolean, default=True)
    missing_fields_json: Mapped[list | dict] = mapped_column(jsonb_type, default=list)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    follow_up_strategy: Mapped[str] = mapped_column(String(48), default="soft_check_in")
    related_memory_ids_json: Mapped[list | dict] = mapped_column(jsonb_type, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utc_naive_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_naive_now, onupdate=utc_naive_now)


class TrackedEventReminder(Base):
    __tablename__ = "tracked_event_reminders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tracked_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tracked_events.id", ondelete="CASCADE"),
        index=True,
    )
    remind_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    hint: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_naive_now)
