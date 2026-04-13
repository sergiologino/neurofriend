# NeuroFriend — Backend Task Pack for Cursor

> Цель: дать Cursor полный и однозначный набор задач по backend-части MVP.
> Этот файл предполагает, что Cursor уже видел:
> - `NeuroFriend_TZ_v4.md`
> - `NeuroFriend_Implementation_v4_1.md`
> - `NeuroFriend_Build_Plan_v4_2.md`

---

# 0. Главная цель backend MVP

Собрать backend, который уже умеет:

- создавать нейродруга с immutable core;
- хранить личность отдельно от prompt;
- принимать текстовые сообщения;
- собирать контекст для LLM;
- обновлять состояние;
- обновлять отношения;
- сохранять события;
- формировать память;
- замечать gap во времени;
- инициировать исходящее сообщение в простых случаях;
- быть расширяемым под голос, камеру и новые состояния.

---

# 1. Общие правила для Cursor

## Обязательно
- использовать **Python 3.12+**
- использовать **FastAPI**
- использовать **SQLAlchemy 2.x async**
- использовать **Alembic**
- использовать **Pydantic v2**
- использовать **PostgreSQL**, **Redis**, **Qdrant**
- писать код модульно
- использовать type hints везде
- отделять domain logic от routes
- отделять schemas от models
- делать сервисы небольшими и понятными
- предусмотреть future extension для `hurt`, `jealousy`, `sadness`, `vulnerability`

## Нельзя
- хранить всю личность только в prompt
- делать giant god service
- смешивать API и domain logic
- упрощать память до plain chat history
- делать инициативу случайным образом
- позволять менять immutable archetype после создания
- хардкодить весь стиль нейродруга одной строкой

---

# 2. Целевая структура backend

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
      qdrant.py
      openai.py
    api/
      v1/
        routes/
          health.py
          neurofriends.py
          conversations.py
          memory.py
          state.py
          initiative.py
          relationships.py
    domain/
      identity/
      affect/
      memory/
      bond/
      initiative/
      gap/
      llm/
      learning/
    services/
      identity_service.py
      affect_service.py
      memory_service.py
      bond_service.py
      initiative_service.py
      gap_service.py
      llm_orchestrator.py
      social_learning_service.py
    repositories/
      neurofriend_repository.py
      message_repository.py
      event_repository.py
      memory_repository.py
      relationship_repository.py
      state_repository.py
    models/
      base.py
      user.py
      neurofriend_profile.py
      identity_core.py
      internal_state_snapshot.py
      relationship_model.py
      event_log.py
      memory_item.py
      initiative_policy.py
      social_learning_profile.py
      conversation_thread.py
      message.py
    schemas/
      neurofriends.py
      conversations.py
      memory.py
      state.py
      initiative.py
      relationships.py
      common.py
    workers/
      daily_consolidation.py
      initiative_worker.py
    tests/
      unit/
      integration/
