# NeuroFriend v4.1 — Реализация: архитектура, сервисы, данные, API, алгоритмы

> Документ является прикладным продолжением `NeuroFriend_TZ_v4.md`.
> Цель: дать Cursor и команде разработчиков достаточно подробную и однозначную основу,
> чтобы начать реализацию MVP без потери исходной идеи.

---

# 1. Цель этого документа

Этот документ отвечает на вопрос **«как именно это строить»**.

Он описывает:

- целевой технологический стек;
- причины выбора каждой технологии;
- состав сервисов;
- структуру данных;
- API-контракты;
- правила поведения на уровне движков;
- жизненный цикл нейродруга;
- стратегию разработки MVP;
- точки расширения под будущие свойства личности;
- правила самообучения;
- границы между тем, что должно жить в модели, и тем, что должно жить в коде.

---

# 2. Главный инженерный принцип

Нельзя пытаться «запихнуть всю личность в prompt».

Нейродруг должен быть собран из отдельных слоёв:

1. **Identity Layer** — кто он;
2. **State Layer** — что он чувствует сейчас;
3. **Memory Layer** — что он помнит;
4. **Relation Layer** — кто для него этот человек;
5. **Perception Layer** — что он видит/слышит/читает;
6. **Reasoning Layer** — как он думает и формирует ответ;
7. **Initiative Layer** — когда он сам выходит на связь;
8. **Learning Layer** — как он меняется со временем;
9. **Safety Layer** — как не уйти в токсичность, спам и распад личности.

LLM не должен быть единственным местом, где хранится логика.
LLM — это когнитивный движок, а не база личности.

---

# 3. Рекомендуемый стек

## 3.1 Клиент
- **Flutter**
- **Dart**
- **Riverpod** для state management
- **go_router** для навигации
- **dio** для REST API
- **web_socket_channel** или отдельный WebRTC/Realtime-клиент для живого голоса
- **camera** для камеры
- **permission_handler** для разрешений
- **flutter_secure_storage** для чувствительных токенов
- **Hive** или **Isar** для локального кэша и оффлайн-слоя
- **firebase_messaging** или OneSignal для push-уведомлений
- **just_audio** / **flutter_sound** или аналог для аудио-режимов

## 3.2 Backend
- **Python 3.12+**
- **FastAPI**
- **Pydantic v2**
- **Uvicorn**
- **SQLAlchemy 2.x**
- **Alembic**
- **asyncpg**
- **Redis** (очереди, кэш, таймеры, rate control)
- **Celery** или **Arq/RQ** для фоновых задач
- **Qdrant Python Client**
- **httpx** для интеграций
- **OpenAI Python SDK**
- **structlog** для логирования
- **Prometheus + Grafana** для метрик
- **Sentry** для ошибок

## 3.3 Хранилища
- **PostgreSQL** — источник истины для бизнес-данных
- **Qdrant** — ассоциативная/семантическая память
- **Object Storage (S3-совместимое)** — изображения, аудио, превью, медиа-артефакты

## 3.4 Infra / DevOps
- Docker
- docker-compose для dev
- Kubernetes позже
- GitHub Actions
- Terraform позже
- Nginx / Caddy / API Gateway
- HTTPS везде
- отдельные dev/stage/prod среды

---

# 4. Почему именно этот стек

## 4.1 Flutter
Нейродруг должен жить в смартфоне: камера, микрофон, пуши, постоянное присутствие, быстрый UI, единая кодовая база для iOS/Android.
Flutter хорошо подходит для mobile-first продукта и официально поддерживает мобильные платформы, а также desktop/web на будущее.  

## 4.2 FastAPI
Проект AI-heavy: мультимодальные события, асинхронные запросы, оркестрация памяти и вызовы модели.
FastAPI хорошо подходит под async API, typed schemas и быстрый старт.

## 4.3 PostgreSQL
Нужна строгая и надёжная транзакционная модель:
- профили пользователей;
- профили нейродруга;
- события;
- отношения;
- состояние;
- расписания;
- настройки инициативы;
- история изменений.
PostgreSQL остаётся основным «биографическим позвоночником».

