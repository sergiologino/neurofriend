from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.datetimeutil import utc_naive_now
from app.core.types import jsonb_type


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
    friction: Mapped[float] = mapped_column(Float, default=0.0)
    respect_signal: Mapped[float] = mapped_column(Float, default=0.5)
    self_respect_activation: Mapped[float] = mapped_column(Float, default=0.0)
    boundary_alert: Mapped[float] = mapped_column(Float, default=0.0)
    affection: Mapped[float] = mapped_column(Float, default=0.35)
    romantic_interest: Mapped[float] = mapped_column(Float, default=0.12)
    flirt_comfort: Mapped[float] = mapped_column(Float, default=0.22)
    emotional_intimacy: Mapped[float] = mapped_column(Float, default=0.18)
    conflict_peak: Mapped[float] = mapped_column(Float, default=0.0)
    cooldown_active: Mapped[bool] = mapped_column(default=False)
    repair_readiness: Mapped[float] = mapped_column(Float, default=0.0)
    reconnection_need: Mapped[float] = mapped_column(Float, default=0.0)


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
    conflict_memory_score: Mapped[float] = mapped_column(Float, default=0.0)
    repair_receptivity: Mapped[float] = mapped_column(Float, default=0.5)
    respect_baseline: Mapped[float] = mapped_column(Float, default=0.5)
    boundary_safety_score: Mapped[float] = mapped_column(Float, default=0.7)
    bond_type: Mapped[str] = mapped_column(String(48), default="platonic")
    affection_score: Mapped[float] = mapped_column(Float, default=0.35)
    romantic_tension_score: Mapped[float] = mapped_column(Float, default=0.12)
    emotional_intimacy_score: Mapped[float] = mapped_column(Float, default=0.18)
    last_interaction_at: Mapped[datetime | None] = mapped_column(nullable=True)
    active_topics_json: Mapped[list | dict] = mapped_column(jsonb_type, default=list)
    unresolved_conflict: Mapped[bool] = mapped_column(default=False)
    last_conflict_at: Mapped[datetime | None] = mapped_column(nullable=True)
    repair_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_repair_attempt_at: Mapped[datetime | None] = mapped_column(nullable=True)
    repair_success_rate: Mapped[float] = mapped_column(Float, default=0.5)