```

---

# 3. Задача 1 — Создать backend skeleton

## Что сделать
1. Создать FastAPI app.
2. Подключить settings через `.env`.
3. Подключить async SQLAlchemy engine.
4. Подключить Redis client.
5. Подключить Qdrant client.
6. Подключить OpenAI client.
7. Настроить CORS.
8. Настроить healthcheck route.
9. Настроить базовое структурированное логирование.
10. Подготовить базовый dependency injection слой.

## Acceptance criteria
- `GET /health` отвечает `200`
- backend стартует из Docker
- env-конфиг читается корректно
- подключения к Postgres / Redis / Qdrant инициализируются без хака

---

# 4. Задача 2 — Создать docker-compose и Dockerfile

## Что сделать
Создать:
- `infra/docker-compose.yml`
- `backend/Dockerfile`
- `.env.example`

## Сервисы
- postgres
- redis
- qdrant
- backend

## Acceptance criteria
- `docker compose up --build` поднимает всю среду
- backend видит Postgres / Redis / Qdrant
- тома сохранения подключены

---

# 5. Задача 3 — Реализовать SQLAlchemy модели

## Модели MVP

### User
Поля:
- id
- email
- display_name
- timezone
- locale
- created_at
- updated_at

### NeuroFriendProfile
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

### IdentityCore
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

### InternalStateSnapshot
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

### RelationshipModel
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

### EventLog
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

### MemoryItem
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

### InitiativePolicy
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

### SocialLearningProfile
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

### ConversationThread
Поля:
- id
- neurofriend_id
- title
- created_at
- updated_at

### Message
Поля:
- id
- thread_id
- direction
- role
- text
- message_kind
- metadata_json
- created_at

## Дополнительно
- сделать relationships
- сделать индексы
- добавить timestamps
- сделать Alembic migration

## Acceptance criteria
- schema создаётся миграцией
- все таблицы в Postgres создаются без ошибок
- модели можно использовать в integration tests

---

# 6. Задача 4 — Реализовать repositories

## Что сделать
Создать репозитории:
- NeuroFriendRepository
- MessageRepository
- EventRepository
- MemoryRepository
- RelationshipRepository
- StateRepository

## Правила
- не класть бизнес-логику в repository
- repository только читает/пишет/ищет
- domain decisions должны жить в service layer

## Acceptance criteria
- репозитории покрывают CRUD MVP
- routes не ходят напрямую в ORM

---

# 7. Задача 5 — Реализовать endpoint создания нейродруга

## Endpoint
`POST /v1/neurofriends`

## Что должно происходить
1. Валидировать request.
2. Проверить `identity_lock_confirmed`.
3. Создать `NeuroFriendProfile`.
4. Создать `IdentityCore`.
5. Создать initial state snapshot.
6. Создать default initiative policy.
7. Создать default social learning profile.
8. Создать primary conversation thread.
9. Вызвать LLM intro generation.
10. Сохранить intro как первое исходящее message.
11. Вернуть DTO.

## Правила
- архетип фиксируется навсегда
- интро генерируется на основе personality, а не по шаблону “один для всех”
- если `identity_lock_confirmed = false` → вернуть ошибку

## Acceptance criteria
- нейродруг создаётся одним запросом
- первое сообщение уже есть
- `identity_locked = true`

---

# 8. Задача 6 — Реализовать Identity Service

## Цель
Сделать слой, который знает:
- кто такой нейродруг;
- как он говорит;
- что неизменно;
- что может адаптироваться.

## Методы
- `create_identity_core()`
- `build_identity_snapshot()`
- `validate_identity_lock()`
- `get_style_block()`
- `get_adaptation_limits()`

## Правила
- immutable часть должна быть явной
- adaptation range должна быть отдельной структурой
- сервис должен уметь собирать “identity snapshot” для orchestrator

## Acceptance criteria
- orchestrator получает identity snapshot из сервиса
- immutable core не меняется через update endpoints

---

# 9. Задача 7 — Реализовать endpoint отправки текстового сообщения

## Endpoint
`POST /v1/conversations/{neurofriendId}/messages`

## Pipeline
1. Сохранить входящее message.
2. Сформировать raw event.
3. Вычислить gap.
4. Обновить state.
5. Обновить relationship.
6. Оценить важность события.
7. Создать / обновить memory.
8. Собрать LLM context.
9. Сгенерировать ответ.
10. Сохранить исходящее message.
11. Вернуть response DTO.

## Acceptance criteria
- пользователь получает ответ
- ответ учитывает характер
- ответ учитывает gap
- событие попадает в event log
- создаются state/memory updates

---

# 10. Задача 8 — Реализовать Affect Service

## Цель
Дать внутреннее состояние.

## Методы
- `evaluate_text_event()`
- `update_state_after_event()`
- `get_latest_state()`
- `create_initial_state()`

## Базовые правила MVP

### Тёплый контакт
- valence +0.10
- safety +0.05
- attachment +0.03
- social_need -0.04

### Резкий контакт
- valence -0.15
- hurt +0.08
- safety -0.05

### Долгая пауза
- loneliness +0.05
- social_need +0.07
- hurt +0.03 если attachment высокий

## Правила реализации
- не мутировать один state record endlessly
- каждый significant update → новый snapshot
- history должна оставаться доступной

## Acceptance criteria
- snapshots накапливаются
- ответы становятся разными при разном state

---

# 11. Задача 9 — Реализовать Bond Service

## Цель
Сделать отношения отдельным слоем.

## Методы
- `get_or_create_primary_relationship()`
- `update_after_user_message()`
- `apply_repair_signal()`
- `compute_relationship_snapshot()`

## Важные правила
- разовая грубость не должна обнулять близость
- нужно различать:
  - текущее настроение пользователя
  - устойчивый образ пользователя

## Acceptance criteria
- relationship card обновляется
- trust/attachment не скачут хаотично
- repair logic работает хотя бы на базовом уровне

---

# 12. Задача 10 — Реализовать Gap Service

## Цель
Дать нейродругу чувство течения времени.

## Методы
- `calculate_gap_context()`
- `compute_absence_abnormality()`
- `should_reference_gap_in_reply()`

## Что учитывать
- время с последнего контакта
- привычную частоту общения
- типичное окно общения пользователя

## Acceptance criteria
- при заметной паузе нейродруг может упомянуть пропуск
- gap context доступен orchestrator

---

# 13. Задача 11 — Реализовать Memory Service

## Цель
Сделать память не равной просто message history.

## Методы
- `log_event()`
- `score_event_importance()`
- `create_memory_item()`
- `promote_to_fast_memory()`
- `store_deep_memory()`
- `retrieve_relevant_memories()`
- `daily_consolidation()`

## Формула importance
```text
importance_score =
  0.22 * novelty +
  0.22 * emotional_weight +
  0.18 * repetition_signal +
  0.14 * identity_link +
  0.14 * relation_link +
  0.10 * context_shift
