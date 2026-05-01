from pydantic import BaseModel, Field, field_validator


class TemperamentPreset(BaseModel):
    softness: float = Field(0.5, ge=0.0, le=1.0)
    directness: float = Field(0.5, ge=0.0, le=1.0)
    humor: float = Field(0.5, ge=0.0, le=1.0)
    initiative: float = Field(0.5, ge=0.0, le=1.0)
    emotionality: float = Field(0.5, ge=0.0, le=1.0)


class ExpertisePresetSeed(BaseModel):
    """Полноценный seed экспертизы из каталога пресетов (SRS): темы для IdentityCore.expertise_profile_json."""

    version: int = Field(default=1, ge=1, le=99)
    core_expertise: list[str] = Field(default_factory=list, max_length=36)
    strong_familiarity: list[str] = Field(default_factory=list, max_length=48)
    weak_or_neutral: list[str] = Field(default_factory=list, max_length=48)

    @field_validator("core_expertise", "strong_familiarity", "weak_or_neutral", mode="before")
    @classmethod
    def _normalize_topic_lists(cls, v: object) -> list[str]:
        if not isinstance(v, list):
            return []
        out: list[str] = []
        for item in v:
            s = str(item).strip().lower()
            if s:
                out.append(s)
        return out


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
    biography_preview: str | None = Field(
        None,
        description="Короткий пользовательский текст: как биография пресета попадает в память и границы воображения.",
        max_length=2000,
    )
    expertise_preview: str | None = Field(
        None,
        description="Короткий пользовательский текст: где персонаж силён и где будет держаться скромно (тон экспертизы).",
        max_length=2000,
    )
    expertise_profile: ExpertisePresetSeed | None = Field(
        None,
        description="Явный профиль экспертизы для создания IdentityCore; если задан, имеет приоритет над эвристикой архетипа.",
    )
