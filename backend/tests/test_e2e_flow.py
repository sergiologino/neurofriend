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

    async def fake_transcribe(*args, **kwargs) -> str:
        audio_bytes = kwargs.get("audio_bytes", b"")
        if audio_bytes == b"guest voice":
            return "Меня зовут Антон"
        if audio_bytes == b"self echo":
            return "Тестовый ответ на Привет голосом"
        if audio_bytes == b"intro echo":
            return "Привет. Я тестовый нейродруг и уже готов к разговору."
        if audio_bytes == b"youtube hallucination":
            return "Thank you so much for watching!"
        return "Привет голосом"

    async def fake_tts(*args, **kwargs) -> bytes:
        return b"mp3"

    asyncio.run(setup())
    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr("app.api.v1.routes.perception.get_openai_client", lambda: object())
    monkeypatch.setattr("app.api.v1.routes.perception.speech_openai.transcribe_audio", fake_transcribe)
    monkeypatch.setattr("app.api.v1.routes.perception.speech_openai.synthesize_speech_mp3", fake_tts)
    monkeypatch.setattr("app.api.v1.routes.perception.generate_reply", fake_reply)
    monkeypatch.setattr("app.api.v1.routes.perception.retrieve_snippets", fake_retrieve)
    monkeypatch.setattr("app.api.v1.routes.perception.index_dialogue_turn", fake_index)
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

    preview = client.get(f"/v1/neurofriends/{nf['id']}/character-preview")
    assert preview.status_code == 200
    pv = preview.json()
    assert "biography_text" in pv and "expertise_text" in pv
    assert len(pv["biography_text"]) > 12
    assert "Сильные темы" in pv["expertise_text"]


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


def test_voice_flow_tracks_participants(client: TestClient) -> None:
    created = client.post(
        "/v1/neurofriends",
        json={
            "name": "Марина",
            "archetype": "warm_companion",
            "selected_preset_id": "warm_companion",
            "identity_lock_confirmed": True,
        },
    )
    assert created.status_code == 200
    nf = created.json()

    first = client.post(
        "/v1/perception/audio",
        data={"neurofriend_id": nf["id"]},
        files={"audio": ("main.wav", b"main voice", "audio/wav")},
    )
    assert first.status_code == 200
    assert first.json()["meta"]["speaker_person_ref"] == "user_main"
    assert first.json()["meta"]["addressing_required"] is False

    guest = client.post(
        "/v1/perception/audio",
        data={"neurofriend_id": nf["id"]},
        files={"audio": ("guest.wav", b"guest voice", "audio/wav")},
    )
    assert guest.status_code == 200
    assert guest.json()["meta"]["participant_kind"] == "known_guest"
    assert guest.json()["meta"]["speaker_display_name"] == "Антон"
    assert guest.json()["meta"]["addressing_required"] is True

    participants = client.get(f"/v1/neurofriends/{nf['id']}/debug/participants")
    assert participants.status_code == 200
    rows = participants.json()
    assert [row["person_ref"] for row in rows][0] == "user_main"
    assert any(row["display_name"] == "Антон" for row in rows)

    ignored = client.post(
        "/v1/perception/audio",
        data={"neurofriend_id": nf["id"], "wake_check": "true"},
        files={"audio": ("guest.wav", b"guest voice", "audio/wav")},
    )
    assert ignored.status_code == 200
    assert ignored.json()["reply_text"] == ""
    assert ignored.json()["audio_base64"] == ""
    assert ignored.json()["meta"]["addressed_to_neurofriend"] is False

    self_echo = client.post(
        "/v1/perception/audio",
        data={
            "neurofriend_id": nf["id"],
            "wake_check": "true",
            "playback_guard_text": "Тестовый ответ на Привет голосом",
        },
        files={"audio": ("echo.wav", b"self echo", "audio/wav")},
    )
    assert self_echo.status_code == 200
    assert self_echo.json()["reply_text"] == ""
    assert self_echo.json()["meta"]["self_voice_echo"] is True

    intro_echo = client.post(
        "/v1/perception/audio",
        data={"neurofriend_id": nf["id"], "wake_check": "true"},
        files={"audio": ("intro.wav", b"intro echo", "audio/wav")},
    )
    assert intro_echo.status_code == 200
    assert intro_echo.json()["reply_text"] == ""
    assert intro_echo.json()["meta"]["self_voice_echo"] is True
    assert intro_echo.json()["meta"]["matched_recent_assistant"] is True

    hallucination = client.post(
        "/v1/perception/audio",
        data={"neurofriend_id": nf["id"], "wake_check": "false"},
        files={"audio": ("silence.wav", b"youtube hallucination", "audio/wav")},
    )
    assert hallucination.status_code == 200
    assert hallucination.json()["reply_text"] == ""
    assert hallucination.json()["meta"]["stt_hallucination"] is True


def test_debug_patch_participant_display_and_consent(client: TestClient) -> None:
    created = client.post(
        "/v1/neurofriends",
        json={
            "name": "Ира",
            "archetype": "warm_companion",
            "identity_lock_confirmed": True,
        },
    )
    assert created.status_code == 200
    nf_id = created.json()["id"]

    msg = client.post(f"/v1/conversations/{nf_id}/messages", json={"text": "привет"})
    assert msg.status_code == 200

    rows = client.get(f"/v1/neurofriends/{nf_id}/debug/participants")
    assert rows.status_code == 200
    data = rows.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    pid = data[0]["id"]

    patched = client.patch(
        f"/v1/neurofriends/{nf_id}/debug/participants/{pid}",
        json={"display_name": "Основной", "consent_status": "explicit_allow"},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["display_name"] == "Основной"
    assert body["consent_status"] == "explicit_allow"

    listed = client.get(f"/v1/neurofriends/{nf_id}/debug/participants").json()
    match = next(x for x in listed if x["id"] == pid)
    assert match["display_name"] == "Основной"
    assert match["consent_status"] == "explicit_allow"
