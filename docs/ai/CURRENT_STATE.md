# Текущее состояние

**Дата актуализации:** 2026-04-13 (семантическая память Qdrant)

## Репозиторий

- **Backend (FastAPI):** `backend/` — PostgreSQL, Alembic `20260412_0001`, эндпоинты `/health`, `/v1/meta/personality-presets`, `/v1/neurofriends` (опционально `preset_id`), `/v1/perception/audio`, `/v1/conversations/...`, debug. Ответы LLM учитывают **недавний транскрипт** активного треда и **стиль пресета** (`character_prompt` в ядре).
- **Инфраструктура:** `infra/docker-compose.yml` (опционально Postgres в контейнере; **для разработки достаточно локального PostgreSQL на хосте** — см. `infra/README.md`). Redis/Qdrant в compose по необходимости. Сборка Docker-образа backend ранее не проверялась (daemon мог быть недоступен).
- **Клиент:** `mobile/` — Flutter: выбор пресета при создании нейродруга, лента чата, голос/текст, инспектор; стек см. `mobile/README.md`.
- Память проекта: `docs/ai/`.

## SRS

- Требования изучены и сведены в `PROJECT_OVERVIEW.md`, `ARCHITECTURE.md`, `DECISIONS.md`.
- Исходные файлы SRS лежат вне этого каталога: `E:\1_MyProjects\1_Human_robofriend\SRS\` (или актуальный путь без `!` в имени папки).

## Сборка и тесты

- Backend: `pip install -e ".[dev]"` в `backend/`, затем `python -m pytest tests/ -q` (последняя проверка **2026-04-13:** **6 passed**).
- Перед запуском API: **локальный PostgreSQL** (рекомендуется), `alembic upgrade head`, `OPENAI_API_KEY`; для семантической памяти — поднять **Qdrant** (`infra/docker-compose.yml` сервис `qdrant` или локально порт 6333) и при необходимости выставить `QDRANT_URL`.
- Клиент: `dart analyze lib` — без замечаний (после доработки UI). Полная сборка зависит от окружения (Flutter, Visual Studio для Windows desktop).

## План реализации

- Детальный поэтапный план: `docs/ai/ROADMAP.md` (голос Whisper+TTS в приоритете, чат как дубликат с лимитом 500 и архивом + 10 сообщений carryover, UI отношений/событий для отладки).
- **Следующие конкретные шаги и бэклог:** `docs/ai/TODO.md`.

## Следующий логичный шаг

- E2e / интеграционные сценарии OpenAPI + Postgres + Qdrant (в т.ч. семантическая память и rollover треда).
- Расширение пресетов: дельты персонализации, `selected_preset_id` на create по SRS.
- Консолидация памяти (воркер), importance/decay; инициатива по `ROADMAP.md` этап 7.
