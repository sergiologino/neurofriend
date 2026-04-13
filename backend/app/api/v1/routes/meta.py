from fastapi import APIRouter

from app.schemas.presets import PersonalityPresetRead
from app.services.presets_catalog import list_personality_presets

router = APIRouter()


@router.get("/personality-presets", response_model=list[PersonalityPresetRead])
def get_personality_presets() -> list[PersonalityPresetRead]:
    """Каталог пресетов для онбординга (галерея до фиксации ядра личности)."""
    return list_personality_presets()