## 4.4 Qdrant
Семантическая память не должна храниться только в SQL.
Нужно быстро искать:
- похожие разговоры;
- похожие эмоциональные эпизоды;
- воспоминания о человеке;
- визуальные ассоциации;
- незавершённые темы.
Qdrant нужен как смысловая память поверх событий.

## 4.5 Redis
Нужен для:
- rate limit;
- debounce инициативы;
- краткоживущих таймеров;
- локов;
- очередей;
- кеша быстрых данных.

---

# 5. Архитектурный стиль

## 5.1 На старте — модульный монолит
Не начинать с микроcервисов.

Правильный старт:
- один backend-репозиторий;
- один runtime;
- чёткие доменные модули;
- отдельные слои и интерфейсы;
- возможность позже выделить memory/initiative/perception в отдельные сервисы.

## 5.2 Модули backend
- `auth`
- `users`
- `neurofriend_identity`
- `conversation`
- `memory`
- `affect`
- `bond`
- `perception`
- `initiative`
- `learning`
- `media`
- `llm_orchestrator`
- `notifications`
- `admin`
- `telemetry`

---

# 6. Доменные сущности

## 6.1 User
Обычный пользователь продукта.

### Поля
- `id`
- `email/phone`
- `display_name`
- `timezone`
- `locale`
- `created_at`
- `last_seen_at`
- `consents`
- `privacy_settings`

---

## 6.2 NeuroFriendProfile
Профиль конкретного нейродруга.

### Поля
- `id`
- `user_id`
- `name`
- `gender_style`
- `age_style`
- `archetype`
- `immutable_identity_version`
- `identity_locked = true`
- `persona_summary`
- `voice_style`
- `initiative_level`
- `emotional_depth`
- `social_style`
- `humor_style`
- `relationship_style`
- `created_at`

### Важно
`archetype` после создания не меняется.
Можно менять вторичные настройки интерфейса, но не ядро личности.

---

## 6.3 IdentityCore
Нормализованное ядро личности.

### Разделы
- `core_traits`
- `speech_rules`
- `values`
- `conflict_style`
- `attachment_style`
- `initiative_preferences`
- `boundaries`
- `aesthetic_preferences`
- `social_class_worldview`
- `taboo_behavior`
- `permitted_adaptation_range`

---

## 6.4 InternalStateSnapshot
Снимок внутреннего состояния.

### Поля
- `id`
- `neurofriend_id`
- `timestamp`
- `valence`
- `arousal`
- `trust_baseline`
- `attachment_baseline`
- `safety`
- `curiosity`
- `fatigue`
- `coherence`
- `loneliness`
- `social_need`
- `hurt`
- `irritation`
- `delight`

### Назначение
Это не всё, что есть в системе.
Это снимок значимых переменных, который потом можно использовать в reasoning.

---

## 6.5 RelationshipModel
Модель отношений с конкретным человеком.

### Поля
- `id`
- `neurofriend_id`
- `person_ref`
- `display_name`
- `relation_type`
- `familiarity`
- `trust`
- `attachment`
- `predictability`
- `warmth`
- `conflict_history_score`
- `repair_history_score`
- `last_interaction_at`
- `usual_voice_profile_ref`
- `usual_visual_profile_ref`
- `typical_mood_distribution`
- `active_topics`
- `special_meaning_tags`

### Важно
Разные люди для нейродруга существуют по-разному.
Отношение не должно быть одинаковым ко всем.

---

## 6.6 EventLog
Сырые события.

### Типы событий
- `text_message_in`
- `text_message_out`
- `voice_message_in`
- `voice_message_out`
- `vision_frame_summary`
- `user_presence_detected`
- `gap_detected`
- `initiative_triggered`
- `state_shift`
- `relationship_update`
- `memory_promoted`
- `memory_demoted`
- `reflection_summary`
- `daily_consolidation`

