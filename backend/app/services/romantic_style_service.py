"""v4.5 — Romantic Style Profiles: каталог, выбор стиля, контекст для LLM и мягкое обновление связи."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.neurofriend import IdentityCore
from app.models.relationship_state import InternalStateSnapshot, RelationshipModel

_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "romantic_style_catalog.json"


@lru_cache
def _raw_catalog() -> dict[str, Any]:
    with _CATALOG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def all_styles() -> list[dict[str, Any]]:
    return list(_raw_catalog().get("styles") or [])


def get_style_by_id(style_id: str) -> dict[str, Any] | None:
    sid = (style_id or "").strip().lower()
    for s in all_styles():
        if s.get("style_id") == sid:
            return s
    return None


def archetype_token_matches(allowed: list[str], archetype: str) -> bool:
    a = (archetype or "").strip().lower()
    if not a:
        return False
    allowed_l = [str(x).strip().lower() for x in allowed if x]
    if a in allowed_l:
        return True
    for token in allowed_l:
        if token and token in a:
            return True
        if token and a in token:
            return True
    return False


def styles_allowed_for_archetype(archetype: str) -> list[dict[str, Any]]:
    out = [s for s in all_styles() if archetype_token_matches(list(s.get("allowed_archetypes") or []), archetype)]
    if not out:
        gw = get_style_by_id("gentle_warm")
        return [gw] if gw else all_styles()[:1]
    return out


def validate_style_for_archetype(style_id: str, archetype: str) -> bool:
    st = get_style_by_id(style_id)
    if not st:
        return False
    return archetype_token_matches(list(st.get("allowed_archetypes") or []), archetype)


def select_initial_romantic_style(
    archetype: str,
    *,
    variation_seed: int,
    preferred_style_id: str | None,
) -> str:
    candidates = styles_allowed_for_archetype(archetype)
    if preferred_style_id and validate_style_for_archetype(preferred_style_id, archetype):
        return preferred_style_id.strip().lower()
    h = int(hashlib.sha256(f"{archetype}\x00{variation_seed}".encode()).hexdigest(), 16)
    pick = candidates[h % len(candidates)]
    return str(pick["style_id"])


def init_new_identity_core_romantic_fields(
    core: IdentityCore,
    *,
    archetype: str,
    neurofriend_id_seed: int,
    preferred_style_id: str | None = None,
) -> None:
    """Заполняет поля романтического стиля у нового IdentityCore (до commit)."""
    settings = get_settings()
    if not settings.romantic_style_profiles_enabled:
        core.romantic_style_id = None
        core.romantic_style_profile_json = None
        core.romantic_variation_seed = 0
        core.romantic_style_locked = True
        return

    seed = int(neurofriend_id_seed) % (2**31) if neurofriend_id_seed else 0
    core.romantic_variation_seed = seed
    core.romantic_style_locked = True
    sid = select_initial_romantic_style(archetype, variation_seed=seed, preferred_style_id=preferred_style_id)
    core.romantic_style_id = sid
    full = get_style_by_id(sid)
    core.romantic_style_profile_json = full or {"style_id": sid, "display_name": sid}


async def ensure_core_has_romantic_style(
    session: AsyncSession,
    core: IdentityCore,
    archetype: str,
) -> None:
    """Ленивое заполнение для старых записей после миграции."""
    if core.romantic_style_id and core.romantic_style_profile_json:
        return
    settings = get_settings()
    if not settings.romantic_style_profiles_enabled:
        return
    seed = int(core.romantic_variation_seed or 0)
    if not seed:
        seed = hash(str(core.neurofriend_id)) % (2**31)
        core.romantic_variation_seed = seed
    sid = select_initial_romantic_style(archetype, variation_seed=seed, preferred_style_id=None)
    core.romantic_style_id = sid
    core.romantic_style_profile_json = get_style_by_id(sid) or {"style_id": sid}
    await session.flush()


def sync_romantic_phase_from_bond(rel: RelationshipModel) -> None:
    bt = rel.bond_type or "platonic"
    t = float(rel.romantic_tension_score or 0.0)
    i = float(rel.emotional_intimacy_score or 0.0)
    a = float(rel.affection_score or 0.35)
    if bt in ("platonic", "warm_acquaintance"):
        rel.romantic_phase = "light_interest" if t >= 0.22 or i >= 0.28 else "none"
    elif bt == "warm_friendship":
        rel.romantic_phase = "warm_interest"
    elif bt == "emotional_close":
        rel.romantic_phase = "deepening_attachment" if i >= 0.44 and a >= 0.45 else "mutual_flirt"
    elif bt == "romantic_soft":
        rel.romantic_phase = "romantic_attached"
    else:
        rel.romantic_phase = "warm_interest"


def apply_post_turn_relationship_styling(
    rel: RelationshipModel,
    *,
    romantic_profile: dict[str, Any] | None,
    romantic_sig: float,
    romance_blocked: bool,
    boundary_mode: str,
) -> None:
    """Обновляет фазы и накопители v4.5 на связи после одного хода Stage C."""
    settings = get_settings()
    if not settings.romantic_style_profiles_enabled:
        return

    sync_romantic_phase_from_bond(rel)

    axes = (romantic_profile or {}).get("core_axes") or {}
    dct = float(axes.get("direct_confession_tendency") or 0.4)

    cr = float(rel.confession_readiness or 0.08)
    fh = float(rel.flirt_history_score or 0.1)
    if not romance_blocked:
        cr = min(1.0, cr + romantic_sig * dct * 0.014)
        fh = min(1.0, fh + romantic_sig * 0.018)
    else:
        cr = max(0.0, cr - 0.012)
        fh = max(0.0, fh - 0.006)

    rel.confession_readiness = cr
    rel.flirt_history_score = fh

    bs = float(rel.boundary_safety_score or 0.7)
    tr = float(rel.trust or 0.5)
    cm = float(rel.conflict_memory_score or 0.0)
    rel.safety_for_vulnerability = max(0.0, min(1.0, bs * 0.4 + tr * 0.35 + (1.0 - cm) * 0.25))

    tense = float(rel.romantic_tension_score or 0.0)
    if romance_blocked or boundary_mode in {"cooldown", "clear_boundary"}:
        rel.romantic_misalignment_score = max(0.0, min(1.0, float(rel.romantic_misalignment_score or 0.0) * 0.92))
    else:
        mis = max(0.0, romantic_sig * 0.55 - tense * 0.4)
        rel.romantic_misalignment_score = max(0.0, min(1.0, mis * 0.35 + float(rel.romantic_misalignment_score or 0.0) * 0.65))


def compute_style_snapshot_fields(
    *,
    previous: InternalStateSnapshot | None,
    rel: RelationshipModel | None,
    romantic_profile: dict[str, Any] | None,
    user_text: str,
    loneliness: float,
    hurt: float,
    boundary_alert: float,
) -> dict[str, float]:
    """Эпизодические поля снимка, окрашенные профилем стиля (v4.5)."""
    settings = get_settings()
    if not settings.romantic_style_profiles_enabled or not romantic_profile:
        return {
            "jealousy_activation": float(getattr(previous, "jealousy_activation", 0.0) or 0.0) * 0.88,
            "vulnerability_pressure": min(1.0, boundary_alert * 0.5 + hurt * 0.45),
            "distance_pain": min(1.0, loneliness * 0.6),
            "desire_for_reassurance": min(1.0, hurt * 0.55 + boundary_alert * 0.2),
        }

    axes = romantic_profile.get("core_axes") or {}
    jealousy_base = float(axes.get("jealousy_tendency") or 0.35)
    dist_ret = float(axes.get("distance_retention") or 0.5)

    t = (user_text or "").lower()
    jealousy_spike = 0.0
    if any(w in t for w in ("ревну", "ревность", "с кем ты", "кто она", "кто он ", "измен", "брос")):
        jealousy_spike = 0.85

    prev_j = float(getattr(previous, "jealousy_activation", 0.0) or 0.0)
    j = min(1.0, prev_j * 0.86 + jealousy_spike * jealousy_base * 0.22)

    vp = min(1.0, boundary_alert * 0.52 + hurt * 0.48)
    dp = min(1.0, float(loneliness) * (0.28 + dist_ret * 0.5))
    safe_v = float(rel.safety_for_vulnerability) if rel else 0.55
    dfr = min(1.0, hurt * 0.48 + max(0.0, 1.0 - safe_v) * 0.38 + float(loneliness) * 0.2 * dist_ret)

    return {
        "jealousy_activation": round(j, 4),
        "vulnerability_pressure": round(vp, 4),
        "distance_pain": round(dp, 4),
        "desire_for_reassurance": round(dfr, 4),
    }


def build_llm_romantic_style_block(
    core: IdentityCore | None,
    rel: RelationshipModel | None,
    state: InternalStateSnapshot | None,
) -> str:
    """Текст для system prompt: профиль стиля + фаза + ограничения безопасности."""
    settings = get_settings()
    if not settings.romantic_style_profiles_enabled or not core:
        return ""

    profile = core.romantic_style_profile_json
    if not profile or not core.romantic_style_id:
        return ""

    sid = core.romantic_style_id
    name = profile.get("display_name") or sid
    desc = str(profile.get("description") or "").strip()
    markers = profile.get("behavior_markers") or {}
    safety = profile.get("safety_constraints") or {}
    axes = profile.get("core_axes") or {}

    lines = [
        f"Романтический стиль поведения (устойчивый v4.5, не менять на ходу): «{name}» (`{sid}`).",
        f"Кратко: {desc}" if desc else "",
        "Оси (0..1, ориентир для тона, не озвучивать числа пользователю напрямую): "
        f"открытость≈{float(axes.get('romantic_openness', 0.5)):.2f}, темп≈{float(axes.get('romantic_pace', 0.5)):.2f}, "
        f"флирт≈{float(axes.get('flirt_intensity', 0.5)):.2f}, удержание дистанции≈{float(axes.get('distance_retention', 0.5)):.2f}, "
        f"игривость≈{float(axes.get('playfulness', 0.5)):.2f}, прямизна признания≈{float(axes.get('direct_confession_tendency', 0.5)):.2f}.",
        "Маркеры (соблюдай в репликах, без ярлыков и карикатуры): "
        + ", ".join(f"{k}={v}" for k, v in list(markers.items())[:6]),
    ]

    if safety:
        lines.append(
            "Безопасность: не унижать; не использовать холод как наказание; "
            f"манипулятивный перегиб держать ниже {float(safety.get('max_manipulation_intensity', 0.25)):.2f}; "
            "не эскалировать интимность без взаимных сигналов и уровня связи."
        )

    if rel:
        lines.append(
            f"Фаза романтической динамики: {rel.romantic_phase or 'none'}; "
            f"готовность к признанию≈{float(rel.confession_readiness or 0):.2f}; "
            f"флирт-история≈{float(rel.flirt_history_score or 0):.2f}; "
            f"безопасность для уязвимости≈{float(rel.safety_for_vulnerability or 0):.2f}; "
            f"рассинхрон сигналов≈{float(rel.romantic_misalignment_score or 0):.2f}."
        )

    if state:
        lines.append(
            f"Эпизодические тона (снимок): ревность≈{float(getattr(state, 'jealousy_activation', 0)):.2f}, "
            f"давление уязвимости≈{float(getattr(state, 'vulnerability_pressure', 0)):.2f}, "
            f"боль дистанции≈{float(getattr(state, 'distance_pain', 0)):.2f}, "
            f"потребность в успокоении≈{float(getattr(state, 'desire_for_reassurance', 0)):.2f}."
        )

    return "\n".join(x for x in lines if x).strip()


def extend_llm_system_prompt(
    system: str,
    core: IdentityCore | None,
    rel: RelationshipModel | None,
    state: InternalStateSnapshot | None,
) -> str:
    block = build_llm_romantic_style_block(core, rel, state)
    if not block:
        return system
    return system + "\n\n### Слой романтического стиля (v4.5)\n" + block
