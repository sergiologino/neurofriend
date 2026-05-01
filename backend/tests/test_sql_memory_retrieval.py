import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.memory_item import MemoryItem
from app.models.neurofriend import NeuroFriendProfile
from app.models.user import User
from app.services.semantic_memory import retrieve_snippets
from app.services.sql_memory_retrieval import merge_vector_and_sql_snippets, retrieve_sql_memory_snippets


def test_merge_prioritizes_vector_and_dedupes() -> None:
    vec = ["alpha уникальная фраза", "beta общая"]
    sql = ["beta общая", "gamma sql only"]
    merged = merge_vector_and_sql_snippets(vec, sql, max_total=10)
    assert merged[0].startswith("alpha")
    assert "beta общая" in merged
    assert merged.count("beta общая") == 1
    assert any("gamma" in x for x in merged)


@pytest.mark.asyncio
async def test_retrieve_sql_boosts_keyword_overlap() -> None:
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
            user = User(display_name="u")
            session.add(user)
            await session.flush()
            nf = NeuroFriendProfile(user_id=user.id, name="N", archetype="c", identity_locked=True)
            session.add(nf)
            await session.flush()
            session.add_all(
                [
                    MemoryItem(
                        neurofriend_id=nf.id,
                        memory_type="episodic",
                        content_text="разговор про погоду и дорогу",
                        importance_score=0.22,
                        access_score=1.0,
                        decay_score=0.0,
                    ),
                    MemoryItem(
                        neurofriend_id=nf.id,
                        memory_type="fast",
                        content_text="пользователь любит зелёный чай вечером на балконе",
                        importance_score=0.88,
                        access_score=1.0,
                        decay_score=0.0,
                    ),
                ]
            )
            await session.flush()

            out = await retrieve_sql_memory_snippets(session, nf.id, "расскажи про чай вечером", limit=2)
            assert len(out) >= 1
            assert any("чай" in x.lower() for x in out)
            assert "чай" in out[0].lower()
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.mark.asyncio
async def test_retrieve_snippets_merges_sql_when_session_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_qdrant(*args: object, **kwargs: object) -> list[str]:
        return ["векторная тема про котика"]

    monkeypatch.setattr(
        "app.services.semantic_memory._retrieve_qdrant_snippets",
        fake_qdrant,
    )
    monkeypatch.setattr(
        "app.services.semantic_memory.semantic_memory_ready",
        lambda: True,
    )

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
            user = User(display_name="u")
            session.add(user)
            await session.flush()
            nf = NeuroFriendProfile(user_id=user.id, name="N", archetype="c", identity_locked=True)
            session.add(nf)
            await session.flush()
            session.add(
                MemoryItem(
                    neurofriend_id=nf.id,
                    memory_type="episodic",
                    content_text="отдельная sql память про работу и проект нейродруг",
                    importance_score=0.95,
                    access_score=1.0,
                    decay_score=0.0,
                )
            )
            await session.flush()

            merged = await retrieve_snippets(
                neurofriend_id=nf.id,
                query_text="как продвигается проект нейродруг",
                session=session,
            )
            assert any("нейродруг" in m for m in merged)
            assert any("котик" in m for m in merged)
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.mark.asyncio
async def test_run_consolidation_all_counts_profiles() -> None:
    from app.services.memory_consolidation import run_consolidation_all_neurofriends

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
            for _ in range(2):
                user = User(display_name="u")
                session.add(user)
                await session.flush()
                nf = NeuroFriendProfile(user_id=user.id, name="N", archetype="c", identity_locked=True)
                session.add(nf)
                await session.flush()
            res = await run_consolidation_all_neurofriends(session)
            assert res["neurofriends"] == 2
            assert res["memory_items_created"] == 0
            assert len(res["details"]) == 2
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
