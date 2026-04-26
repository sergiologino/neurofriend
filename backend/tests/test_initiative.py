import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.neurofriend import NeuroFriendProfile
from app.models.relationship_state import RelationshipModel
from app.models.user import User
from app.services.initiative_service import (
    compute_readiness,
    get_boundary_cooldown_factor,
    in_quiet_hours_for_timezone,
    in_quiet_hours_utc,
)


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


@pytest.mark.asyncio
async def test_boundary_cooldown_suppresses_initiative() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        async with session_factory() as session:
            user = User(display_name="user")
            session.add(user)
            await session.flush()
            nf = NeuroFriendProfile(user_id=user.id, name="Test", archetype="companion", identity_locked=True)
            session.add(nf)
            await session.flush()
            session.add(
                RelationshipModel(
                    neurofriend_id=nf.id,
                    person_ref="user_main",
                    conflict_memory_score=0.7,
                    boundary_safety_score=0.3,
                )
            )
            await session.flush()
            assert await get_boundary_cooldown_factor(session, nf.id) == 0.0
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
