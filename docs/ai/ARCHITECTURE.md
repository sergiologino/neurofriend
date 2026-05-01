# NeuroFriend — архитектура

## Решение по платформам (веб + мобильные + десктоп в перспективе)

| Слой | Выбор | Обоснование |
|------|--------|----------------|
| **Клиент** | **Flutter** (iOS, Android, **Web**; при необходимости позже desktop) | Один UI/логика для мобильных и веб-версии; SRS изначально задаёт Flutter + поэтапное расширение; меньше дублирования, чем отдельный React + отдельный mobile. |
| **Backend** | **Модульный монолит** FastAPI | Один деплой, чёткие доменные модули; позже возможно выделение memory/initiative/perception без переписывания с нуля. |
| **Данные** | PostgreSQL (источник истины), Redis (кэш, очереди, rate limit, таймеры), Qdrant (семантическая память), S3-совместимое хранилище для медиа | Как в SRS v4.1. |

Детали выбора зафиксированы в `DECISIONS.md`.

## Логические слои «личности» (не класть всё в prompt)

1. Identity — кто он (неизменяемый архетип + параметры в рамках допуска).
2. State — текущий аффективный снимок.
3. Memory — working / fast / deep + semantic summaries; retrieval + консолидация.
4. Relation (Bond) — модель отношений с пользователем (и при необходимости с другими персонами).
5. Perception — **голос с первых этапов** (OpenAI Whisper → текст; ответ → OpenAI TTS); текст из чата — тот же контур; зрение позже.
6. Reasoning — LLM orchestrator поверх подготовленного контекста.
7. Initiative — когда писать первым (score, политика, тишина ночью, DND).
8. Learning — социальное перенимание в границах.
9. Safety — границы тона, анти-спам, этика близости.

## Целевая структура репозитория (monorepo)

Рекомендуемая раскладка при появлении кода:

```text
Application/
  backend/           # FastAPI, доменные модули, workers, tests
  mobile/            # Flutter: общий код + mobile-конфигурации
  web/               # опционально: Flutter web entry / конфиг, если разнесение удобнее CI
  infra/             # docker-compose, позже k8s/terraform
  docs/ai/           # память проекта (этот каталог)
```

Вариант без отдельной папки `web`: единый Flutter-проект с таргетами `web`, `android`, `ios` в одном `mobile/` или `app/` — уточняется при первом коммите клиента.

## Backend — модули (из SRS)

`auth`, `users`, `neurofriend_identity`, `conversation`, `memory`, `affect`, `bond`, `perception`, `initiative`, `learning`, `media`, `llm_orchestrator`, `notifications`, `admin`, `telemetry` — в виде пакетов/папок внутри одного приложения.

## Голос и чат (уточнение к SRS)

- **Источник истины для личности и памяти** — доменные сущности и **EventLog** (и производная память), а не лента чата.
- **Голос** — основной режим: Whisper (вход) → пайплайн ответа → TTS (выход). Реализации **OpenAI** на старте, с абстракцией под смену провайдера (`DECISIONS.md`).
- **Чат** — дублирование реплик для удобства и fallback при сбое голоса; сообщения привязаны к событиям диалога где возможно.
- **Активный тред чата:** при **500 сообщениях** (суммарно user+assistant) текущий тред **архивируется**, создаётся новый активный; в него **переносятся 10 последних** сообщений предыдущего треда для непрерывности; архивы доступны для чтения.

Подробный порядок работ — `docs/ai/ROADMAP.md`.

## Ключевые интеграции

- **LLM:** OpenAI SDK (или совместимый API), оркестрация через отдельный сервис.
- **Речь:** OpenAI **Whisper** (распознавание), OpenAI **TTS** (синтез) — первая итерация; граница абстракций для замены.
- **Векторы:** Qdrant; эмбеддинги для памяти и поиска top-k с rerank.
- **Фоновые задачи:** Celery / Arq / RQ + Redis.
- **Клиент:** dio, Riverpod, go_router; локальный кэш Hive/Isar; запись/воспроизведение аудио; push — Firebase/OneSignal (по SRS).

## API (черновой контракт из SRS)

- `POST /v1/neurofriends` — создание профиля + identity lock + первое сообщение.
- `POST /v1/conversations/{neurofriendId}/messages` — исходящий/входящий пайплайн.
- `GET /v1/neurofriends/{id}/state`, `GET .../memory/summary`, `GET .../relationships/primary`, `PATCH .../initiative-policy`.
- `POST /v1/perception/audio` — **с этапа голосового MVP** (Whisper + нормализация в событие); `POST /v1/perception/vision` — позже.
- Эндпоинты чтения для **отладочного UI:** лента событий/отношений (см. `ROADMAP.md`, этап 4).

### Межличностная динамика (addendum v4.3 Stage C)

