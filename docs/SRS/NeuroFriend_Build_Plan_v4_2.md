# NeuroFriend v4.2 — Build Plan для Cursor
## Пошаговый план реализации MVP: backend skeleton, docker-compose, модели, endpoints, Flutter onboarding + chat

> Этот документ предназначен как практическое продолжение:
> - `NeuroFriend_TZ_v4.md`
> - `NeuroFriend_Implementation_v4_1.md`
>
> Цель: дать Cursor и разработчику максимально понятный план,
> **что именно делать по шагам**, в каком порядке, с какими файлами,
> сущностями, контрактами и критериями готовности.

---

# 0. Главная цель этого этапа

Нужно собрать **первую живую версию NeuroFriend**, которая уже умеет:

- создавать нейродруга с неизменяемым ядром личности;
- начинать разговор первой;
- помнить важное;
- замечать паузы во времени;
- отвечать в устойчивом характере;
- немного адаптироваться к пользователю;
- хранить основу для дальнейшего развития.

На этом этапе **не нужно** сразу делать:
- полноценное зрение;
- сложную обработку голоса;
- ревность/обиду;
- сложный агентный loop 24/7.

Нужно сделать **живой текстовый MVP**, к которому позже удобно подключить голос и камеру.

---

# 1. Что именно должен уметь MVP

## 1.1 Пользовательский сценарий
1. Пользователь устанавливает приложение.
2. Проходит онбординг.
3. Создает нейродруга:
   - имя;
   - пол / стиль;
   - возрастной образ;
   - архетип;
   - характер;
   - инициативность;
   - стиль речи.
4. Подтверждает, что ядро личности фиксируется навсегда.
5. Получает первое сообщение от нейродруга.
6. Общается в чате.
7. Нейродруг:
   - помнит важное;
   - замечает разрывы во времени;
   - иногда пишет первым;
   - говорит в своем стиле;
   - не превращается в безликий FAQ.

## 1.2 Обязательные признаки “живости”
- нейродруг начинает знакомство сам;
- у него есть узнаваемый стиль;
- он не забывает важное через одно сообщение;
- он реагирует на длительный пропуск;
- он не ведет себя как безличный ассистент;
- он слегка подстраивается под пользователя, но не теряет характер.

---

# 2. Итог этапа разработки

После завершения этого этапа у тебя должно быть:

## Backend
- FastAPI skeleton
- Docker Compose
- PostgreSQL
- Redis
- Qdrant
- SQLAlchemy models
- Alembic migrations
- базовый LLM orchestrator
- Memory service
- Affect service
- Initiative lite
- daily consolidation job

## Mobile app
- Flutter app
- onboarding
- создание нейродруга
- экран чата
- базовые настройки
- отображение первого сообщения
- получение инициативных сообщений через push или имитацию polling/pull

---

# 3. Репозитории

## Вариант A — один monorepo (рекомендовано на старте)
```text
neurofriend/
  backend/
  mobile/
  infra/
  docs/
```

## Вариант B — два репозитория
- `neurofriend-backend`
- `neurofriend-mobile`

Для MVP рекомендую **monorepo**, чтобы не разрывать контекст и быстрее итерироваться.

---

# 4. Порядок работ

---

# ШАГ 1. Создать backend skeleton

## Цель
Собрать основу FastAPI-проекта с понятной доменной структурой.

## Структура
```text
backend/
  app/
    main.py
    core/
      config.py
      database.py
      redis.py
      logging.py
      security.py
    api/
      v1/
        routes/
          health.py
          neurofriends.py
          conversations.py
          memory.py
          state.py
          initiative.py
    domain/
      identity/
      affect/
      memory/
      bond/
      initiative/
      llm/
    services/
      identity_service.py
      affect_service.py
      memory_service.py
      bond_service.py
      initiative_service.py
      llm_orchestrator.py
    models/
    schemas/
    repositories/
    workers/
    tests/
```

## Что должен сделать Cursor
1. Создать FastAPI app factory.
2. Добавить `/health`.
3. Подключить settings через Pydantic Settings.
4. Настроить CORS.
5. Подключить SQLAlchemy async engine.
6. Подключить Redis client.
7. Подключить Qdrant client.
8. Настроить логирование.

## Критерий готовности
- backend запускается;
- `/health` отвечает;
- есть конфиг через `.env`;
- все зависимости подключены.

---

