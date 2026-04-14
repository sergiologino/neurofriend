import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.models.neurofriend import IdentityCore, NeuroFriendProfile
from app.schemas.perception import TtsRequest, TtsResponse, VoiceTurnResponse
from app.services import affect_lite, chat_thread_service, event_service, speech_openai
from app.services.tts_voice_catalog import normalize_voice_choice
from app.services.conversation_prompt import build_recent_transcript_text
from app.services.llm_orchestrator import generate_reply
from app.services.semantic_memory import index_dialogue_turn, retrieve_snippets
from app.services.openai_client import get_openai_client

router = APIRouter()


def _resolved_tts_voice(nf: NeuroFriendProfile) -> str:
    return normalize_voice_choice(nf.tts_voice, nf.gender_style)


@router.post("/tts", response_model=TtsResponse)
async def perception_tts(
    body: TtsRequest,
    session: AsyncSession = Depends(get_session),
) -> TtsResponse:
    """Озвучка произвольного текста (тот же TTS, что после голосового хода)."""
    if get_openai_client() is None:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")

    rnf = await session.execute(select(NeuroFriendProfile).where(NeuroFriendProfile.id == body.neurofriend_id))
    nf = rnf.scalar_one_or_none()
    if not nf:
        raise HTTPException(status_code=404, detail="NeuroFriend not found")

    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    voice = _resolved_tts_voice(nf)
    try:
        mp3 = await speech_openai.synthesize_speech_mp3(text=text, voice=voice)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    settings = get_settings()
    return TtsResponse(
        audio_base64=speech_openai.bytes_to_base64_mp3(mp3),
        meta={"tts_model": settings.tts_model, "tts_voice": voice},
    )


@router.post("/audio", response_model=VoiceTurnResponse)
async def perception_audio(
    neurofriend_id: uuid.UUID = Form(...),
    session: AsyncSession = Depends(get_session),
    audio: UploadFile = File(...),
) -> VoiceTurnResponse:
    if get_openai_client() is None:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")

    raw = await audio.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty audio")

    rnf = await session.execute(select(NeuroFriendProfile).where(NeuroFriendProfile.id == neurofriend_id))
    nf = rnf.scalar_one_or_none()
    if not nf:
        raise HTTPException(status_code=404, detail="NeuroFriend not found")

    rcore = await session.execute(select(IdentityCore).where(IdentityCore.neurofriend_id == neurofriend_id))
    core = rcore.scalar_one_or_none()

    filename = audio.filename or "audio.webm"
    try:
        transcript = await speech_openai.transcribe_audio(
            audio_bytes=raw,
            filename=filename,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    if not transcript.strip():
        raise HTTPException(status_code=400, detail="Could not transcribe audio")

    await affect_lite.touch_relationship(session, neurofriend_id=nf.id, user_display=None)
    state = await affect_lite.snapshot_after_user_text(session, neurofriend_id=nf.id, user_text=transcript)
    from sqlalchemy import select as sa_select

    from app.models.relationship_state import RelationshipModel

    rrel = await session.execute(
        sa_select(RelationshipModel).where(
            RelationshipModel.neurofriend_id == nf.id,
            RelationshipModel.person_ref == "user_main",
        )
    )
    rel = rrel.scalar_one_or_none()

    inbound = await event_service.log_event(
        session,
        neurofriend_id=nf.id,
        event_type="voice_message_in",
        source="voice",
        normalized={"text": transcript, "mime": audio.content_type},
        raw={"filename": filename},
    )

    transcript_ctx = await build_recent_transcript_text(session, nf.id)
    memory_snippets = await retrieve_snippets(neurofriend_id=nf.id, query_text=transcript)
    reply_text = await generate_reply(
        nf=nf,
        core=core,
        state=state,
        rel=rel,
        user_text=transcript,
        memory_snippets=memory_snippets,
        conversation_transcript=transcript_ctx,
    )

    voice = _resolved_tts_voice(nf)
    try:
        mp3 = await speech_openai.synthesize_speech_mp3(text=reply_text, voice=voice)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    settings = get_settings()
    outbound = await event_service.log_event(
        session,
        neurofriend_id=nf.id,
        event_type="voice_message_out",
        source="voice",
        normalized={
            "text": reply_text,
            "tts_model": settings.tts_model,
            "tts_voice": voice,
        },
    )

    thread, _u, _a = await chat_thread_service.append_transcript_pair(
        session,
        neurofriend_id=nf.id,
        user_text=transcript,
        assistant_text=reply_text,
        source="voice",
        inbound_event_id=inbound.id,
        outbound_event_id=outbound.id,
    )

    await session.commit()

    await index_dialogue_turn(
        neurofriend_id=nf.id,
        user_text=transcript,
        assistant_text=reply_text,
        source="voice",
        user_event_id=inbound.id,
        assistant_event_id=outbound.id,
    )

    return VoiceTurnResponse(
        transcript=transcript,
        reply_text=reply_text,
        audio_base64=speech_openai.bytes_to_base64_mp3(mp3),
        neurofriend_id=nf.id,
        inbound_event_id=inbound.id,
        outbound_event_id=outbound.id,
        thread_id=thread.id,
        meta={"chat_model": settings.chat_model},
    )
