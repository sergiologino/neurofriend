from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_session
from app.core.database import Base
from app.main import app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def setup() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def teardown() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    async def fake_intro(*args, **kwargs) -> str:
        return "Привет. Я тестовый нейродруг и уже готов к разговору."

    async def fake_reply(*args, **kwargs) -> str:
        user_text = kwargs.get("user_text", "")
        return f"Тестовый ответ на: {user_text}"

    async def fake_retrieve(*args, **kwargs) -> list[str]:
        return []

    async def fake_index(*args, **kwargs) -> None:
        return None

    asyncio.run(setup())
    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr("app.services.llm_orchestrator.generate_intro_message", fake_intro)
    monkeypatch.setattr("app.api.v1.routes.conversations.generate_reply", fake_reply)
    monkeypatch.setattr("app.api.v1.routes.conversations.retrieve_snippets", fake_retrieve)
    monkeypatch.setattr("app.api.v1.routes.conversations.index_dialogue_turn", fake_index)
    monkeypatch.setattr("app.api.v1.routes.neurofriends.index_intro_only", fake_index)

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        asyncio.run(teardown())


def test_create_neurofriend_then_text_message_and_history(client: TestClient) -> None:
    created = client.post(
        "/v1/neurofriends",
        json={
            "name": "Марина",
            "archetype": "adventurous_warm",
            "selected_preset_id": "warm_companion",
            "personalization": {
                "softness_delta": 0.04,
                "reply_length_preference": "medium",
                "closeness_preference": "warm_equal",
            },
            "identity_lock_confirmed": True,
        },
    )
    assert created.status_code == 200
    nf = created.json()
    assert nf["identity_locked"] is True
    assert nf["first_intro_message"]

    reply = client.post(
        f"/v1/conversations/{nf['id']}/messages",
        json={"text": "Привет, проверим связность."},
    )
    assert reply.status_code == 200
    assert reply.json()["reply_text"] == "Тестовый ответ на: Привет, проверим связность."

    history = client.get(f"/v1/conversations/{nf['id']}/threads/active/messages")
    assert history.status_code == 200
    messages = history.json()["messages"]
    assert [m["role"] for m in messages] == ["assistant", "user", "assistant"]
    assert messages[0]["source"] == "bootstrap"
    assert messages[1]["source"] == "text_fallback"

    biography = client.get(f"/v1/neurofriends/{nf['id']}/debug/biography")
    assert biography.status_code == 200
    assert biography.json()["snapshot"]["current_life_stage"] == "forming_first_relationship_with_user"

    expertise = client.get(f"/v1/neurofriends/{nf['id']}/debug/expertise")
    assert expertise.status_code == 200
    assert expertise.json()["profile"]["core_expertise"]


def test_personalization_outside_preset_range_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/neurofriends",
        json={
            "name": "Марина",
            "archetype": "companion",
            "selected_preset_id": "warm_companion",
            "personalization": {"softness_delta": -0.5},
            "identity_lock_confirmed": True,
        },
    )
    assert response.status_code == 400
    assert "allowed preset range" in response.json()["detail"]


def test_thread_rollover_keeps_carryover(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.chat_thread_service.get_settings",
        lambda: SimpleNamespace(chat_max_messages_per_thread=2, chat_carryover_messages=1),
    )

    created = client.post(
        "/v1/neurofriends",
        json={
            "name": "Олег",
            "archetype": "direct_pragmatic",
            "selected_preset_id": "clear_advisor",
            "identity_lock_confirmed": True,
        },
    )
    assert created.status_code == 200
    nf = created.json()

    reply = client.post(
        f"/v1/conversations/{nf['id']}/messages",
        json={"text": "Нужен rollover."},
    )
    assert reply.status_code == 200

    archived = client.get(f"/v1/conversations/{nf['id']}/threads/archived")
    assert archived.status_code == 200
    assert len(archived.json()["threads"]) == 1

    active = client.get(f"/v1/conversations/{nf['id']}/threads/active/messages")
    assert active.status_code == 200
    messages = active.json()["messages"]
    assert len(messages) == 3
    assert messages[0]["role"] == "assistant"
    assert messages[-2]["text"] == "Нужен rollover."
