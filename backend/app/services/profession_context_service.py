"""v4.6 — эвристики домена и профессии (лексика, самоописание)."""

from __future__ import annotations

import re

# Домен → маркеры (нижний регистр). Охват — иллюстративный; без вывода с одного слова.
DOMAIN_LEXICON: dict[str, list[str]] = {
    "software_engineering": [
        "деплой",
        "прод",
        "production",
        "баг",
        "фича",
        "рефакторинг",
        "рефактор",
        "api",
        "миграция",
        "коммит",
        "пулл",
        "репозиторий",
        "ci",
        "cd",
        "devops",
        "backend",
        "фронт",
        "kubernetes",
        "docker",
        "костыль",
        "техдолг",
        "скрам",
        "спринт",
    ],
    "machining": [
        "станок",
        "токарн",
        "фрезер",
        "допуск",
        "резец",
        "подач",
        "биение",
        "проход",
        "зажим",
        "шпиндель",
        "люфт",
        "шлифов",
    ],
    "medicine": [
        "анамнез",
        "симптом",
        "диагноз",
        "протокол",
        "назначен",
        "терапия",
        "стационар",
        "анализ",
        "узи",
        "мрт",
    ],
    "law": [
        "договор",
        "иск",
        "норма",
        "закон",
        "су",
        "судебн",
        "должник",
        "кредитор",
        "юрист",
        "адвокат",
    ],
    "design": [
        "макет",
        "ui",
        "ux",
        "композиц",
        "типограф",
        "прототип",
        "фигма",
        "референс",
    ],
    "sculpture": [
        "скульпт",
        "пластик",
        "фактура",
        "форма",
        "объём",
        "масса",
        "гипс",
        "лепнин",
    ],
    "construction": [
        "объект",
        "смета",
        "прораб",
        "бетон",
        "монтаж",
        "чертеж",
        "проект",
    ],
    "sales": [
        "клиент",
        "сделк",
        "воронк",
        "лид",
        "кп",
        "менеджер по продаж",
        "холодн",
    ],
    "finance": [
        "бухгалтер",
        "отчётность",
        "налог",
        "аудит",
        "баланс",
        "кредит",
        "инвест",
    ],
}

# Прямое самоописание → домен
_DIRECT_REPORT_REGEX: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\bя\s+программист", re.I), "software_engineering", "software_engineer"),
    (re.compile(r"\bя\s+(?:разработчик|девелопер|кодер)", re.I), "software_engineering", "software_engineer"),
    (re.compile(r"\bя\s+токар", re.I), "machining", "machinist"),
    (re.compile(r"\bя\s+(?:врач|медик)", re.I), "medicine", "physician"),
    (re.compile(r"\bя\s+юрист", re.I), "law", "lawyer"),
    (re.compile(r"\bя\s+конструктор", re.I), "machining", "engineer_mechanical"),
    (re.compile(r"\bя\s+дизайнер", re.I), "design", "designer"),
    (re.compile(r"\bя\s+скульптор", re.I), "sculpture", "sculptor"),
]


def detect_domain_markers(text: str) -> dict[str, list[str]]:
    """Какие термины каких доменов встретились в реплике."""
    t = (text or "").lower()
    out: dict[str, list[str]] = {}
    for domain, terms in DOMAIN_LEXICON.items():
        hits = [w for w in terms if w in t]
        if hits:
            out[domain] = hits
    return out


def direct_self_report_hits(text: str) -> list[tuple[str, str]]:
    """[(domain_name, profession_key), ...] — прямое сообщение о профессии."""
    found: list[tuple[str, str]] = []
    for rx, domain, prof in _DIRECT_REPORT_REGEX:
        if rx.search(text or ""):
            found.append((domain, prof))
    return found


def get_domain_lexicon_for_context(domain: str, *, top_terms_from_vocab: list[str], max_terms: int = 14) -> list[str]:
    """Базовый глоссарий + термины пользователя по этому домену."""
    base = DOMAIN_LEXICON.get(domain, [])[:8]
    merged: list[str] = []
    seen: set[str] = set()
    for w in list(base) + top_terms_from_vocab:
        k = w.lower().strip()
        if k and k not in seen:
            seen.add(k)
            merged.append(w.strip())
        if len(merged) >= max_terms:
            break
    return merged


def infer_thinking_style(domain: str) -> str:
    m = {
        "software_engineering": "process",
        "machining": "craft",
        "medicine": "diagnostic",
        "law": "normative",
        "design": "visual",
        "sculpture": "artistic",
        "construction": "process",
        "sales": "entrepreneurial",
        "finance": "normative",
    }
    return m.get(domain, "general")


def merge_vocab_counts(existing: dict[str, int], new_terms: list[str]) -> dict[str, int]:
    out = dict(existing or {})
    for term in new_terms:
        k = str(term).lower().strip()
        if not k:
            continue
        out[k] = int(out.get(k, 0)) + 1
    return out