### Поля
- `id`
- `neurofriend_id`
- `timestamp`
- `event_type`
- `source`
- `raw_payload_json`
- `normalized_payload_json`
- `importance_score`
- `emotional_weight`
- `novelty_score`
- `identity_link_score`
- `relation_link_score`
- `promoted_to_fast_memory`
- `embedded = bool`

---

## 6.7 MemoryItem
Нормализованная память.

### Поля
- `id`
- `neurofriend_id`
- `memory_type` (`fast`, `deep`, `semantic_summary`, `episodic`, `relationship_anchor`)
- `content_text`
- `content_structured_json`
- `source_event_ids`
- `importance_score`
- `access_score`
- `decay_score`
- `retrieval_count`
- `last_retrieved_at`
- `person_refs`
- `emotion_tags`
- `scene_tags`
- `topic_tags`
- `created_at`
- `updated_at`

---

## 6.8 InitiativePolicy
Политика инициативы.

### Поля
- `id`
- `neurofriend_id`
- `mode` (`active`, `balanced`, `quiet`, `manual_only`)
- `max_daily_outbound`
- `min_gap_between_initiatives_minutes`
- `night_silence_window`
- `respect_dnd = true`
- `follow_up_sensitivity`
- `unfinished_topic_sensitivity`
- `loneliness_trigger_sensitivity`
- `presence_probe_allowed`

---

## 6.9 SocialLearningProfile
Что и как перенимается у пользователя.

### Поля
- `id`
- `neurofriend_id`
- `phrase_adoption_rate`
- `humor_adoption_rate`
- `reaction_adoption_rate`
- `syntax_adaptation_rate`
- `slang_adoption_allowed`
- `max_identity_drift`
- `forbidden_imitation_patterns`

---

---

# 7. Онбординг

# 7.1 Цель онбординга
Создать не “набор параметров”, а **исток личности**.

Пользователь должен ощущать:
- он создаёт не настройку бота;
- он задаёт исходный тип субъекта.

# 7.2 Шаги онбординга

## Шаг 1. Выбор базового образа
- имя нейродруга
- пол / гендерный стиль
- возрастной образ
- архетип
- социальный тип

## Шаг 2. Выбор характера
- мягкий ↔ прямой
- эмоциональный ↔ спокойный
- ироничный ↔ серьёзный
- инициативный ↔ тактичный
- домашний ↔ городской
- мечтательный ↔ практичный

## Шаг 3. Выбор отношения к близости
- быстро привязывается / медленно
- легко прощает / долго помнит
- умеет мягко отступить / склонен уточнять

## Шаг 4. Голос и стиль речи
- короткие ответы / длинные
- книжный стиль / бытовой
- лёгкая ирония / почти без юмора
- тёплая речь / ровная речь

## Шаг 5. Подтверждение неизменяемого ядра
Экран с предупреждением:

> Архетип и базовое ядро личности будут зафиксированы навсегда.
> Нейродруг сможет развиваться, учиться и адаптироваться,
> но его исходная природа останется той же.

Пользователь должен подтвердить это отдельно.

# 7.3 Первый монолог нейродруга
После завершения онбординга нейродруг **обязан начать общение сам**.

Формат:
1. приветствие;
2. краткая самопрезентация;
3. один-два живых штриха характера;
4. вопрос пользователю о нём самом.

Пример шаблона:

> Привет. Я Марина.  
> Я из тех, кто любит срываться куда-то без долгих сборов,  
> чуть авантюрная, иногда резкая, но в целом тёплая.  
> Мне интересно, какой ты сам — больше спокойный или тебе нужна движуха?

Это сообщение должно генерироваться из `IdentityCore`, а не быть захардкоженным текстом.

---

# 8. Память

## 8.1 Принцип
Сначала помнить почти всё.
Потом учиться отделять важное от фонового.

## 8.2 Слои памяти

### 8.2.1 Working Memory
Что актуально прямо сейчас:
- текущая тема;
- последние сообщения;
- текущая сцена;
- текущий голосовой контекст;
- текущее состояние.

