"""Yandex SpeechKit: TTS (REST v1) и короткое распознавание STT v1 (oggopus)."""

from __future__ import annotations

import json
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
STT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"


def _yandex_auth_headers() -> dict[str, str]:
    s = get_settings()
    key = (s.yandex_speech_api_key or "").strip()
    if not key:
        raise RuntimeError("YANDEX_SPEECH_API_KEY is not configured")
    return {"Authorization": f"Api-Key {key}"}


def _folder_query() -> dict[str, str]:
    s = get_settings()
    fid = (s.yandex_speech_folder_id or "").strip()
    if fid:
        return {"folderId": fid}
    return {}


def _yandex_speed(speed: float | None) -> float | None:
    if speed is None:
        return None
    return max(0.1, min(3.0, float(speed)))


async def synthesize_speech_mp3(*, text: str, voice: str, speed: float | None = None) -> bytes:
    """Синтез MP3; voice — уже разрешённый id для API (см. tts_api_voice_id)."""
    if not text.strip():
        return b""
    s = get_settings()
    data: dict[str, str] = {
        "text": text,
        "lang": "ru-RU",
        "voice": voice,
        "format": "mp3",
    }
    y_spd = _yandex_speed(speed)
    if y_spd is not None:
        data["speed"] = str(y_spd)
    data.update(_folder_query())

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        r = await client.post(
            TTS_URL,
            headers={**_yandex_auth_headers(), "Content-Type": "application/x-www-form-urlencoded"},
            content=urlencode(data),
        )
    if r.status_code >= 400:
        detail = (r.text or "")[:500]
        raise RuntimeError(f"Yandex TTS error {r.status_code}: {detail}")
    return r.content


def _stt_format_for_filename(filename: str) -> str | None:
    lower = (filename or "").lower()
    if lower.endswith((".ogg", ".oga", ".opus")):
        return "oggopus"
    if lower.endswith(".webm"):
        return None
    if lower.endswith(".wav"):
        return None
    return None


async def transcribe_audio(*, audio_bytes: bytes, filename: str) -> str:
    fmt = _stt_format_for_filename(filename)
    if fmt is None:
        raise RuntimeError(
            "Yandex STT v1 для этого эндпоинта ожидает Ogg Opus (.ogg). "
            "Браузерный WebM пока не поддержан — оставьте SPEECH_STT_PROVIDER=openai "
            "или конвертируйте аудио в Ogg Opus."
        )
    params: dict[str, str] = {"lang": "ru-RU", "format": fmt}
    params.update(_folder_query())

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        r = await client.post(
            STT_URL,
            params=params,
            headers=_yandex_auth_headers(),
            content=audio_bytes,
        )
    if r.status_code >= 400:
        detail = (r.text or "")[:500]
        raise RuntimeError(f"Yandex STT error {r.status_code}: {detail}")

    ct = (r.headers.get("content-type") or "").lower()
    if "application/json" in ct or r.text.strip().startswith("{"):
        try:
            payload = r.json()
        except json.JSONDecodeError:
            return (r.text or "").strip()
        if isinstance(payload, dict):
            res = payload.get("result")
            if isinstance(res, str):
                return res.strip()
            if res is None and "error" in payload:
                raise RuntimeError(str(payload.get("error")))
        return (r.text or "").strip()
    return (r.text or "").strip()
