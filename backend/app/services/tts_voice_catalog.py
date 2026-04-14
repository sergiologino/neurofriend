"""
Голоса OpenAI TTS (`tts-1` / `tts-1-hd`). Подбор под `gender_style` пресета; для русского — обычно
стабильнее нейтральные/«читающие» голоса; точная оценка качества — на слух, далее возможен Yandex TTS.
Список имён синхронизирован с API: https://platform.openai.com/docs/guides/text-to-speech
"""

from __future__ import annotations

from typing import Literal

GenderBucket = Literal["masculine", "feminine", "neutral"]

# id — значение поля `voice` в audio.speech.create
_TTS_VOICES_RU: dict[str, dict[str, str]] = {
    # Мужские (OpenAI TTS; для русского часто стабильны echo / onyx)
    "onyx": {"gender": "masculine", "label_ru": "Onyx — глубокий, чёткая дикция"},
    "echo": {"gender": "masculine", "label_ru": "Echo — спокойный, нейтральный"},
    "ash": {"gender": "masculine", "label_ru": "Ash — ровный, современный"},
    "verse": {"gender": "masculine", "label_ru": "Verse — выразительный"},
    "cedar": {"gender": "masculine", "label_ru": "Cedar — мягкий"},
    # Женские
    "nova": {"gender": "feminine", "label_ru": "Nova — ясная, тёплая"},
    "shimmer": {"gender": "feminine", "label_ru": "Shimmer — мягкая, светлая"},
    "coral": {"gender": "feminine", "label_ru": "Coral — спокойная"},
    "marin": {"gender": "feminine", "label_ru": "Marin — ровная подача"},
    # Нейтральные / универсальные (alloy часто удачно на RU)
    "alloy": {"gender": "neutral", "label_ru": "Alloy — универсальный (нейтральный)"},
    "ballad": {"gender": "neutral", "label_ru": "Ballad — ровный, повествовательный"},
    "fable": {"gender": "neutral", "label_ru": "Fable — выразительный"},
    "sage": {"gender": "neutral", "label_ru": "Sage — спокойный, нейтральный"},
}


def default_voice_for_gender(gender_style: str | None) -> str:
    g = (gender_style or "neutral").strip().lower()
    if g == "masculine":
        return "onyx"
    if g == "feminine":
        return "nova"
    return "alloy"


def voices_for_bucket(bucket: GenderBucket) -> list[dict[str, str]]:
    """Список для UI: id + подпись (только голоса выбранной группы)."""
    return [
        {"id": vid, "label": meta["label_ru"], "gender": meta["gender"]}
        for vid, meta in sorted(_TTS_VOICES_RU.items(), key=lambda x: x[0])
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
    meta = _TTS_VOICES_RU.get(voice_id)
    if not meta:
        return False
    return meta["gender"] == bucket


def normalize_voice_choice(voice_id: str | None, gender_style: str | None) -> str:
    """Если None или невалидно — дефолт по полу."""
    if voice_id and is_valid_voice_for_gender(voice_id.strip(), gender_style):
        return voice_id.strip()
    return default_voice_for_gender(gender_style)
