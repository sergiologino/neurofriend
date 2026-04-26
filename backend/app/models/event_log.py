from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.datetimeutil import utc_naive_now
from app.core.types import jsonb_type


class EventLog(Base):
    __tablename__ = "event_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    neurofriend_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("neurofriend_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(default=utc_naive_now, index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(64), default="api")
    raw_payload_json: Mapped[dict | None] = mapped_column(jsonb_type, nullable=True)
    normalized_payload_json: Mapped[dict | None] = mapped_column(jsonb_type, nullable=True)
    importance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
