from __future__ import annotations

import hashlib
import io
import math
import re
import statistics
import struct
import uuid
import wave
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetimeutil import utc_naive_now
from app.models.participant import ConversationParticipant

_NAME_RE = re.compile(
    r"(?:^|\b)(?:меня\s+зовут|мо[её]\s+имя|я)\s+([А-ЯЁA-Z][а-яёa-zA-ZА-ЯЁ-]{1,40})",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"[0-9a-zа-яё]+", re.IGNORECASE)
VOICEPRINT_MATCH_DISTANCE = 0.24
ASSISTANT_SELF_MATCH_DISTANCE = 0.34
VOICEPRINT_BLEND_ALPHA = 0.25
ASSISTANT_SELF_REF = "assistant_self"
MIN_WAKE_RMS = 0.012
MIN_WAKE_VOICED_RATIO = 0.08
_STT_HALLUCINATION_PHRASES = (
    "share this video",
    "share this video with your friends",
    "share this video with your friends on social media",
    "thank you so much for watching",
    "thank you for watching",
    "thanks for watching",
    "thanks for watching this video",
    "please subscribe",
    "subscribe to my channel",
    "like and subscribe",
    "dont forget to like and subscribe",
    "don't forget to like and subscribe",
    "welcome back to my channel",
    "hi guys welcome back to my channel",
    "hope you guys enjoy todays video",
)


@dataclass(frozen=True)
class SpeakerTurn:
    participant: ConversationParticipant
    is_new_voice: bool
    addressing_required: bool
    speaker_context: str


def build_audio_fingerprint(audio_bytes: bytes) -> dict:
    digest = hashlib.sha256(audio_bytes).hexdigest()
    features = extract_acoustic_voice_features(audio_bytes)
    if features:
        return {
            "algorithm": "wav_acoustic_mvp",
            "hash": digest,
            "prefix": digest[:16],
            "features": features,
        }
    return {
        "algorithm": "sha256_audio_fallback",
        "hash": digest,
        "prefix": digest[:16],
    }


def _pcm_samples_from_wav(audio_bytes: bytes, *, max_samples: int = 16000 * 6) -> list[float]:
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            frame_count = min(wav.getnframes(), max_samples)
            raw = wav.readframes(frame_count)
    except (wave.Error, EOFError):
        return []
    if sample_width != 2 or not raw:
        return []
    values = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    if channels > 1:
        values = values[::channels]
    return [max(-1.0, min(1.0, v / 32768.0)) for v in values]


def extract_acoustic_voice_features(audio_bytes: bytes) -> list[float]:
    """Small dependency-free voiceprint MVP for WAV chunks; replace with real speaker embeddings later."""
    samples = _pcm_samples_from_wav(audio_bytes)
    if len(samples) < 800:
        return []
    frame_size = 1024
    rms_values: list[float] = []
    zcr_values: list[float] = []
    abs_means: list[float] = []
    peak_values: list[float] = []
    for start in range(0, len(samples) - frame_size + 1, frame_size):
        frame = samples[start : start + frame_size]
        rms = math.sqrt(sum(x * x for x in frame) / frame_size)
        if rms < 0.005:
            continue
        zero_cross = sum(1 for a, b in zip(frame, frame[1:]) if (a < 0 <= b) or (b < 0 <= a)) / frame_size
        rms_values.append(rms)
        zcr_values.append(zero_cross)
        abs_means.append(sum(abs(x) for x in frame) / frame_size)
        peak_values.append(max(abs(x) for x in frame))
    if not rms_values:
        return []

    def mean(xs: list[float]) -> float:
        return float(sum(xs) / len(xs))

    def stdev(xs: list[float]) -> float:
        return float(statistics.pstdev(xs)) if len(xs) > 1 else 0.0

    voiced_ratio = min(1.0, len(rms_values) / max(1, len(samples) / frame_size))
    return [
        mean(rms_values),
        stdev(rms_values),
        mean(zcr_values),
        stdev(zcr_values),
        mean(abs_means),
        mean(peak_values),
        voiced_ratio,
    ]


