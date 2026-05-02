"""v4.6 — накопление речевого профиля пользователя и блок для LLM."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.datetimeutil import utc_naive_now
from app.models.language_adaptation import SocialLearningProfile, UserDomainProfile, UserLanguageProfile
from app.models.relationship_state import RelationshipModel
from app.services import profession_context_service

# Связки / «паразиты» (добавлять в профиль; LLM — редко, без карикатуры)
_FILLER_FRAGMENTS = [
    "ну смотри",
    "по факту",
    "короче",
    "на самом деле",
    "в целом",
    "сейчас докрут",
    "докрутим",
    "разрулим",
    "по-хорошему",
]

_PROFANITY_HINT = re.compile(
    r"\b(?:бля|хуй|пизд|еб[а-я]{2,}|сука)\b",
    re.I,
)

_TOXIC_IMITATION = re.compile(
    r"\b(?:тупой|идиот|дебил|даун|урод)\b",
    re.I,
)


def extract_lexical_markers(text: str) -> dict[str, Any]:
    t = text or ""
    low = t.lower()
    fillers: dict[str, int] = {}
    for frag in _FILLER_FRAGMENTS:
        if frag in low:
            fillers[frag] = low.count(frag)
    rough = bool(_PROFANITY_HINT.search(t))
    toxic = bool(_TOXIC_IMITATION.search(t))
    length = len(t.strip())
    return {
        "fillers": fillers,
        "message_length": length,
        "profanity_flag": rough,
        "toxic_flag": toxic,
    }


def filter_overimitation(terms: list[str], forbidden_patterns: list[str]) -> list[str]:
    if not forbidden_patterns:
        return terms
    out: list[str] = []
    for term in terms:
        tl = term.lower()
        if any(p.lower() in tl for p in forbidden_patterns if p):
            continue
        out.append(term)
    return out


def compute_adaptation_mode(*, primary_confidence: float) -> str:
    if primary_confidence < 0.28:
        return "almost_neutral"
    if primary_confidence < 0.52:
        return "light_adaptation"
    return "contextual_domain"


def style_blend_weights(*, bond_emotional: float) -> tuple[float, float, float]:
    """SRS §11: 70/20/10; при более тёплой связи — 60/25/15."""
    if bond_emotional >= 0.48:
        return (0.60, 0.25, 0.15)
    return (0.70, 0.20, 0.10)


async def _get_or_create_language_profile(session: AsyncSession, user_id: uuid.UUID) -> UserLanguageProfile:
    r = await session.execute(select(UserLanguageProfile).where(UserLanguageProfile.user_id == user_id))
    row = r.scalar_one_or_none()
    if row:
        return row
    row = UserLanguageProfile(user_id=user_id, last_updated_at=utc_naive_now())
    session.add(row)
    await session.flush()
    return row


async def _get_or_create_social_learning(session: AsyncSession, neurofriend_id: uuid.UUID) -> SocialLearningProfile:
    r = await session.execute(
        select(SocialLearningProfile).where(SocialLearningProfile.neurofriend_id == neurofriend_id)
    )
    row = r.scalar_one_or_none()
    if row:
        return row
    row = SocialLearningProfile(neurofriend_id=neurofriend_id)
    session.add(row)
    await session.flush()
    return row


async def _upsert_domain_row(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    domain: str,
    matched_terms: list[str],
    direct_boost: bool,
) -> None:
    r = await session.execute(
        select(UserDomainProfile).where(
            UserDomainProfile.user_id == user_id,
            UserDomainProfile.domain_name == domain,
        )
    )
    row = r.scalar_one_or_none()
    increment = 0.035 * min(3.0, len(matched_terms)) + (0.22 if direct_boost else 0.0)
    lex = profession_context_service.merge_vocab_counts({}, matched_terms)
    now = utc_naive_now()
    if row:
        row.confidence_score = min(1.0, float(row.confidence_score or 0.0) * 0.96 + increment)
        row.active_vocabulary_json = profession_context_service.merge_vocab_counts(
            dict(row.active_vocabulary_json or {}),
            matched_terms,
        )
        row.topic_frequency_score = min(1.0, float(row.topic_frequency_score or 0.0) + 0.02 * len(matched_terms))
        row.thinking_style = row.thinking_style or profession_context_service.infer_thinking_style(domain)
        row.last_seen_at = now
    else:
        session.add(
            UserDomainProfile(
                user_id=user_id,
                domain_name=domain,
                confidence_score=min(1.0, increment + 0.05),
                active_vocabulary_json=lex,
                topic_frequency_score=min(1.0, 0.04 * len(matched_terms)),
                thinking_style=profession_context_service.infer_thinking_style(domain),
                last_seen_at=now,
            )
        )


async def ingest_user_message(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    user_id: uuid.UUID,
    user_text: str,
) -> None:
    settings = get_settings()
    if not settings.language_adaptation_enabled:
        return

    lang = await _get_or_create_language_profile(session, user_id)
    await _get_or_create_social_learning(session, neurofriend_id)

    markers = extract_lexical_markers(user_text)
    fillers = dict((lang.lexical_markers_json or {}).get("fillers") or {})
    for k, v in markers["fillers"].items():
        fillers[k] = int(fillers.get(k, 0)) + int(v)
    lex_root = dict(lang.lexical_markers_json or {})
    lex_root["fillers"] = fillers

    disc = dict(lang.discourse_style_json or {})
    n_msg = int(disc.get("messages_observed") or 0) + 1
    prev_avg = float(disc.get("avg_message_length") or 0.0)
    mlen = float(markers["message_length"])
    disc["messages_observed"] = n_msg
    disc["avg_message_length"] = (prev_avg * (n_msg - 1) + mlen) / max(1, n_msg)
    if markers["profanity_flag"]:
        disc["saw_profanity"] = True
        lang.profanity_tolerance = max(0.0, float(lang.profanity_tolerance or 0.0) - 0.02)
    if markers["toxic_flag"]:
        disc["saw_toxic_addressing"] = True

    lang.lexical_markers_json = lex_root
    lang.discourse_style_json = disc
    lang.last_updated_at = utc_naive_now()

    if settings.profession_detection_enabled:
        hits_map = profession_context_service.detect_domain_markers(user_text)
        direct_list = profession_context_service.direct_self_report_hits(user_text)
        direct_domains = {d for d, _ in direct_list}

        dlex = dict(lang.domain_lexicon_json or {})
        for _dom, terms in hits_map.items():
            dlex = profession_context_service.merge_vocab_counts(dlex, terms)
        lang.domain_lexicon_json = dlex

        detected = list(lang.detected_professions_json or [])
        if not isinstance(detected, list):
            detected = []
        prof_by_key: dict[str, Any] = {}
        for x in detected:
            if isinstance(x, dict) and x.get("profession_key"):
                prof_by_key[str(x["profession_key"])] = x
        for domain, pkey in direct_list:
            entry = prof_by_key.get(pkey) or {"profession_key": pkey, "domain": domain, "score": 0.0}
            entry["score"] = min(1.0, float(entry.get("score", 0.0)) + 0.35)
            entry["domain"] = domain
            prof_by_key[pkey] = entry
        lang.detected_professions_json = list(prof_by_key.values())

        for domain, matched in hits_map.items():
            await _upsert_domain_row(
                session,
                user_id=user_id,
                domain=domain,
                matched_terms=matched,
                direct_boost=domain in direct_domains,
            )
        for domain, _ in direct_list:
            await _upsert_domain_row(
                session,
                user_id=user_id,
                domain=domain,
                matched_terms=[],
                direct_boost=True,
            )

        rdoms = await session.execute(
            select(UserDomainProfile)
            .where(UserDomainProfile.user_id == user_id)
            .order_by(UserDomainProfile.confidence_score.desc())
            .limit(5)
        )
        top_domains = rdoms.scalars().all()
        max_conf = max((float(d.confidence_score or 0.0) for d in top_domains), default=0.0)
        direct_any = 1.0 if direct_list else 0.0
        vocab_rich = min(1.0, len(hits_map) * 0.15 + sum(len(v) for v in hits_map.values()) * 0.04)
        raw = min(
            1.0,
            0.38 * direct_any + 0.32 * max_conf + 0.30 * min(1.0, vocab_rich * 0.55),
        )
        prev_pc = float(lang.primary_profession_confidence or 0.0)
        lang.primary_profession_confidence = min(1.0, prev_pc * 0.5 + raw * 0.5)

        lang.professional_domains_json = [
            {"domain": d.domain_name, "confidence": float(d.confidence_score or 0.0)} for d in top_domains
        ]

    await session.flush()


async def get_primary_domain_row(session: AsyncSession, user_id: uuid.UUID) -> UserDomainProfile | None:
    r = await session.execute(
        select(UserDomainProfile)
        .where(UserDomainProfile.user_id == user_id)
        .order_by(UserDomainProfile.confidence_score.desc())
        .limit(1)
    )
    return r.scalar_one_or_none()


def build_language_adaptation_prompt_block(
    *,
    lang: UserLanguageProfile | None,
    social: SocialLearningProfile | None,
    primary_domain: UserDomainProfile | None,
    rel: RelationshipModel | None,
) -> str:
    settings = get_settings()
    if not settings.language_adaptation_enabled or not lang:
        return ""

    bond_i = float(rel.emotional_intimacy_score or 0.0) if rel else 0.0
    w_id, w_user, w_dom = style_blend_weights(bond_emotional=bond_i)
    mode = compute_adaptation_mode(primary_confidence=float(lang.primary_profession_confidence or 0.0))
    max_jargon = float(social.max_jargon_density if social else 0.18)
    forbidden = list(social.forbidden_domain_imitation_patterns or []) if social else []

    lines = [
        f"Режим подстройки: {mode} (уверенность в проф. контексте≈{float(lang.primary_profession_confidence or 0):.2f}).",
        f"Баланс стиля (ориентир, не озвучивать числа пользователю): личность нейродруга≈{w_id:.0%}, "
        f"мягкая подстройка под речь пользователя≈{w_user:.0%}, доменный контекст≈{w_dom:.0%}.",
        f"Максимальная плотность жаргона/узкой лексики в ответе: низкая-средняя (порог≈{max_jargon:.2f}). "
        "Не вставляй термин в каждое предложение; не косплей чужую профессию.",
        "Избегай токсичного жаргона, оскорблений и уничижительных клише; не закрепляй явную грубость пользователя как норму.",
    ]

    if mode == "almost_neutral":
        lines.append("Сейчас говори почти в нейтральном своём стиле; только слегка учитывай длину и тон реплик пользователя.")

    fillers = dict((lang.lexical_markers_json or {}).get("fillers") or {})
    top_fillers = sorted(fillers.items(), key=lambda x: -x[1])[:5]
    if top_fillers and settings.contextual_jargon_enabled:
        fstr = ", ".join(f"«{k}»" for k, _ in top_fillers)
        lines.append(f"Замеченные связки пользователя (очень редко, если уместно): {fstr}.")

    if primary_domain and settings.domain_lexicon_enabled:
        dom = primary_domain.domain_name
        user_terms = sorted(
            (primary_domain.active_vocabulary_json or {}).keys(),
            key=lambda x: int((primary_domain.active_vocabulary_json or {}).get(x, 0)),
            reverse=True,
        )[:10]
        lex = profession_context_service.get_domain_lexicon_for_context(dom, top_terms_from_vocab=list(user_terms))
        lex = filter_overimitation(lex, forbidden)[:12]
        if lex:
            lines.append(
                f"Основной профессиональный контекст пользователя (домен `{dom}`): уместно использовать отдельные термины, "
                f"в первую очередь в рабочих темах и метафорах; примеры лексики: {', '.join(lex)}."
            )
            ts = primary_domain.thinking_style or profession_context_service.infer_thinking_style(dom)
            lines.append(f"Стиль мышления в этом домене (ориентир для примеров, не для ярлыков): {ts}.")

    if not settings.contextual_jargon_enabled:
        lines.append("Жаргон пользователя в промпте приглушён (feature off); не уплотняй сленг.")

    return "\n".join(lines)


async def build_language_adaptation_context(
    session: AsyncSession,
    *,
    neurofriend_id: uuid.UUID,
    user_id: uuid.UUID,
    rel: RelationshipModel | None,
) -> str | None:
    settings = get_settings()
    if not settings.language_adaptation_enabled:
        return None
    r_lang = await session.execute(select(UserLanguageProfile).where(UserLanguageProfile.user_id == user_id))
    lang = r_lang.scalar_one_or_none()
    r_soc = await session.execute(
        select(SocialLearningProfile).where(SocialLearningProfile.neurofriend_id == neurofriend_id)
    )
    social = r_soc.scalar_one_or_none()
    primary = await get_primary_domain_row(session, user_id)
    block = build_language_adaptation_prompt_block(lang=lang, social=social, primary_domain=primary, rel=rel)
    return block if block else None


def extend_llm_language_adaptation_prompt(system: str, block: str | None) -> str:
    if not block or not block.strip():
        return system
    return system + "\n\n### Слой адаптации языка и профессии (v4.6)\n" + block.strip()
