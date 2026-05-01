import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.models.conversation import ConversationThread, Message
from app.models.neurofriend import IdentityCore, NeuroFriendProfile
from app.schemas.perception import TtsRequest, TtsResponse, VoiceTurnResponse
from app.services import affect_lite, chat_thread_service, event_service, speech_openai
from app.services.biography_service import biography_snapshot_text, get_biography_profile
from app.services.conversation_prompt import build_recent_transcript_text
from app.services.llm_orchestrator import generate_reply
from app.services.openai_client import get_openai_client
from app.services.semantic_memory import index_dialogue_turn, retrieve_snippets
from app.services.speaker_identity_service import (
    audio_activity_metrics,
    is_assistant_self_voice,
    is_likely_assistant_echo,
    is_likely_assistant_echo_from_history,
    is_likely_stt_hallucination,
    is_probably_speech,
    remember_assistant_self_voice,
    resolve_voice_speaker,
    should_respond_to_voice_turn,
)
from app.services.tts_voice_catalog import normalize_voice_choice

router = APIRouter()


def _resolved_tts_voice(nf: NeuroFriendProfile) -> str:
    return normalize_voice_choice(nf.tts_voice, nf.gender_style)


async def _recent_assistant_texts(session: AsyncSession, neurofriend_id: uuid.UUID, *, limit: int = 8) -> list[str]:
    result = await session.execute(
        select(Message.text)
        .join(ConversationThread, ConversationThread.id == Message.thread_id)
        .where(
            ConversationThread.neurofriend_id == neurofriend_id,
            Message.role == "assistant",
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return [row[0] for row in result.all() if row[0]]


async def _ignored_voice_response(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    settings_chat_model: str,
    event_source: str,
    transcript: str,
    filename: str,
    mime: str | None,
    normalized_extra: dict,
    raw_extra: dict | None = None,
) -> VoiceTurnResponse:
    inbound = await event_service.log_event(
        session,
        neurofriend_id=neurofriend_id,
        event_type="voice_message_ignored",
        source=event_source,
        normalized={
            "text": transcript,
            "mime": mime,
            "addressed_to_neurofriend": False,
            **normalized_extra,
        },
        raw={"filename": filename, **(raw_extra or {})},
    )
    await session.commit()
    return VoiceTurnResponse(
        transcript=transcript,
        reply_text="",
        audio_base64="",
        neurofriend_id=neurofriend_id,
        inbound_event_id=inbound.id,
        meta={
            "chat_model": settings_chat_model,
            "addressed_to_neurofriend": False,
            **normalized_extra,
        },
    )


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
    wake_check: bool = Form(False),
    playback_guard_text: str | None = Form(None),
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
    settings = get_settings()
    if wake_check:
        speech_flag = is_probably_speech(raw)
        if speech_flag is False:
            return await _ignored_voice_response(
                session,
                neurofriend_id=nf.id,
                settings_chat_model=settings.chat_model,
                event_source="voice_activity_guard",
                transcript="",
                filename=filename,
                mime=audio.content_type,
                normalized_extra={
                    "wake_check": True,
                    "voice_activity_rejected": True,
                },
                raw_extra={"audio_activity": audio_activity_metrics(raw)},
            )
        if await is_assistant_self_voice(session, neurofriend_id=nf.id, audio_bytes=raw):
            return await _ignored_voice_response(
                session,
                neurofriend_id=nf.id,
                settings_chat_model=settings.chat_model,
                event_source="voice_self_profile_guard",
                transcript="",
                filename=filename,
                mime=audio.content_type,
                normalized_extra={
                    "speaker_person_ref": "assistant_self",
                    "participant_kind": "assistant_self",
                    "self_voice_profile_match": True,
                    "wake_check": True,
                },
                raw_extra={"audio_activity": audio_activity_metrics(raw)},
            )
    try:
        transcript = await speech_openai.transcribe_audio(
            audio_bytes=raw,
            filename=filename,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    if not transcript.strip():
        raise HTTPException(status_code=400, detail="Could not transcribe audio")

    if is_likely_stt_hallucination(transcript):
        return await _ignored_voice_response(
            session,
            neurofriend_id=nf.id,
            settings_chat_model=settings.chat_model,
            event_source="voice_stt_hallucination_guard",
            transcript=transcript,
            filename=filename,
            mime=audio.content_type,
            normalized_extra={
                "wake_check": wake_check,
                "stt_hallucination": True,
            },
            raw_extra={"audio_activity": audio_activity_metrics(raw)},
        )
    recent_assistant_texts = await _recent_assistant_texts(session, nf.id)
    if is_likely_assistant_echo(transcript, playback_guard_text) or is_likely_assistant_echo_from_history(
        transcript,
        recent_assistant_texts,
    ):
        await remember_assistant_self_voice(session, neurofriend_id=nf.id, audio_bytes=raw)
        return await _ignored_voice_response(
            neurofriend_id=nf.id,
            session=session,
            settings_chat_model=settings.chat_model,
            event_source="voice_self_guard",
            transcript=transcript,
            filename=filename,
            mime=audio.content_type,
            normalized_extra={
                "speaker_person_ref": "assistant_self",
                "participant_kind": "assistant_self",
                "self_voice_echo": True,
                "wake_check": wake_check,
                "matched_recent_assistant": True,
            },
        )
    speaker_turn = await resolve_voice_speaker(
        session,
        neurofriend_id=nf.id,
        audio_bytes=raw,
        transcript=transcript,
    )
    addressed = should_respond_to_voice_turn(
        transcript=transcript,
        neurofriend_name=nf.name,
        is_new_voice=speaker_turn.is_new_voice,
        addressing_required=speaker_turn.addressing_required,
        wake_check=wake_check,
    )
    if not addressed:
        inbound = await event_service.log_event(
            session,
            neurofriend_id=nf.id,
            event_type="voice_message_ignored",
            source="voice_wake_check",
            normalized={
                "text": transcript,
                "mime": audio.content_type,
                "speaker_person_ref": speaker_turn.participant.person_ref,
                "speaker_display_name": speaker_turn.participant.display_name,
                "participant_kind": speaker_turn.participant.participant_kind,
                "is_new_voice": speaker_turn.is_new_voice,
                "addressing_required": speaker_turn.addressing_required,
                "addressed_to_neurofriend": False,
                "wake_check": True,
            },
            raw={"filename": filename, "voiceprint": speaker_turn.participant.voiceprint_json},
        )
        await session.commit()
        return VoiceTurnResponse(
            transcript=transcript,
            reply_text="",
            audio_base64="",
            neurofriend_id=nf.id,
            inbound_event_id=inbound.id,
            meta={
                "chat_model": settings.chat_model,
                "speaker_person_ref": speaker_turn.participant.person_ref,
                "speaker_display_name": speaker_turn.participant.display_name,
                "participant_kind": speaker_turn.participant.participant_kind,
                "is_new_voice": speaker_turn.is_new_voice,
                "addressing_required": speaker_turn.addressing_required,
                "addressed_to_neurofriend": False,
                "wake_check": True,
            },
        )
    await affect_lite.touch_relationship(session, neurofriend_id=nf.id, user_display=None)
    state = await affect_lite.snapshot_after_user_text(session, neurofriend_id=nf.id, user_text=transcript)
    await affect_lite.update_relationship_boundaries(
        session,
        neurofriend_id=nf.id,
        user_text=transcript,
        friction=state.friction,
    )
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
        normalized={
            "text": transcript,
            "mime": audio.content_type,
            "speaker_person_ref": speaker_turn.participant.person_ref,
            "speaker_display_name": speaker_turn.participant.display_name,
            "participant_kind": speaker_turn.participant.participant_kind,
            "is_new_voice": speaker_turn.is_new_voice,
            "addressing_required": speaker_turn.addressing_required,
            "addressed_to_neurofriend": True,
            "wake_check": wake_check,
        },
        raw={"filename": filename, "voiceprint": speaker_turn.participant.voiceprint_json},
    )

    transcript_ctx = await build_recent_transcript_text(session, nf.id)
    memory_snippets = await retrieve_snippets(neurofriend_id=nf.id, query_text=transcript, session=session)
    biography = await get_biography_profile(session, nf.id)
    reply_text = await generate_reply(
        nf=nf,
        core=core,
        state=state,
        rel=rel,
        user_text=transcript,
        memory_snippets=memory_snippets,
        conversation_transcript=transcript_ctx,
        biography_snapshot=biography_snapshot_text(biography),
        speaker_context=speaker_turn.speaker_context if settings.voice_addressing_enabled else None,
    )

    voice = _resolved_tts_voice(nf)
    try:
        mp3 = await speech_openai.synthesize_speech_mp3(text=reply_text, voice=voice)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

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
        user_metadata={
            "speaker_person_ref": speaker_turn.participant.person_ref,
            "speaker_display_name": speaker_turn.participant.display_name,
            "participant_kind": speaker_turn.participant.participant_kind,
            "is_new_voice": speaker_turn.is_new_voice,
            "addressing_required": speaker_turn.addressing_required,
            "addressed_to_neurofriend": True,
            "wake_check": wake_check,
        },
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
        meta={
            "chat_model": settings.chat_model,
            "speaker_person_ref": speaker_turn.participant.person_ref,
            "speaker_display_name": speaker_turn.participant.display_name,
            "participant_kind": speaker_turn.participant.participant_kind,
            "is_new_voice": speaker_turn.is_new_voice,
            "addressing_required": speaker_turn.addressing_required,
            "addressed_to_neurofriend": True,
            "wake_check": wake_check,
        },
    )