def audio_activity_metrics(audio_bytes: bytes) -> dict[str, float] | None:
    samples = _pcm_samples_from_wav(audio_bytes)
    if len(samples) < 800:
        return None
    frame_size = 1024
    rms_values: list[float] = []
    voiced_frames = 0
    total_frames = 0
    for start in range(0, len(samples) - frame_size + 1, frame_size):
        total_frames += 1
        frame = samples[start : start + frame_size]
        rms = math.sqrt(sum(x * x for x in frame) / frame_size)
        rms_values.append(rms)
        if rms >= MIN_WAKE_RMS:
            voiced_frames += 1
    if not rms_values or total_frames == 0:
        return None
    return {
        "rms_mean": float(sum(rms_values) / len(rms_values)),
        "rms_peak": float(max(rms_values)),
        "voiced_ratio": float(voiced_frames / total_frames),
    }


def is_probably_speech(audio_bytes: bytes) -> bool | None:
    metrics = audio_activity_metrics(audio_bytes)
    if metrics is None:
        return None
    return metrics["rms_peak"] >= MIN_WAKE_RMS and metrics["voiced_ratio"] >= MIN_WAKE_VOICED_RATIO


def voiceprint_distance(a: list[float] | None, b: list[float] | None) -> float | None:
    if not a or not b or len(a) != len(b):
        return None
    scales = [0.25, 0.18, 0.25, 0.15, 0.22, 0.6, 1.0]
    total = 0.0
    for av, bv, scale in zip(a, b, scales):
        total += ((av - bv) / scale) ** 2
    return math.sqrt(total / len(a))


def blend_voice_features(old: list[float], new: list[float], *, alpha: float = VOICEPRINT_BLEND_ALPHA) -> list[float]:
    if len(old) != len(new):
        return old
    return [(1 - alpha) * ov + alpha * nv for ov, nv in zip(old, new)]


def extract_self_introduction_name(text: str) -> str | None:
    lower = text.lower()
    if "нейродруг" in lower or "твой друг" in lower:
        return None
    match = _NAME_RE.search(text.strip())
    if not match:
        return None
    name = match.group(1).strip(" .,!?:;")
    return name[:1].upper() + name[1:] if name else None


def _norm_words(text: str) -> set[str]:
    return {w.lower().replace("ё", "е") for w in _WORD_RE.findall(text)}


def _norm_text(text: str) -> str:
    return " ".join(w.lower().replace("ё", "е") for w in _WORD_RE.findall(text))


def is_likely_stt_hallucination(transcript: str) -> bool:
    normalized = _norm_text(transcript)
    if not normalized:
        return False
    if any(_norm_text(phrase) in normalized for phrase in _STT_HALLUCINATION_PHRASES):
        return True
    words = normalized.split()
    video_words = {"video", "watching", "subscribe", "channel", "social", "media"}
    return len(words) <= 12 and len(video_words & set(words)) >= 2


def is_addressed_to_neurofriend(text: str, neurofriend_name: str) -> bool:
    name_words = _norm_words(neurofriend_name)
    if not name_words:
        return False
    text_words = _norm_words(text)
    return bool(name_words & text_words)


def should_respond_to_voice_turn(
    *,
    transcript: str,
    neurofriend_name: str,
    is_new_voice: bool,
    addressing_required: bool,
    wake_check: bool,
) -> bool:
    if not wake_check:
        return True
    if is_new_voice:
        return True
    if not addressing_required:
        return True
    return is_addressed_to_neurofriend(transcript, neurofriend_name)


def transcript_similarity(a: str, b: str) -> float:
    aw = _norm_words(a)
    bw = _norm_words(b)
    if not aw or not bw:
        return 0.0
    return len(aw & bw) / max(1, min(len(aw), len(bw)))


def is_likely_assistant_echo(transcript: str, playback_guard_text: str | None) -> bool:
    if not playback_guard_text or not playback_guard_text.strip():
        return False
    return transcript_similarity(transcript, playback_guard_text) >= 0.62


