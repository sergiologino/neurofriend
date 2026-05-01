from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationThread
from app.models.neurofriend import IdentityCore, NeuroFriendProfile
from app.models.relationship_state import InternalStateSnapshot, RelationshipModel
from app.models.user import User
from app.schemas.neurofriends import NeuroFriendCreateRequest, PersonalizationIn, TemperamentIn
from app.schemas.presets import PersonalityPresetRead
from app.services import llm_orchestrator
from app.services.biography_service import biography_snapshot_text, create_initial_biography_from_preset
from app.services.expertise_service import build_initial_expertise_profile
from app.core.config import get_settings
from app.services.presets_catalog import get_preset_by_id
from app.services.tts_voice_catalog import normalize_voice_choice


_PERSONALIZATION_FIELDS = {
    "softness": "softness_delta",
    "directness": "directness_delta",
    "initiative": "initiative_delta",
    "emotionality": "emotionality_delta",
    "humor": "humor_delta",
}


def _allowed_personalization_range(base_value: float) -> tuple[float, float]:
    """Current canonical preset JSON has no explicit ranges yet; keep deltas conservative."""
    return max(0.0, base_value - 0.15), min(1.0, base_value + 0.15)


def _apply_personalization(
    base: TemperamentIn,
    personalization: PersonalizationIn | None,
    preset: PersonalityPresetRead | None,
) -> TemperamentIn:
    if not personalization:
        return base
    if not preset:
        raise ValueError("personalization requires selected_preset_id")

    data = base.model_dump()
    p_data = personalization.model_dump()
    for field_name, delta_name in _PERSONALIZATION_FIELDS.items():
        base_value = float(data[field_name])
        candidate = max(0.0, min(1.0, base_value + float(p_data[delta_name])))
        lo, hi = _allowed_personalization_range(base_value)
        if not lo <= candidate <= hi:
            raise ValueError(
                f"personalization.{delta_name} moves {field_name} outside allowed preset range "
                f"({lo:.2f}..{hi:.2f})"
            )
        data[field_name] = candidate
    return TemperamentIn(**data)


async def create_neurofriend(session: AsyncSession, body: NeuroFriendCreateRequest) -> tuple[User, NeuroFriendProfile, str]:
    if not body.identity_lock_confirmed:
        raise ValueError("identity_lock_confirmed must be true")
    settings = get_settings()

    base_t = TemperamentIn()
    speech_style = body.speech_style
    social_style = body.social_style
    relationship_style = body.relationship_style
    character_voice: str | None = None
    gender_style = body.gender_style
    life_legend: str | None = None

    selected_preset_id = body.selected_preset_id or body.preset_id
    preset = get_preset_by_id(selected_preset_id) if selected_preset_id else None
    if selected_preset_id and not preset:
        raise ValueError(f"Unknown selected_preset_id: {selected_preset_id}")
    if preset:
        if preset.temperament:
            base_t = TemperamentIn(**{**base_t.model_dump(), **preset.temperament.model_dump()})
        speech_style = speech_style or preset.speech_style
        social_style = social_style or preset.social_style
        relationship_style = relationship_style or preset.relationship_style
        character_voice = preset.character_prompt
        gender_style = gender_style or preset.gender_style
        life_legend = preset.life_legend

    tts_resolved = normalize_voice_choice(body.tts_voice, gender_style)

    if body.temperament:
        base_t = TemperamentIn(**{**base_t.model_dump(), **body.temperament.model_dump()})
    base_t = _apply_personalization(base_t, body.personalization, preset)

    temperament_final = base_t.model_dump()

    user = User(
        email=None,
        display_name=body.user_display_name or "user",
        timezone=body.user_timezone or "UTC",
    )
    session.add(user)
    await session.flush()

    nf = NeuroFriendProfile(
        user_id=user.id,
        name=body.name.strip(),
        gender_style=gender_style,
        age_style=body.age_style,
        archetype=body.archetype.strip(),
        tts_voice=tts_resolved,
        identity_locked=True,
        biography_enabled=settings.biography_profile_enabled,
        expertise_profile_version=1 if settings.expertise_profile_enabled else 0,
        persona_summary=None,
    )
    session.add(nf)
    await session.flush()

    core_traits: dict = {
        "temperament": temperament_final,
        "social_style": social_style,
        "speech_style": speech_style,
        "relationship_style": relationship_style,
        "character_voice": character_voice,
        "selected_preset_id": selected_preset_id,
        "personalization": body.personalization.model_dump() if body.personalization else None,
    }
    if life_legend:
        core_traits["life_legend"] = life_legend

    core = IdentityCore(
        neurofriend_id=nf.id,
        core_traits_json=core_traits,
        speech_rules_json={"speech_style": speech_style or "alive_informal"},
        values_json={},
        expertise_profile_json=build_initial_expertise_profile(preset, nf.archetype)
        if settings.expertise_profile_enabled
        else {},
    )
    session.add(core)
    await session.flush()

    biography = None
    if settings.biography_profile_enabled:
        biography = await create_initial_biography_from_preset(session, nf=nf, core=core, preset=preset)

    session.add(
        InternalStateSnapshot(
            neurofriend_id=nf.id,
        )
    )
    session.add(
        RelationshipModel(
            neurofriend_id=nf.id,
            person_ref="user_main",
            display_name=user.display_name,
        )
    )
    session.add(ConversationThread(neurofriend_id=nf.id, status="active", message_count=0))
    await session.flush()

    intro = await llm_orchestrator.generate_intro_message(
        nf=nf,
        core=core,
        biography_snapshot=biography_snapshot_text(biography),
        expertise_profile=core.expertise_profile_json,
    )
    return user, nf, intro
