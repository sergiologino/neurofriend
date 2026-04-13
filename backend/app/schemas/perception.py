import uuid
from typing import Any

from pydantic import BaseModel, Field


class VoiceTurnResponse(BaseModel):
    transcript: str
    reply_text: str
    audio_base64: str = Field(..., description="MP3 from TTS, base64-encoded")
    audio_mime: str = "audio/mpeg"
    neurofriend_id: uuid.UUID
    inbound_event_id: uuid.UUID
    outbound_event_id: uuid.UUID
    thread_id: uuid.UUID
    meta: dict[str, Any] = Field(default_factory=dict)
