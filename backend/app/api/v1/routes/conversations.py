import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.conversation import ConversationThread, Message
from app.models.neurofriend import IdentityCore, NeuroFriendProfile
from app.schemas.neurofriends import MessageCreate, MessageResponse
from app.services import affect_lite, chat_thread_service, event_service
from app.services.biography_service import biography_snapshot_text, get_biography_profile
from app.services.conversation_prompt import build_recent_transcript_text
from app.services.llm_orchestrator import generate_reply
from app.services.semantic_memory import index_dialogue_turn, retrieve_snippets
from app.services.speaker_identity_service import resolve_text_speaker

router = APIRouter()


@router.post("/{neurofriend_id}/messages", response_model=MessageResponse)
async def send_text_message(
    neurofriend_id: uuid.UUID,
    body: MessageCreate,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Fallback text path — same pipeline as voice; chat remains transcript mirror."""

    rnf = await session.execute(select(NeuroFriendProfile).where(NeuroFriendProfile.id == neurofriend_id))
    nf = rnf.scalar_one_or_none()
    if not nf:
        raise HTTPException(status_code=404, detail="NeuroFriend not found")

    rcore = await session.execute(select(IdentityCore).where(IdentityCore.neurofriend_id == neurofriend_id))
    core = rcore.scalar_one_or_none()

    speaker = await resolve_text_speaker(session, neurofriend_id=nf.id)
    await affect_lite.touch_relationship(session, neurofriend_id=nf.id, user_display=None)
    state = await affect_lite.snapshot_after_user_text(session, neurofriend_id=nf.id, user_text=body.text)
    await affect_lite.update_relationship_boundaries(
        session,
        neurofriend_id=nf.id,
        user_text=body.text,
        friction=state.friction,
    )

    from app.models.relationship_state import RelationshipModel

    rrel = await session.execute(
        select(RelationshipModel).where(
            RelationshipModel.neurofriend_id == nf.id,
            RelationshipModel.person_ref == "user_main",
        )
    )
    rel = rrel.scalar_one_or_none()

    inbound = await event_service.log_event(
        session,
        neurofriend_id=nf.id,
        event_type="text_message_in",
        source="text_fallback",
        normalized={"text": body.text, "speaker_person_ref": speaker.person_ref},
    )

    transcript_ctx = await build_recent_transcript_text(session, nf.id)
    memory_snippets = await retrieve_snippets(neurofriend_id=nf.id, query_text=body.text, session=session)
    biography = await get_biography_profile(session, nf.id)
    reply_text = await generate_reply(
        nf=nf,
        core=core,
        state=state,
        rel=rel,
        user_text=body.text,
        memory_snippets=memory_snippets,
        conversation_transcript=transcript_ctx,
        biography_snapshot=biography_snapshot_text(biography),
    )

    from app.core.config import get_settings

    settings = get_settings()
    outbound = await event_service.log_event(
        session,
        neurofriend_id=nf.id,
        event_type="text_message_out",
        source="text_fallback",
        normalized={"text": reply_text, "chat_model": settings.chat_model},
    )

    thread, uid, aid = await chat_thread_service.append_transcript_pair(
        session,
        neurofriend_id=nf.id,
        user_text=body.text,
        assistant_text=reply_text,
        source="text_fallback",
        inbound_event_id=inbound.id,
        outbound_event_id=outbound.id,
        user_metadata={
            "speaker_person_ref": speaker.person_ref,
            "speaker_display_name": speaker.display_name,
            "participant_kind": speaker.participant_kind,
        },
    )
    await session.commit()

    await index_dialogue_turn(
        neurofriend_id=nf.id,
        user_text=body.text,
        assistant_text=reply_text,
        source="text_fallback",
        user_event_id=inbound.id,
        assistant_event_id=outbound.id,
    )

    return MessageResponse(
        reply_text=reply_text,
        user_message_id=uid,
        assistant_message_id=aid,
        thread_id=thread.id,
        meta={"mode": "text_fallback"},
    )


@router.get("/{neurofriend_id}/threads/active/messages")
async def list_active_messages(
    neurofriend_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    stmt = (
        select(ConversationThread)
        .where(
            ConversationThread.neurofriend_id == neurofriend_id,
            ConversationThread.status == "active",
        )
        .limit(1)
    )
    r = await session.execute(stmt)
    thread = r.scalar_one_or_none()
    if not thread:
        return {"thread_id": None, "messages": []}
    q = await session.execute(
        select(Message).where(Message.thread_id == thread.id).order_by(Message.created_at.asc())
    )
    msgs = q.scalars().all()
    return {
        "thread_id": str(thread.id),
        "messages": [
            {
                "id": str(m.id),
                "direction": m.direction,
                "role": m.role,
                "text": m.text,
                "source": m.source,
                "created_at": m.created_at.isoformat(),
                "event_id": str(m.event_id) if m.event_id else None,
                "metadata": m.metadata_json or {},
            }
            for m in msgs
        ],
    }


@router.get("/{neurofriend_id}/threads/archived")
async def list_archived_threads(
    neurofriend_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    r = await session.execute(
        select(ConversationThread)
        .where(
            ConversationThread.neurofriend_id == neurofriend_id,
            ConversationThread.status == "archived",
        )
        .order_by(ConversationThread.archived_at.desc())
    )
    rows = r.scalars().all()
    return {
        "threads": [
            {
                "id": str(t.id),
                "archived_at": t.archived_at.isoformat() if t.archived_at else None,
                "message_count": t.message_count,
            }
            for t in rows
        ]
    }
