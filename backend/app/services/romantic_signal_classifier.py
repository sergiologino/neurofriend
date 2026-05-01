"""Опциональный LLM-буст для оценки романтического сигнала в тексте пользователя (Stage C polish)."""

from __future__ import annotations

import json

from app.core.config import get_settings
from app.services.openai_client import get_openai_client


async def romantic_signal_llm_hint(user_text: str) -> float | None:
    """
    Возвращает 0..1 или None (выключено / нет клиента / ошибка).
    Используется как верхняя граница вместе с эвристикой `evaluate_romantic_signal`.
    """
    settings = get_settings()
    if not settings.romantic_signal_classifier_llm_enabled:
        return None
    raw = (user_text or "").strip()
    if len(raw) < 2:
        return None
    client = get_openai_client()
    if not client:
        return None

    prompt = (
        "Ты классификатор. По одной реплике пользователя оцени, насколько в ней явный романтический "
        "или флиртующий посыл к собеседнику (не дружба вообще, а именно романтика/влюблённость/свидания)."
        " Верни ТОЛЬКО JSON: {\"intensity\": число от 0 до 1}.\n"
        f"Текст:\n{raw[:1200]}"
    )
    try:
        resp = await client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": "Отвечай только компактным JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=60,
            response_format={"type": "json_object"},
        )
        chunk = (resp.choices[0].message.content or "").strip()
        data = json.loads(chunk)
        val = data.get("intensity")
        if val is None:
            return None
        return max(0.0, min(1.0, float(val)))
    except Exception:
        return None
