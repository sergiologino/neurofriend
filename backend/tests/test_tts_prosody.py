from app.services.tts_prosody import tts_speed_for_bond_type


def test_tts_speed_monotonic_for_warmer_bonds() -> None:
    assert tts_speed_for_bond_type("platonic") >= tts_speed_for_bond_type("emotional_close")
    assert tts_speed_for_bond_type("emotional_close") >= tts_speed_for_bond_type("romantic_soft")
    assert 0.25 <= tts_speed_for_bond_type(None) <= 1.4