def is_likely_assistant_echo_from_history(transcript: str, assistant_texts: list[str]) -> bool:
    return any(transcript_similarity(transcript, text) >= 0.58 for text in assistant_texts if text.strip())


async def _participants_count(session: AsyncSession, neurofriend_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.count()).select_from(ConversationParticipant).where(
            ConversationParticipant.neurofriend_id == neurofriend_id,
            ConversationParticipant.person_ref != ASSISTANT_SELF_REF,
        )
    )
    return int(result.scalar_one())


async def _find_by_voiceprint(
    session: AsyncSession,
    neurofriend_id: uuid.UUID,
    fingerprint: dict,
) -> ConversationParticipant | None:
    features = fingerprint.get("features")
    result = await session.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.neurofriend_id == neurofriend_id,
        )
    )
    best: tuple[ConversationParticipant, float] | None = None
    for participant in result.scalars().all():
        if participant.person_ref == ASSISTANT_SELF_REF or participant.participant_kind == ASSISTANT_SELF_REF:
            continue
        vp = participant.voiceprint_json or {}
        if vp.get("hash") == fingerprint.get("hash"):
            return participant
        distance = voiceprint_distance(vp.get("features"), features)
        if distance is not None and (best is None or distance < best[1]):
            best = (participant, distance)
    if best is not None and best[1] <= VOICEPRINT_MATCH_DISTANCE:
        vp = dict(best[0].voiceprint_json or {})
        vp["features"] = blend_voice_features(vp.get("features") or [], features or [])
        vp["last_distance"] = round(best[1], 4)
        best[0].voiceprint_json = vp
        best[0].voiceprint_confidence = min(0.95, max(float(best[0].voiceprint_confidence or 0.0), 1.0 - best[1]))
        return best[0]
    return None


async def _get_assistant_self_participant(
    session: AsyncSession,
    neurofriend_id: uuid.UUID,
) -> ConversationParticipant | None:
    result = await session.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.neurofriend_id == neurofriend_id,
            ConversationParticipant.person_ref == ASSISTANT_SELF_REF,
        )
    )
    return result.scalar_one_or_none()


async def is_assistant_self_voice(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    audio_bytes: bytes,
) -> bool:
    participant = await _get_assistant_self_participant(session, neurofriend_id)
    if participant is None:
        return False
    current = build_audio_fingerprint(audio_bytes).get("features")
    stored = (participant.voiceprint_json or {}).get("features")
    distance = voiceprint_distance(stored, current)
    if distance is None:
        return False
    if distance <= ASSISTANT_SELF_MATCH_DISTANCE:
        vp = dict(participant.voiceprint_json or {})
        vp["last_distance"] = round(distance, 4)
        if current:
            vp["features"] = blend_voice_features(stored or [], current)
        participant.voiceprint_json = vp
        participant.last_seen_at = utc_naive_now()
        participant.turns_seen = (participant.turns_seen or 0) + 1
        await session.flush()
        return True
    return False


async def remember_assistant_self_voice(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    audio_bytes: bytes,
) -> ConversationParticipant | None:
    fingerprint = build_audio_fingerprint(audio_bytes)
    if not fingerprint.get("features"):
        return None
    now = utc_naive_now()
    participant = await _get_assistant_self_participant(session, neurofriend_id)
    if participant is None:
        participant = ConversationParticipant(
            neurofriend_id=neurofriend_id,
            person_ref=ASSISTANT_SELF_REF,
            display_name="assistant self voice",
            participant_kind=ASSISTANT_SELF_REF,
            voiceprint_json=fingerprint,
            voiceprint_confidence=0.8,
            consent_status="system_internal",
            first_seen_at=now,
            last_seen_at=now,
            turns_seen=1,
        )
        session.add(participant)
        await session.flush()
        return participant
    vp = dict(participant.voiceprint_json or {})
    old_features = vp.get("features")
    if old_features:
        vp["features"] = blend_voice_features(old_features, fingerprint["features"])
    else:
        vp["features"] = fingerprint["features"]
    vp["algorithm"] = "wav_acoustic_mvp"
    vp["hash"] = fingerprint["hash"]
    vp["prefix"] = fingerprint["prefix"]
    participant.voiceprint_json = vp
    participant.voiceprint_confidence = min(0.95, max(float(participant.voiceprint_confidence or 0.0), 0.82))
    participant.last_seen_at = now
    participant.turns_seen = (participant.turns_seen or 0) + 1
    await session.flush()
    return participant


