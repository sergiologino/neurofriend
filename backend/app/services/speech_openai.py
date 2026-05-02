"""Speech I/O: OpenAI Whisper + TTS или Yandex SpeechKit (см. config speech_*_provider)."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.services.openai_client import get_openai_client
from app.services.tts_voice_catalog import tts_api_voice_id

if TYPE_CHECKING:
    pass


async def transcribe_audio(*, audio_bytes: bytes, filename: str) -> str:
    settings = get_settings()
    if settings.speech_stt_provider == "yandex":
        from app.services import speech_yandex

        return await speech_yandex.transcribe_audio(audio_bytes=audio_bytes, filename=filename)

    client = get_openai_client()
    if not client:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    import io

    bio = io.BytesIO(audio_bytes)
    fname = filename or "audio.webm"
    transcript = await client.audio.transcriptions.create(
        model=settings.whisper_model,
        file=(fname, bio),
    )
    return (transcript.text or "").strip()


async def synthesize_speech_mp3(*, text: str, voice: str | None = None, speed: float | None = None) -> bytes:
    settings = get_settings()
    v_raw = voice or settings.tts_voice

    if settings.speech_tts_provider == "yandex":
        from app.services import speech_yandex

        v = tts_api_voice_id(v_raw)
        return await speech_yandex.synthesize_speech_mp3(text=text, voice=v, speed=speed)

    client = get_openai_client()
    if not client:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    params: dict[str, object] = {
        "model": settings.tts_model,
        "voice": v_raw,
        "input": text,
        "response_format": "mp3",
    }
    if speed is not None:
        params["speed"] = max(0.25, min(4.0, float(speed)))
    speech = await client.audio.speech.create(**params)  # type: ignore[arg-type]
    return speech.content  # bytes (OpenAI Python SDK)


def bytes_to_base64_mp3(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
