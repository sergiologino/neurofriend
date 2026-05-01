from app.models.relationship_state import InternalStateSnapshot, RelationshipModel
from app.services.boundary_response_service import (
    apply_boundary_to_state,
    boundary_prompt_context,
    detect_repair_signal,
    evaluate_disrespect_level,
    select_boundary_mode,
    update_relationship_boundary,
)


def test_disrespect_and_repair_detection() -> None:
    assert evaluate_disrespect_level("Заткнись, ты тупой") == 3
    assert evaluate_disrespect_level("Ты бесишь") == 2
    assert evaluate_disrespect_level("нормально поговорим") == 0
    assert detect_repair_signal("Извини, я погорячился")


def test_boundary_mode_escalates_without_toxicity() -> None:
    assert select_boundary_mode(disrespect_level=0, friction=0.0, repair_signal=False) == "normal"
    assert select_boundary_mode(disrespect_level=1, friction=0.33, repair_signal=False) == "dry_distance"
    assert select_boundary_mode(disrespect_level=2, friction=0.6, repair_signal=False) == "clear_boundary"
    assert select_boundary_mode(disrespect_level=3, friction=0.8, repair_signal=False) == "cooldown"
    assert select_boundary_mode(disrespect_level=3, friction=0.8, repair_signal=True) == "repair_opening"


def test_apply_boundary_to_state_and_relationship() -> None:
    previous = InternalStateSnapshot(friction=0.2, safety=0.7, hurt=0.1, valence=0.0)
    result = apply_boundary_to_state(
        previous=previous,
        text="Ты бесишь, молчи",
        valence=0.0,
        hurt=0.1,
        safety=0.7,
    )

    assert result["friction"] > 0.2
    assert result["boundary_alert"] > 0
    assert result["initiative_cooldown"] is True

    rel = RelationshipModel()
    update_relationship_boundary(rel, text="Ты бесишь, молчи", friction=float(result["friction"]))
    assert rel.conflict_memory_score > 0
    assert rel.boundary_safety_score < 0.7


def test_boundary_prompt_context_contains_mode() -> None:
    state = InternalStateSnapshot(friction=0.6, boundary_alert=0.5, respect_signal=0.2)
    rel = RelationshipModel(conflict_memory_score=0.4, boundary_safety_score=0.4, repair_receptivity=0.5)

    context = boundary_prompt_context(state, rel)

    assert "Boundary mode" in context
    assert "clear_boundary" in context