async def resolve_voice_speaker(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    audio_bytes: bytes,
    transcript: str,
) -> SpeakerTurn:
    fingerprint = build_audio_fingerprint(audio_bytes)
    now = utc_naive_now()
    participant = await _find_by_voiceprint(session, neurofriend_id, fingerprint)
    is_new = participant is None
    total_before = await _participants_count(session, neurofriend_id)

    introduced_name = extract_self_introduction_name(transcript)
    if participant is None:
        if total_before == 0:
            participant = ConversationParticipant(
                neurofriend_id=neurofriend_id,
                person_ref="user_main",
                display_name=introduced_name,
                participant_kind="primary_user",
                voiceprint_json=fingerprint,
                voiceprint_confidence=0.85,
                first_seen_at=now,
                last_seen_at=now,
                turns_seen=0,
            )
        else:
            participant = ConversationParticipant(
                neurofriend_id=neurofriend_id,
                person_ref=f"guest_{fingerprint['prefix']}",
                display_name=introduced_name,
                participant_kind="unknown_voice" if introduced_name is None else "known_guest",
                voiceprint_json=fingerprint,
                voiceprint_confidence=0.7,
                first_seen_at=now,
                last_seen_at=now,
                turns_seen=0,
            )
        session.add(participant)
        await session.flush()
    else:
        if introduced_name and not participant.display_name:
            participant.display_name = introduced_name
            if participant.participant_kind == "unknown_voice":
                participant.participant_kind = "known_guest"
        participant.last_seen_at = now

    participant.turns_seen = (participant.turns_seen or 0) + 1
    await session.flush()

    total_after = max(total_before + (1 if is_new else 0), 1)
    addressing_required = total_after > 1
    speaker_context = build_speaker_prompt_context(
        participant=participant,
        is_new_voice=is_new,
        addressing_required=addressing_required,
    )
    return SpeakerTurn(
        participant=participant,
        is_new_voice=is_new,
        addressing_required=addressing_required,
        speaker_context=speaker_context,
    )


def build_speaker_prompt_context(
    *,
    participant: ConversationParticipant,
    is_new_voice: bool,
    addressing_required: bool,
) -> str:
    name = participant.display_name or "неизвестный участник"
    if is_new_voice and participant.participant_kind == "unknown_voice":
        return (
            "В разговоре появился новый голос. Культурно представься сам, скажи, что слышишь нового участника, "
            "и попроси его имя. Не делай вид, что это основной пользователь."
        )
    if addressing_required:
        return (
            f"Сейчас говорит участник `{participant.person_ref}` ({name}). "
            "Так как в разговоре больше одного человека, при необходимости обращайся к нему по имени или кратко уточняй адресата."
        )
    return (
        f"Сейчас говорит основной пользователь `{participant.person_ref}`. "
        "Других активных участников не обнаружено, поэтому отдельное обращение по имени не требуется."
    )


async def resolve_text_speaker(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    display_name: str | None = None,
) -> ConversationParticipant:
    now = utc_naive_now()
    result = await session.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.neurofriend_id == neurofriend_id,
            ConversationParticipant.person_ref == "user_main",
        )
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        participant = ConversationParticipant(
            neurofriend_id=neurofriend_id,
            person_ref="user_main",
            display_name=display_name,
            participant_kind="primary_user",
            first_seen_at=now,
            last_seen_at=now,
            turns_seen=0,
        )
        session.add(participant)
    elif display_name and not participant.display_name:
        participant.display_name = display_name
    participant.last_seen_at = now
    participant.turns_seen = (participant.turns_seen or 0) + 1
    await session.flush()
    return participant
