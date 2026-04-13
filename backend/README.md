# NeuroFriend backend

FastAPI приложение: голос (Whisper → LLM → TTS), события, чат-транскрипт, отладочные API.

## Рекомендуемый локальный запуск (PostgreSQL на машине)

Используйте **уже развёрнутый локальный PostgreSQL**: создайте базу и пользователя (или возьмите существующие). Скопируйте `../.env.example` в **`backend/.env`** и пропишите строку подключения (при запуске `uvicorn` из этой папки читается именно `backend/.env`).

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
# в .env: DATABASE_URL=postgresql+asyncpg://USER:PASS@127.0.0.1:5432/ВАША_БД
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API: `http://localhost:8000`, OpenAPI: `http://localhost:8000/docs`.

## Запуск всего стека в Docker (без обязательного Postgres на хосте)

Если нужен изолированный Postgres в контейнере — см. `../infra/docker-compose.yml` и `../infra/README.md`. Для ежедневной работы с локальным Postgres контейнер с БД **не требуется**.

## Тесты

```bash
# DATABASE_URL должен указывать на доступный PostgreSQL, если гоняете интеграционные тесты с БД в будущем.
alembic upgrade head
pytest -q
```

Сейчас в репозитории unit/smoke-тесты не требуют живой БД для базового прогона (`python -m pytest tests/ -q`).
