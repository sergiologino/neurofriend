"""v4.4 — поля конфликта на снимке состояния и флаги связи для repair initiative."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.datetimeutil import utc_naive_now
from app.services.boundary_response_service import detect_repair_signal, evaluate_disrespect_level

if TYPE_CHECKING:
    from app.models.relationship_state import InternalStateSnapshot, RelationshipModel


def compute_conflict_peak(*, previous: InternalStateSnapshot | None, boundary_alert: float) -> float:
    prev_peak = float(getattr(previous, "conflict_peak", 0.0) or 0.0) if previous else 0.0
    decayed = prev_peak * 0.88
    return max(0.0, min(1.0, max(decayed, float(boundary_alert))))


def compute_cooldown_active(*, boundary_mode: str, friction: float) -> bool:
    return boundary_mode in {"cooldown", "clear_boundary"} or friction >= 0.55


def compute_repair_readiness_values(
    *,
    rel: RelationshipModel | None,
    friction: float,
    conflict_peak: float,
    cooldown_active: bool,
) -> tuple[float, float]:
    """Возвращает (repair_readiness, reconnection_need) для снимка состояния."""
    if rel is None or not rel.unresolved_conflict or rel.last_conflict_at is None:
        return 0.0, 0.0

    now = utc_naive_now()
    hours = max(0.0, (now - rel.last_conflict_at).total_seconds() / 3600.0)
    cool = cooldown_hours_for_peak(conflict_peak)
    base = min(1.0, hours / max(cool, 0.01))
    attempts = int(rel.repair_attempt_count or 0)
    penalty = max(0.35, 1.0 - 0.18 * attempts)
    readiness = min(1.0, base * penalty)
    if cooldown_active:
        readiness *= 0.65

    conflict_mem = float(rel.conflict_memory_score or 0.0)
    reconnect = min(1.0, conflict_mem * 0.55 + float(friction) * 0.45)
    return round(readiness, 4), round(reconnect, 4)


def cooldown_hours_for_peak(conflict_peak: float) -> float:
    """Часы ожидания до допустимой repair-попытки (эвристика SRS §1.10)."""
    p = float(conflict_peak)
    if p < 0.28:
        return 0.75
    if p < 0.48:
        return 2.5
    if p < 0.72:
        return 8.0
    return 22.0


def sync_relationship_conflict_flags(
    rel: RelationshipModel | None,
    *,
    user_text: str,
    boundary_mode: str,
    friction: float,
) -> None:
    """Обновляет unresolved_conflict / last_conflict_at и метрики после примирения."""
    if rel is None:
        return
    if detect_repair_signal(user_text):
        rel.unresolved_conflict = False
        rel.repair_success_rate = min(1.0, float(rel.repair_success_rate or 0.5) + 0.06)
        return

    level = evaluate_disrespect_level(user_text)
    severe = boundary_mode in {"cooldown", "clear_boundary"} or level >= 2 or (
        level >= 1 and friction >= 0.48
    )
    if severe:
        rel.unresolved_conflict = True
        rel.last_conflict_at = utc_naive_now()


def repair_followup_context_for_llm(rel: RelationshipModel | None, state: InternalStateSnapshot | None) -> str:
    """Короткая строка для generate_reply при неразрешённом конфликте."""
    if not rel or not state or not rel.unresolved_conflict:
        return ""
    return (
        "В отношении ещё есть неразрешённое напряжение после конфликта. "
        f"repair_readiness≈{state.repair_readiness:.2f}, reconnection_need≈{state.reconnection_need:.2f}. "
        "Не используй шантаж молчанием и не унижай; допустимы честность и мягкая проверка контакта."
    )