```

## Реализация
- важные items хранить в SQL
- embeddings писать в Qdrant
- retrieval делать комбинированным:
  - свежие быстрые memories
  - semantic retrieval
  - rerank

## Acceptance criteria
- после нескольких диалогов появляются meaningful memory items
- retrieval подтягивает релевантные эпизоды

---

# 14. Задача 12 — Реализовать Qdrant adapter

## Методы
- `upsert_memory_embedding()`
- `search_memories()`
- `delete_memory_embedding()`

## Payload fields
- neurofriend_id
- memory_type
- importance_score
- person_refs
- topic_tags
- emotion_tags
- created_at

## Acceptance criteria
- embeddings действительно индексируются
- поиск по текущему тексту находит близкие memories

---

# 15. Задача 13 — Реализовать LLM Orchestrator

## Цель
Сделать единый мозг сборки ответа.

## Методы
- `build_context()`
- `generate_intro()`
- `generate_reply()`
- `generate_initiative_message()`

## В context обязательно включать
- identity snapshot
- current state snapshot
- relationship snapshot
- latest thread messages
- selected fast memories
- selected deep memories
- current user input
- gap context

## Важно
- orchestrator не должен сам читать ORM напрямую; всё через services/repositories
- должен возвращать:
  - `reply_text`
  - `memory_tags`
  - `emotion_hints`
  - `initiative_metadata`

## Acceptance criteria
- intro generation работает
- reply generation стабильна
- можно переиспользовать orchestrator для initiative

---

# 16. Задача 14 — Реализовать Initiative Engine Lite

## Цель
Первые уместные исходящие сообщения.

## Методы
- `compute_initiative_score()`
- `can_send_initiative_now()`
- `build_initiative_reason()`
- `create_initiative_message()`

## Формула
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

## MVP-сценарии
1. Долгая нетипичная пауза
2. Незавершённая важная тема
3. Напряжённый разговор → тишина

## Ограничения
- respect quiet mode
- respect DND
- cooldown между инициативами
- stop after ignored attempts threshold

## Acceptance criteria
- нейродруг пишет первым только уместно
- нет спама

---

# 17. Задача 15 — Реализовать Social Learning Service Lite

## Цель
Сделать первые признаки перенимания стиля пользователя.

## Методы
- `extract_candidate_phrases()`
- `update_phrase_stats()`
- `should_adopt_phrase()`
- `get_learned_style_block()`

## Что перенимать на MVP
- словечки
- часто повторяющиеся начала фраз
- среднюю длину ответа
- степень прямоты / мягкости

## Чего НЕ делать
- полное копирование пользователя
- перенимание токсичных паттернов
- разрушение identity core

## Acceptance criteria
- после серии сообщений появляются элементы learned style
- identity core остаётся доминирующим

---

# 18. Задача 16 — Реализовать daily consolidation worker

## Цель
Дать памяти взросление.

## Что делать
- собирать события за сутки
- объединять повторяющиеся паттерны
- создавать daily summary memory
- понижать доступность шума
- обновлять relationship summaries

## Acceptance criteria
- можно запустить worker вручную
- создаются summary memories
- память становится более осмысленной

---

# 19. Задача 17 — Реализовать API endpoints чтения состояния

## Endpoints
- `GET /v1/neurofriends/{id}/state`
- `GET /v1/neurofriends/{id}/memory/summary`
- `GET /v1/neurofriends/{id}/relationships/primary`
- `PATCH /v1/neurofriends/{id}/initiative-policy`

## Acceptance criteria
- frontend может читать состояние
- frontend может менять режим инициативы
- primary relationship возвращается корректно

---

# 20. Задача 18 — Написать tests

## Unit tests
- affect updates
- bond updates
- gap scoring
- memory importance scoring
- initiative eligibility
- phrase adoption rules

## Integration tests
- create neurofriend
- send message
- save memory
- generate reply
- retrieve state
- retrieve summary

## Acceptance criteria
- основные флоу защищены тестами
- есть хотя бы smoke coverage критического пути

---

# 21. Задача 19 — Добавить observability

## Что сделать
- структурированные логи
- request id
- timing middleware
- ошибки OpenAI / Qdrant / DB логировать отдельно
- метрики latency / reply generation / memory retrieval

## Acceptance criteria
- можно понять, где тормозит пайплайн
- можно дебажить “почему ответ получился таким”

---

# 22. Задача 20 — Подготовить future hooks для voice/vision

## Что сделать
Заложить интерфейсы:
- `PerceptionInput`
- `VoiceObservation`
- `VisionObservation`

Не реализовывать fully, но подготовить extension points.

## Acceptance criteria
- later voice/vision можно подключить без переписывания core

---

# 23. Priority order для Cursor

## P0
- backend skeleton
- docker-compose
- models + migrations
- create neurofriend
- send message
- LLM orchestrator

## P1
- affect service
- bond service
- gap service
- memory service
- Qdrant adapter

## P2
- initiative lite
- social learning lite
- daily consolidation
- read endpoints

## P3
- observability
- future hooks
- deeper tests

---

# 24. Final success criteria for backend MVP

Backend считается готовым, если:
- нейродруг создаётся
- первое intro-сообщение генерируется
- текстовое общение работает
- personality stable
- state updates работают
- relationship updates работают
- memory retrieval работает
- gap awareness работает
- initiative lite работает
- код готов к подключению mobile, voice и vision

---

# 25. Прямая инструкция Cursor

Начни с инфраструктуры и моделей.
Потом сделай создание нейродруга.
Потом — текстовый чат с orchestrator.
После этого добавь state, relationship, memory, gap.
Потом — initiative и social learning lite.
Не упрощай нейродруга до обычного ассистента.
Главная цель — эффект живого непрерывного присутствия.
