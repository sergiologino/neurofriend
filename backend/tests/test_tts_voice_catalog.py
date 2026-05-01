from app.services.tts_voice_catalog import (
    bucket_from_gender_style,
    default_voice_for_gender,
    is_valid_voice_for_gender,
    normalize_voice_choice,
    voices_for_bucket,
)


def test_default_by_gender() -> None:
    assert default_voice_for_gender("masculine") == "onyx"
    assert default_voice_for_gender("feminine") == "nova"
    assert default_voice_for_gender("neutral") == "alloy"
    assert default_voice_for_gender(None) == "alloy"


def test_strict_bucket_validation() -> None:
    assert is_valid_voice_for_gender("onyx", "masculine") is True
    assert is_valid_voice_for_gender("alloy", "masculine") is False
    assert is_valid_voice_for_gender("nova", "feminine") is True
    assert is_valid_voice_for_gender("onyx", "feminine") is False
    assert is_valid_voice_for_gender("alloy", "neutral") is True


def test_normalize_invalid_falls_back() -> None:
    assert normalize_voice_choice("invalid", "masculine") == "onyx"
    assert normalize_voice_choice(None, "feminine") == "nova"


def test_voices_for_bucket_counts() -> None:
    assert len(voices_for_bucket("masculine")) >= 1
    assert len(voices_for_bucket("feminine")) >= 1
    assert len(voices_for_bucket("neutral")) >= 1
    for v in voices_for_bucket("masculine"):
        assert v["gender"] == "masculine"


def test_bucket_from_gender_style() -> None:
    assert bucket_from_gender_style("Masculine") == "masculine"
    assert bucket_from_gender_style(None) == "neutral"
