import uuid
from typing import Any

from pydantic import BaseModel, Field


class TemperamentIn(BaseModel):
    softness: float = 0.5
    directness: float = 0.5
    humor: float = 0.5
    initiative: float = 0.5
    emotionality: float = 0.5


class PersonalizationIn(BaseModel):
    softness_delta: float = Field(0.0, ge=-1.0, le=1.0)
    directness_delta: float = Field(0.0, ge=-1.0, le=1.0)
    initiative_delta: float = Field(0.0, ge=-1.0, le=1.0)
    emotionality_delta: float = Field(0.0, ge=-1.0, le=1.0)
    humor_delta: float = Field(0.0, ge=-1.0, le=1.0)
    reply_length_preference: str | None = Field(None, max_length=64)
    closeness_preference: str | None = Field(None, max_length=64)


class NeuroFriendCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    gender_style: str | None = None
    age_style: str | None = None
    archetype: str = Field(..., min_length=1, max_length=120)
    """Если задан, backend подмешивает темперамент и стиль из каталога `personality_presets.json`."""
    preset_id: str | None = Field(None, max_length=64)
    """SRS-имя поля; если задано, имеет приоритет над legacy `preset_id`."""
    selected_preset_id: str | None = Field(None, max_length=64)
    temperament: TemperamentIn | None = None
    personalization: PersonalizationIn | None = None
    social_style: str | None = None
    speech_style: str | None = None
    relationship_style: str | None = None
    identity_lock_confirmed: bool = False
    user_display_name: str | None = Field(None, max_length=200)
    user_timezone: str | None = Field(None, max_length=64)
    """Голос OpenAI TTS; должен соответствовать `gender_style` (после слияния с пресетом)."""
    tts_voice: str | None = Field(None, max_length=32)


class NeuroFriendPatchRequest(BaseModel):
    tts_voice: str | None = Field(None, max_length=32)


class NeuroFriendCreateResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    identity_locked: bool
    first_intro_message: str


class NeuroFriendRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    archetype: str
    identity_locked: bool

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=32000)
    client_timestamp: str | None = None


class MessageResponse(BaseModel):
    reply_text: str
    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID
    thread_id: uuid.UUID
    meta: dict[str, Any] = Field(default_factory=dict)