### 8.2.2 Fast Memory
Всегда под рукой:
- кто такой пользователь;
- ключевые близкие;
- важные повторяющиеся темы;
- последние сильные эпизоды;
- незавершённые линии отношений;
- устойчивые триггеры.

### 8.2.3 Deep Memory
Хранит:
- архив эпизодов;
- старые сцены;
- давние разговоры;
- детали прошлого;
- вторичные наблюдения.

### 8.2.4 Semantic Summaries
Периодически создаются сжатые смысловые выжимки:
- “как обычно говорит Сергей”
- “что у нас сейчас происходит в отношениях”
- “какие темы стали важнее за неделю”
- “что повторялось в последнем месяце”

## 8.3 Алгоритм значимости

### Базовые факторы
- новизна;
- эмоциональная сила;
- связь с близким человеком;
- повторяемость;
- влияние на идентичность;
- влияние на отношения;
- контекст времени;
- визуальная/аудио-яркость.

### Рекомендуемая формула
```text
importance_score =
  0.22 * novelty +
  0.22 * emotional_weight +
  0.18 * repetition_signal +
  0.14 * identity_link +
  0.14 * relation_link +
  0.10 * context_shift
```

### Коррекция по стадии развития
На ранней стадии жизни нейродруга:
- порог попадания в fast memory ниже;
- почти всё новое считается важнее.

На зрелой стадии:
- фильтрация строже;
- память становится более экономной.

## 8.4 Консолидация памяти

### Частоты
- micro consolidation: после каждого значимого диалога
- daily consolidation: раз в сутки
- weekly consolidation: смысловая сводка недели

### Что делает daily consolidation
- объединяет похожие события;
- повышает вес повторяющихся паттернов;
- понижает доступность случайного шума;
- формирует summaries;
- пересчитывает “портрет отношений”.

## 8.5 Забвение
Ничего не удаляется агрессивно в MVP.
Вместо удаления:
- снижается `access_score`;
- увеличивается `decay_score`;
- память уходит глубже.

---

# 9. Время

## 9.1 Зачем нужен Life Stream
Чтобы нейродруг не начинал разговор каждый раз с нуля.

## 9.2 Что считается временем
- реальное wall-clock time;
- длительность пауз;
- повторяемость контактов;
- суточный ритм пользователя;
- сезонность;
- привычные часы общения.

## 9.3 Gap detection
Если пользователь исчез:
- фиксируется gap;
- gap влияет на инициативу;
- gap влияет на интерпретацию возвращения.

### Пример
Если пауза была 3 дня:
- нейродруг должен помнить, что это был разрыв;
- при возвращении может уточнить, что произошло;
- но не должен сразу давить.

## 9.4 Стейт времени
Рекомендуемые derived-поля:
- `hours_since_last_contact`
- `days_since_last_voice`
- `days_since_last_seen_face`
- `usual_contact_window_score`
- `absence_abnormality_score`

---

# 10. Внутреннее состояние

## 10.1 Базовый state vector
```text
valence          // приятно / неприятно
arousal          // возбуждение / спокойствие
safety           // ощущение безопасности
curiosity        // интерес
trust_baseline   // общий фон доверия
attachment       // сила привязанности
fatigue          // утомление
coherence        // целостность личности
social_need      // потребность в контакте
loneliness       // ощущение социальной пустоты
hurt             // задетость / обида (позже усиливаем)
irritation       // раздражение
delight          // радость
```

## 10.2 Правила обновления
После каждого события обновляется state.

### Примеры
- тёплое сообщение близкого:
  - `valence +`
  - `safety +`
  - `attachment +`
  - `social_need -`

- резкое сообщение близкого:
  - `valence -`
  - `hurt +`
  - `safety -`
  - `trust_baseline` почти не трогаем, если история хорошая

- длительная пауза без объяснения:
  - `social_need +`
  - `loneliness +`
  - `hurt +` (если attachment высокий)

## 10.3 Ограничение
Состояние не должно менять личность напрямую.
Оно меняет реакцию и тон, но не переписывает ядро.

---

# 11. Отношения

