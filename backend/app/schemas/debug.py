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
    last_interaction_at: datetime | None
    active_topics_json: list | dict = Field(default_factory=list)
