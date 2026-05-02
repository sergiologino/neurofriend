"""Юнит-тесты v4.4 — repair state и конфликт."""

from types import SimpleNamespace

from app.services.repair_state import (
    cooldown_hours_for_peak,
    compute_conflict_peak,
    compute_cooldown_active,
    sync_relationship_conflict_flags,
)


def test_cooldown_hours_for_peak_tiers() -> None:
    assert cooldown_hours_for_peak(0.1) < 1.0
    assert 2.0 <= cooldown_hours_for_peak(0.35) <= 3.0
    assert cooldown_hours_for_peak(0.99) >= 20.0


def test_compute_conflict_peak_decay_and_raise() -> None:
    prev = SimpleNamespace(conflict_peak=0.6)
    peak = compute_conflict_peak(previous=prev, boundary_alert=0.2)
    assert peak >= 0.5
    peak2 = compute_conflict_peak(previous=None, boundary_alert=0.9)
    assert peak2 >= 0.89


def test_compute_cooldown_active_modes() -> None:
    assert compute_cooldown_active(boundary_mode="cooldown", friction=0.2) is True
    assert compute_cooldown_active(boundary_mode="normal", friction=0.6) is True
    assert compute_cooldown_active(boundary_mode="normal", friction=0.2) is False


def test_sync_clears_on_repair_signal() -> None:
    rel = SimpleNamespace(unresolved_conflict=True, repair_success_rate=0.5)
    sync_relationship_conflict_flags(rel, user_text="прости, погорячился", boundary_mode="clear_boundary", friction=0.8)
    assert rel.unresolved_conflict is False
    assert rel.repair_success_rate > 0.5


def test_sync_sets_unresolved_on_severe() -> None:
    rel = SimpleNamespace(unresolved_conflict=False, repair_success_rate=0.5, last_conflict_at=None)
    sync_relationship_conflict_flags(rel, user_text="отвали", boundary_mode="cooldown", friction=0.9)
    assert rel.unresolved_conflict is True
    assert rel.last_conflict_at is not None
