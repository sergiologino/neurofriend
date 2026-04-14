from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.datetimeutil import utc_naive_now
from app.models.user import User


class NeuroFriendProfile(Base):
    __tablename__ = "neurofriend_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    gender_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    age_style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    archetype: Mapped[str] = mapped_column(String(120))
    # Имя голоса OpenAI TTS; при NULL при озвучке подставляется дефолт по gender_style.
    tts_voice: Mapped[str | None] = mapped_column(String(32), nullable=True)
    identity_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    persona_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_naive_now)

    user: Mapped["User"] = relationship(back_populates="neurofriends")
    identity_core: Mapped["IdentityCore | None"] = relationship(back_populates="neurofriend", uselist=False)


class IdentityCore(Base):
    __tablename__ = "identity_cores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    neurofriend_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("neurofriend_profiles.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    core_traits_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    speech_rules_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    values_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    immutable_version: Mapped[int] = mapped_column(Integer, default=1)

    neurofriend: Mapped[NeuroFriendProfile] = relationship(
        back_populates="identity_core",
        foreign_keys=[neurofriend_id],
    )
