"""v4.6 — языковая и профессиональная адаптация под пользователя."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.datetimeutil import utc_naive_now
from app.core.types import jsonb_type
from app.models.user import User

if TYPE_CHECKING:
    from app.models.neurofriend import NeuroFriendProfile


class UserLanguageProfile(Base):
    __tablename__ = "user_language_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    detected_professions_json: Mapped[list | dict] = mapped_column(jsonb_type, default=list)
    primary_profession_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    lexical_markers_json: Mapped[dict] = mapped_column(jsonb_type, default=dict)
    favorite_phrases_json: Mapped[list | dict] = mapped_column(jsonb_type, default=list)
    discourse_style_json: Mapped[dict] = mapped_column(jsonb_type, default=dict)
    jargon_tolerance: Mapped[float] = mapped_column(Float, default=0.5)
    profanity_tolerance: Mapped[float] = mapped_column(Float, default=0.0)
    humor_style_json: Mapped[dict] = mapped_column(jsonb_type, default=dict)
    professional_domains_json: Mapped[list | dict] = mapped_column(jsonb_type, default=list)
    domain_lexicon_json: Mapped[dict] = mapped_column(jsonb_type, default=dict)
    last_updated_at: Mapped[datetime] = mapped_column(default=utc_naive_now, onupdate=utc_naive_now)

    user: Mapped["User"] = relationship(back_populates="language_profile")


class UserDomainProfile(Base):
    __tablename__ = "user_domain_profiles"

    __table_args__ = (UniqueConstraint("user_id", "domain_name", name="uq_user_domain_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    domain_name: Mapped[str] = mapped_column(String(64), index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    active_vocabulary_json: Mapped[dict] = mapped_column(jsonb_type, default=dict)
    topic_frequency_score: Mapped[float] = mapped_column(Float, default=0.0)
    thinking_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metaphor_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(default=utc_naive_now, onupdate=utc_naive_now)

    user: Mapped["User"] = relationship(back_populates="domain_profiles")


class SocialLearningProfile(Base):
    __tablename__ = "social_learning_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    neurofriend_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("neurofriend_profiles.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    jargon_adoption_rate: Mapped[float] = mapped_column(Float, default=0.35)
    domain_lexicon_adoption_rate: Mapped[float] = mapped_column(Float, default=0.40)
    professional_style_alignment: Mapped[float] = mapped_column(Float, default=0.30)
    max_jargon_density: Mapped[float] = mapped_column(Float, default=0.18)
    forbidden_domain_imitation_patterns: Mapped[list | dict] = mapped_column(jsonb_type, default=list)

    neurofriend: Mapped["NeuroFriendProfile"] = relationship(back_populates="social_learning_profile")
