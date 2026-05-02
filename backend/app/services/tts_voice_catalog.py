"""
Голоса TTS: OpenAI (`tts-1` / `tts-1-hd`) или Yandex SpeechKit.
Список OpenAI: https://platform.openai.com/docs/guides/text-to-speech
"""

from __future__ import annotations

from typing import Literal

from app.core.config import get_settings

GenderBucket = Literal["masculine", "feminine", "neutral"]

# id — значение поля `voice` в audio.speech.create
_TTS_VOICES_RU_OPENAI: dict[str, dict[str, str]] = {
    "onyx": {"gender": "masculine", "label_ru": "Onyx — глубокий, чёткая дикция"},
    "echo": {"gender": "masculine", "label_ru": "Echo — спокойный, нейтральный"},
    "ash": {"gender": "masculine", "label_ru": "Ash — ровный, современный"},
    "verse": {"gender": "masculine", "label_ru": "Verse — выразительный"},
    "cedar": {"gender": "masculine", "label_ru": "Cedar — мягкий"},
    "nova": {"gender": "feminine", "label_ru": "Nova — ясная, тёплая"},
    "shimmer": {"gender": "feminine", "label_ru": "Shimmer — мягкая, светлая"},
    "coral": {"gender": "feminine", "label_ru": "Coral — спокойная"},
    "marin": {"gender": "feminine", "label_ru": "Marin — ровная подача"},
    "alloy": {"gender": "neutral", "label_ru": "Alloy — универсальный (нейтральный)"},
    "ballad": {"gender": "neutral", "label_ru": "Ballad — ровный, повествовательный"},
    "fable": {"gender": "neutral", "label_ru": "Fable — выразительный"},
    "sage": {"gender": "neutral", "label_ru": "Sage — спокойный, нейтральный"},
}

# api_voice — имя в Yandex API; id — ключ в БД/UI
_TTS_VOICES_RU_YANDEX: dict[str, dict[str, str]] = {
    "filipp": {"gender": "masculine", "label_ru": "Yandex — Филипп", "api_voice": "filipp"},
    "ermil": {"gender": "masculine", "label_ru": "Yandex — Ермил", "api_voice": "ermil"},
    "zahar": {"gender": "masculine", "label_ru": "Yandex — Захар", "api_voice": "zahar"},
    "alena": {"gender": "feminine", "label_ru": "Yandex — Алёна", "api_voice": "alena"},
    "jane": {"gender": "feminine", "label_ru": "Yandex — Джейн", "api_voice": "jane"},
    "marina": {"gender": "feminine", "label_ru": "Yandex — Марина", "api_voice": "marina"},
    "filipp_neu": {"gender": "neutral", "label_ru": "Yandex — Филипп (нейтр.)", "api_voice": "filipp"},
    "alena_neu": {"gender": "neutral", "label_ru": "Yandex — Алёна (нейтр.)", "api_voice": "alena"},
    "ermil_neu": {"gender": "neutral", "label_ru": "Yandex — Ермил (нейтр.)", "api_voice": "ermil"},
}

OPENAI_TO_YANDEX_VOICE: dict[str, str] = {
    "onyx": "filipp",
    "echo": "ermil",
    "ash": "zahar",
    "verse": "filipp",
    "cedar": "ermil",
    "nova": "alena",
    "shimmer": "jane",
    "coral": "marina",
    "marin": "marina",
    "alloy": "ermil_neu",
    "ballad": "filipp_neu",
    "fable": "alena_neu",
    "sage": "ermil_neu",
}

YANDEX_TO_OPENAI_VOICE: dict[str, str] = {
    "filipp": "onyx",
    "ermil": "echo",
    "zahar": "ash",
    "alena": "nova",
    "jane": "shimmer",
    "marina": "marin",
    "filipp_neu": "ballad",
    "alena_neu": "fable",
    "ermil_neu": "alloy",
}


def _active_voice_table() -> dict[str, dict[str, str]]:
    if get_settings().speech_tts_provider == "yandex":
        return _TTS_VOICES_RU_YANDEX
    return _TTS_VOICES_RU_OPENAI


def tts_api_voice_id(voice_ui_id: str) -> str:
    """Для Yandex — реальное имя голоса в API (после нормализации UI id)."""
    if get_settings().speech_tts_provider != "yandex":
        return voice_ui_id
    meta = _TTS_VOICES_RU_YANDEX.get(voice_ui_id)
    if meta and meta.get("api_voice"):
        return meta["api_voice"]
    return voice_ui_id


def default_voice_for_gender(gender_style: str | None) -> str:
    g = (gender_style or "neutral").strip().lower()
    if get_settings().speech_tts_provider == "yandex":
        if g == "masculine":
            return "filipp"
        if g == "feminine":
            return "alena"
        return "ermil_neu"
    if g == "masculine":
        return "onyx"
    if g == "feminine":
        return "nova"
    return "alloy"


def voices_for_bucket(bucket: GenderBucket) -> list[dict[str, str]]:
    """Список для UI: id + подпись (только голоса выбранной группы)."""
    table = _active_voice_table()
    return [
        {"id": vid, "label": meta["label_ru"], "gender": meta["gender"]}
        for vid, meta in sorted(table.items(), key=lambda x: x[0])
        if meta["gender"] == bucket
    ]


def bucket_from_gender_style(gender_style: str | None) -> GenderBucket:
    g = (gender_style or "neutral").strip().lower()
    if g == "masculine":
        return "masculine"
    if g == "feminine":
        return "feminine"
    return "neutral"


def is_valid_voice_for_gender(voice_id: str, gender_style: str | None) -> bool:
    """Голос должен совпадать с группой пресета (мужской/женский/нейтральный), без смешения."""
    bucket = bucket_from_gender_style(gender_style)
    table = _active_voice_table()
    meta = table.get(voice_id)
    if not meta:
        return False
    return meta["gender"] == bucket


def normalize_voice_choice(voice_id: str | None, gender_style: str | None) -> str:
    """Если None или невалидно — дефолт по полу; при смене провайдера маппит известные id."""
    provider = get_settings().speech_tts_provider
    table = _active_voice_table()
    vid = (voice_id or "").strip()

    def in_table(v: str) -> bool:
        return v in table and is_valid_voice_for_gender(v, gender_style)

    if vid and in_table(vid):
        return vid

    if provider == "yandex" and vid in OPENAI_TO_YANDEX_VOICE:
        mapped = OPENAI_TO_YANDEX_VOICE[vid]
        if in_table(mapped):
            return mapped

    if provider == "openai" and vid in YANDEX_TO_OPENAI_VOICE:
        mapped = YANDEX_TO_OPENAI_VOICE[vid]
        if in_table(mapped):
            return mapped

    return default_voice_for_gender(gender_style)
