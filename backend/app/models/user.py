from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.datetimeutil import utc_naive_now

if TYPE_CHECKING:
    from app.models.neurofriend import NeuroFriendProfile


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    locale: Mapped[str] = mapped_column(String(32), default="ru")
    created_at: Mapped[datetime] = mapped_column(default=utc_naive_now)

    neurofriends: Mapped[list[NeuroFriendProfile]] = relationship(back_populates="user")
