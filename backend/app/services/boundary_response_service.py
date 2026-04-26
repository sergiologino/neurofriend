from __future__ import annotations

from dataclasses import dataclass

from app.models.relationship_state import InternalStateSnapshot, RelationshipModel

INSULT_WORDS = (
    "дурак",
    "тупой",
    "идиот",
    "заткнись",
    "отвали",
    "пошел",
    "пошёл",
    "ненавижу тебя",
)
DISRESPECT_WORDS = (
    "бесишь",
    "раздражаешь",
    "молчи",
    "ты никто",
    "не лезь",
    "надоел",
)
REPAIR_WORDS = (
    "извини",
    "прости",
    "не хотел",
    "не хотела",
    "погорячился",
    "погорячилась",
    "давай нормально",
)


@dataclass(frozen=True)
class BoundaryAssessment:
    disrespect_level: int
    repair_signal: bool
    boundary_mode: str
    initiative_cooldown: bool


def evaluate_disrespect_level(text: str) -> int:
    t = text.lower()
    if any(word in t for word in INSULT_WORDS):
        return 3
    if any(word in t for word in DISRESPECT_WORDS):
        return 2
    if "!" in t and any(word in t for word in ("стоп", "хватит", "не хочу")):
        return 1
    return 0


def detect_repair_signal(text: str) -> bool:
    t = text.lower()
    return any(word in t for word in REPAIR_WORDS)


def select_boundary_mode(
    *,
    disrespect_level: int,
    friction: float,
    repair_signal: bool,
) -> str:
    if repair_signal:
        return "repair_opening"
    if disrespect_level >= 3 or friction >= 0.78:
        return "cooldown"
    if disrespect_level == 2 or friction >= 0.55:
        return "clear_boundary"
    if disrespect_level == 1 or friction >= 0.32:
        return "dry_distance"
    return "normal"


def boundary_level_for_mode(mode: str) -> int:
    return {
        "normal": 0,
        "repair_opening": 0,
        "dry_distance": 1,
        "clear_boundary": 2,
        "cooldown": 4,
    }.get(mode, 0)


def assess_boundary_event(
    *,
    text: str,
    previous_friction: float,
) -> BoundaryAssessment:
    level = evaluate_disrespect_level(text)
    repair = detect_repair_signal(text)
    next_friction = max(0.0, previous_friction - 0.24) if repair else min(1.0, previous_friction + level * 0.22)
    mode = select_boundary_mode(disrespect_level=level, friction=next_friction, repair_signal=repair)
    return BoundaryAssessment(
        disrespect_level=level,
        repair_signal=repair,
        boundary_mode=mode,
        initiative_cooldown=mode in {"clear_boundary", "cooldown"},
    )


def apply_boundary_to_state(
    *,
    previous: InternalStateSnapshot | None,
    text: str,
    valence: float,
    hurt: float,
    safety: float,
) -> dict[str, float | str | bool]:
    prev_friction = previous.friction if previous else 0.0
    assessment = assess_boundary_event(text=text, previous_friction=prev_friction)
    friction = max(0.0, prev_friction - 0.24) if assessment.repair_signal else min(1.0, prev_friction + assessment.disrespect_level * 0.22)
    boundary_alert = min(1.0, assessment.disrespect_level / 3)
    respect_signal = 1.0 if assessment.repair_signal else max(0.0, 0.65 - assessment.disrespect_level * 0.25)
    self_respect = min(1.0, friction + boundary_alert * 0.35)
    if assessment.disrespect_level:
        valence = max(-1.0, valence - 0.06 * assessment.disrespect_level)
        hurt = min(1.0, hurt + 0.04 * assessment.disrespect_level)
        safety = max(0.0, safety - 0.04 * assessment.disrespect_level)
    if assessment.repair_signal:
        safety = min(1.0, safety + 0.08)
        hurt = max(0.0, hurt - 0.08)
    return {
        "friction": friction,
        "boundary_alert": boundary_alert,
        "respect_signal": respect_signal,
        "self_respect_activation": self_respect,
        "boundary_mode": assessment.boundary_mode,
        "initiative_cooldown": assessment.initiative_cooldown,
        "valence": valence,
        "hurt": hurt,
        "safety": safety,
    }


def update_relationship_boundary(
    rel: RelationshipModel,
    *,
    text: str,
    friction: float,
) -> None:
    assessment = assess_boundary_event(text=text, previous_friction=friction)
    if assessment.repair_signal:
        rel.repair_receptivity = min(1.0, (rel.repair_receptivity or 0.5) + 0.08)
        rel.boundary_safety_score = min(1.0, (rel.boundary_safety_score or 0.7) + 0.05)
        rel.conflict_memory_score = max(0.0, (rel.conflict_memory_score or 0.0) - 0.06)
        return
    if assessment.disrespect_level:
        rel.conflict_memory_score = min(1.0, (rel.conflict_memory_score or 0.0) + 0.06 * assessment.disrespect_level)
        rel.boundary_safety_score = max(0.0, (rel.boundary_safety_score or 0.7) - 0.05 * assessment.disrespect_level)
        rel.respect_baseline = max(0.0, (rel.respect_baseline or 0.5) - 0.03 * assessment.disrespect_level)


def boundary_prompt_context(state: InternalStateSnapshot | None, rel: RelationshipModel | None) -> str:
    if not state:
        return ""
    mode = select_boundary_mode(
        disrespect_level=0,
        friction=state.friction,
        repair_signal=False,
    )
    parts = [
        f"Boundary mode: {mode} (level {boundary_level_for_mode(mode)}).",
        f"friction={state.friction:.2f}, boundary_alert={state.boundary_alert:.2f}, respect_signal={state.respect_signal:.2f}.",
    ]
    if rel:
        parts.append(
            f"Relationship boundary safety={rel.boundary_safety_score:.2f}, conflict_memory={rel.conflict_memory_score:.2f}, repair_receptivity={rel.repair_receptivity:.2f}."
        )
    parts.append(
        "If boundary mode is dry_distance, be shorter and less warm. If clear_boundary, state the boundary plainly. "
        "If cooldown, do not continue the rude tone: short refusal or cooling-off, without insult or guilt pressure."
    )
    return " ".join(parts)
