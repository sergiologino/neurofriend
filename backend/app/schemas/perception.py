import uuid
from typing import Any

from pydantic import BaseModel, Field


class TtsRequest(BaseModel):
    """Синтез речи по уже готовому тексту (intro, ответ из чата, повтор)."""

    neurofriend_id: uuid.UUID
    text: str = Field(..., min_length=1, max_length=4096)


class TtsResponse(BaseModel):
    audio_base64: str = Field(..., description="MP3, base64")
    audio_mime: str = "audio/mpeg"
    meta: dict[str, Any] = Field(default_factory=dict)


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
