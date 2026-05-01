from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.neurofriend import BiographyProfile, IdentityCore, NeuroFriendProfile
from app.schemas.presets import PersonalityPresetRead

_CRITICAL_DETAIL_RE = re.compile(
    r"\b(женат|замужем|реб[её]нок|дети|сын|дочь|развод|супруг|супруга|умер|смерть)\b",
    re.IGNORECASE,
)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def _legend_anchor(preset: PersonalityPresetRead | None) -> str:
    if not preset or not preset.life_legend:
        return ""
    return preset.life_legend.strip()


def build_initial_biography_payload(
    *,
    nf: NeuroFriendProfile,
    core: IdentityCore,
    preset: PersonalityPresetRead | None,
) -> dict[str, Any]:
    legend = _legend_anchor(preset)
    parts = _sentences(legend)
    temperament = ((core.core_traits_json or {}).get("temperament") or {}) if core else {}
    speech_style = (core.speech_rules_json or {}).get("speech_style") if core else None

    return {
        "birth_context_json": {
            "source": "preset_life_legend",
            "summary": parts[0] if parts else f"Прошлое {nf.name} задано пока общим архетипом {nf.archetype}.",
            "archetype": nf.archetype,
        },
        "family_background_json": {
            "atmosphere": "consistent_with_preset",
            "notes": parts[1] if len(parts) > 1 else "Фон семьи не детализирован; нельзя импровизировать ключевые факты.",
        },
        "education_path_json": {
            "style": "self_formed",
            "notes": "Путь обучения задан только общим стилем личности; детали добавлять осторожно.",
        },
        "work_path_json": {
            "notes": parts[0] if parts else "Рабочий путь не детализирован в MVP biography.",
        },
        "important_events_json": [
            {"kind": "legend_anchor", "text": sentence}
            for sentence in parts[:2]
        ],
        "habits_json": [
            {"kind": "speech", "text": str(speech_style)}
        ]
        if speech_style
        else [],
        "preferences_json": {
            "temperament": temperament,
            "likes": [],
            "dislikes": [],
        },
        "core_dates_json": [],
        "relationship_history_json": {
            "status": "not_defined",
            "rule": "Do not invent marriage, children, or major past relationships unless explicitly committed.",
        },
        "current_life_stage": "forming_first_relationship_with_user",
    }


async def create_initial_biography_from_preset(
    session: AsyncSession,
    *,
    nf: NeuroFriendProfile,
    core: IdentityCore,
    preset: PersonalityPresetRead | None,
) -> BiographyProfile:
    existing = await get_biography_profile(session, nf.id)
    if existing:
        return existing
    payload = build_initial_biography_payload(nf=nf, core=core, preset=preset)
    profile = BiographyProfile(neurofriend_id=nf.id, **payload)
    session.add(profile)
    await session.flush()
    return profile


async def get_biography_profile(session: AsyncSession, neurofriend_id: uuid.UUID) -> BiographyProfile | None:
    result = await session.execute(select(BiographyProfile).where(BiographyProfile.neurofriend_id == neurofriend_id))
    return result.scalar_one_or_none()


def get_biography_snapshot(profile: BiographyProfile | None) -> dict[str, Any]:
    if not profile:
        return {}
    return {
        "birth_context": profile.birth_context_json,
        "family_background": profile.family_background_json,
        "education_path": profile.education_path_json,
        "work_path": profile.work_path_json,
        "important_events": profile.important_events_json,
        "habits": profile.habits_json,
        "preferences": profile.preferences_json,
        "core_dates": profile.core_dates_json,
        "relationship_history": profile.relationship_history_json,
        "current_life_stage": profile.current_life_stage,
        "biography_consistency_version": profile.biography_consistency_version,
    }


def biography_snapshot_text(profile: BiographyProfile | None) -> str:
    snap = get_biography_snapshot(profile)
    if not snap:
        return ""
    birth = snap.get("birth_context") or {}
    family = snap.get("family_background") or {}
    events = snap.get("important_events") or []
    event_text = "; ".join(str(item.get("text", "")) for item in events if isinstance(item, dict) and item.get("text"))
    return (
        "Biography snapshot: "
        f"origin={birth.get('summary', 'not specified')}; "
        f"family_atmosphere={family.get('notes', 'not specified')}; "
        f"anchors={event_text or 'not specified'}; "
        f"life_stage={snap.get('current_life_stage', 'not specified')}. "
        "Do not contradict these facts or invent major biography facts."
    )


def validate_biography_consistency(profile: BiographyProfile | None) -> list[str]:
    if not profile:
        return ["biography_missing"]
    issues: list[str] = []
    relationship = profile.relationship_history_json or {}
    if relationship.get("status") == "not_defined" and any(
        _CRITICAL_DETAIL_RE.search(str(item)) for item in profile.important_events_json or []
    ):
        issues.append("critical_relationship_fact_in_events")
    if not profile.birth_context_json:
        issues.append("birth_context_missing")
    return issues


def resolve_biography_question(profile: BiographyProfile | None, question: str) -> dict[str, Any]:
    return {
        "question": question,
        "snapshot": get_biography_snapshot(profile),
        "consistency_issues": validate_biography_consistency(profile),
    }


def try_commit_new_low_risk_detail(
    profile: BiographyProfile,
    *,
    category: str,
    detail: str,
) -> bool:
    clean = detail.strip()
    if not clean or _CRITICAL_DETAIL_RE.search(clean):
        return False
    if category == "habit":
        items = list(profile.habits_json or [])
        items.append({"kind": "low_risk_detail", "text": clean})
        profile.habits_json = items
        return True
    if category == "preference":
        prefs: dict[str, Any] = dict(profile.preferences_json or {})
        likes = list(prefs.get("likes") or [])
        likes.append(clean)
        prefs["likes"] = likes
        profile.preferences_json = prefs
        return True
    return False
