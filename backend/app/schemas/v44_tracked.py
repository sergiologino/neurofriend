"""Схемы API v4.4 — отслеживаемые события."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TrackedEventRead(BaseModel):
    id: uuid.UUID
    event_type: str
    title: str
    subject_person: str | None = None
    description: str | None = None
    event_time: datetime | None = None
    time_precision: str
    status: str
    needs_clarification: bool
    missing_fields_json: list | dict = Field(default_factory=list)
    importance_score: float
    follow_up_strategy: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TrackedEventCreate(BaseModel):
    event_type: str = Field(..., max_length=48)
    title: str = Field(..., max_length=320)
    subject_person: str | None = Field(None, max_length=200)
    description: str | None = None
    event_time: datetime | None = None
    time_precision: str = Field("unknown", max_length=24)
    status: str = Field("draft", max_length=24)
    needs_clarification: bool = True
    missing_fields_json: list[str] | None = None
    importance_score: float = Field(0.5, ge=0.0, le=1.0)
    follow_up_strategy: str = Field("soft_check_in", max_length=48)


class TrackedEventPatch(BaseModel):
    title: str | None = Field(None, max_length=320)
    subject_person: str | None = Field(None, max_length=200)
    description: str | None = None
    event_time: datetime | None = None
    time_precision: str | None = Field(None, max_length=24)
    status: str | None = Field(None, max_length=24)
    needs_clarification: bool | None = None
    missing_fields_json: list[str] | None = None
    importance_score: float | None = Field(None, ge=0.0, le=1.0)
    follow_up_strategy: str | None = Field(None, max_length=48)


class ActiveConflictRead(BaseModel):
    unresolved_conflict: bool
    last_conflict_at: datetime | None = None
    repair_attempt_count: int = 0
    last_repair_attempt_at: datetime | None = None
    repair_success_rate: float = 0.5
    conflict_memory_score: float = 0.0
    boundary_safety_score: float = 0.7
