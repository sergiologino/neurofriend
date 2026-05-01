from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class EventTimelineItem(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    event_type: str
    source: str
    importance_score: float | None
    normalized_payload_json: dict[str, Any] | None = None


class RelationshipRead(BaseModel):
    id: uuid.UUID
    person_ref: str
    display_name: str | None
    trust: float
    attachment: float
    warmth: float
    conflict_memory_score: float = 0.0
    repair_receptivity: float = 0.5
    respect_baseline: float = 0.5
    boundary_safety_score: float = 0.7
    bond_type: str = "platonic"
    affection_score: float = 0.35
    romantic_tension_score: float = 0.12
    emotional_intimacy_score: float = 0.18
    last_interaction_at: datetime | None
    active_topics_json: list | dict = Field(default_factory=list)


class BiographyDebugRead(BaseModel):
    neurofriend_id: uuid.UUID
    snapshot: dict[str, Any]
    consistency_issues: list[str] = Field(default_factory=list)


class ExpertiseDebugRead(BaseModel):
    neurofriend_id: uuid.UUID
    profile: dict[str, Any]


class ParticipantDebugRead(BaseModel):
    id: uuid.UUID
    person_ref: str
    display_name: str | None
    participant_kind: str
    voiceprint_confidence: float
    consent_status: str
    first_seen_at: datetime
    last_seen_at: datetime
    turns_seen: int
    voiceprint_json: dict[str, Any] | None = None


PARTICIPANT_CONSENT_USER_SET = frozenset(
    {
        "implicit_conversation",
        "explicit_allow",
        "declined",
    }
)


class ParticipantPatch(BaseModel):
    """Отладочное изменение участника голоса (имя для людей, согласие на дообучение отпечатка)."""

    display_name: str | None = None
    consent_status: str | None = None

    @model_validator(mode="after")
    def require_any_field(self) -> ParticipantPatch:
        if self.display_name is None and self.consent_status is None:
            raise ValueError("At least one of display_name, consent_status must be set")
        return self

    @field_validator("consent_status")
    @classmethod
    def consent_user_values(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in PARTICIPANT_CONSENT_USER_SET:
            raise ValueError("consent_status must be implicit_conversation, explicit_allow, or declined")
        return v