# ШАГ 2. Поднять инфраструктуру через docker-compose

## Цель
Получить локальную среду, в которой можно запускать MVP без ручной магии.

## Сервисы
- `postgres`
- `redis`
- `qdrant`
- `backend`
- опционально `adminer`/`pgadmin`

## Что должен сделать Cursor
Сгенерировать `docker-compose.yml`, где:
- PostgreSQL с volume;
- Redis с volume или без;
- Qdrant с volume;
- backend собирается из `backend/Dockerfile`.

## Пример структуры
```text
infra/
  docker-compose.yml
backend/
  Dockerfile
  requirements.txt / pyproject.toml
```

## Переменные окружения
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `REDIS_URL`
- `QDRANT_URL`
- `OPENAI_API_KEY`
- `APP_ENV`
- `SECRET_KEY`

## Критерий готовности
- `docker compose up` поднимает всё;
- backend подключается к PostgreSQL, Redis и Qdrant;
- данные БД и Qdrant сохраняются в volume.

---

# ШАГ 3. Реализовать SQLAlchemy models

## Цель
Создать источник истины для доменной логики.

## Обязательные модели MVP

### 3.1 User
Поля:
- id
- email или phone
- display_name
- timezone
- locale
- created_at
- updated_at

### 3.2 NeuroFriendProfile
Поля:
- id
- user_id
- name
- gender_style
- age_style
- archetype
- identity_locked
- initiative_level
- emotional_depth
- social_style
- humor_style
- relationship_style
- persona_summary
- created_at
- updated_at

### 3.3 IdentityCore
Поля:
- id
- neurofriend_id
- core_traits_json
- speech_rules_json
- values_json
- conflict_style
- attachment_style
- initiative_preferences_json
- worldview_json
- permitted_adaptation_range_json
- immutable_version

### 3.4 InternalStateSnapshot
Поля:
- id
- neurofriend_id
- timestamp
- valence
- arousal
- safety
- curiosity
- trust_baseline
- attachment
- fatigue
- coherence
- social_need
- loneliness
- hurt
- irritation
- delight

### 3.5 RelationshipModel
Поля:
- id
- neurofriend_id
- person_ref
- display_name
- relation_type
- familiarity
- trust
- attachment
- predictability
- warmth
- conflict_history_score
- repair_history_score
- last_interaction_at
- typical_mood_distribution_json
- active_topics_json
- special_meaning_tags_json

### 3.6 EventLog
Поля:
- id
- neurofriend_id
- timestamp
- event_type
- source
- raw_payload_json
- normalized_payload_json
- importance_score
- emotional_weight
- novelty_score
- identity_link_score
- relation_link_score
- promoted_to_fast_memory
- embedded

### 3.7 MemoryItem
Поля:
- id
- neurofriend_id
- memory_type
- content_text
- content_structured_json
- source_event_ids_json
- importance_score
- access_score
- decay_score
- retrieval_count
- last_retrieved_at
- person_refs_json
- emotion_tags_json
- scene_tags_json
- topic_tags_json
- created_at
- updated_at

### 3.8 InitiativePolicy
Поля:
- id
- neurofriend_id
- mode
- max_daily_outbound
- min_gap_between_initiatives_minutes
- night_silence_window_json
- respect_dnd
- follow_up_sensitivity
- unfinished_topic_sensitivity
- loneliness_trigger_sensitivity
- presence_probe_allowed

### 3.9 SocialLearningProfile
Поля:
- id
- neurofriend_id
- phrase_adoption_rate
- humor_adoption_rate
- reaction_adoption_rate
- syntax_adaptation_rate
- slang_adoption_allowed
- max_identity_drift
- forbidden_imitation_patterns_json

### 3.10 ConversationThread
Поля:
- id
- neurofriend_id
- title
- created_at
- updated_at

### 3.11 Message
Поля:
- id
- thread_id
- direction
- role
- text
- message_kind
- metadata_json
- created_at

## Что должен сделать Cursor
1. Создать базовый `Base` для моделей.
2. Создать все модели.
3. Добавить связи.
4. Создать Alembic migration.
5. Сгенерировать initial schema.

## Критерий готовности
- миграции применяются;
- таблицы создаются;
- связи работают;
- можно создать тестовые записи.

---

# ШАГ 4. Реализовать создание нейродруга

## Цель
Дать пользователю возможность создать личность.

## Endpoint
`POST /v1/neurofriends`

