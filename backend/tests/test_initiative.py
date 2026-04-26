from app.services.initiative_service import compute_readiness, in_quiet_hours_for_timezone, in_quiet_hours_utc


def test_quiet_hours_span_midnight() -> None:
    from datetime import datetime, timezone

    # 23:00 UTC — внутри 22–7
    assert in_quiet_hours_utc(datetime(2026, 4, 13, 23, 0, tzinfo=timezone.utc), start_hour=22, end_hour=7)
    # 10:00 UTC — днём тихих часов нет
    assert not in_quiet_hours_utc(datetime(2026, 4, 13, 10, 0, tzinfo=timezone.utc), start_hour=22, end_hour=7)


def test_readiness_zero_when_quiet() -> None:
    assert (
        compute_readiness(
            gap_hours=48.0,
            warmth=1.0,
            in_quiet=True,
            min_gap_h=4.0,
            strong_gap_h=24.0,
        )
        == 0.0
    )


def test_readiness_grows_with_gap() -> None:
    a = compute_readiness(
        gap_hours=5.0,
        warmth=0.5,
        in_quiet=False,
        min_gap_h=4.0,
        strong_gap_h=24.0,
    )
    b = compute_readiness(
        gap_hours=30.0,
        warmth=0.5,
        in_quiet=False,
        min_gap_h=4.0,
        strong_gap_h=24.0,
    )
    assert b > a


def test_quiet_hours_use_user_timezone() -> None:
    from datetime import datetime, timezone

    # 19:00 UTC is 23:00 in Europe/Moscow, inside 22-7 local quiet hours.
    assert in_quiet_hours_for_timezone(
        datetime(2026, 4, 13, 19, 0, tzinfo=timezone.utc),
        timezone_name="Europe/Moscow",
        start_hour=22,
        end_hour=7,
    )
