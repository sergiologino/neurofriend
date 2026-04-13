from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_personality_presets_catalog() -> None:
    r = client.get("/v1/meta/personality-presets")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert "id" in first
    assert "title" in first
    assert "archetype" in first
    assert "description" in first
    assert "suggested_name" in first
    assert first.get("character_prompt")
    assert first.get("life_legend")
    assert first.get("gender_style")