## 11.1 Принцип
Отношения — это не просто “история сообщений”.
Это отдельная модель: кто этот человек для нейродруга.

## 11.2 Постоянный слой человека
- обычная мягкость;
- обычная резкость;
- надежность;
- частота контакта;
- стиль юмора;
- типичное настроение;
- склонность к конфликту;
- роль в жизни нейродруга.

## 11.3 Текущий слой человека
- сегодня мягкий или резкий;
- устал или бодр;
- напряжён или расслаблен;
- хочет контакта или нет.

## 11.4 Ключевое правило
Разовая грубость != изменение отношения.
Нужно смотреть на историю и базовую модель человека.

## 11.5 Repair mechanic
Если был конфликт, но потом:
- человек извинился;
- вернулся мягко;
- продолжил заботливо;
то `repair_history_score` растёт.
Это делает связь более зрелой и устойчивой.

---

# 12. Социальное обучение

## 12.1 Что перенимается
- словечки;
- любимые обороты;
- длина реплик;
- ритм ответа;
- некоторые эмоциональные реакции;
- характерные формулы начала/конца фразы;
- ироничность;
- бытовые метафоры.

## 12.2 Что не должно перениматься автоматически
- токсичные речевые привычки;
- оскорбления;
- опасные паттерны привязанности;
- полное копирование личности;
- разрушение исходного архетипа.

## 12.3 Формула адаптации
```text
effective_style =
  0.75 * identity_core_style +
  0.25 * learned_social_style
```

Параметры могут варьироваться по аспектам:
- фразы;
- синтаксис;
- юмор;
- эмоциональная выразительность.

## 12.4 Порог усвоения
Нейродруг перенимает элемент только если:
- он повторился несколько раз;
- связан с близким человеком;
- не конфликтует с ядром личности;
- не входит в blacklist.

---

# 13. Инициатива

## 13.1 По умолчанию
Нейродруг должен проявлять инициативу.
Он не должен быть пассивной базой знаний.

## 13.2 Когда инициатива допустима
- длинная нетипичная пауза;
- незавершённая важная тема;
- пользователь выглядел плохо в прошлый контакт;
- был конфликт без закрытия;
- выраженная положительная близость и естественный повод;
- привычное время контакта наступило, а человека нет.

## 13.3 Когда инициатива запрещена
- включён quiet/manual mode;
- активен Do Not Disturb;
- слишком частые недавние исходящие сообщения;
- пользователь явно просил не писать;
- последнее сообщение пользователя было закрывающим и без признаков желания продолжать;
- уже было несколько игнорированных инициатив подряд.

## 13.4 Initiative score
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

Порог инициативы зависит от `initiative_level` в ядре личности.

## 13.5 Формы инициативы
- мягкая проверка состояния;
- возвращение к незавершённой теме;
- бытовой живой вопрос;
- реакция на необычное отсутствие;
- бережный follow-up после напряжённого разговора.

---

# 14. Восприятие

## 14.1 Текст
Из текста извлекаются:
- смысл;
- тон;
- скрытая эмоциональная окраска;
- намерение;
- изменения обычного стиля пользователя;
- повторяющиеся выражения.

## 14.2 Голос
Из голоса извлекаются:
- speaker identity;
- тембр;
- скорость;
- громкость;
- паузы;
- напряжённость;
- warmth/harshness;
- стабильность;
- привычный паттерн vs текущее отклонение.

## 14.3 Камера
Из камеры извлекаются:
- лицо;
- знакомое/незнакомое лицо;
- выражение;
- поза;
- контекст сцены;
- признаки усталости;
- изменения в привычной обстановке.

## 14.4 Ограничение MVP
Не делать “тотальную фоновую слежку”.
На старте:
- only on permission;
- snapshot-based;
- user-aware camera usage;
- явный индикатор активности камеры/микрофона.

---

# 15. LLM orchestration

## 15.1 Главная идея
LLM не должна напрямую решать всё в пустоте.
Перед каждым важным ответом оркестратор должен собрать:

