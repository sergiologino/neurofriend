# Текущее состояние

**Дата актуализации:** 2026-04-26 (voice wake-by-name MVP)

## Репозиторий

- **Backend (FastAPI):** `backend/` — PostgreSQL, Alembic `20260412_0001` + последующие ревизии, эндпоинты `/health`, `/v1/meta/personality-presets`, `/v1/neurofriends` (`selected_preset_id` / legacy `preset_id`, personalization deltas), `/v1/perception/audio`, **`/v1/perception/tts`** (озвучка готового текста), `/v1/conversations/...`, debug. Ответы LLM учитывают **недавний транскрипт** активного треда, **стиль пресета** (`character_prompt` в ядре), v4.3 Stage A biography/expertise, Stage B boundary context/anti-flattery, а в voice flow — speaker context.
- **Инфраструктура:** `infra/docker-compose.yml` (опционально Postgres в контейнере; **для разработки достаточно локального PostgreSQL на хосте** — см. `infra/README.md`). Redis/Qdrant в compose по необходимости. Сборка Docker-образа backend ранее не проверялась (daemon мог быть недоступен).
- **Клиент:** `mobile/` — Flutter: `go_router`, первая SRS-итерация onboarding (welcome, галерея, preview, имя/голос, personalization, identity lock, birth/intro), лента чата, голос/текст, hands-free режим "слушать имя", инспектор; при голосовом раунде показывается плашка обработки. Стек см. `mobile/README.md`.
- Память проекта: `docs/ai/`.

## SRS

- Требования изучены и сведены в `PROJECT_OVERVIEW.md`, `ARCHITECTURE.md`, `DECISIONS.md`.
- Исходные файлы SRS лежат вне этого каталога: `E:\1_MyProjects\1_Human_robofriend\SRS\` (или актуальный путь без `!` в имени папки).

## Сборка и тесты

- Backend: `pip install -e ".[dev]"` в `backend/`, затем `python -m pytest tests/ -q` (последняя проверка **2026-04-26:** **32 passed**).
- Перед запуском API: **локальный PostgreSQL** (рекомендуется), `alembic upgrade head`, `OPENAI_API_KEY`; для семантической памяти — поднять **Qdrant** (`infra/docker-compose.yml` сервис `qdrant` или локально порт 6333) и при необходимости выставить `QDRANT_URL`.
- Клиент: `flutter pub get`, затем `dart analyze lib` — без замечаний (последняя проверка **2026-04-26**). Полная сборка зависит от окружения (Flutter, Visual Studio для Windows desktop).

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

## Следующий логичный шаг

- v4.3 Stage C: romantic/interpersonal dynamics.
- Полировка voice participants: реальные speaker embeddings/voiceprint, diarization, echo cancellation/VAD, enrollment/consent UX.
- Полировка SRS-onboarding: feature-based структура и widget tests.