## Request
```json
{
  "name": "Марина",
  "gender_style": "female",
  "age_style": "young_adult",
  "archetype": "adventurous_warm",
  "temperament": {
    "softness": 0.55,
    "directness": 0.45,
    "humor": 0.60,
    "initiative": 0.72,
    "emotionality": 0.67
  },
  "social_style": "urban_free",
  "speech_style": "alive_informal",
  "relationship_style": "warm_equal",
  "identity_lock_confirmed": true
}
```

## Логика
При создании нужно:
1. Создать `NeuroFriendProfile`.
2. Создать `IdentityCore`.
3. Создать initial `InternalStateSnapshot`.
4. Создать `InitiativePolicy`.
5. Создать `SocialLearningProfile`.
6. Сгенерировать первое сообщение-знакомство через LLM.
7. Создать thread.
8. Сохранить первое исходящее сообщение.

## Важные правила
- если `identity_lock_confirmed = false`, не создавать;
- `archetype` и базовое ядро фиксируются навсегда;
- интро должно быть сгенерировано **из параметров личности**.

## Критерий готовности
После запроса:
- в БД создан нейродруг;
- создано первое сообщение;
- возвращается `identity_locked: true`.

---

# ШАГ 5. Реализовать отправку текстового сообщения

## Цель
Собрать живую основу общения.

## Endpoint
`POST /v1/conversations/{neurofriendId}/messages`

## Request
```json
{
  "text": "Привет, я пропал на три дня",
  "client_timestamp": "2026-03-29T18:00:00+02:00"
}
```

## Pipeline
1. Принять сообщение.
2. Сохранить `Message`.
3. Создать `EventLog`.
4. Определить gap по времени.
5. Обновить `InternalStateSnapshot`.
6. Обновить `RelationshipModel` пользователя.
7. Создать / обновить память.
8. Подготовить LLM context.
9. Сгенерировать ответ.
10. Сохранить ответ как исходящее сообщение.
11. Вернуть ответ клиенту.

## Критерий готовности
- пользователь пишет сообщение;
- нейродруг отвечает;
- ответ учитывает характер;
- ответ не забывает контекст;
- история хранится.

---

# ШАГ 6. Сделать LLM orchestrator

## Цель
Собрать правильный контекст перед генерацией ответа.

## Входные данные orchestrator
- IdentityCore
- последний InternalStateSnapshot
- RelationshipModel пользователя
- последние сообщения thread
- fast memory
- релевантные deep memory items
- текущий user input
- gap context

## Выход
- текст ответа
- reasoning metadata (внутренние структурированные признаки, без раскрытия chain-of-thought)
- tags для памяти
- optional initiative hints

## Правило
Cursor должен реализовать orchestrator как отдельный сервис,
а не размазывать сбор prompt по endpoint.

## Формат внутреннего prompt assembly
Пример блоков:
- system block: кто такой нейродруг
- style block: как он говорит
- state block: текущее внутреннее состояние
- relation block: кто ему пользователь
- memory block: что важно вспомнить
- user block: текущее сообщение
- output contract: формат ответа

## Важно
Не хранить всю логику только в prompt.
Часть решений должна приниматься кодом:
- какие memories подать;
- инициатива допустима или нет;
- какой gap критичен;
- как обновлять state.

## Критерий готовности
- orchestrator вынесен в сервис;
- контекст собирается централизованно;
- ответы становятся стабильнее и “живее”.

---

# ШАГ 7. Реализовать Memory Service

## Цель
Дать нейродругу память, а не просто историю чата.

## Основные функции
- log_event()
- score_event_importance()
- promote_to_fast_memory()
- store_deep_memory()
- retrieve_relevant_memories()
- consolidate_daily()
- create_summary_memory()

## Алгоритм оценки важности
Использовать базовую формулу:
```text
importance_score =
  0.22 * novelty +
  0.22 * emotional_weight +
  0.18 * repetition_signal +
  0.14 * identity_link +
  0.14 * relation_link +
  0.10 * context_shift
```

## Что должен сделать Cursor
1. Написать сервис оценки значимости.
2. Создавать `MemoryItem`.
3. При достаточной важности — помечать как fast memory.
4. Иначе отправлять в deep memory.
5. Генерировать embeddings.
6. Писать память в Qdrant.

## Критерий готовности
- после диалога остаются memory items;
- retrieval возвращает осмысленные воспоминания;
- важные эпизоды остаются ближе.

