from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.datetimeutil import utc_naive_now
from app.core.types import jsonb_type


class MemoryItem(Base):
    __tablename__ = "memory_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    neurofriend_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("neurofriend_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    memory_type: Mapped[str] = mapped_column(String(64), default="episodic", index=True)
    content_text: Mapped[str] = mapped_column(Text)
    content_structured_json: Mapped[dict] = mapped_column(jsonb_type, default=dict)
    source_event_ids_json: Mapped[list] = mapped_column(jsonb_type, default=list)
    importance_score: Mapped[float] = mapped_column(Float, default=0.3, index=True)
    access_score: Mapped[float] = mapped_column(Float, default=1.0)
    decay_score: Mapped[float] = mapped_column(Float, default=0.0)
    retrieval_count: Mapped[float] = mapped_column(Float, default=0.0)
    person_refs_json: Mapped[list] = mapped_column(jsonb_type, default=list)
    emotion_tags_json: Mapped[list] = mapped_column(jsonb_type, default=list)
    topic_tags_json: Mapped[list] = mapped_column(jsonb_type, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utc_naive_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(default=utc_naive_now, onupdate=utc_naive_now)
