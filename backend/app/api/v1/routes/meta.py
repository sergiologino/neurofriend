from fastapi import APIRouter, Query

from app.schemas.presets import PersonalityPresetRead
from app.schemas.tts_meta import TtsVoiceItem
from app.services.presets_catalog import list_personality_presets
from app.services.tts_voice_catalog import bucket_from_gender_style, voices_for_bucket

router = APIRouter()


@router.get("/personality-presets", response_model=list[PersonalityPresetRead])
def get_personality_presets() -> list[PersonalityPresetRead]:
    """Каталог пресетов для онбординга (галерея до фиксации ядра личности)."""
    return list_personality_presets()


@router.get("/tts-voices", response_model=list[TtsVoiceItem])
def get_tts_voices(
    gender_style: str | None = Query(
        None,
        description="SRS gender_style пресета: neutral / masculine / feminine — фильтр списка голосов.",
    ),
) -> list[TtsVoiceItem]:
    """Голоса OpenAI TTS, сгруппированные по манере пресета (для выбора при создании нейродруга)."""
    b = bucket_from_gender_style(gender_style)
    raw = voices_for_bucket(b)
    return [TtsVoiceItem(id=x["id"], label=x["label"], gender=x["gender"]) for x in raw]