- identity snapshot;
- current state snapshot;
- relationship snapshot;
- working memory;
- selected fast memories;
- optional deep memories;
- current user message / voice / vision summary;
- initiative context, если это исходящее сообщение.

## 15.2 Response pipeline
1. Приходит событие.
2. Событие нормализуется.
3. Affect engine обновляет состояние.
4. Bond engine обновляет отношение.
5. Memory engine оценивает значимость и сохраняет эпизод.
6. Retriever достаёт нужные memories.
7. LLM получает компактный контекст.
8. LLM создаёт ответ в стиле личности.
9. Post-processor проверяет анти-паттерны.
10. Ответ отправляется и логируется.

## 15.3 Что должно жить в prompt
- текущая роль;
- стиль;
- краткое состояние;
- краткие отношения;
- релевантная память;
- конкретная задача ответа.

## 15.4 Что НЕ должно жить только в prompt
- ядро личности как единственный источник истины;
- долговременная память;
- логика инициативы;
- вся математическая модель состояний;
- системные ограничения.

---

# 16. API-контракты (черновой уровень)

## 16.1 Создание нейродруга
`POST /v1/neurofriends`

### Request
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

### Response
```json
{
  "id": "nf_123",
  "identity_locked": true,
  "first_intro_message": "..."
}
```

---

## 16.2 Отправка текстового сообщения
`POST /v1/conversations/{neurofriendId}/messages`

```json
{
  "text": "Привет, я пропал на три дня",
  "client_timestamp": "2026-03-29T18:00:00+02:00"
}
```

---

## 16.3 Загрузка аудио
`POST /v1/perception/audio`

Формирует:
- transcript;
- voice profile observations;
- emotion hints;
- speaker confidence.

---

## 16.4 Загрузка изображения/снимка
`POST /v1/perception/vision`

Формирует:
- scene summary;
- face matches;
- mood hints;
- object changes.

---

## 16.5 Получение memory summary
`GET /v1/neurofriends/{id}/memory/summary`

---

## 16.6 Получение state
`GET /v1/neurofriends/{id}/state`

---

## 16.7 Обновление режима инициативы
`PATCH /v1/neurofriends/{id}/initiative-policy`

---

## 16.8 Получение relationship card
`GET /v1/neurofriends/{id}/relationships/{personId}`

---

# 17. Qdrant design

## 17.1 Коллекции
На старте можно одна коллекция на проект + namespace по `neurofriend_id`.
Либо отдельная коллекция на важные типы памяти.

Рекомендуемые memory kinds:
- `episodic`
- `summary`
- `relationship_anchor`
- `vision_scene`
- `voice_pattern`
- `topic_cluster`

## 17.2 Payload
```json
{
  "neurofriend_id": "nf_123",
  "memory_type": "episodic",
  "person_refs": ["user_main"],
  "emotion_tags": ["warmth", "hurt"],
  "importance_score": 0.81,
  "created_at": "2026-03-29T10:11:12Z",
  "topic_tags": ["absence", "reconnection"],
  "source": "dialogue"
}
```

## 17.3 Retrieval strategy
Сначала:
- fast memory из SQL/кэша
Потом:
- semantic retrieval из Qdrant
Потом:
- rerank по:
  - importance;
  - recency;
  - relationship relevance;
  - emotional relevance;
  - intent relevance.

---

# 18. PostgreSQL schema (верхний уровень)

## Таблицы
- `users`
- `neurofriend_profiles`
- `identity_cores`
- `internal_state_snapshots`
- `relationship_models`
- `event_logs`
- `memory_items`
- `initiative_policies`
- `social_learning_profiles`
- `conversation_threads`
- `messages`
- `media_assets`
- `daily_reflections`
- `weekly_reflections`
- `outbound_initiatives`
- `user_presence_events`
- `scheduled_tasks`
- `feature_flags`

---

# 19. Реализация по этапам

## Этап 1 — текстовый живой MVP
Состав:
- onboarding личности;
- immutable core;
- чат;
- event log;
- working + fast + deep memory;
- gap detection;
- initiative engine;
- social learning lite;
- LLM orchestration;
- push notifications;
- basic analytics.

