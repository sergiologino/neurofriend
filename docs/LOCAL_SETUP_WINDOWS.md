# Локальный запуск NeuroFriend на Windows 11

Инструкция для человека с базовым опытом: что нажать, куда положить файлы, какие адреса вписать. Путь к проекту ниже обозначен как `Application` — папка с кодом внутри вашего каталога разработки (например `...\Human_robofriend\Application`).

### Важно: Flutter и символ `!` в пути (Windows)

Сборка **Flutter для Windows** (`flutter run -d windows`) **не работает**, если полный путь к проекту содержит символ **`!`** (и ряд других: `' # $ ^ & * = | , ; < > ?`).

Типичный случай: папка `!_Human_robofriend` — тогда появляется ошибка *Path ... contains invalid characters*.

**Решение:** переименуйте родительскую папку без `!` (например `Human_robofriend` или `_Human_robofriend`) или **скопируйте** каталог `Application` в другое место с «простым» путём. После переименования откройте проект из нового расположения в IDE.

Код Dart (например `const String ...`) вставляют **только в файлы `.dart` в редакторе**, а не в окно PowerShell — иначе оболочка пытается выполнить это как команду и выдаёт ошибку про `const`.

### После переименования или переноса папки: Python `.venv`

На Windows скрипты в `backend\.venv\Scripts\` (`uvicorn.exe`, `alembic.exe` и т.д.) запоминают **старый полный путь** к `python.exe`. Если каталог проекта переименовали (например убрали `!` из имени), появляется ошибка *Fatal error in launcher: Unable to create process* с путём к **прежнему** расположению.

**Решение:** удалить папку `backend\.venv`, создать окружение заново (`python -m venv .venv`, `pip install -e ".[dev]"`), затем `alembic upgrade head`. Файл `backend\.env` переносить не нужно.

---

## Часть 1. База данных PostgreSQL (один раз)

1. Убедитесь, что **PostgreSQL** запущен (служба Windows или pgAdmin показывает сервер «online»).
2. Создайте **пустую базу** и пользователя с правами на неё (через pgAdmin, DBeaver или `psql`). Запомните:
   - имя базы (например `neurofriend`);
   - логин и пароль;
   - порт (часто **5432**).

Если база уже есть — используйте её.

---

## Часть 2. Запуск backend (сервер API)

### 2.1. Python и виртуальное окружение

1. Откройте **PowerShell** или **cmd**.
2. Перейдите в папку **`backend`** (не в корень `Application`):

```text
cd <ваш путь>\Application\backend
```

(Подставьте свой диск и путь, если проект лежит иначе.)

Файл проекта Python — **`backend\pyproject.toml`**. Команды `pip install -e ".[dev]"`, `alembic`, `uvicorn` выполняются **только из папки `backend`**. Если запустить `pip install -e ".[dev]"` из корня `Application`, появится ошибка *«does not appear to be a Python project»*.

3. Создайте виртуальное окружение (один раз):

```text
python -m venv .venv
```

4. **Активируйте** окружение перед каждой новой сессией терминала:

```text
.venv\Scripts\activate
```

Слева в строке появится префикс `(.venv)`.

5. Установите зависимости (после активации, при обновлении проекта — повторить):

```text
pip install -e ".[dev]"
```

### 2.2. Файл с переменными окружения

Backend при старте читает файл **`.env` из папки `backend`** (там же, откуда вы запускаете `uvicorn`).

1. Скопируйте из корня проекта файл `Application\.env.example` в `Application\backend\.env`  
   (имя именно `.env`, без слова example).
2. Откройте `backend\.env` в блокноте или IDE и заполните:

| Переменная | Зачем | Пример / что вписать |
|------------|--------|----------------------|
| `DATABASE_URL` | Подключение к PostgreSQL | `postgresql+asyncpg://ЛОГИН:ПАРОЛЬ@127.0.0.1:5432/ИМЯ_БД` |
| `OPENAI_API_KEY` | Голос (Whisper), ответы LLM, TTS | Ключ с [platform.openai.com](https://platform.openai.com/) (без кавычек) |
| `SECRET_KEY` | Секрет приложения (пока можно любая длинная строка для своего ПК) | Не оставляйте пустым в общей сети |
| `CORS_ORIGINS` | Каким сайтам/портам разрешено обращаться к API из браузера | См. ниже |

**Про пароль в `DATABASE_URL`:** если в пароле есть спецсимволы (`@`, `#` и т.д.), их нужно **кодировать для URL** (или используйте пароль без таких символов для локальной разработки).

**Минимум для первого запуска:** корректный `DATABASE_URL` и `OPENAI_API_KEY`, если вы хотите голос и ответы нейросети. Без ключа OpenAI часть функций не заработает.

**Qdrant (семантическая память)** нужен для индексации и поиска по смыслу; без него API работает, но блок памяти в промпте пустой. В `backend/.env` обычно: `QDRANT_URL=http://127.0.0.1:6333`, `SEMANTIC_MEMORY_ENABLED=true`, плюс `OPENAI_API_KEY` (эмбеддинги). Отключить память полностью: `SEMANTIC_MEMORY_ENABLED=false`.

#### Запуск Qdrant через Docker Desktop (Windows)

1. Запустите **Docker Desktop** и дождитесь статуса *Running* (иконка кита в трее).
2. Откройте **PowerShell** или **cmd** и перейдите в корень репозитория приложения (папка, где лежит каталог `infra`), например:
   ```text
   cd E:\1_MyProjects\1_Human_robofriend\Application
   ```
3. Поднимите только Qdrant в фоне:
   ```text
   docker compose -f infra/docker-compose.yml up -d qdrant
   ```
   Первый раз скачается образ `qdrant/qdrant` (версия в `infra/docker-compose.yml`, согласована с `qdrant-client` в backend); порты **6333** (REST) и **6334** (gRPC) пробрасываются на ваш ПК.
4. Проверка: в браузере откройте [http://127.0.0.1:6333/dashboard](http://127.0.0.1:6333/dashboard) — должна открыться панель Qdrant. Либо в PowerShell: `curl http://127.0.0.1:6333/` (ожидается JSON с версией).
5. Запустите backend (`uvicorn` из `backend/`). При старте создаётся коллекция для семантической памяти (если Qdrant доступен и задан ключ OpenAI).
6. Остановка контейнера (когда не нужен): из того же корня репозитория:
   ```text
   docker compose -f infra/docker-compose.yml stop qdrant
   ```
   Удалить контейнер и том с данными векторов — только если осознанно нужно очистить хранилище (см. `docker compose down -v` в документации Docker; **осторожно:** затронет том `neurofriend_qdrant`).

Если порт **6333** уже занят другим приложением, измените проброс в `infra/docker-compose.yml` (например `"6335:6333"`) и укажите в `.env` соответствующий `QDRANT_URL`.

**Redis** желателен, если используете очередь инициатив (`nf:initiative:candidates`); для ручного теста sweep не обязателен.

**Инициатива (этап 7):** в `backend/.env` можно задать `INITIATIVE_SWEEP_SECRET` (длинная случайная строка). Тогда по расписанию (Планировщик заданий Windows, cron в WSL и т.д.) вызывайте:

```text
curl -X POST http://127.0.0.1:8000/v1/internal/initiative/sweep -H "X-Initiative-Sweep-Key: ВАШ_СЕКРЕТ"
```

Без секрета эндпоинт отвечает 404. Параметры порогов и тихих часов — `INITIATIVE_*` в `.env` (см. `app/core/config.py`).

Проверка списка голосов TTS под пресет (мужской/женский/нейтральный манерный стиль):

```text
curl "http://127.0.0.1:8000/v1/meta/tts-voices?gender_style=masculine"
```

---

### 2.2a. Полный стек для локального теста (этап 7 + голос + память)

Ниже — что поднять и какие переменные имеют смысл для «как в проде, но на своём ПК». Минимум по-прежнему: PostgreSQL, `DATABASE_URL`, `OPENAI_API_KEY`; остальное — по необходимости.

| Что запустить | Зачем |
|---------------|--------|
| PostgreSQL | Основное хранилище |
| `uvicorn` (backend из `backend/`) | HTTP API |
| Qdrant (Docker `infra/docker-compose.yml`) | Семантическая память (векторы) |
| Redis | Очередь кандидатов инициативы (`nf:initiative:candidates`) |
| Планировщик или ручной `curl` | `POST /v1/internal/initiative/sweep` с `X-Initiative-Sweep-Key`, если задан `INITIATIVE_SWEEP_SECRET` |
| Flutter (`mobile/`) | Клиент |

| Переменная (файл `backend/.env`) | Назначение |
|-----------------------------------|------------|
| `DATABASE_URL` | Async PostgreSQL (`postgresql+asyncpg://…`) |
| `OPENAI_API_KEY` | Чат, Whisper, TTS (`tts-1`), эмбеддинги для Qdrant |
| `SECRET_KEY` | Секрет приложения |
| `CORS_ORIGINS` | Origin’ы браузера (Flutter web / dev server) |
| `REDIS_URL` | Redis для инициативы; без Redis sweep может не находить кандидатов |
| `QDRANT_URL` | URL Qdrant REST |
| `QDRANT_API_KEY` | Если Qdrant с ключом (локально обычно пусто) |
| `QDRANT_COLLECTION_SEMANTIC` | Имя коллекции (по умолчанию `neurofriend_semantic`) |
| `SEMANTIC_MEMORY_ENABLED` | `true`/`false` — включить память и индексацию |
| `EMBEDDING_MODEL` | Модель эмбеддингов (по умолчанию `text-embedding-3-small`) |
| `SEMANTIC_MEMORY_TOP_K` | Сколько фрагментов подмешивать в промпт |
| `CHAT_MODEL` | Модель ответов |
| `WHISPER_MODEL` | Транскрипция голоса |
| `TTS_MODEL` | Модель озвучки (например `tts-1`) |
| `TTS_VOICE` | Голос по умолчанию, если у нейродруга в БД нет своего (`tts_voice` в профиле задаётся при создании / PATCH) |
| `CHAT_MAX_MESSAGES_PER_THREAD` / `CHAT_CARRYOVER_MESSAGES` | Лимиты истории в потоке |
| `INITIATIVE_ENABLED` | Включить логику инициативы |
| `INITIATIVE_GAP_HOURS_MIN` / `INITIATIVE_GAP_HOURS_STRONG` | Пороги «тишины» между сообщениями |
| `INITIATIVE_READINESS_THRESHOLD` | Порог готовности к пингу |
| `INITIATIVE_QUIET_HOURS_START_UTC` / `INITIATIVE_QUIET_HOURS_END_UTC` | Тихие часы (UTC) |
| `INITIATIVE_COOLDOWN_HOURS` | Кулдаун между инициативами |
| `INITIATIVE_SWEEP_SECRET` | Секрет для `POST /v1/internal/initiative/sweep` |

Голос нейродруга в приложении: при создании передаётся `tts_voice` (список из `GET /v1/meta/tts-voices?gender_style=…` согласован с `gender_style` пресета). Озвучка `POST /v1/perception/tts` и ответ на голосовой ход используют сохранённый голос. Дальнейший **Yandex TTS** — отдельный провайдер в коде (пока OpenAI).

**CORS для своего ПК:** добавьте адреса, с которых откроете клиент. Примеры:

- Только с этого компьютера, Flutter web: оставьте строку из примера и при необходимости добавьте через запятую, например `http://localhost:5555` (порт подставьте тот, который покажет Flutter при `flutter run -d chrome`).
- Для простоты на чисто локальных тестах иногда временно расширяют список; в продакшене так не делают.

### 2.3. Миграции базы

В том же терминале (с активированным `.venv` и папкой `backend`):

```text
alembic upgrade head
```

Эта команда создаёт нужные таблицы в вашей базе.

### 2.4. Запуск сервера

```text
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **`--host 0.0.0.0`** — чтобы к серверу могли подключиться **эмулятор Android** и **телефон в Wi‑Fi** с этого же ПК (не только «localhost» с самого компьютера).
- Окно терминала **не закрывайте**, пока тестируете приложение.

Проверка в браузере на ПК:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) — документация API (Swagger).

---

## Часть 3. Клиент на десктопе (Windows) + переменные

Клиент — **Flutter** (Dart в комплекте). **npm для этого шага не нужен.**

### 3.1. Установка Flutter

1. Установите Flutter по официальной инструкции: [https://docs.flutter.dev/get-started/install/windows](https://docs.flutter.dev/get-started/install/windows).
2. В PowerShell выполните `flutter doctor` и устраните замечания (Android toolchain, при желании Visual Studio для Windows desktop).

### 3.2. Включение сборки под Windows (десктоп)

Один раз:

```text
flutter config --enable-windows-desktop
```

### 3.2a. Visual Studio — нужна для `flutter run -d windows`

Сборка **нативного** окна под Windows использует инструменты Microsoft C++ (CMake, MSVC). **Visual Studio Code этого не заменяет.** Нужен **Visual Studio 2022** (достаточно бесплатной редакции **Community**).

1. Скачайте установщик: [https://visualstudio.microsoft.com/downloads/](https://visualstudio.microsoft.com/downloads/) → **Community 2022**.
2. В установщике отметьте рабочую нагрузку **«Разработка классических приложений на C++»** (в английском интерфейсе: **Desktop development with C++**).
3. В составе справа убедитесь, что выбраны **Windows SDK** (под вашу версию Windows 10/11) и **MSVC**.
4. Дождитесь окончания установки, **перезапустите** терминал и снова выполните:

```text
flutter doctor
```

В блоке **Visual Studio** должно быть без красных ошибок (или с понятным предупреждением, которое не мешает).

После этого снова: `flutter run -d windows`.

**Если ставить Visual Studio сейчас не хотите:** можно временно гонять клиент в **браузере** (другой набор инструментов):

```text
flutter run -d chrome
```

или `flutter run -d edge` — для проверки UI без нативного окна Windows.

### 3.2b. Режим разработчика и симлинки (Developer Mode)

Сборка с плагинами на Windows использует **симлинки** в каталоге сборки. Если Flutter пишет *Building with plugins requires symlink support*:

1. Включите **режим разработчика**: `Параметры` → **Конфиденциальность и защита** → **Для разработчиков** → **Режим разработчика** (или команда `start ms-settings:developers`).
2. **Полностью закройте** PowerShell / IDE и при необходимости **выйдите из учётной записи Windows или перезагрузите ПК** — иногда переключатель применяется не сразу.
3. В папке `mobile` выполните `flutter clean`, затем снова `flutter pub get` и `flutter run -d windows`.

### 3.2c. Ошибки сборки `record_linux` / `RecordLinux.hasPermission` при `flutter run -d windows`

Это известная несовместимость старых версий пакета **`record`** с подпакетом `record_linux`. В проекте зафиксировано **`record: ^6.2.0`** в `mobile/pubspec.yaml`. После обновления зависимостей выполните в `mobile/`:

```text
flutter clean
flutter pub get
flutter run -d windows
```

### 3.3. Подготовка папки `mobile` (если ещё не делали)

В каталоге `Application\mobile`:

```text
cd <ваш путь>\Application\mobile
flutter create . --project-name neurofriend_mobile --org com.neurofriend --platforms=android,ios,web,windows
flutter pub get
```

(Если `flutter create` уже выполняли — достаточно `flutter pub get`.)

### 3.4. Адрес API для десктопа

На **том же ПК**, где крутится backend:

- Базовый URL API: **`http://127.0.0.1:8000`** или **`http://localhost:8000`**.

В репозитории уже есть **`lib/core/api_config.dart`**: константа `kApiBaseUrl` (по умолчанию `http://127.0.0.1:8000`). Меняйте URL в файле или передайте при сборке:

```text
flutter run -d windows --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

### 3.5. Запуск оконного приложения

Команды **`flutter run`**, **`flutter pub get`**, **`flutter build`** нужно выполнять **из корня Flutter-проекта** — папки `mobile`, где лежит файл **`pubspec.yaml`**. Если запустить `flutter run` из `C:\Users\...` или из `Application` без входа в `mobile`, будет ошибка *No pubspec.yaml file found*.

```text
cd <ваш путь>\Application\mobile
flutter run -d windows
```

---

## Часть 4. Сборка под Android, запуск в эмуляторе (Android Studio)

### 4.0. Если `flutter doctor` ругается на Android (cmdline-tools, licenses)

На сборку **Windows desktop** это обычно **не влияет**. Для **Android** (эмулятор, телефон) лучше исправить:

1. **Android Studio** → **Settings** → **Languages & Frameworks** → **Android SDK** → вкладка **SDK Tools** → установите **Android SDK Command-line Tools (latest)**.
2. В терминале: `flutter doctor --android-licenses` — примите лицензии (много раз `y`).
3. При необходимости задайте переменную окружения **ANDROID_HOME** = путь из поля **Android SDK Location** на той же странице SDK (после изменения — новый терминал).

Подробнее: [настройка Android под Flutter на Windows](https://flutter.dev/to/windows-android-setup).

### 4.1. Эмулятор

1. Откройте **Android Studio** → **Device Manager** → создайте виртуальное устройство (AVD), запустите его.
2. Пока эмулятор включён, в терминале:

```text
cd <ваш путь>\Application\mobile
flutter devices
```

Должен появиться ваш эмулятор.

### 4.2. Адрес API с эмулятора

С эмулятора **нельзя** использовать `127.0.0.1` как «ваш ПК» так же, как с браузера. Для Android эмулятора адрес хоста:

**`http://10.0.2.2:8000`**

В клиенте для сборки под Android используйте эту базу URL (или `dart-define` отдельно для Android).

### 4.3. CORS

CORS важен для **браузера**. Нативное Android‑приложение к CORS не относится так же, как сайт; главное — чтобы URL был верным и сервер слушал `0.0.0.0:8000`.

### 4.4. Запуск на эмуляторе

```text
flutter run
```

или явно:

```text
flutter run -d emulator
```

---

## Часть 5. Телефон по USB или Wi‑Fi

### 5.1. Один Wi‑Fi

Телефон и компьютер должны быть в **одной сети Wi‑Fi**.

### 5.2. Узнать IP компьютера в локальной сети

В PowerShell:

```text
ipconfig
```

Найдите **IPv4-адрес** вашего Wi‑Fi адаптера (что-то вроде `192.168.0.15`).

### 5.3. Адрес API на телефоне

В приложении укажите:

```text
http://ВАШ_IP:8000
```

Например: `http://192.168.0.15:8000`.

### 5.4. Фаервол Windows

При первом запуске `uvicorn` Windows может спросить доступ для **частной сети** — разрешите для домашней сети. Если телефон не коннектится — проверьте правило брандмауэра для входящих подключений на **порт 8000** (документация Microsoft по «Inbound rule» для порта).

### 5.5. USB-отладка (Android)

1. На телефоне: режим разработчика и **отладка по USB**.
2. Подключите кабелем, подтвердите отладку.
3. `flutter devices` — должен быть ваш телефон.
4. `flutter run` — установит и запустит приложение.

Для **iOS** нужен macOS и Xcode; на чистом Windows только Android из коробки.

### 5.6. Релизная сборка на телефон (кратко)

Для установки «как приложение» без кабеля каждый раз — собирают APK/AAB и ставят вручную или через магазин. Для локальной проверки достаточно `flutter run` на устройстве.

---

## Часть 6. Проверка «всё ли сошлось»

| Шаг | Проверка |
|-----|----------|
| PostgreSQL | Подключение теми же данными, что в `DATABASE_URL` |
| Миграции | `alembic upgrade head` без ошибки |
| Backend | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) открывается |
| Десктоп | `flutter run -d windows`, приложение стартует |
| Эмулятор | В приложении базовый URL `http://10.0.2.2:8000` |
| Телефон | Тот же Wi‑Fi, URL `http://IP_ПК:8000`, `uvicorn` с `--host 0.0.0.0` |

---

## Часть 7. Автотесты backend (по желанию)

Из папки `backend` с активированным `.venv`:

```text
python -m pytest tests/ -q
```

---

## Если что-то не работает

1. **`pip install -e ".[dev]"` — «does not appear to be a Python project»** — вы в корне `Application`, а нужно перейти в **`backend`** (`cd ...\Application\backend`), затем снова `pip install -e ".[dev]"`. Виртуальное окружение (`.venv`) удобно создавать тоже в `backend`.
2. **Flutter — «Path ... contains invalid characters»** — в пути к `mobile` есть запрещённый символ (часто **`!`** в имени папки). Переименуйте каталоги или перенесите проект в путь без `!` и других символов из списка в начале этой инструкции.
3. **Flutter — «No pubspec.yaml file found»** — вы не в папке проекта. Перейдите в **`Application\mobile`** (там лежит `pubspec.yaml`), затем снова `flutter run ...`.
4. **Flutter — «Unable to find suitable Visual Studio toolchain»** при `flutter run -d windows` — установите **Visual Studio 2022** с нагрузкой **«Разработка классических приложений на C++»**, затем снова `flutter doctor`. Временная альтернатива без VS: `flutter run -d chrome` (см. раздел 3.2a).
5. **PowerShell ругается на `const String`** — вы вставили код Dart в терминал; правьте только файлы `.dart` в IDE.
6. **`Fatal error in launcher` / в ошибке путь к старой папке** — после переименования проекта пересоздайте `backend\.venv` (см. блок «После переименования или переноса папки» выше).
7. **Backend не стартует** — прочитайте текст ошибки в терминале; чаще всего неверный `DATABASE_URL` или не запущен PostgreSQL.
8. **401/ошибки OpenAI** — проверьте `OPENAI_API_KEY` и баланс/лимиты на стороне OpenAI.
9. **Эмулятор не видит сервер** — используйте `10.0.2.2`, не `localhost`.
10. **Телефон не видит сервер** — IP, один Wi‑Fi, фаервол, `uvicorn --host 0.0.0.0`.

Более короткий технический чеклист по backend: `backend/README.md`. Общая память проекта: `docs/ai/CURRENT_STATE.md`.
