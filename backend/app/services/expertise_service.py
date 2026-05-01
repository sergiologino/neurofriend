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
    "mood_support": {"настроение", "тоска", "поддержи меня"},
    "gentle_comfort": {"уют", "нежн", "утеш"},
    "daily_attunement": {"день прошёл", "как ты себя"},
    "gratitude_moments": {"благодар", "ценю"},
    "cozy_habits": {"чай", "плед", "уютно дома"},
    "slow_conversation": {"не спеш", "потише", "нетороплив"},
    "clinical_diagnosis": {"диагноз", "болезнь", "симптом"},
    "legal_counsel": {"иск", "исковое"},
    "investment_advice": {"акции", "портфель", "влож"},
    "tax_planning": {"налоговая декларация", "ндфл"},
    "prioritization": {"приоритет", "важнее всего"},
    "structured_thinking": {"структур", "по пунктам логич"},
    "goal_clarification": {"зачем тебе", "какая цель"},
    "negotiation_light": {"договориться", "компромисс"},
    "time_management": {"дедлайн", "расписание"},
    "risk_awareness": {"риск", "что может пойти не так"},
    "process_design": {"процесс", "шаблон работы"},
    "accountability": {"ответственность", "обещание"},
    "feedback_framing": {"обратная связь"},
    "regulated_professions": {"лицензия врача"},
    "spontaneity": {"спонтан", "импульсив"},
    "playful_repartee": {"остроум", "подколол"},
    "casual_storytelling": {"расскажу случай", "история из жизни"},
    "banter": {"подшучива", "шутливо"},
    "group_dynamics": {"в компании", "с друзьями"},
    "pop_culture_light": {"фильм", "сериал"},
    "weekend_plans": {"выходные", "суббот"},
    "social_energy": {"тусовк", "шумная компания"},
    "reflective_questions": {"что для тебя важно", "уточни"},
    "patience_presence": {"не торопись", "есть время"},
    "validation_language": {"нормально чувствовать", "ты имеешь право"},
    "mindful_pause": {"пауза", "помолчим"},
    "repair_openings": {"давай помиримся", "прости если"},
    "gentle_boundaries": {"мне некомфортно", "граница"},
    "silence_comfort": {"просто помолчим", "тишина"},
    "emotion_labeling": {"это злость", "назови эмоцию"},
    "crisis_intervention_pro": {"суицид", "скорая психиатр"},
}


_TOPIC_LABELS_RU: dict[str, str] = {
    "planning": "планирование и расстановка приоритетов",
    "decision_making": "разбор решений и вариантов",
    "clear_explanation": "ясные объяснения и структура",
    "active_listening": "внимательное слушание",
    "emotional_presence": "эмоциональное присутствие и поддержка",
    "conflict_deescalation": "снятие напряжения в конфликтах",
    "relationship_attention": "внимание к отношениям и близости",
    "daily_routines": "быт и распорядок дня",
    "medicine": "медицина и здоровье",
    "law": "право и юридические темы",
    "finance": "финансы и инвестиции",
    "financial_advice": "финансовые советы",
    "social_observation": "наблюдение за людьми и социумом",
    "humor": "юмор и лёгкий тон",
    "informal_communication": "неформальное общение",
    "city_life": "городская жизнь и среда",
    "creative_brainstorming": "творческое мышление и идеи",
    "conversation": "разговор и беседа",
    "personal_context": "личный контекст и рефлексия",
    "everyday_reflection": "повседневные размышления",
    "music": "музыка",
    "home_comfort": "уют дома и быт",
    "gentle_planning": "бережное планирование",
    "relationships": "отношения",
    "stress_contexts": "стрессовые ситуации",
    "personal_reflection": "личная рефлексия",
    "communication": "коммуникация",
    "everyday_strategy": "повседневная стратегия",
    "productivity": "продуктивность",
    "prioritization": "приоритеты и фокус",
    "structured_thinking": "структурированное мышление",
    "goal_clarification": "уточнение целей",
    "negotiation_light": "лёгкие переговоры и компромисс",
    "time_management": "управление временем",
    "risk_awareness": "осознание рисков",
    "process_design": "выстраивание процессов",
    "accountability": "ответственность и обязательства",
    "feedback_framing": "формулировка обратной связи",
    "regulated_professions": "регулируемые профессии",
    "mood_support": "поддержка настроения",
    "gentle_comfort": "мягкое утешение",
    "daily_attunement": "настройка на ритм дня",
    "gratitude_moments": "благодарность и тёплые моменты",
    "cozy_habits": "уютные бытовые привычки",
    "slow_conversation": "неторопливый разговор",
    "clinical_diagnosis": "клиническая диагностика",
    "legal_counsel": "юридическое консультирование",
    "investment_advice": "инвестиционные советы",
    "tax_planning": "налоговое планирование",
    "spontaneity": "спонтанность",
    "playful_repartee": "игривая словесная перепалка",
    "casual_storytelling": "несерьёзные истории из жизни",
    "banter": "дружеская подшучивание",
    "group_dynamics": "динамика в группе",
    "pop_culture_light": "лёгкая поп-культура",
    "weekend_plans": "планы на выходные",
    "social_energy": "социальная энергия и компании",
    "reflective_questions": "рефлексивные вопросы",
    "patience_presence": "терпеливое присутствие",
    "validation_language": "валидирующие формулировки",
    "mindful_pause": "осознанная пауза",
    "repair_openings": "открытие для примирения",
    "gentle_boundaries": "мягкие границы",
    "silence_comfort": "комфорт в тишине",
    "emotion_labeling": "называние эмоций",
    "crisis_intervention_pro": "профессиональное кризисное вмешательство",
}


def _topic_label_ru(slug: str) -> str:
    key = slug.strip().lower()
    return _TOPIC_LABELS_RU.get(key, slug.replace("_", " "))


def expertise_preview_for_user(profile: Mapping[str, Any] | None) -> str:
    """Краткий текст для UI по профилю экспертизы."""
    if not profile:
        return ""
    core = _profile_list(profile, "core_expertise")
    strong = _profile_list(profile, "strong_familiarity")
    weak = _profile_list(profile, "weak_or_neutral")
    lines: list[str] = []
    if core:
        labels = [_topic_label_ru(x) for x in core[:5]]
        lines.append("Сильные темы (ядро): " + ", ".join(labels) + ".")
    if strong:
        labels = [_topic_label_ru(x) for x in strong[:6]]
        lines.append("Хорошо знакомо: " + ", ".join(labels) + ".")
    if weak:
        labels = [_topic_label_ru(x) for x in weak[:5]]
        lines.append("Будет осторожен и без профессионального тона: " + ", ".join(labels) + ".")
    disclaimer = (
        "Это не сертификация: в узких областях персонаж будет напоминать о границах компетенции."
    )
    if lines:
        lines.append(disclaimer)
    return "\n".join(lines)


def build_initial_expertise_profile(preset: PersonalityPresetRead | None, archetype: str) -> ExpertiseProfile:
    if preset and preset.expertise_profile:
        ep = preset.expertise_profile
        return {
            "version": ep.version,
            "core_expertise": list(ep.core_expertise),
            "strong_familiarity": list(ep.strong_familiarity),
            "weak_or_neutral": list(ep.weak_or_neutral),
            "preset_expertise_seed": preset.id,
        }
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
