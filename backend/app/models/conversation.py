from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.datetimeutil import utc_naive_now
from app.core.types import jsonb_type


class ConversationThread(Base):
    __tablename__ = "conversation_threads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    neurofriend_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("neurofriend_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utc_naive_now)
    archived_at: Mapped[datetime | None] = mapped_column(nullable=True)

    messages: Mapped[list[Message]] = relationship(
        back_populates="thread",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversation_threads.id", ondelete="CASCADE"),
        index=True,
    )
    direction: Mapped[str] = mapped_column(String(8))
    role: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    message_kind: Mapped[str] = mapped_column(String(64), default="transcript")
    source: Mapped[str] = mapped_column(String(32), default="voice")
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("event_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict | None] = mapped_column(jsonb_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_naive_now, index=True)

    thread: Mapped[ConversationThread] = relationship(back_populates="messages")
