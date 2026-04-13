from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.datetimeutil import utc_naive_now


class InternalStateSnapshot(Base):
    __tablename__ = "internal_state_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    neurofriend_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("neurofriend_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(default=utc_naive_now, index=True)
    valence: Mapped[float] = mapped_column(Float, default=0.0)
    arousal: Mapped[float] = mapped_column(Float, default=0.3)
    trust_baseline: Mapped[float] = mapped_column(Float, default=0.5)
    attachment: Mapped[float] = mapped_column(Float, default=0.4)
    safety: Mapped[float] = mapped_column(Float, default=0.6)
    curiosity: Mapped[float] = mapped_column(Float, default=0.5)
    loneliness: Mapped[float] = mapped_column(Float, default=0.0)
    hurt: Mapped[float] = mapped_column(Float, default=0.0)


class RelationshipModel(Base):
    __tablename__ = "relationship_models"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    neurofriend_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("neurofriend_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    person_ref: Mapped[str] = mapped_column(String(64), default="user_main", index=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    trust: Mapped[float] = mapped_column(Float, default=0.5)
    attachment: Mapped[float] = mapped_column(Float, default=0.4)
    warmth: Mapped[float] = mapped_column(Float, default=0.5)
    last_interaction_at: Mapped[datetime | None] = mapped_column(nullable=True)
    active_topics_json: Mapped[list | dict] = mapped_column(JSONB, server_default="[]")
