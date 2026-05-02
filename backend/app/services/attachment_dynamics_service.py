"""v4.3 Stage C — межличностная и романтическая динамика (медленное развитие, границы)."""

from __future__ import annotations

from app.models.relationship_state import InternalStateSnapshot, RelationshipModel

# Ограничения на один пользовательский ход — без «прыжка» в romantic_soft за одно сообщение.
_MAX_DELTA_AFFECTION = 0.042
_MAX_DELTA_INTIMACY = 0.038
_MAX_DELTA_TENSION = 0.048


def archetype_romantic_baseline(archetype: str) -> float:
    """Базовая склонность архетипа к тёплой/романтической окраске (не поведение пользователя)."""
    a = (archetype or "").lower()
    if any(x in a for x in ("романт", "нежн", "муза", "partner", "партнёр", "партнер", "возлюб")):
        return 0.64
    if any(x in a for x in ("наставник", "учитель", "коуч", "stoic", "стоик", "строг")):
        return 0.26
    return 0.42


def evaluate_romantic_signal(text: str) -> float:
    """Эвристика сильных романтических маркеров в реплике пользователя, 0..1."""
    t = (text or "").lower()
    score = 0.0
    if any(w in t for w in ("люблю тебя", "целую", "обнимаю", "скучаю по тебе", "ты особенн")):
        score += 0.42
    if any(w in t for w in ("хочу быть рядом", "ты дорог мне", "ты дорога мне", "влюблён", "влюблена")):
        score += 0.38
    if any(w in t for w in ("флирт", "свидан", "целоваться", "поцелуй")):
        score += 0.28
    if any(w in t for w in ("красив", "милая", "милый", "очаров", "привлекательн")):
        score += 0.18
    return min(1.0, score)


def evaluate_warmth_signal(text: str) -> float:
    t = (text or "").lower()
    score = 0.0
    if any(w in t for w in ("спасибо", "рад тебя", "приятно", "скучал", "скучала")):
        score += 0.35
    if any(w in t for w in ("поддерживаю", "понимаю", "рядом")):
        score += 0.15
    return min(1.0, score)


def boundary_check(
    *,
    boundary_mode: str,
    friction: float,
    boundary_alert: float,
    rel: RelationshipModel,
) -> bool:
    """
    True — усиление романтики/флирта сейчас недопустимо (конфликт, границы, трение).
    Согласуется с BoundaryResponseService по режимам.
    """
    if boundary_mode == "repair_opening":
        if float(rel.conflict_memory_score or 0.0) >= 0.52:
            return True
        if friction >= 0.72 or boundary_alert >= 0.72:
            return True
        return False

    if float(rel.conflict_memory_score or 0.0) >= 0.4:
        return True
    if float(rel.boundary_safety_score or 0.7) <= 0.38:
        return True
    if boundary_mode == "cooldown":
        return True
    if boundary_mode == "clear_boundary":
        return True
    if boundary_mode == "dry_distance" and friction >= 0.38:
        return True
    if friction >= 0.58:
        return True
    if boundary_alert >= 0.55:
        return True
    return False


def should_allow_flirtation(
    *,
    romance_blocked: bool,
    emotional_intimacy_score: float,
    affection_score: float,
) -> bool:
    if romance_blocked:
        return False
    return emotional_intimacy_score >= 0.26 and affection_score >= 0.32


def compute_bond_type(rel: RelationshipModel, *, romance_blocked: bool) -> str:
    a = float(rel.affection_score or 0.0)
    i = float(rel.emotional_intimacy_score or 0.0)
    t = float(rel.romantic_tension_score or 0.0)
    if i < 0.24 and t < 0.22:
        return "platonic"
    if i < 0.36 and a < 0.4:
        return "warm_acquaintance"
    if i < 0.46 or a < 0.42:
        return "warm_friendship"
    if romance_blocked or t < 0.36:
        return "emotional_close"
    if i >= 0.54 and a >= 0.5 and t >= 0.46:
        return "romantic_soft"
    return "emotional_close"


def update_bond_type(rel: RelationshipModel, *, romance_blocked: bool) -> None:
    rel.bond_type = compute_bond_type(rel, romance_blocked=romance_blocked)