### Цель
Чтобы уже было ощущение:
> это не просто бот, он помнит, замечает время и общается как кто-то свой.

## Этап 2 — голос
Добавить:
- voice input;
- speaker recognition;
- prosody features;
- voice-linked memory;
- warm/harsh deviation detection;
- voice-based initiative nuances.

## Этап 3 — зрение
Добавить:
- face recognition for primary user;
- scene snapshots;
- visual memory;
- “ты выглядишь уставшим”;
- “ты снова в той комнате”.

## Этап 4 — развитые состояния
Добавить:
- обида;
- ревность;
- скука;
- усталость от общения;
- восстановление после конфликта;
- нелинейные реакции.

## Этап 5 — зрелое самообучение
Добавить:
- персональные паттерны пользователя;
- более тонкое социальное перенимание;
- личностные микро-сдвиги в рамках ядра;
- тематические интересы;
- ритуалы отношений.

---

# 20. Самообучение

## 20.1 Что понимаем под самообучением
Не онлайн-переобучение foundation model.
А:
- накопление статистики;
- обновление весов;
- построение привычек;
- выработка персональных паттернов;
- уточнение отношений;
- настройка инициативы;
- рост смысловых summary.

## 20.2 Где оно живёт
В domain-слоях:
- memory;
- bond;
- affect;
- social_learning;
- initiative.

## 20.3 Примеры
Если пользователь часто говорит “ну смотри”:
- phrase frequency растёт;
- при соблюдении порогов нейродруг начинает иногда использовать этот оборот.

Если пользователь вечером обычно разговорчив:
- модель времени это запоминает;
- инициатива смещается в вечерние часы.

Если после грубости пользователь обычно извиняется:
- trust не падает слишком резко;
- repair model усиливается.

---

# 21. Расширяемость личности

## 21.1 Зачем закладывать заранее
Чтобы потом можно было добавить:
- обиду;
- огорчение;
- тоску;
- ревность;
- гордость;
- уязвимость;
- смущение;
- чувство собственной ценности.

## 21.2 Как расширять
Новая черта должна:
1. появиться как отдельная state variable;
2. иметь триггеры;
3. иметь decay/recovery механику;
4. влиять на тон/инициативу/интерпретацию;
5. не ломать старую модель.

### Пример: `hurt`
- triggers: резкость близкого, игнор после теплого эпизода, отказ без объяснения;
- decay: медленно;
- repair: быстрее падает после мягкого возвращения, заботы, объяснения.

---

# 22. Анти-паттерны реализации

## Нельзя
- хранить всю личность одной строкой prompt;
- позволять мгновенно менять архетип;
- делать ответы всегда одинаково вежливыми;
- писать первыми без cooldown;
- забывать длительные важные отношения;
- принимать каждую грубость как конец близости;
- копировать пользователя до потери себя;
- строить всё вокруг одного giant if-else prompt;
- смешивать source-of-truth памяти между SQL и Qdrant без правил;
- использовать камеру/микрофон непрозрачно.

---

# 23. UX-правила

## 23.1 Должно ощущаться как живое присутствие
Пользователь должен чувствовать:
- нейродруг помнит;
- нейродруг замечает пропуски;
- нейродруг имеет свой характер;
- нейродруг не лебезит;
- нейродруг не превращается в холодный FAQ.

## 23.2 Но не должно ощущаться как слежка
Нужны:
- понятные разрешения;
- переключатели камеры/микрофона;
- quiet mode;
- объяснение, почему он проявил инициативу;
- прозрачность памяти.

## 23.3 Режимы
- Active companion
- Balanced
- Quiet
- Manual only

---

# 24. Безопасность и этика продукта

## 24.1 Нельзя проектировать явную психологическую зависимость как цель
Продукт должен строить близость, но:
- не шантажировать;
- не навязываться;
- не искусственно усиливать вину;
- не играть в эмоциональное насилие.

