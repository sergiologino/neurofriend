# NeuroFriend — Application monorepo

Структура:

- `backend/` — FastAPI, PostgreSQL, Redis, Qdrant; голос: OpenAI Whisper + TTS; чат-транскрипт с лимитом треда.
- `infra/` — Docker (Redis, Qdrant, опционально Postgres в compose); **повседневно можно использовать уже установленный локальный PostgreSQL** — см. `infra/README.md`.
- `mobile/` — клиент Flutter (после `flutter create` / `flutter pub get`).
- `docs/ai/` — память проекта для разработки.

Быстрый старт backend см. `backend/README.md` (все команды `pip`, `alembic`, `uvicorn` — из каталога **`backend/`**, там лежит `pyproject.toml`). Скопируйте `.env.example` в **`backend/.env`** и задайте `OPENAI_API_KEY` для голоса и LLM.

Пошаговый локальный запуск на **Windows 11** (PostgreSQL, backend, Flutter desktop/Android/телефон): `docs/LOCAL_SETUP_WINDOWS.md`.