def update_affection_after_event(
    *,
    previous_state: InternalStateSnapshot | None,
    rel: RelationshipModel,
    user_text: str,
    archetype: str,
    boundary_mode: str,
    friction: float,
    boundary_alert: float,
    valence: float,
    romantic_signal_hint: float | None = None,
    romantic_profile: dict | None = None,
) -> dict[str, float]:
    """
    Обновляет накопительные scores в RelationshipModel и возвращает поля для нового InternalStateSnapshot.
    """
    baseline = archetype_romantic_baseline(archetype)
    romance_blocked = boundary_check(
        boundary_mode=boundary_mode,
        friction=friction,
        boundary_alert=boundary_alert,
        rel=rel,
    )
    warm = evaluate_warmth_signal(user_text)
    romantic_sig = evaluate_romantic_signal(user_text)
    if romantic_signal_hint is not None:
        hint = max(0.0, min(1.0, float(romantic_signal_hint)))
        romantic_sig = max(romantic_sig, hint)

    a = float(rel.affection_score or 0.35)
    i = float(rel.emotional_intimacy_score or 0.18)
    tense = float(rel.romantic_tension_score or 0.12)

    aff_delta = (warm * 0.028 + max(0.0, valence) * 0.018) * (0.75 + baseline * 0.35)
    aff_delta = min(_MAX_DELTA_AFFECTION, aff_delta)
    if valence < -0.25:
        aff_delta -= 0.012

    int_delta = warm * 0.022 * (0.8 + baseline * 0.25)
    int_delta += max(0.0, valence) * 0.014
    int_delta = min(_MAX_DELTA_INTIMACY, int_delta)
    if romance_blocked:
        int_delta *= 0.35

    tension_delta = 0.0
    projected_a = max(0.0, min(1.0, a + aff_delta))
    projected_i = max(0.0, min(1.0, i + int_delta))
    if not romance_blocked and should_allow_flirtation(
        romance_blocked=False,
        emotional_intimacy_score=projected_i,
        affection_score=projected_a,
    ):
        tension_delta = romantic_sig * _MAX_DELTA_TENSION * (0.45 + baseline * 0.45)
        tension_delta = min(_MAX_DELTA_TENSION, tension_delta)
    elif romantic_sig > 0.0 and romance_blocked:
        tense = max(0.05, tense - 0.008)

    a = max(0.0, min(1.0, a + aff_delta))
    i = max(0.0, min(1.0, i + int_delta))
    tense = max(0.0, min(1.0, tense + tension_delta))

    rel.affection_score = a
    rel.emotional_intimacy_score = i
    rel.romantic_tension_score = tense

    update_bond_type(rel, romance_blocked=romance_blocked)

    from app.services.romantic_style_service import apply_post_turn_relationship_styling

    apply_post_turn_relationship_styling(
        rel,
        romantic_profile=romantic_profile,
        romantic_sig=romantic_sig,
        romance_blocked=romance_blocked,
        boundary_mode=boundary_mode,
    )

    ephemeral = min(0.08, romantic_sig * 0.06) if not romance_blocked else 0.0
    snap_romantic_interest = min(1.0, tense + ephemeral)

    flirt_comfort = max(0.0, min(1.0, (i + a) / 2 - (0.12 if romance_blocked else 0.0)))

    return {
        "affection": a,
        "romantic_interest": snap_romantic_interest,
        "flirt_comfort": flirt_comfort,
        "emotional_intimacy": i,
    }


def romantic_prompt_context(state: InternalStateSnapshot | None, rel: RelationshipModel | None) -> str:
    if not state or not rel:
        return ""
    bond = rel.bond_type or "platonic"
    lines = [
        f"Межличностная связь (SRS): тип «{bond}».",
        f"Привязанность≈{state.affection:.2f}, эмоциональная близость≈{state.emotional_intimacy:.2f}, "
        f"романтический интерес≈{state.romantic_interest:.2f}, комфорт тёплого тона≈{state.flirt_comfort:.2f}.",
    ]
    if bond in {"platonic", "warm_acquaintance"}:
        lines.append(
            "Тон дружеский или нейтрально-тёплый; без давления романтики и без намёков на быструю близость."
        )
    elif bond == "warm_friendship":
        lines.append("Допускается искренняя теплота без романтического форса.")
    elif bond == "emotional_close":
        lines.append("Можно бережная эмоциональная близость; без явной эротики.")
    else:
        lines.append(
            "Допустима осторожная романтическая окраска в рамках уважения; без графичности и без форса."
        )
    lines.append(
        "Не обгоняй уровень связи: если связь ещё не emotional_close / romantic_soft — не играй в «партнёрские» сценарии."
    )
    return " ".join(lines)
