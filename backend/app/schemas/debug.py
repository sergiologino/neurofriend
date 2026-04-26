import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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
