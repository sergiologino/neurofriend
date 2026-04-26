from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.datetimeutil import utc_naive_now
from app.core.types import jsonb_type


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint("neurofriend_id", "person_ref", name="uq_conversation_participant_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    neurofriend_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("neurofriend_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    person_ref: Mapped[str] = mapped_column(String(64), index=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    participant_kind: Mapped[str] = mapped_column(String(32), default="known_user", index=True)
    voiceprint_json: Mapped[dict | None] = mapped_column(jsonb_type, nullable=True)
    voiceprint_confidence: Mapped[float] = mapped_column(default=0.0)
    consent_status: Mapped[str] = mapped_column(String(32), default="implicit_conversation")
    first_seen_at: Mapped[datetime] = mapped_column(default=utc_naive_now)
    last_seen_at: Mapped[datetime] = mapped_column(default=utc_naive_now)
    turns_seen: Mapped[int] = mapped_column(Integer, default=0)
