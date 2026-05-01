from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    database_url: str = "postgresql+asyncpg://neurofriend:neurofriend@localhost:5432/neurofriend"
    redis_url: str | None = "redis://localhost:6379/0"
    qdrant_url: str | None = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_semantic: str = Field(
        default="neurofriend_semantic",
        description="Коллекция Qdrant для семантической памяти (эмбеддинги OpenAI).",
    )
    semantic_memory_enabled: bool = Field(
        default=True,
        description="Индексация и retrieval; без qdrant_url отключено.",
    )
    embedding_model: str = "text-embedding-3-small"
    embedding_vector_size: int = 1536
    semantic_memory_top_k: int = 8

    openai_api_key: str | None = None
    cors_origins: str = "http://localhost:3000,http://localhost:8080,http://127.0.0.1:8080"

    # LLM / speech defaults (OpenAI)
    chat_model: str = "gpt-4o-mini"
    whisper_model: str = "whisper-1"
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"

    # Chat transcript policy (product requirement); override via env CHAT_MAX_MESSAGES_PER_THREAD / CHAT_CARRYOVER_MESSAGES
    chat_max_messages_per_thread: int = 500
    chat_carryover_messages: int = 10

    # Инициатива (этап 7), эвристики UTC
    initiative_enabled: bool = True
    initiative_gap_hours_min: float = 4.0
    initiative_gap_hours_strong: float = 24.0
    initiative_readiness_threshold: float = 0.55
    initiative_quiet_hours_start_utc: int = 22
    initiative_quiet_hours_end_utc: int = 7
    initiative_cooldown_hours: float = 12.0
    """Если задан, `POST /v1/internal/initiative/sweep` требует заголовок `X-Initiative-Sweep-Key` с этим значением."""
    initiative_sweep_secret: str | None = None

    # Addendum v4.3 rollout flags
    biography_profile_enabled: bool = True
    expertise_profile_enabled: bool = True
    boundary_response_enabled: bool = True
    romantic_dynamics_enabled: bool = True
    speaker_recognition_enabled: bool = True
    voice_addressing_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