- Накопительные метрики в `relationship_models` (`bond_type`, affection / emotional intimacy / romantic tension scores) и зеркальные поля в последнем `internal_state_snapshots`; обновление на каждом входящем тексте/транскрипте в `affect_lite.snapshot_after_user_text` при включённом `romantic_dynamics_enabled`.
- Логика медленной прогрессии и границ: `app/services/attachment_dynamics_service.py`; контекст для LLM — `romantic_prompt_context` в `generate_reply` и `generate_initiative_ping`.
- Полировка: опционально **`ROMANTIC_SIGNAL_CLASSIFIER_LLM_ENABLED`** — `romantic_signal_llm_hint()` объединяется с эвристикой (`max`); **`STAGE_C_TTS_PROSODY_ENABLED`** — модуляция `speed` синтеза по `bond_type` (`tts_prosody.py`, `speech_openai.synthesize_speech_mp3`).

### Реализованные HTTP-поверхности (backend)

- `GET /health`, `GET /v1/health`
- `POST /v1/neurofriends`, `GET /v1/neurofriends/{id}`, `GET /v1/neurofriends/{id}/character-preview` — пользовательский текстовый предпросмотр биографии и экспертизы (не debug JSON)
- `POST /v1/perception/audio` (multipart: `neurofriend_id`, `audio`)
- `POST /v1/perception/tts` (JSON: `neurofriend_id`, `text`) — TTS; при `ROMANTIC_DYNAMICS_ENABLED` и **`STAGE_C_TTS_PROSODY_ENABLED`** (default true) в ответе **`meta`** может быть **`tts_speed`** в зависимости от `bond_type` primary relationship
- `POST /v1/conversations/{neurofriend_id}/messages`, `GET .../threads/active/messages`, `GET .../threads/archived`
- `GET /v1/neurofriends/{id}/debug/events`, `GET .../debug/relationships/primary`
- `GET /v1/neurofriends/{id}/debug/participants`, `PATCH .../debug/participants/{participant_id}` — участники голоса (имя, согласие на дообучение MVP-отпечатка)
- `GET /v1/neurofriends/{id}/initiative/status` — gap, тихие часы, readiness (этап 7, отладка)
- `POST /v1/internal/initiative/sweep` — заголовок `X-Initiative-Sweep-Key` + `INITIATIVE_SWEEP_SECRET` в env; перебор профилей, генерация исходящей реплики при условиях, запись в чат и событие `initiative_message_out`
- `POST /v1/internal/memory/consolidate`, `POST /v1/internal/memory/consolidate-all` — то же для SQL memory consolidation (один профиль / все)
- `GET /v1/meta/personality-presets` — каталог пресетов для онбординга (канонический JSON: `backend/app/data/personality_presets.json`); опциональные поля `biography_preview`, `expertise_preview` для пользовательского preview до создания профиля

### Семантическая память (этап 6)

- **Qdrant** — векторное хранилище; коллекция задаётся `QDRANT_COLLECTION_SEMANTIC` (по умолчанию `neurofriend_semantic`).
- **Эмбеддинги** — OpenAI (`EMBEDDING_MODEL`, размер вектора `EMBEDDING_VECTOR_SIZE` = 1536 для `text-embedding-3-small`).
- **Индексация** — после успешного ответа (голос/текст) и при bootstrap intro; payload: текст, роль, источник, `event_id`, `neurofriend_id`.
- **SQL `memory_items`** — консолидация из `EventLog` (`memory_consolidation`), decay/access; retrieval через `sql_memory_retrieval` при вызове `retrieve_snippets(..., session=...)` совместно с Qdrant (дедуп, приоритет векторным попаданиям); выключение: `SQL_MEMORY_RETRIEVAL_ENABLED=false`.
- **Retrieval** — перед вызовом LLM; сниппеты в `generate_reply` / инициатива. При недоступности Qdrant или ключа OpenAI — деградация без падения; SQL-слой доступен при живой БД и переданной сессии.


## Пресеты личности (UI + backend)

- **Сейчас:** клиент подгружает каталог через `GET /v1/meta/personality-presets`; в JSON задаются `life_legend`, опционально **`biography_preview` / `expertise_preview`**, структура **`expertise_profile`** (`ExpertisePresetSeed`: `core_expertise`, `strong_familiarity`, `weak_or_neutral`) — при создании профиля имеет приоритет над эвристикой архетипа в `build_initial_expertise_profile`; пользователь выбирает пресет → `POST /v1/neurofriends` с `identity_lock_confirmed`. После создания пользовательский текст биографии/экспертизы доступен через **`GET /v1/neurofriends/{id}/character-preview`** (в приложении — «О персонаже»).
- **По SRS (углубление):** галерея из внешнего `neurofriend_presets.json`, персонализация в `allowed_personalization_ranges`, приём `selected_preset_id` на backend с валидацией дельт — в бэклоге.

## Наблюдаемость

Структурированные логи, метрики (latency, retrieval, стоимость prompt), Sentry — по мере внедрения (SRS).
