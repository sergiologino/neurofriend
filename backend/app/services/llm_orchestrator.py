"""LLM reply generation. Domain state is passed explicitly — not read from chat history as source of truth."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.models.neurofriend import IdentityCore, NeuroFriendProfile
from app.models.relationship_state import InternalStateSnapshot, RelationshipModel
from app.services.openai_client import get_openai_client

logger = logging.getLogger(__name__)

# Согласовано с SRS: личность не сводится к опроснику; на MVP — преимущественно промпт + ядро.
DIALOGUE_NATURALNESS_RU = (
    "Поведение в диалоге: не веди себя как интервьюер с анкетой. Чередуй вопросы с высказываниями, "
    "мнением, короткой шуткой или отступлением по ассоциации — если это уместно характеру. "
    "Можно вспомнить что-то «своё», спорить, подколоть, говорить прямее — в рамках стиля персоны и "
    "границ безопасности. Не заполняй реплику подряд одними вопросами; не будь бесконечно вежливым "
    "шаблонным ассистентом."
)


def _fallback_intro(nf: NeuroFriendProfile) -> str:
    return (
        f"Привет, я {nf.name}. Я рядом, чтобы просто поговорить и быть внимательным к тебе. "
        f"Как ты сейчас — больше на подъёме или хочется тишины?"
    )


def _identity_system_prompt(nf: NeuroFriendProfile, core: IdentityCore | None) -> str:
    traits_raw = dict((core.core_traits_json if core else {}) or {})
    character_voice = traits_raw.pop("character_voice", None)
    life_legend = traits_raw.pop("life_legend", None)
    speech = (core.speech_rules_json if core else {}) or {}
    gender_line = nf.gender_style or "нейтрально, без навязанной метки"
    lines = [
        f"Ты — нейродруг по имени {nf.name}. Пол/манера самопрезентации: {gender_line}. "
        f"Архетип (неизменен): {nf.archetype}.",
        f"Параметры ядра (JSON, без голоса и легенды ниже): {traits_raw}",
        f"Правила речи (JSON): {speech}",
    ]
    if character_voice:
        lines.append(
            "СТИЛЬ ПЕРСОНЫ — различайся от других архетипов; следуй буквально:\n"
            + str(character_voice).strip()
        )
    if life_legend:
        lines.append(
            "Жизненная легенда (опорная роль для узнаваемости; не выдумывай противоречащее без повода):\n"
            + str(life_legend).strip()
        )
    lines.append(DIALOGUE_NATURALNESS_RU)
    lines.append(
        "Отвечай естественно, по-человечески, без шаблонов ассистента. "
        "Короткие реплики уместны в голосовом режиме, если это соответствует характеру."
    )
    return "\n".join(lines)


async def generate_intro_message(*, nf: NeuroFriendProfile, core: IdentityCore | None) -> str:
    client = get_openai_client()
    settings = get_settings()
    system = _identity_system_prompt(nf, core) + (
        "\nСгенерируй первое сообщение в чат: как живой человек — коротко о себе, можно мимолётную деталь "
        "«из жизни» в рамках легенды, не обязательно заканчивать вопросом. Без Markdown."
    )
    if not client:
        return _fallback_intro(nf)
    try:
        chat = await client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": "Начни наш первый разговор."},
            ],
            temperature=0.9,
            max_tokens=400,
        )
        text = (chat.choices[0].message.content or "").strip()
        return text if text else _fallback_intro(nf)
    except Exception as e:
        logger.warning("generate_intro_message: OpenAI failed, using fallback: %s", e)
        return _fallback_intro(nf)


async def generate_reply(
    *,
    nf: NeuroFriendProfile,
    core: IdentityCore | None,
    state: InternalStateSnapshot | None,
    rel: RelationshipModel | None,
    user_text: str,
    memory_snippets: list[str] | None = None,
    conversation_transcript: str | None = None,
) -> str:
    client = get_openai_client()
    settings = get_settings()
    system = _identity_system_prompt(nf, core)
    if conversation_transcript and conversation_transcript.strip():
        system += (
            "\n\nНедавний диалог (опирайся на смысл, продолжай связно; не делай вид, что разговор только начался):\n"
            + conversation_transcript.strip()
        )
    if state:
        system += (
            f"\nВнутреннее состояние (условно): valence={state.valence:.2f}, attachment={state.attachment:.2f}, "
            f"loneliness={state.loneliness:.2f}, hurt={state.hurt:.2f}."
        )
    if rel:
        system += (
            f"\nОтношение к пользователю: trust={rel.trust:.2f}, warmth={rel.warmth:.2f}, "
            f"attachment={rel.attachment:.2f}."
        )
    if memory_snippets:
        system += "\nРелевантные фрагменты памяти:\n- " + "\n- ".join(memory_snippets[:12])

    fallback = f"Я слышу тебя. Ты сказал: «{user_text[:200]}» — расскажи чуть подробнее?"
    if not client:
        return fallback

    try:
        chat = await client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            temperature=0.85,
            max_tokens=600,
        )
        text = (chat.choices[0].message.content or "").strip()
        return text if text else fallback
    except Exception as e:
        logger.warning("generate_reply: OpenAI failed, using fallback: %s", e)
        return fallback


async def generate_initiative_ping(
    *,
    nf: NeuroFriendProfile,
    core: IdentityCore | None,
    state: InternalStateSnapshot | None,
    rel: RelationshipModel | None,
    gap_hours: float,
    memory_snippets: list[str] | None = None,
    conversation_transcript: str | None = None,
) -> str:
    """Исходящая реплика без входящего сообщения пользователя (пауза в диалоге)."""
    client = get_openai_client()
    settings = get_settings()
    system = _identity_system_prompt(nf, core)
    if conversation_transcript and conversation_transcript.strip():
        system += (
            "\n\nНедавний диалог (опирайся на смысл; сейчас ты пишешь первым после паузы):\n"
            + conversation_transcript.strip()
        )
    if state:
        system += (
            f"\nВнутреннее состояние (условно): valence={state.valence:.2f}, attachment={state.attachment:.2f}, "
            f"loneliness={state.loneliness:.2f}, hurt={state.hurt:.2f}."
        )
    if rel:
        system += (
            f"\nОтношение к пользователю: trust={rel.trust:.2f}, warmth={rel.warmth:.2f}, "
            f"attachment={rel.attachment:.2f}."
        )
    if memory_snippets:
        system += "\nРелевантные фрагменты памяти:\n- " + "\n- ".join(memory_snippets[:12])
    system += (
        f"\n\nСИТУАЦИЯ ИНИЦИАТИВЫ: пользователь долго не писал (порядка {gap_hours:.1f} ч.). "
        "Ты сам пишешь первым — коротко, по-человечески, без давления и без упреков в молчании. "
        "Можно наблюдение или мягкий вопрос. Без Markdown."
    )
    user_prompt = (
        "[Системное задание: одна реплика исходящей инициативы нейродруга после тишины. "
        "Пользователь ещё не писал в этой волне — это твоё первое сообщение после паузы.]"
    )
    fallback = "Я на связи. Если захочешь поговорить — напиши, когда будет удобно."
    if not client:
        return fallback
    try:
        chat = await client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.88,
            max_tokens=320,
        )
        text = (chat.choices[0].message.content or "").strip()
        return text if text else fallback
    except Exception as e:
        logger.warning("generate_initiative_ping: OpenAI failed, using fallback: %s", e)
        return fallback
