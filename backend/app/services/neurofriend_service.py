from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationThread
from app.models.neurofriend import IdentityCore, NeuroFriendProfile
from app.models.relationship_state import InternalStateSnapshot, RelationshipModel
from app.models.user import User
from app.schemas.neurofriends import NeuroFriendCreateRequest, TemperamentIn
from app.services import llm_orchestrator
from app.services.presets_catalog import get_preset_by_id


async def create_neurofriend(session: AsyncSession, body: NeuroFriendCreateRequest) -> tuple[User, NeuroFriendProfile, str]:
    if not body.identity_lock_confirmed:
        raise ValueError("identity_lock_confirmed must be true")

    base_t = TemperamentIn()
    speech_style = body.speech_style
    social_style = body.social_style
    relationship_style = body.relationship_style
    character_voice: str | None = None
    gender_style = body.gender_style
    life_legend: str | None = None

    preset = get_preset_by_id(body.preset_id) if body.preset_id else None
    if preset:
        if preset.temperament:
            base_t = TemperamentIn(**{**base_t.model_dump(), **preset.temperament.model_dump()})
        speech_style = speech_style or preset.speech_style
        social_style = social_style or preset.social_style
        relationship_style = relationship_style or preset.relationship_style
        character_voice = preset.character_prompt
        gender_style = gender_style or preset.gender_style
        life_legend = preset.life_legend

    if body.temperament:
        base_t = TemperamentIn(**{**base_t.model_dump(), **body.temperament.model_dump()})

    temperament_final = base_t.model_dump()

    user = User(
        email=None,
        display_name=body.user_display_name or "user",
    )
    session.add(user)
    await session.flush()

    nf = NeuroFriendProfile(
        user_id=user.id,
        name=body.name.strip(),
        gender_style=gender_style,
        age_style=body.age_style,
        archetype=body.archetype.strip(),
        identity_locked=True,
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
    }
    if life_legend:
        core_traits["life_legend"] = life_legend

    core = IdentityCore(
        neurofriend_id=nf.id,
        core_traits_json=core_traits,
        speech_rules_json={"speech_style": speech_style or "alive_informal"},
        values_json={},
    )
    session.add(core)

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

    intro = await llm_orchestrator.generate_intro_message(nf=nf, core=core)
    return user, nf, intro
