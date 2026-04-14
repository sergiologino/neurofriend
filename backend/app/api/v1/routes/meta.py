from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.schemas.perception import TtsResponse
from app.schemas.presets import PersonalityPresetRead
from app.schemas.tts_meta import TtsPreviewRequest, TtsVoiceItem
from app.services import speech_openai
from app.services.openai_client import get_openai_client
from app.services.presets_catalog import list_personality_presets
from app.services.tts_voice_catalog import (
    bucket_from_gender_style,
    is_valid_voice_for_gender,
    voices_for_bucket,
)

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


@router.post("/tts-preview", response_model=TtsResponse)
async def post_tts_preview(body: TtsPreviewRequest) -> TtsResponse:
    """Прослушивание голоса до создания нейродруга (тот же синтез, что в `/perception/tts`)."""
    if get_openai_client() is None:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")
    vid = body.tts_voice.strip()
    if not is_valid_voice_for_gender(vid, body.gender_style):
        raise HTTPException(
            status_code=400,
            detail="Voice does not match gender_style for this preset",
        )
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")
    settings = get_settings()
    try:
        mp3 = await speech_openai.synthesize_speech_mp3(text=text, voice=vid)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return TtsResponse(
        audio_base64=speech_openai.bytes_to_base64_mp3(mp3),
        meta={
            "tts_model": settings.tts_model,
            "tts_voice": vid,
            "gender_style": body.gender_style,
        },
    )
