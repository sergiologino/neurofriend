"""API чтения политики инициативы (этап 7)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InitiativeStatusRead(BaseModel):
    last_user_message_at: datetime | None = None
    gap_hours: float | None = Field(None, description="Часы с последней реплики пользователя (inbound)")
    in_quiet_hours: bool = Field(..., description="Сейчас «тихие часы» (UTC), инициатива подавляется")
    readiness_score: float = Field(..., ge=0.0, le=1.0, description="Условная готовность написать первым")
    eligible_to_reach_out: bool = Field(
        ...,
        description="True если порог превышен и фича включена (ещё не означает отправку)",
    )
    initiative_enabled: bool
    meta: dict[str, Any] = Field(default_factory=dict)
