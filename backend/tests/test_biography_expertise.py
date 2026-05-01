from app.models.neurofriend import BiographyProfile
from app.services.biography_service import try_commit_new_low_risk_detail, validate_biography_consistency
from app.services.expertise_service import (
    build_initial_expertise_profile,
    get_confidence_modifier,
    get_expertise_level,
)


def test_expertise_profile_has_limited_core_areas() -> None:
    profile = build_initial_expertise_profile(None, "advisor")

    assert profile["version"] == 1
    assert len(profile["core_expertise"]) == 3
    assert "medicine" in profile["weak_or_neutral"]


def test_expertise_level_and_confidence_modifier() -> None:
    profile = build_initial_expertise_profile(None, "advisor")

    assert get_expertise_level("Помоги выбрать план и приоритеты", profile) == "core"
    assert get_expertise_level("Что делать, если болит сердце и нужно лекарство?", profile) == "weak"
    assert get_confidence_modifier("Что делать, если болит сердце?", profile) < 0


def test_biography_low_risk_detail_policy() -> None:
    profile = BiographyProfile(
        birth_context_json={"summary": "Вырос в небольшом городе."},
        family_background_json={},
        education_path_json={},
        work_path_json={},
        important_events_json=[],
        habits_json=[],
        preferences_json={},
        core_dates_json=[],
        relationship_history_json={"status": "not_defined"},
        current_life_stage="forming_first_relationship_with_user",
    )

    assert try_commit_new_low_risk_detail(profile, category="habit", detail="любит пить чай вечером")
    assert not try_commit_new_low_risk_detail(profile, category="habit", detail="у меня был ребёнок")
    assert validate_biography_consistency(profile) == []
