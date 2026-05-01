"""v4.3 Stage C — attachment / romantic dynamics (slow progression, boundaries)."""

from app.models.relationship_state import InternalStateSnapshot, RelationshipModel
from app.services.attachment_dynamics_service import (
    archetype_romantic_baseline,
    boundary_check,
    compute_bond_type,
    evaluate_romantic_signal,
    update_affection_after_event,
)


def test_evaluate_romantic_signal_soft_vs_strong() -> None:
    assert evaluate_romantic_signal("как дела") < 0.15
    assert evaluate_romantic_signal("люблю тебя") >= 0.4


def test_archetype_baselines_differ() -> None:
    assert archetype_romantic_baseline("романтический спутник") > archetype_romantic_baseline("строгий наставник")


def test_boundary_conflict_blocks_romance() -> None:
    rel = RelationshipModel(conflict_memory_score=0.55)
    assert boundary_check(boundary_mode="normal", friction=0.1, boundary_alert=0.0, rel=rel) is True


def test_clear_boundary_mode_blocks() -> None:
    rel = RelationshipModel(conflict_memory_score=0.05, boundary_safety_score=0.7)
    assert boundary_check(boundary_mode="clear_boundary", friction=0.2, boundary_alert=0.1, rel=rel) is True


def test_repair_opening_allows_when_not_severe() -> None:
    rel = RelationshipModel(conflict_memory_score=0.35, boundary_safety_score=0.6)
    assert boundary_check(boundary_mode="repair_opening", friction=0.35, boundary_alert=0.2, rel=rel) is False


def test_one_flirt_burst_does_not_jump_to_romantic_soft() -> None:
    rel = RelationshipModel()
    prev = InternalStateSnapshot()
    update_affection_after_event(
        previous_state=prev,
        rel=rel,
        user_text="люблю тебя, целую, ты особенный человек для меня",
        archetype="романтический друг",
        boundary_mode="normal",
        friction=0.0,
        boundary_alert=0.0,
        valence=0.5,
    )
    assert rel.bond_type != "romantic_soft"
    assert rel.romantic_tension_score < 0.35


def test_insult_boundary_blocks_tension_gain() -> None:
    rel = RelationshipModel(emotional_intimacy_score=0.45, affection_score=0.42, romantic_tension_score=0.25)
    prev = InternalStateSnapshot(friction=0.65, boundary_alert=0.5)
    before = rel.romantic_tension_score
    update_affection_after_event(
        previous_state=prev,
        rel=rel,
        user_text="люблю тебя",
        archetype="companion",
        boundary_mode="cooldown",
        friction=0.65,
        boundary_alert=0.5,
        valence=-0.3,
    )
    assert rel.romantic_tension_score <= before


def test_romantic_signal_hint_boosts_without_lexicon() -> None:
    prev = InternalStateSnapshot(friction=0.05, boundary_alert=0.0)
    rel_low = RelationshipModel(emotional_intimacy_score=0.48, affection_score=0.46, romantic_tension_score=0.22)
    rel_hi = RelationshipModel(emotional_intimacy_score=0.48, affection_score=0.46, romantic_tension_score=0.22)
    update_affection_after_event(
        previous_state=prev,
        rel=rel_low,
        user_text="окей понял",
        archetype="companion",
        boundary_mode="normal",
        friction=0.05,
        boundary_alert=0.0,
        valence=0.1,
        romantic_signal_hint=None,
    )
    update_affection_after_event(
        previous_state=prev,
        rel=rel_hi,
        user_text="окей понял",
        archetype="companion",
        boundary_mode="normal",
        friction=0.05,
        boundary_alert=0.0,
        valence=0.1,
        romantic_signal_hint=0.88,
    )
    assert rel_hi.romantic_tension_score > rel_low.romantic_tension_score


def test_archetype_increases_tension_when_gate_passes() -> None:
    base_rel = RelationshipModel(emotional_intimacy_score=0.48, affection_score=0.46, romantic_tension_score=0.22)
    prev = InternalStateSnapshot(friction=0.05, boundary_alert=0.0)
    rel_hot = RelationshipModel(
        emotional_intimacy_score=0.48,
        affection_score=0.46,
        romantic_tension_score=0.22,
    )
    rel_cold = RelationshipModel(
        emotional_intimacy_score=0.48,
        affection_score=0.46,
        romantic_tension_score=0.22,
    )
    text = "ты особенный человек"
    update_affection_after_event(
        previous_state=prev,
        rel=rel_hot,
        user_text=text,
        archetype="романтический друг",
        boundary_mode="normal",
        friction=0.05,
        boundary_alert=0.0,
        valence=0.2,
    )
    update_affection_after_event(
        previous_state=prev,
        rel=rel_cold,
        user_text=text,
        archetype="строгий наставник",
        boundary_mode="normal",
        friction=0.05,
        boundary_alert=0.0,
        valence=0.2,
    )
    assert rel_hot.romantic_tension_score >= rel_cold.romantic_tension_score


def test_compute_bond_romantic_soft_requires_thresholds() -> None:
    low = RelationshipModel(
        affection_score=0.48,
        emotional_intimacy_score=0.5,
        romantic_tension_score=0.4,
        bond_type="platonic",
    )
    assert compute_bond_type(low, romance_blocked=False) != "romantic_soft"
    high = RelationshipModel(
        affection_score=0.55,
        emotional_intimacy_score=0.58,
        romantic_tension_score=0.48,
        bond_type="platonic",
    )
    assert compute_bond_type(high, romance_blocked=False) == "romantic_soft"


def test_conflict_prevents_romantic_soft_label() -> None:
    rel = RelationshipModel(
        affection_score=0.58,
        emotional_intimacy_score=0.58,
        romantic_tension_score=0.48,
        bond_type="platonic",
    )
    assert compute_bond_type(rel, romance_blocked=True) != "romantic_soft"
