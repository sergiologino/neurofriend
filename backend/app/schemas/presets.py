from pydantic import BaseModel, Field


class TemperamentPreset(BaseModel):
    softness: float = Field(0.5, ge=0.0, le=1.0)
    directness: float = Field(0.5, ge=0.0, le=1.0)
    humor: float = Field(0.5, ge=0.0, le=1.0)
    initiative: float = Field(0.5, ge=0.0, le=1.0)
    emotionality: float = Field(0.5, ge=0.0, le=1.0)


class PersonalityPresetRead(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=200)
    archetype: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=1, max_length=2000)
    suggested_name: str = Field(..., min_length=1, max_length=120)
    gender_style: str | None = Field(
        None,
        description="Манера самопрезентации (SRS gender_style): neutral / masculine / feminine / …",
    )
    speech_style: str | None = None
    social_style: str | None = None
    relationship_style: str | None = None
    temperament: TemperamentPreset | None = None
    character_prompt: str | None = Field(
        None,
        description="Явные отличия голоса для LLM — коротко, но жёстко задают манеру.",
    )
    life_legend: str | None = Field(
        None,
        description="Опорная «биография» для роли; на MVP не источник истины в БД, но задаёт узнаваемость.",
    )
