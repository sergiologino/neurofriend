import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.conversation import Message
from app.models.neurofriend import NeuroFriendProfile
from app.schemas.neurofriends import (
    CharacterPreviewRead,
    NeuroFriendCreateRequest,
    NeuroFriendCreateResponse,
    NeuroFriendPatchRequest,
)
from app.services import chat_thread_service, event_service, neurofriend_service
from app.services.biography_service import biography_preview_for_user, get_biography_profile
from app.services.expertise_service import expertise_preview_for_user
from app.services.semantic_memory import index_intro_only

from sqlalchemy import select
from sqlalchemy.orm import selectinload

router = APIRouter()


@router.post("", response_model=NeuroFriendCreateResponse)
async def create_neurofriend(
    body: NeuroFriendCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> NeuroFriendCreateResponse:
    try:
        user, nf, intro = await neurofriend_service.create_neurofriend(session, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    intro_ev = await event_service.log_event(
        session,
        neurofriend_id=nf.id,
        event_type="text_message_out",
        source="bootstrap",
        normalized={"text": intro, "kind": "intro"},
    )
    thread = await chat_thread_service.get_or_create_active_thread(session, nf.id)
    session.add(
        Message(
            thread_id=thread.id,
            direction="out",
            role="assistant",
            text=intro,
            message_kind="intro",
            source="bootstrap",
            event_id=intro_ev.id,
            metadata_json={"kind": "intro"},
        )
    )
    thread.message_count += 1
    await session.commit()

    await index_intro_only(
        neurofriend_id=nf.id,
        assistant_text=intro,
        source="bootstrap",
        event_id=intro_ev.id,
    )

    return NeuroFriendCreateResponse(
        id=nf.id,
        user_id=user.id,
        identity_locked=True,
        first_intro_message=intro,
    )


@router.get("/{neurofriend_id}/character-preview", response_model=CharacterPreviewRead)
async def get_character_preview(
    neurofriend_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> CharacterPreviewRead:
    r = await session.execute(
        select(NeuroFriendProfile)
        .where(NeuroFriendProfile.id == neurofriend_id)
        .options(selectinload(NeuroFriendProfile.identity_core))
    )
    nf = r.scalar_one_or_none()
    if not nf:
        raise HTTPException(status_code=404, detail="NeuroFriend not found")

    bio = await get_biography_profile(session, neurofriend_id)
    bio_text = biography_preview_for_user(bio)
    core = nf.identity_core
    exp_profile = core.expertise_profile_json if core else {}
    exp_text = expertise_preview_for_user(exp_profile or {})
    return CharacterPreviewRead(biography_text=bio_text, expertise_text=exp_text)


@router.get("/{neurofriend_id}", response_model=dict)
async def get_neurofriend(
    neurofriend_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    r = await session.execute(select(NeuroFriendProfile).where(NeuroFriendProfile.id == neurofriend_id))
    nf = r.scalar_one_or_none()
    if not nf:
        raise HTTPException(status_code=404, detail="NeuroFriend not found")
    return {
        "id": str(nf.id),
        "user_id": str(nf.user_id),
        "name": nf.name,
        "archetype": nf.archetype,
        "gender_style": nf.gender_style,
        "tts_voice": nf.tts_voice,
        "identity_locked": nf.identity_locked,
    }


@router.patch("/{neurofriend_id}", response_model=dict)
async def patch_neurofriend(
    neurofriend_id: uuid.UUID,
    body: NeuroFriendPatchRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.services.tts_voice_catalog import is_valid_voice_for_gender

    r = await session.execute(select(NeuroFriendProfile).where(NeuroFriendProfile.id == neurofriend_id))
    nf = r.scalar_one_or_none()
    if not nf:
        raise HTTPException(status_code=404, detail="NeuroFriend not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "tts_voice" in updates:
        vid = updates["tts_voice"]
        if vid is None or (isinstance(vid, str) and not vid.strip()):
            raise HTTPException(status_code=400, detail="tts_voice cannot be empty")
        vid = vid.strip()
        if not is_valid_voice_for_gender(vid, nf.gender_style):
            raise HTTPException(
                status_code=400,
                detail=f"Voice '{vid}' does not match neurofriend gender_style",
            )
        nf.tts_voice = vid

    await session.commit()
    await session.refresh(nf)
    return {
        "id": str(nf.id),
        "gender_style": nf.gender_style,
        "tts_voice": nf.tts_voice,
    }