---

# ШАГ 8. Реализовать Affect Service

## Цель
Дать внутреннее состояние.

## Основные функции
- evaluate_event_emotion()
- update_state_snapshot()
- get_current_state()

## Простые правила на старте
### Тёплое сообщение
- valence +0.1
- safety +0.05
- attachment +0.03

### Резкое сообщение
- valence -0.15
- hurt +0.08
- safety -0.05

### Долгий разрыв
- social_need +0.07
- loneliness +0.05
- hurt +0.03 если attachment высокий

## Что должен сделать Cursor
1. Реализовать state update rules в отдельном сервисе.
2. После каждого события создавать новый snapshot.
3. Не мутировать старый snapshot in place без истории.

## Критерий готовности
- состояние обновляется предсказуемо;
- можно посмотреть историю состояния;
- ответы начинают меняться в зависимости от state.

---

# ШАГ 9. Реализовать Bond Service

## Цель
Отдельно хранить отношения, а не путать их с текущим тоном.

## Основные функции
- get_or_create_primary_relationship()
- update_relationship_after_event()
- detect_repair_signal()
- compute_relation_warmth()

## Логика
Если пользователь был груб:
- не рушить сразу trust;
- учитывать историю;
- различать текущее состояние и общий образ человека.

## Критерий готовности
- у пользователя есть relationship card;
- разовая грубость не стирает близость;
- “ремонт отношений” возможен.

---

# ШАГ 10. Реализовать gap detection

## Цель
Дать ощущение реального времени.

## Механика
После каждого входящего сообщения вычислять:
- сколько прошло с последнего контакта;
- насколько это типично;
- стоит ли отразить gap в ответе.

## Derived fields
- `hours_since_last_contact`
- `absence_abnormality_score`
- `usual_contact_window_score`

## Что должен сделать Cursor
1. Реализовать helper/service для gap detection.
2. Прокидывать gap context в orchestrator.
3. Использовать это в ответе и инициативе.

## Критерий готовности
Если пользователь пропал надолго, нейродруг это замечает.

---

# ШАГ 11. Реализовать Initiative Engine Lite

## Цель
Сделать первые самостоятельные исходящие сообщения.

## На MVP достаточно
- простого score;
- ограничения по частоте;
- уважения quiet mode.

## Базовая формула
```text
initiative_score =
  0.30 * gap_factor +
  0.20 * unfinished_topic_factor +
  0.15 * social_need +
  0.10 * loneliness +
  0.10 * concern_factor +
  0.10 * usual_contact_window_factor +
  0.05 * relation_warmth
```

## Что должен сделать Cursor
1. Реализовать сервис расчёта инициативы.
2. Хранить last outbound initiative.
3. Не позволять спамить.
4. Генерировать короткое инициативное сообщение через orchestrator.

## На старте хватит 3 сценариев
1. Пользователь давно пропал.
2. Осталась незакрытая важная тема.
3. Был напряжённый разговор, потом тишина.

## Критерий готовности
Нейродруг иногда пишет первым уместно и не липнет.

---

# ШАГ 12. Реализовать daily consolidation job

## Цель
Сделать постепенное взросление памяти.

## Что делает джоба
- агрегирует события за день;
- создаёт summary;
- повышает вес повторяющихся паттернов;
- понижает доступность шума;
- обновляет relationship summaries.

## Что должен сделать Cursor
1. Создать background worker.
2. Сканировать события за сутки.
3. Формировать 1–N summary memories.
4. Пересчитывать access/decay scores.

## Критерий готовности
Память начинает быть не “простынёй логов”, а системой смыслов.

---

# ШАГ 13. Сделать Flutter onboarding

## Цель
Дать пользователю создать нейродруга как личность.

## Экраны
1. Welcome
2. Имя нейродруга
3. Пол / возрастной образ
4. Архетип
5. Характер (ползунки)
6. Стиль общения
7. Инициативность
8. Подтверждение identity lock
9. Завершение и получение первого сообщения

## Важно
UI должен передавать ощущение:
- создаётся не бот;
- создаётся кто-то со своим характером.

## Критерий готовности
Пользователь может пройти onboarding и создать нейродруга без ручного API.

---

# ШАГ 14. Сделать Flutter chat screen

## Цель
Собрать первое живое общение.

