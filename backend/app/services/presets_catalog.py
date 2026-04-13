"""Канонический каталог пресетов личности (SRS: галерея до создания нейродруга)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas.presets import PersonalityPresetRead

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "personality_presets.json"


@lru_cache
def list_personality_presets() -> list[PersonalityPresetRead]:
    raw = _DATA_FILE.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("personality_presets.json must be a JSON array")
    return [PersonalityPresetRead.model_validate(item) for item in data]


def get_preset_by_id(preset_id: str) -> PersonalityPresetRead | None:
    for p in list_personality_presets():
        if p.id == preset_id:
            return p
    return None
