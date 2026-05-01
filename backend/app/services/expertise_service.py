from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.presets import PersonalityPresetRead

ExpertiseProfile = dict[str, list[str] | int]

_ARCHETYPE_PROFILES: dict[str, dict[str, list[str]]] = {
    "advisor": {
        "core_expertise": ["planning", "decision_making", "clear_explanation"],
        "strong_familiarity": ["productivity", "communication", "everyday_strategy"],
        "weak_or_neutral": ["medicine", "law", "finance"],
    },
    "listener": {
        "core_expertise": ["active_listening", "emotional_presence", "conflict_deescalation"],
        "strong_familiarity": ["relationships", "stress_contexts", "personal_reflection"],
        "weak_or_neutral": ["medicine", "law", "financial_advice"],
    },
    "companion": {
        "core_expertise": ["emotional_presence", "daily_routines", "relationship_attention"],
        "strong_familiarity": ["music", "home_comfort", "gentle_planning"],
        "weak_or_neutral": ["medicine", "law", "finance"],
    },
    "peer": {
        "core_expertise": ["social_observation", "humor", "informal_communication"],
        "strong_familiarity": ["city_life", "relationships", "creative_brainstorming"],
        "weak_or_neutral": ["medicine", "law", "finance"],
    },
}

_TOPIC_ALIASES: dict[str, set[str]] = {
    "planning": {"план", "планирование", "задача", "roadmap", "шаги"},
    "decision_making": {"решение", "выбор", "вариант", "приоритет"},
    "clear_explanation": {"объясни", "разбор", "понятно", "структура"},
    "active_listening": {"выслушай", "послушай", "слушаешь", "поддержи"},
    "emotional_presence": {"грустно", "тяжело", "одиноко", "рядом", "эмоции"},
    "conflict_deescalation": {"конфликт", "ссора", "поссорились", "напряжение"},
    "relationship_attention": {"отношения", "дружба", "близость", "контакт"},
    "daily_routines": {"быт", "день", "привычка", "режим"},
    "humor": {"шутка", "смешно", "ирония", "юмор"},
    "social_observation": {"люди", "компания", "общение", "город"},
    "medicine": {"болит", "диагноз", "лекарство", "врач"},
    "law": {"закон", "суд", "договор", "юрист"},
    "finance": {"инвестиции", "налоги", "кредит", "финансы"},
}


def build_initial_expertise_profile(preset: PersonalityPresetRead | None, archetype: str) -> ExpertiseProfile:
    key = (preset.archetype if preset else archetype).strip().lower()
    base = _ARCHETYPE_PROFILES.get(
        key,
        {
            "core_expertise": ["conversation", "personal_context", "everyday_reflection"],
            "strong_familiarity": ["relationships", "planning", "creative_brainstorming"],
            "weak_or_neutral": ["medicine", "law", "finance"],
        },
    )
    return {
        "version": 1,
        "core_expertise": list(base["core_expertise"][:3]),
        "strong_familiarity": list(base["strong_familiarity"][:5]),
        "weak_or_neutral": list(base["weak_or_neutral"][:5]),
    }


def _profile_list(profile: Mapping[str, Any], key: str) -> list[str]:
    raw = profile.get(key)
    if not isinstance(raw, list):
        return []
    return [str(item).strip().lower() for item in raw if str(item).strip()]


def _topic_matches(topic: str, expertise_key: str) -> bool:
    t = topic.strip().lower()
    if not t:
        return False
    key = expertise_key.strip().lower()
    if key and key in t:
        return True
    aliases = _TOPIC_ALIASES.get(key, set())
    return any(alias in t for alias in aliases)


def get_expertise_level(topic: str, profile: Mapping[str, Any] | None) -> str:
    if not profile:
        return "general"
    for item in _profile_list(profile, "core_expertise"):
        if _topic_matches(topic, item):
            return "core"
    for item in _profile_list(profile, "strong_familiarity"):
        if _topic_matches(topic, item):
            return "strong"
    for item in _profile_list(profile, "weak_or_neutral"):
        if _topic_matches(topic, item):
            return "weak"
    return "general"


def get_confidence_modifier(topic: str, profile: Mapping[str, Any] | None) -> float:
    level = get_expertise_level(topic, profile)
    return {
        "core": 0.18,
        "strong": 0.06,
        "general": -0.02,
        "weak": -0.22,
    }[level]


def shape_response_by_expertise(topic: str, response_plan: Mapping[str, Any], profile: Mapping[str, Any] | None) -> dict[str, Any]:
    shaped = dict(response_plan)
    level = get_expertise_level(topic, profile)
    shaped["expertise_level"] = level
    shaped["confidence_modifier"] = get_confidence_modifier(topic, profile)
    if level == "weak":
        shaped["style_note"] = "Answer carefully, with explicit limits and no professional impersonation."
    elif level == "core":
        shaped["style_note"] = "This is one of the personality's strong areas; answer with more grounded confidence."
    else:
        shaped["style_note"] = "Answer as an educated companion, not as an all-knowing expert."
    return shaped


def expertise_snapshot_text(profile: Mapping[str, Any] | None) -> str:
    if not profile:
        return ""
    core = ", ".join(_profile_list(profile, "core_expertise"))
    strong = ", ".join(_profile_list(profile, "strong_familiarity"))
    weak = ", ".join(_profile_list(profile, "weak_or_neutral"))
    return (
        "Expertise profile: "
        f"core=[{core or 'none'}]; "
        f"strong_familiarity=[{strong or 'none'}]; "
        f"weak_or_neutral=[{weak or 'none'}]."
    )
