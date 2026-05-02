# Текущее состояние

**Дата актуализации:** 2026-05-02 (v4.4 tracked events + repair initiative; см. `docs/SRS/NeuroFriend_Addendum_v4_4_Repair_And_Tracked_Events (1).md`)

## Репозиторий

- **Backend (FastAPI):** `backend/` — PostgreSQL, Alembic до ревизии **`20260502_8`** (v4.4: `tracked_events`, `tracked_event_reminders`, поля repair/conflict в snapshot/relationship), эндпоинты `/health`, `/v1/meta/personality-presets`, `/v1/neurofriends`, **`GET/PATCH .../tracked-events`**, **`GET .../conflicts/active`**, `/v1/perception/audio`, **`/v1/perception/tts`**, `/v1/conversations/...`, debug. Ответы LLM учитывают транскрипт, пресет, biography/expertise, boundary, Stage C, **контекст отслеживаемых событий и repair после конфликта** (при включённых флагах).
- **Инфраструктура:** `infra/docker-compose.yml` (опционально Postgres в контейнере; **для разработки достаточно локального PostgreSQL на хосте** — см. `infra/README.md`). Redis/Qdrant в compose по необходимости. Сборка Docker-образа backend ранее не проверялась (daemon мог быть недоступен).
- **Клиент:** `mobile/` — Flutter: `go_router`; onboarding в `lib/features/onboarding/` с preview пресета (**в т.ч. чипы тем из `expertise_profile`**); в чате **«О персонаже»** (`GET .../character-preview`). Лента чата, голос/текст, hands-free «слушать имя», **инспектор с русскими подписями bond и шкалами Stage C**; плашка обработки голоса. Стек см. `mobile/README.md`.
- Память проекта: `docs/ai/`.

## SRS

