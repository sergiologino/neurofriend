import io
import math
import struct
import wave

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.datetimeutil import utc_naive_now
from app.models.neurofriend import NeuroFriendProfile
from app.models.participant import ConversationParticipant
from app.models.user import User
from app.services.speaker_identity_service import (
    _find_by_voiceprint,
    build_audio_fingerprint,
    extract_self_introduction_name,
    is_likely_assistant_echo,
    is_likely_assistant_echo_from_history,
    is_likely_stt_hallucination,
    is_addressed_to_neurofriend,
    is_probably_speech,
    is_assistant_self_voice,
    remember_assistant_self_voice,
    resolve_voice_speaker,
    should_respond_to_voice_turn,
    voiceprint_distance,
)


@pytest.mark.asyncio
async def test_voice_speaker_first_known_new_guest_and_name() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with session_factory() as session:
            user = User(display_name="main")
            session.add(user)
            await session.flush()
            nf = NeuroFriendProfile(user_id=user.id, name="Друг", archetype="companion", identity_locked=True)
            session.add(nf)
            await session.flush()

            first = await resolve_voice_speaker(
                session,
                neurofriend_id=nf.id,
                audio_bytes=b"main voice",
                transcript="Привет",
            )
            assert first.participant.person_ref == "user_main"
            assert first.participant.participant_kind == "primary_user"
            assert first.addressing_required is False

            known = await resolve_voice_speaker(
                session,
                neurofriend_id=nf.id,
                audio_bytes=b"main voice",
                transcript="Это снова я",
            )
            assert known.participant.id == first.participant.id
            assert known.is_new_voice is False

            guest = await resolve_voice_speaker(
                session,
                neurofriend_id=nf.id,
                audio_bytes=b"guest voice",
                transcript="Меня зовут Антон",
            )
            assert guest.participant.person_ref.startswith("guest_")
            assert guest.participant.display_name == "Антон"
            assert guest.participant.participant_kind == "known_guest"
            assert guest.addressing_required is True
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.mark.asyncio
async def test_assistant_self_voice_profile_is_not_counted_as_human() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with session_factory() as session:
            user = User(display_name="main")
            session.add(user)
            await session.flush()
            nf = NeuroFriendProfile(user_id=user.id, name="Друг", archetype="companion", identity_locked=True)
            session.add(nf)
            await session.flush()

            assistant_audio = _tone_wav(440)
            await remember_assistant_self_voice(session, neurofriend_id=nf.id, audio_bytes=assistant_audio)
            assert await is_assistant_self_voice(session, neurofriend_id=nf.id, audio_bytes=_tone_wav(442))

            first_human = await resolve_voice_speaker(
                session,
                neurofriend_id=nf.id,
                audio_bytes=_tone_wav(220),
                transcript="Привет",
            )
            assert first_human.participant.person_ref == "user_main"
            assert first_human.addressing_required is False
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.mark.asyncio
async def test_find_by_voiceprint_declined_skips_feature_blend() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    feats = [0.12, 0.04, 0.18, 0.02, 0.11, 0.35, 0.55]
    try:
        async with session_factory() as session:
            user = User(display_name="main")
            session.add(user)
            await session.flush()
            nf = NeuroFriendProfile(user_id=user.id, name="Друг", archetype="companion", identity_locked=True)
            session.add(nf)
            await session.flush()
            now = utc_naive_now()
            p = ConversationParticipant(
                neurofriend_id=nf.id,
                person_ref="user_main",
                participant_kind="primary_user",
                voiceprint_json={"algorithm": "wav_acoustic_mvp", "features": list(feats)},
                voiceprint_confidence=0.8,
                consent_status="declined",
                first_seen_at=now,
                last_seen_at=now,
                turns_seen=1,
            )
            session.add(p)
            await session.flush()

            fingerprint = {
                "algorithm": "wav_acoustic_mvp",
                "features": list(feats),
                "hash": "other_hash_not_equal",
                "prefix": "other_hash_not",
            }
            matched = await _find_by_voiceprint(session, nf.id, fingerprint)
            assert matched is not None
            assert matched.voiceprint_json is not None
            assert matched.voiceprint_json["features"] == feats
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


def test_audio_fingerprint_and_name_extraction_are_stable() -> None:
    assert build_audio_fingerprint(b"abc") == build_audio_fingerprint(b"abc")
    assert build_audio_fingerprint(b"abc") != build_audio_fingerprint(b"abcd")
    assert extract_self_introduction_name("меня зовут Марина") == "Марина"
    assert extract_self_introduction_name("Привет, я Вася, твой нейродруг") is None


def test_wake_addressing_policy() -> None:
    assert is_addressed_to_neurofriend("Марина, ты слышишь?", "Марина")
    assert should_respond_to_voice_turn(
        transcript="просто говорю рядом",
        neurofriend_name="Марина",
        is_new_voice=False,
        addressing_required=False,
        wake_check=True,
    )
    assert should_respond_to_voice_turn(
        transcript="просто говорю рядом",
        neurofriend_name="Марина",
        is_new_voice=True,
        addressing_required=True,
        wake_check=True,
    )
    assert not should_respond_to_voice_turn(
        transcript="просто говорю рядом",
        neurofriend_name="Марина",
        is_new_voice=False,
        addressing_required=True,
        wake_check=True,
    )
    assert should_respond_to_voice_turn(
        transcript="Марина, ответь",
        neurofriend_name="Марина",
        is_new_voice=False,
        addressing_required=True,
        wake_check=True,
    )


def _tone_wav(freq: float, *, amplitude: float = 0.35, seconds: float = 1.0, sample_rate: int = 16_000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = []
        for i in range(int(sample_rate * seconds)):
            value = int(amplitude * 32767 * math.sin(2 * math.pi * freq * i / sample_rate))
            frames.append(struct.pack("<h", value))
        wav.writeframes(b"".join(frames))
    return buf.getvalue()


def test_acoustic_voiceprint_groups_similar_wav_chunks() -> None:
    a = build_audio_fingerprint(_tone_wav(220))["features"]
    b = build_audio_fingerprint(_tone_wav(225))["features"]
    c = build_audio_fingerprint(_tone_wav(640))["features"]

    near = voiceprint_distance(a, b)
    far = voiceprint_distance(a, c)

    assert near is not None and far is not None
    assert near < far


def test_voice_activity_rejects_silent_wav() -> None:
    assert is_probably_speech(_tone_wav(220, amplitude=0.0)) is False
    assert is_probably_speech(_tone_wav(220, amplitude=0.35)) is True


def test_stt_hallucination_detection_filters_common_youtube_phrases() -> None:
    assert is_likely_stt_hallucination("Thank you so much for watching!")
    assert is_likely_stt_hallucination("Please subscribe to my channel. Thank you.")
    assert is_likely_stt_hallucination("Share this video with your friends on social media.")
    assert is_likely_stt_hallucination("Hi guys! Welcome back to my channel!")
    assert not is_likely_stt_hallucination("Марина, я хочу поговорить про видео")


def test_assistant_echo_detection_uses_transcript_overlap() -> None:
    assert is_likely_assistant_echo(
        "Это тестовый ответ про голос",
        "Тестовый ответ про голос и продолжение",
    )
    assert not is_likely_assistant_echo(
        "Марина, подожди, я хочу уточнить",
        "Тестовый ответ про голос и продолжение",
    )
    assert is_likely_assistant_echo_from_history(
        "Привет, я Вася, твой нейродруг",
        ["Привет! Я Вася, твой нейродруг. Выросла в маленьком приморском городе."],
    )
