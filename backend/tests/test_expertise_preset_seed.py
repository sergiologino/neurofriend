from app.services.expertise_service import build_initial_expertise_profile
from app.services.presets_catalog import get_preset_by_id


def test_warm_companion_uses_json_expertise_seed_not_archetype_truncation() -> None:
    preset = get_preset_by_id("warm_companion")
    assert preset is not None
    assert preset.expertise_profile is not None
    prof = build_initial_expertise_profile(preset, archetype="advisor")
    assert prof.get("preset_expertise_seed") == "warm_companion"
    assert "mood_support" in prof["core_expertise"]
    assert len(prof["core_expertise"]) >= 5
    assert "clinical_diagnosis" in prof["weak_or_neutral"]


def test_unknown_archetype_falls_back_when_no_seed() -> None:
    from app.schemas.presets import PersonalityPresetRead

    loose = PersonalityPresetRead(
        id="x",
        title="X",
        archetype="custom_unknown",
        description="d",
        suggested_name="n",
    )
    prof = build_initial_expertise_profile(loose, archetype="custom_unknown")
    assert "preset_expertise_seed" not in prof
    assert prof["core_expertise"]