- Требования изучены и сведены в `PROJECT_OVERVIEW.md`, `ARCHITECTURE.md`, `DECISIONS.md`.
- Исходные файлы SRS лежат вне этого каталога: `E:\1_MyProjects\1_Human_robofriend\SRS\` (или актуальный путь без `!` в имени папки).

## Сборка и тесты

- Backend: `pip install -e ".[dev]"` в `backend/`, затем **`alembic upgrade head`**, `python -m pytest tests/ -q` (последняя проверка **2026-05-02:** **62 passed**).
- Перед запуском API: **локальный PostgreSQL** (рекомендуется), `alembic upgrade head`, `OPENAI_API_KEY`; для семантической памяти — поднять **Qdrant** (`infra/docker-compose.yml` сервис `qdrant` или локально порт 6333) и при необходимости выставить `QDRANT_URL`.

### Переменные окружения (Stage C и смежное)

Имена соответствуют полям в `backend/app/core/config.py` (Pydantic Settings: **верхний регистр**, подчёркивания).

| Переменная | По умолчанию | Назначение |
|------------|----------------|------------|
| `ROMANTIC_DYNAMICS_ENABLED` | `true` | Включает обновление affection / romantic interest / bond и контекст в оркестраторе. |
| `ROMANTIC_SIGNAL_CLASSIFIER_LLM_ENABLED` | **`true`** | Дополнительный Chat Completions JSON `intensity` 0..1 для романтического сигнала; смешивается с эвристикой (`max`). Без `OPENAI_API_KEY` шаг пропускается. Для отключения (латентность/стоимость): `false`. |
| `STAGE_C_TTS_PROSODY_ENABLED` | `true` | Параметр **`speed`** для OpenAI TTS по `bond_type` основного отношения; в meta ответа может быть `tts_speed`. |

### Переменные окружения (v4.4 tracked events + repair)

| Переменная | По умолчанию | Назначение |
|------------|----------------|------------|
| `TRACKED_EVENTS_ENABLED` | `true` | LLM-детект кандидатов событий из входящих реплик и сохранение `TrackedEvent`. |
| `EVENT_CLARIFICATION_ENABLED` | `true` | Промпт-подсказки уточнять неполные события (черновики с `needs_clarification`). |
| `TRACKED_EVENT_REMINDERS_ENABLED` | `true` | Строки `TrackedEventReminder` и исходящие **`event_followup`** в sweep инициативы. |
| `REPAIR_INITIATIVE_ENABLED` | `true` | Исходящая **`repair_initiative`** после конфликта и паузы (тип события `repair_initiative_out`). |
| `REPAIR_READINESS_THRESHOLD` | `0.62` | Порог готовности к repair (0..1). |
| `REPAIR_INITIATIVE_GAP_HOURS_MIN` | `3` | Мин. пауза без сообщений пользователя перед repair. |
| `REPAIR_ATTEMPT_GAP_HOURS` | `18` | Мин. интервал между попытками repair. |
| `REPAIR_ATTEMPT_MAX` | `4` | Лимит попыток repair за эпизод конфликта. |

- Клиент: `flutter pub get`, затем `dart analyze lib test` — без замечаний; `flutter test` — **4 passed** (**2026-05-01**). Полная сборка зависит от окружения (Flutter, Visual Studio для Windows desktop).

## Известные ограничения (UX)

- **Голосовой ход:** между отправкой записи и ответом проходит заметное время (Whisper + LLM + TTS); базовая плашка обработки добавлена, точные стадии можно углубить позже при разбиении backend pipeline.

## Известные ограничения (качество диалога)

- Реплика вида **«Я слышу тебя. Ты сказал: «…» — расскажи чуть подробнее?»** — это **не** «характер» нейродруга, а **запасной ответ (fallback)** в `llm_orchestrator.generate_reply`, если в окружении **нет `OPENAI_API_KEY`**, вызов Chat Completions **завершился ошибкой** или модель вернула **пустой** текст. Нужны ключ на машине, где крутится `uvicorn`, и просмотр логов при сбоях.

- **Содержательное** качество беседы (глубина, уместность, опора на память и пресеты) на текущем этапе **не является целевой полировкой**: инфраструктура и контур важнее; тонкая настройка промптов и поведения — **по мере готовности остального** и по `ROADMAP.md` / `TODO.md`.

- В ленте чата сообщения отображаются как **выделяемый текст** (`SelectableText`), чтобы можно было **копировать** реплики без скриншотов.

## План реализации

- Детальный поэтапный план: `docs/ai/ROADMAP.md` (голос Whisper+TTS в приоритете, чат как дубликат с лимитом 500 и архивом + 10 сообщений carryover, UI отношений/событий для отладки).
- **Следующие конкретные шаги и бэклог:** `docs/ai/TODO.md`.
- Addendum v4.3 добавлен в единый план как безопасное расширение текущей архитектуры. Stage A (biography + expertise) реализован первой итерацией: `BiographyProfile`, `BiographyService`, `expertise_profile_json`, `ExpertiseService`, debug API, orchestrator context.
- Full-stack HTTP smoke: `python scripts/full_stack_smoke.py --base-url http://127.0.0.1:8000` после `alembic upgrade head`; 2026-04-26 базовый прогон успешно прошёл health, presets, create, text message, debug endpoints, initiative status.
- Память/инициатива: добавлен SQL-слой `MemoryItem`, daily consolidation из `EventLog` в memory items + semantic summary, decay/access score, internal endpoint `/v1/internal/memory/consolidate`, timezone-aware quiet hours, `scripts/initiative_worker.py`, polling чата в Flutter.
- Stage B conflict/boundaries: добавлен `boundary_response_enabled`, поля conflict/boundary в `InternalStateSnapshot` и `RelationshipModel`, `BoundaryResponseService`, подавление инициативы при конфликте, boundary context в orchestrator, анти-лесть в naturalness prompt.
- Voice participants/wake MVP: `ConversationParticipant`, `speaker_recognition_enabled`, `voice_addressing_enabled`, распознавание первого/нового голоса через `wav_acoustic_mvp`, сохранение имени при самопредставлении, speaker metadata в voice events/messages, `/debug/participants`, backend `wake_check` policy, `playback_guard_text` + recent assistant history guard против self-echo, STT hallucination guard на тишине/YouTube-фразах и Flutter hands-free режим "слушать имя" с возможностью перебить TTS. Onboarding показывает мягкое предупреждение при возможном mismatch имени и gender-style манеры.
- v4.3 Stage C (романтическая/межличностная динамика): флаг `romantic_dynamics_enabled`; поля `affection`, `romantic_interest`, `flirt_comfort`, `emotional_intimacy` в снимке состояния; в отношениях — `bond_type`, `affection_score`, `romantic_tension_score`, `emotional_intimacy_score`; сервис `attachment_dynamics_service`; **`romantic_signal_classifier_llm_enabled`** (по умолчанию **вкл.**; см. таблицу env выше) + `romantic_signal_classifier.py` (LLM JSON intensity, max с эвристикой); **`stage_c_tts_prosody_enabled`** — `speed` в OpenAI TTS по `bond_type` (`tts_prosody.py`); контекст в `generate_reply` и `generate_initiative_ping`; Alembic `20260426_7`.
- Инспектор Flutter / debug API: карточка отношений — русские подписи **`bond_type`**, шкалы affection / emotional intimacy / romantic tension, блок конфликта/границ; голосовые участники; `PATCH .../debug/participants/{participant_id}` (имя, согласие; при `declined` backend не смешивает MVP-отпечаток).
- Память: `retrieve_snippets` при переданной DB-сессии подмешивает топ фрагментов из **SQL `memory_items`** (ранг importance×access×(1−decay) + пересечение слов с запросом) рядом с **Qdrant**; флаги `SQL_MEMORY_RETRIEVAL_ENABLED`, `SQL_MEMORY_TOP_K`, `SQL_MEMORY_CANDIDATE_POOL`. Добавлены `run_consolidation_all_neurofriends`, `POST /v1/internal/memory/consolidate-all` (тот же секрет, что sweep), флаг воркера `scripts/initiative_worker.py --consolidate-memory-first`.
- **v4.4 repair + tracked events:** таблицы `tracked_events`, `tracked_event_reminders`; поля конфликта/repair в snapshot и `relationship_models`; детект событий LLM + уточнение в промпте; sweep инициативы: due reminder → **repair_initiative_out** → обычная инициатива; API `GET .../conflicts/active`, CRUD tracked-events; Alembic `20260502_8`. SRS: `docs/SRS/NeuroFriend_Addendum_v4_4_Repair_And_Tracked_Events (1).md`.

## Следующий логичный шаг

- Voice participants: embeddings/voiceprint, diarization, echo/VAD, merge участников.
- Точная topic classification / расширение алиасов экспертизы по мере данных.
- Scheduler инициативы, push.
