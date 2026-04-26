from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import httpx


def _ok(response: httpx.Response, label: str) -> Any:
    if response.status_code >= 400:
        raise RuntimeError(f"{label} failed: {response.status_code} {response.text}")
    print(f"OK {label}: {response.status_code}")
    if response.content:
        return response.json()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="NeuroFriend full-stack HTTP smoke test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--tts", action="store_true", help="Also call /v1/perception/tts.")
    parser.add_argument("--voice-file", type=Path, help="Optional WAV/MP3 file for /v1/perception/audio.")
    parser.add_argument("--initiative-key", help="Optional X-Initiative-Sweep-Key for internal sweep.")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    with httpx.Client(base_url=base, timeout=120.0) as client:
        _ok(client.get("/health"), "root health")
        _ok(client.get("/v1/health"), "v1 health")
        presets = _ok(client.get("/v1/meta/personality-presets"), "personality presets")
        if not presets:
            raise RuntimeError("No presets returned")
        preset = presets[0]

        created = _ok(
            client.post(
                "/v1/neurofriends",
                json={
                    "name": preset.get("suggested_name") or "Smoke",
                    "archetype": preset["archetype"],
                    "selected_preset_id": preset["id"],
                    "personalization": {
                        "softness_delta": 0.0,
                        "directness_delta": 0.0,
                        "initiative_delta": 0.0,
                        "emotionality_delta": 0.0,
                        "humor_delta": 0.0,
                        "reply_length_preference": "medium",
                        "closeness_preference": "warm_equal",
                    },
                    "identity_lock_confirmed": True,
                },
            ),
            "create neurofriend",
        )
        neurofriend_id = created["id"]

        _ok(
            client.post(
                f"/v1/conversations/{neurofriend_id}/messages",
                json={"text": "Smoke test: проверь связность, память и стиль."},
            ),
            "send text message",
        )
        _ok(client.get(f"/v1/conversations/{neurofriend_id}/threads/active/messages"), "active messages")
        _ok(client.get(f"/v1/neurofriends/{neurofriend_id}/debug/events"), "debug events")
        _ok(client.get(f"/v1/neurofriends/{neurofriend_id}/debug/relationships/primary"), "debug relationship")
        _ok(client.get(f"/v1/neurofriends/{neurofriend_id}/debug/biography"), "debug biography")
        _ok(client.get(f"/v1/neurofriends/{neurofriend_id}/debug/expertise"), "debug expertise")
        _ok(client.get(f"/v1/neurofriends/{neurofriend_id}/initiative/status"), "initiative status")

        if args.tts:
            _ok(
                client.post(
                    "/v1/perception/tts",
                    json={"neurofriend_id": neurofriend_id, "text": "Короткая проверка озвучки."},
                ),
                "tts",
            )

        if args.voice_file:
            with args.voice_file.open("rb") as f:
                _ok(
                    client.post(
                        "/v1/perception/audio",
                        data={"neurofriend_id": neurofriend_id},
                        files={"audio": (args.voice_file.name, f, "application/octet-stream")},
                    ),
                    "voice audio",
                )

        if args.initiative_key:
            _ok(
                client.post("/v1/internal/initiative/sweep", headers={"X-Initiative-Sweep-Key": args.initiative_key}),
                "initiative sweep",
            )

    print("Full-stack smoke completed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
