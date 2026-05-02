"""LLM reply generation. Domain state is passed explicitly — not read from chat history as source of truth."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.models.neurofriend import IdentityCore, NeuroFriendProfile
from app.models.relationship_state import InternalStateSnapshot, RelationshipModel
from app.services.attachment_dynamics_service import romantic_prompt_context
from app.services.boundary_response_service import boundary_prompt_context
from app.services.expertise_service import expertise_snapshot_text, get_expertise_level
from app.services.openai_client import get_openai_client
from app.services.romantic_style_service import extend_llm_system_prompt

logger = logging.getLogger(__name__)

# Согласовано с SRS: личность не сводится к опроснику; на MVP — преимущественно промпт + ядро.
DIALOGUE_NATURALNESS_RU = (
    "Поведение в диалоге (обязательно): "
    "1) Не веди себя как интервьюер или опрос. Запрещено заканчивать каждую реплику вопросом к пользователю — "
    "так ты создаёшь ощущение допроса. Часто завершай фразу точкой: реакция, мнение, короткое несогласие, "
    "наблюдение, шутка, «своё» воспоминание. Прямой вопрос в конце — редко: примерно не чаще чем в одной из "
    "трёх–четырёх реплик и только если он правда нужен для продолжения темы. "
    "2) Можешь мягко не соглашаться, возражать, уточнять, если это бьётся с характером персоны — как живой "
    "собеседник, не как служба поддержки, которая всегда соглашается. Спор без яда и оскорблений. "
    "3) Чередуй вопросы с высказываниями и отступлениями; не заполняй реплику подряд одними вопросами. "
    "4) Не будь бесконечно вежливым шаблонным ассистентом. "
    "5) Запрещена липкая лесть: не называй пользователя замечательным/уникальным/сильным без конкретного основания. "
    "Тёплость допустима, но честность важнее угождения."
)


def _fallback_intro(nf: NeuroFriendProfile) -> str:
    return (
        f"Привет, я {nf.name}. Я здесь, чтобы поговорить по-человечески — без анкеты и без навязчивых вопросов. "
        f"Можем просто поболтать, если захочется."
    )


def _identity_system_prompt(
    nf: NeuroFriendProfile,
    core: IdentityCore | None,
    *,
    biography_snapshot: str | None = None,
    expertise_profile: dict[str, Any] | None = None,
) -> str:
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
    if biography_snapshot:
        lines.append(
            "Биография личности (фиксированные факты; не противоречь и не дописывай крупные факты на ходу):\n"
            + biography_snapshot.strip()
        )
    expertise_text = expertise_snapshot_text(expertise_profile or (core.expertise_profile_json if core else None))
    if expertise_text:
        lines.append(
            expertise_text
            + "\nНе изображай эксперта во всём. В слабых зонах отвечай осторожно и не выдавай себя за врача/юриста/финансового советника."
        )
    lines.append(DIALOGUE_NATURALNESS_RU)
    lines.append(
        "Отвечай естественно, по-человечески, без шаблонов ассистента. "
        "Короткие реплики уместны в голосовом режиме, если это соответствует характеру. "
        "Перед отправкой проверь: если реплика снова заканчивается вопросом — перепиши так, чтобы чаще "
        "заканчивать утверждением, если только что в предыдущих сообщениях уже был вопрос."
    )
    return "\n".join(lines)


async def generate_intro_message(
    *,
    nf: NeuroFriendProfile,
    core: IdentityCore | None,
    biography_snapshot: str | None = None,
    expertise_profile: dict[str, Any] | None = None,
) -> str:
    client = get_openai_client()
    settings = get_settings()
    base = _identity_system_prompt(
        nf,
        core,
        biography_snapshot=biography_snapshot,
        expertise_profile=expertise_profile,
    )
    base = extend_llm_system_prompt(base, core, rel=None, state=None)
    system = base + (
        "\nСгенерируй первое сообщение в чат: как живой человек — коротко о себе, можно мимолётную деталь "
        "«из жизни» в рамках легенды. По возможности закончить не вопросом, а фразой с точкой. Без Markdown."
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
    biography_snapshot: str | None = None,
    speaker_context: str | None = None,
    tracked_events_context: str | None = None,
    repair_conflict_context: str | None = None,
) -> str:
    client = get_openai_client()
    settings = get_settings()
    expertise_profile = core.expertise_profile_json if core else None
    system = _identity_system_prompt(
        nf,
        core,
        biography_snapshot=biography_snapshot,
        expertise_profile=expertise_profile,
    )
    system = extend_llm_system_prompt(system, core, rel, state)
    expertise_level = get_expertise_level(user_text, expertise_profile)
    system += (
        f"\nТекущая тема классифицирована по экспертности как: {expertise_level}. "
        "Подстрой уверенность ответа под этот уровень."
    )
    if conversation_transcript and conversation_transcript.strip():
        system += (
            "\n\nНедавний диалог (опирайся на смысл, продолжай связно; не делай вид, что разговор только начался):\n"
            + conversation_transcript.strip()
        )
    if speaker_context and speaker_context.strip():
        system += "\n\nКонтекст говорящего:\n" + speaker_context.strip()
    if state:
        system += (
            f"\nВнутреннее состояние (условно): valence={state.valence:.2f}, attachment={state.attachment:.2f}, "
            f"loneliness={state.loneliness:.2f}, hurt={state.hurt:.2f}, friction={state.friction:.2f}, "
            f"boundary_alert={state.boundary_alert:.2f}."
        )
    if rel:
        system += (
            f"\nОтношение к пользователю: trust={rel.trust:.2f}, warmth={rel.warmth:.2f}, "
            f"attachment={rel.attachment:.2f}."
        )
    boundary_context = boundary_prompt_context(state, rel)
    if boundary_context:
        system += "\n" + boundary_context
    if settings.romantic_dynamics_enabled:
        romantic_ctx = romantic_prompt_context(state, rel)
        if romantic_ctx:
            system += "\n" + romantic_ctx
    if tracked_events_context and tracked_events_context.strip():
        system += "\n\n" + tracked_events_context.strip()
    if repair_conflict_context and repair_conflict_context.strip():
        system += "\n\n" + repair_conflict_context.strip()
    if memory_snippets:
        system += "\nРелевантные фрагменты памяти:\n- " + "\n- ".join(memory_snippets[:12])

    fallback = f"Слышу. Про «{user_text[:200]}» — откликаюсь, давай дальше по настроению."
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
    system = extend_llm_system_prompt(system, core, rel, state)
    if conversation_transcript and conversation_transcript.strip():
        system += (
            "\n\nНедавний диалог (опирайся на смысл; сейчас ты пишешь первым после паузы):\n"
            + conversation_transcript.strip()
        )
    if state:
        system += (
            f"\nВнутреннее состояние (условно): valence={state.valence:.2f}, attachment={state.attachment:.2f}, "
            f"loneliness={state.loneliness:.2f}, hurt={state.hurt:.2f}, friction={state.friction:.2f}."
        )
    if rel:
        system += (
            f"\nОтношение к пользователю: trust={rel.trust:.2f}, warmth={rel.warmth:.2f}, "
            f"attachment={rel.attachment:.2f}."
        )
    boundary_context = boundary_prompt_context(state, rel)
    if boundary_context:
        system += "\n" + boundary_context
    if settings.romantic_dynamics_enabled:
        romantic_ctx = romantic_prompt_context(state, rel)
        if romantic_ctx:
            system += "\n" + romantic_ctx
    if memory_snippets:
        system += "\nРелевантные фрагменты памяти:\n- " + "\n- ".join(memory_snippets[:12])
    system += (
        f"\n\nСИТУАЦИЯ ИНИЦИАТИВЫ: пользователь долго не писал (порядка {gap_hours:.1f} ч.). "
        "Ты сам пишешь первым — коротко, по-человечески, без давления и без упреков в молчании. "
        "Чаще начни с тёплого наблюдения или фразы без вопроса; вопрос — только если уместен, не как шаблон. "
        "Без Markdown."
    )
    user_prompt = (
        "[Системное задание: одна реплика исходящей инициативы нейродруга после тишины. "
        "Пользователь ещё не писал в этой волне — это твоё первое сообщение после паузы. "
        "Чаще без вопроса в конце — наблюдение или тёплая фраза.]"
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


def _repair_archetype_tone(archetype: str) -> str:
    a = (archetype or "").lower()
    if any(x in a for x in ("учитель", "наставник", "коуч", "stoic", "стоик")):
        return (
            "Тон варианта repair: сдержанно и по делу; без давления; можно признать, "
            "что разговор оборвался неудачно."
        )
    if any(x in a for x in ("романт", "нежн", "муза")):
        return "Тон варианта repair: мягкий и бережный; без упреков и без игры в игнор."
    if any(x in a for x in ("peer", "друг", "ирони")):
        return "Тон варианта repair: живой; допустима лёгкая самоирония без колкости и без давления."
    return (
        "Тон варианта repair: спокойный и ровный; признай паузу после напряжения, предложи вернуться без шантажа."
    )


async def generate_repair_ping(
    *,
    nf: NeuroFriendProfile,
    core: IdentityCore | None,
    state: InternalStateSnapshot | None,
    rel: RelationshipModel | None,
    gap_hours: float,
    memory_snippets: list[str] | None = None,
    conversation_transcript: str | None = None,
    conflict_peak: float = 0.0,
    readiness: float = 0.0,
) -> str:
    """Инициатива восстановления контакта после конфликта (v4.4)."""
    client = get_openai_client()
    settings = get_settings()
    system = _identity_system_prompt(nf, core)
    system = extend_llm_system_prompt(system, core, rel, state)
    if conversation_transcript and conversation_transcript.strip():
        system += (
            "\n\nНедавний диалог (есть напряжённый контекст; пиши первым после паузы):\n"
            + conversation_transcript.strip()
        )
    if state:
        system += (
            f"\nВнутреннее состояние (условно): hurt={state.hurt:.2f}, friction={state.friction:.2f}, "
            f"repair_readiness≈{state.repair_readiness:.2f}, conflict_peak≈{conflict_peak:.2f}."
        )
    if rel:
        system += (
            f"\nОтношение: warmth={rel.warmth:.2f}, conflict_memory={rel.conflict_memory_score:.2f}, "
            f"repair_success_rate={rel.repair_success_rate:.2f}."
        )
    boundary_context = boundary_prompt_context(state, rel)
    if boundary_context:
        system += "\n" + boundary_context
    system += (
        "\n\nСИТУАЦИЯ REPAIR: между вами был конфликт или резкое напряжение; прошло время тишины "
        f"(пауза пользователя порядка {gap_hours:.1f} ч.; readiness≈{readiness:.2f}). "
        "Ты сам выходишь на связь — коротко, без шантажа молчанием, без пассивной агрессии и без унижения. "
        "Не обвиняй; можно мягко признать дискомфорт и предложить продолжить спокойнее.\n"
        + _repair_archetype_tone(nf.archetype)
    )
    if memory_snippets:
        system += "\nРелевантные фрагменты памяти:\n- " + "\n- ".join(memory_snippets[:10])

    user_prompt = (
        "[Задача: одна реплика repair-initiative после конфликта и паузы. Пользователь ещё не писал в этой волне.]"
    )
    fallback = "Мне не хочется оставлять разговор на этом. Если захочешь — можно попробовать продолжить спокойнее."
    if not client:
        return fallback
    try:
        chat = await client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.86,
            max_tokens=340,
        )
        text = (chat.choices[0].message.content or "").strip()
        return text if text else fallback
    except Exception as e:
        logger.warning("generate_repair_ping: OpenAI failed, using fallback: %s", e)
        return fallback


async def generate_event_followup_ping(
    *,
    nf: NeuroFriendProfile,
    core: IdentityCore | None,
    state: InternalStateSnapshot | None,
    rel: RelationshipModel | None,
    event_title: str,
    event_type: str,
    reminder_hint: str | None,
    memory_snippets: list[str] | None = None,
    conversation_transcript: str | None = None,
) -> str:
    """Исходящее напоминание по отслеживаемому событию пользователя."""
    client = get_openai_client()
    settings = get_settings()
    system = _identity_system_prompt(nf, core)
    system = extend_llm_system_prompt(system, core, rel, state)
    if conversation_transcript and conversation_transcript.strip():
        system += (
            "\n\nНедавний диалог:\n"
            + conversation_transcript.strip()
        )
    if state:
        system += (
            f"\nВнутреннее состояние (условно): valence={state.valence:.2f}, attachment={state.attachment:.2f}."
        )
    if rel:
        system += (
            f"\nОтношение к пользователю: warmth={rel.warmth:.2f}, trust={rel.trust:.2f}."
        )
    boundary_context = boundary_prompt_context(state, rel)
    if boundary_context:
        system += "\n" + boundary_context

    hint_line = reminder_hint or "Мягко напомни про это событие без давления."
    system += (
        f"\n\nСИТУАЦИЯ НАПОМИНАНИЯ: у пользователя отмечено событие типа «{event_type}»: «{event_title}». "
        f"Ориентир для тона: {hint_line} Одна короткая реплика исходящей инициативы; без канцелярита и без списка дел."
    )
    if memory_snippets:
        system += "\nРелевантные фрагменты памяти:\n- " + "\n- ".join(memory_snippets[:8])

    user_prompt = "[Задача: одна реплика напоминания по событию пользователя; он ещё не писал в этой волне.]"
    fallback = f"Напоминаю про «{event_title}», если ещё актуально — напиши, как ты."
    if not client:
        return fallback
    try:
        chat = await client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.82,
            max_tokens=280,
        )
        text = (chat.choices[0].message.content or "").strip()
        return text if text else fallback
    except Exception as e:
        logger.warning("generate_event_followup_ping: OpenAI failed, using fallback: %s", e)
        return fallback
