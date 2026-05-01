from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.event_log import EventLog
from app.models.memory_item import MemoryItem
from app.models.neurofriend import NeuroFriendProfile
from app.models.user import User
from app.services.memory_consolidation import run_consolidation_for_neurofriend, score_event_importance


def test_score_event_importance_promotes_personal_emotional_content() -> None:
    neutral = score_event_importance("ок", event_type="text_message_in")
    important = score_event_importance("мне важно, запомни: я очень рад этому", event_type="text_message_in")

    assert important > neutral


@pytest.mark.asyncio
async def test_run_consolidation_creates_memory_items_and_summary() -> None:
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
            nf = NeuroFriendProfile(
                user_id=user.id,
                name="Test",
                archetype="companion",
                identity_locked=True,
            )
            session.add(nf)
            await session.flush()
            session.add(
                EventLog(
                    neurofriend_id=nf.id,
                    event_type="text_message_in",
                    source="test",
                    normalized_payload_json={"text": "Запомни: мне важно пить чай вечером."},
                )
            )
            await session.flush()

            result = await run_consolidation_for_neurofriend(session, nf.id)
            await session.commit()

            assert result["created_memory_items"] == 1
            assert result["created_summary"] is True
            rows = (await session.execute(MemoryItem.__table__.select())).all()
            assert len(rows) == 2
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
