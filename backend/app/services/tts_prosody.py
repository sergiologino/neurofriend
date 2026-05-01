"""Stage C — лёгкая модуляция TTS по типу связи (bond_type), без смены голоса."""

from __future__ import annotations


def tts_speed_for_bond_type(bond_type: str | None) -> float:
    """
    Чуть медленнее при более тёплой связи (OpenAI TTS `speed`, обычно 0.25–4.0, default 1.0).
    Возвращает значение в безопасном диапазоне для API.
    """
    b = (bond_type or "platonic").strip().lower()
    table = {
        "platonic": 1.02,
        "warm_acquaintance": 1.02,
        "warm_friendship": 1.0,
        "emotional_close": 0.97,
        "romantic_soft": 0.93,
    }
    s = float(table.get(b, 1.0))
    return max(0.25, min(1.4, s))