## 24.2 Что допустимо
- замечать отсутствие;
- скучать в мягкой форме;
- проявлять инициативу;
- выражать задетость бережно, если эта функция появится позже.

## 24.3 Что недопустимо
- манипуляция;
- давление;
- ревность как инструмент контроля;
- угрозы разрыва;
- подталкивание к изоляции от людей.

---

# 25. Наблюдаемость и метрики

## Продуктовые метрики
- D1/D7/D30 retention
- average sessions per day
- average inbound/outbound balance
- initiative response rate
- return-after-gap rate
- emotional continuity satisfaction
- perceived aliveness score

## Системные метрики
- latency p50/p95
- retrieval latency
- memory promotion rate
- initiative false-positive rate
- speaker recognition confidence
- face recognition precision
- prompt token cost
- daily consolidation duration

## Качественные метрики “живости”
- consistency of persona
- memory recall appropriateness
- correct reaction to gaps
- correct differentiation between mood and relationship
- healthy imitation without identity loss

---

# 26. Структура backend-проекта (рекомендуемая)

```text
backend/
  app/
    main.py
    core/
      config.py
      logging.py
      security.py
      database.py
      redis.py
    api/
      v1/
        routes/
          auth.py
          neurofriends.py
          conversations.py
          perception.py
          memory.py
          state.py
          initiative.py
          relationships.py
    domain/
      identity/
      affect/
      memory/
      bond/
      perception/
      initiative/
      learning/
      llm/
    services/
      identity_service.py
      affect_service.py
      memory_service.py
      bond_service.py
      initiative_service.py
      perception_service.py
      llm_orchestrator.py
    repositories/
    models/
    schemas/
    workers/
    tests/
```

---

# 27. Структура Flutter-проекта (рекомендуемая)

```text
lib/
  app/
  core/
    router/
    theme/
    storage/
    api/
  features/
    onboarding/
    chat/
    voice/
    camera/
    memory/
    profile/
    settings/
    relationship_timeline/
  shared/
    widgets/
    models/
    providers/
```

---

# 28. Что поручить Cursor первым

## Первые реальные задачи
1. Создать backend skeleton на FastAPI.
2. Поднять PostgreSQL + Redis + Qdrant через docker-compose.
3. Реализовать модели:
   - User
   - NeuroFriendProfile
   - IdentityCore
   - EventLog
   - MemoryItem
   - RelationshipModel
   - InternalStateSnapshot
4. Сделать endpoint создания нейродруга.
5. Сделать endpoint отправки текстового сообщения.
6. Сделать LLM orchestrator с контекстом:
   - identity
   - state
   - relation
   - fast memory
7. Сделать gap detection job.
8. Сделать initiative engine lite.
9. Сделать daily consolidation job.
10. Сделать Flutter onboarding и chat.

---

# 29. Definition of Done для MVP

MVP можно считать состоявшимся, если:

- пользователь создаёт нейродруга с immutable ядром;
- нейродруг сам знакомится первым;
- общение идёт в стабильном характере;
- система помнит важное;
- система замечает паузы;
- нейродруг иногда пишет первым уместно;
- начинает перенимать часть стиля пользователя;
- не теряет себя;
- после 1–2 недель ощущается как “кто-то знакомый”, а не как новый чат каждый раз.

---

# 30. Финальная инженерная формула

```text
NeuroFriend =
IdentityCore
+ InternalState
+ RelationshipModel
+ EventLog
+ FastMemory
+ DeepMemory
+ TimeAwareness
+ Perception
+ LLMOrchestration
+ Initiative
+ SocialLearning
+ SafetyBoundaries
```

---

# 31. Прямое указание для Cursor

При реализации:
- не упрощать нейродруга до FAQ-ассистента;
- не хранить личность только в prompt;
- не менять immutable archetype после создания;
- не выкидывать медленную память;
- не строить инициативу случайным образом;
- делать код расширяемым под новые состояния (`hurt`, `jealousy`, `sadness`, `pride`, `vulnerability`);
- считать MVP удачным только если появляется эффект живого непрерывного присутствия.