## Экран должен уметь
- показывать историю;
- отправлять текст;
- получать ответ;
- показывать typing state;
- показывать первое интро;
- отображать время сообщений.

## Желательно
- небольшой блок профиля нейродруга;
- имя и краткий архетип в header;
- мягкая визуальная дифференциация исходящих/входящих.

## Критерий готовности
Можно реально пообщаться и получить ощущение непрерывности.

---

# ШАГ 15. Настройки

## Минимальные настройки MVP
- режим инициативы: Active / Balanced / Quiet / Manual only
- уведомления on/off
- локаль
- timezone
- разрешение на будущий голос
- разрешение на будущую камеру

## Что не давать менять
- архетип
- базовое ядро личности

## Критерий готовности
Пользователь контролирует степень присутствия нейродруга, не ломая его сущность.

---

# ШАГ 16. Qdrant integration

## Цель
Сделать смысловую память реально работающей.

## Что должен сделать Cursor
1. Создать adapter для embeddings.
2. Создать adapter для upsert/search в Qdrant.
3. Сохранять embeddings для:
   - MemoryItem
   - summaries
   - relationship anchors
4. Искать top-k релевантных memories по:
   - текущему сообщению;
   - user context;
   - gap context.

## На старте можно
- использовать одну коллекцию;
- фильтровать по `neurofriend_id` и `memory_type`.

## Критерий готовности
LLM получает не только последние сообщения, но и “смысловую биографию”.

---

# ШАГ 17. Tests

## Что нужно покрыть тестами

### Unit tests
- scoring memory importance
- affect updates
- bond updates
- initiative score
- gap detection

### Integration tests
- create neurofriend
- send message
- save memory
- retrieve memory
- generate reply

### E2E smoke
- onboarding → intro → first user message → answer

## Критерий готовности
Есть минимальный защитный слой от регрессий.

---

# ШАГ 18. Прямые указания Cursor по генерации кода

Cursor должен:
- писать код модульно;
- использовать typing везде;
- не смешивать domain logic и API routes;
- делать Pydantic schemas отдельно;
- не класть бизнес-правила в random utility files;
- не делать giant service “god object” на всё;
- закладывать расширение на future states;
- писать TODO-комментарии в местах, где позже подключатся voice/vision.

Cursor не должен:
- жёстко хардкодить весь характер в один giant prompt;
- терять immutable archetype;
- упрощать память до plain chat history;
- делать инициативу случайным `if random()`;
- писать всю логику только в controller/route.

---

# ШАГ 19. Минимальный roadmap по неделям

## Неделя 1
- backend skeleton
- docker-compose
- models
- migrations
- create neurofriend endpoint

## Неделя 2
- send message endpoint
- LLM orchestrator
- affect service
- bond service
- memory save

## Неделя 3
- Qdrant retrieval
- gap detection
- initiative lite
- daily consolidation

## Неделя 4
- Flutter onboarding
- Flutter chat
- settings
- integration polish

---

# ШАГ 20. Definition of Done этого build plan

Считать этап успешным, если:

1. Пользователь создаёт нейродруга через мобильный onboarding.
2. Нейродруг знакомится сам.
3. Общение идёт через backend с памятью.
4. Личность стабильна.
5. Нейродруг помнит важное.
6. Он замечает пропуски.
7. Он может иногда писать первым.
8. Он слегка перенимает стиль пользователя.
9. Архетип не меняется.
10. Кодовая база готова к добавлению голоса, камеры и новых состояний.

---

# ШАГ 21. Что будет следующим документом

После этого шага логично сделать:
- `NeuroFriend_Backend_Task_Pack.md`
- `NeuroFriend_Flutter_Task_Pack.md`
- `NeuroFriend_Prompt_Contracts.md`
- `NeuroFriend_DB_Schema.sql`
- `NeuroFriend_API_OpenAPI.yaml`

Но для старта этот файл уже должен позволить Cursor начать писать MVP.

---

# 22. Прямая команда для Cursor

Используй этот документ как build plan.
Начни с backend skeleton и docker-compose.
Потом реализуй SQLAlchemy модели и миграции.
Затем сделай создание нейродруга, отправку сообщений и LLM orchestrator.
После этого подключи память, state, отношения, gap detection и initiative lite.
Затем собери Flutter onboarding и chat.
Не упрощай нейродруга до обычного AI-чата.
Главная цель MVP — создать эффект непрерывного живого присутствия.
