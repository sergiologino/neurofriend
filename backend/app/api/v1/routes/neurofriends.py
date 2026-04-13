import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.conversation import Message
from app.schemas.neurofriends import NeuroFriendCreateRequest, NeuroFriendCreateResponse
from app.services import chat_thread_service, event_service, neurofriend_service
from app.services.semantic_memory import index_intro_only

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


@router.get("/{neurofriend_id}", response_model=dict)
async def get_neurofriend(
    neurofriend_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from sqlalchemy import select

    from app.models.neurofriend import NeuroFriendProfile

    r = await session.execute(select(NeuroFriendProfile).where(NeuroFriendProfile.id == neurofriend_id))
    nf = r.scalar_one_or_none()
    if not nf:
        raise HTTPException(status_code=404, detail="NeuroFriend not found")
    return {
        "id": str(nf.id),
        "user_id": str(nf.user_id),
        "name": nf.name,
        "archetype": nf.archetype,
        "identity_locked": nf.identity_locked,
    }
