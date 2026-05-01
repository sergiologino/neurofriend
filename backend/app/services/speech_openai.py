"""Speech I/O via OpenAI Whisper + TTS. Replace implementation keeping public functions."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.services.openai_client import get_openai_client

if TYPE_CHECKING:
    pass


async def transcribe_audio(*, audio_bytes: bytes, filename: str) -> str:
    client = get_openai_client()
    settings = get_settings()
    if not client:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    # Whisper API expects multipart file
    import io

    bio = io.BytesIO(audio_bytes)
    fname = filename or "audio.webm"
    transcript = await client.audio.transcriptions.create(
        model=settings.whisper_model,
        file=(fname, bio),
    )
    return (transcript.text or "").strip()


async def synthesize_speech_mp3(*, text: str, voice: str | None = None, speed: float | None = None) -> bytes:
    client = get_openai_client()
    settings = get_settings()
    if not client:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    v = voice or settings.tts_voice
    params: dict[str, object] = {
        "model": settings.tts_model,
        "voice": v,
        "input": text,
        "response_format": "mp3",
    }
    if speed is not None:
        params["speed"] = max(0.25, min(4.0, float(speed)))
    speech = await client.audio.speech.create(**params)  # type: ignore[arg-type]
    return speech.content  # bytes (OpenAI Python SDK)


def bytes_to_base64_mp3(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
