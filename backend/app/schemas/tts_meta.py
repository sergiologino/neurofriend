from pydantic import BaseModel, Field


class TtsVoiceItem(BaseModel):
    id: str = Field(..., min_length=1, max_length=32)
    label: str = Field(..., min_length=1, max_length=500)
    gender: str = Field(..., min_length=1, max_length=32)
