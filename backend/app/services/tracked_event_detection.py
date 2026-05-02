"""LLM: извлечение кандидатов отслеживаемых событий из реплики пользователя (v4.4)."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings
from app.services.openai_client import get_openai_client

logger = logging.getLogger(__name__)

ALLOWED_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "birthday",
        "flight",
        "purchase",
        "delivery",
        "deadline",
        "payment",
        "meeting",
        "booking",
        "family_event",
        "trip",
        "appointment",
        "promise",
        "follow_up_task",
        "submission",
        "renewal",
    }
)


async def detect_tracked_event_candidates(user_text: str) -> list[dict[str, Any]]:
    """Возвращает список кандидатов (dict) или [] при выключенном флаге / без клиента / ошибке."""
    settings = get_settings()
    if not settings.tracked_events_enabled:
        return []

    raw = (user_text or "").strip()
    if len(raw) < 6:
        return []

    client = get_openai_client()
    if not client:
        return []

    prompt = (
        "Ты извлекатель событий из реплики пользователя (русский). Ищи будущие или актуальные дела: "
        "день рождения, рейс, покупка, доставка, дедлайн, обещание, встреча, бронь, оплата, поездка и т.п.\n"
        "Верни ТОЛЬКО JSON: {\"candidates\": [ {...}, ... ]}. Каждый кандидат:\n"
        '{ "event_type": один из birthday flight purchase delivery deadline payment meeting booking '
        'family_event trip appointment promise follow_up_task submission renewal,\n'
        '  "title": краткий заголовок на русском,\n'
        '  "subject_person": кто затронут или null,\n'
        '  "description": кратко или null,\n'
        '  "event_time_iso": ISO8601 дата/время если явно сказано иначе null,\n'
        '  "time_precision": one of exact day_only approximate unknown,\n'
        '  "confidence": 0..1,\n'
        '  "needs_clarification": boolean,\n'
        '  "missing_fields": массив строк (например [\"event_time\"]),\n'
        '  "importance_score": 0..1,\n'
        '  "follow_up_strategy": one of single_reminder multiple_reminders soft_check_in '
        'preparation_prompt relationship_sensitive_followup }\n'
        "Если событий нет — {\"candidates\": []}.\n"
        f"Текст пользователя:\n{raw[:1800]}"
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": "Отвечай только компактным JSON без Markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=900,
            response_format={"type": "json_object"},
        )
        chunk = (resp.choices[0].message.content or "").strip()
        data = json.loads(chunk)
        raw_list = data.get("candidates") if isinstance(data, dict) else None
        if not isinstance(raw_list, list):
            return []
        out: list[dict[str, Any]] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            et = str(item.get("event_type") or "").strip().lower()
            if et not in ALLOWED_EVENT_TYPES:
                continue
            conf = float(item.get("confidence") or 0)
            if conf < 0.38:
                continue
            out.append(item)
        return out
    except Exception as e:
        logger.warning("detect_tracked_event_candidates failed: %s", e)
        return []
