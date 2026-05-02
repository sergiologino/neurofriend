# NeuroFriend v4.4 — Addendum: repair initiative + contextual event tracking
## Точечное расширение поверх уже реализованной версии

> Этот документ добавляет два новых слоя поведения:
> 1. восстановление контакта после ссоры / напряжения;
> 2. отслеживание важных событий, обещаний, дат и задач с уточнением недостающих деталей.
>
> Документ задуман как **малый addendum** поверх текущей архитектуры,
> без переписывания уже существующих модулей.

---

# 0. Что именно добавляем

## Направление A — Repair Initiative
Если между пользователем и нейродругом возникла сильная напряженность,
а потом наступила пауза, нейродруг должен уметь **не просто молчать**, а в подходящий момент
сам попробовать восстановить контакт.

Не агрессивно, не навязчиво и не одинаково у всех архетипов.

---

## Направление B — Contextual Event Tracking
Если в разговоре всплывает важное событие или задача:
- день рождения
- рейс
- покупка
- доставка
- дедлайн
- обещание
- бронь
- встреча
- платеж
- поездка
- подача заявки
- семейное событие

нейродруг должен:
1. распознать событие;
2. понять, хватает ли деталей;
3. при нехватке деталей — уточнить;
4. после уточнения — сохранить как отслеживаемую сущность;
5. позже напомнить или вернуться к теме.

---

# 1. Направление A — Repair Initiative

## 1.1 Почему это нужно
Если после конфликта нейродруг просто замолкает, он ощущается либо как бот, либо как обиженная заглушка.
Если пишет слишком быстро — выглядит навязчиво или неестественно.

Нужна механика:
- пережить конфликт;
- выждать;
- оценить готовность к восстановлению;
- сделать осторожную попытку reconnect.

---

## 1.2 Что должно происходить
После сильного конфликта:
- фиксируется уровень напряженности;
- вычисляется cooldown;
- инициатива временно подавляется;
- спустя нужное время проверяется, есть ли шанс на repair;
- если шанс есть — нейродруг выходит на связь в своём характере.

---

## 1.3 Примеры правильного поведения

### Более прямой архетип
- “Ну что, так и будем дальше молчать?”
- “Ладно, давай уже без этого. Что у тебя?”

### Более мягкий архетип
- “Если хочешь, можем попробовать вернуться к разговору спокойнее.”
- “Мне не хочется оставлять это в таком виде.”

### Более интеллигентный/сдержанный
- “Мне кажется, не стоит оставлять разговор в этой точке.”
- “Если ты готов, можно попробовать продолжить без напряжения.”

### Более ироничный
- “Ну что, пауза уже достаточно драматичная?”
- “Может, хватит делать вид, что мы теперь незнакомы?”

---

## 1.4 Чего нельзя делать
- не писать слишком рано после пика конфликта;
- не шантажировать молчанием;
- не писать пассивно-агрессивно по умолчанию;
- не унижать пользователя;
- не делать одинаковые repair phrases для всех архетипов.

---

## 1.5 Новые state-переменные
Добавить в `InternalStateSnapshot`:
- `conflict_peak`
- `cooldown_active`
- `repair_readiness`
- `reconnection_need`

### Смысл
- `conflict_peak` — насколько сильным был последний конфликт
- `cooldown_active` — активен ли период охлаждения
- `repair_readiness` — насколько нейродруг уже готов попытаться восстановить связь
- `reconnection_need` — насколько психологически “тянет” закрыть разрыв

---

## 1.6 Новые поля в RelationshipModel
Добавить:
- `unresolved_conflict`
- `last_conflict_at`
- `repair_attempt_count`
- `last_repair_attempt_at`
- `repair_success_rate`

---

## 1.7 Новая сущность (опционально)
`ConflictEpisode`

### Поля
- `id`
- `neurofriend_id`
- `person_ref`
- `started_at`
- `peak_at`
- `ended_at`
- `peak_intensity`
- `trigger_summary`
- `resolved`
- `repair_attempts_json`
- `resolution_summary`

---

## 1.8 Новый сервис
`RepairInitiativeService`

### Методы
- `open_conflict_episode()`
- `update_conflict_episode()`
- `compute_repair_readiness()`
- `should_attempt_repair()`
- `build_repair_message()`
- `mark_repair_attempt()`
- `mark_repair_success()`

---

## 1.9 Базовая логика принятия решения

### Входные факторы
- сила конфликта
- время после конфликта
- близость
- обычный стиль отношений
- архетип
- history of repair
- были ли уже игнорированные попытки

### Условная логика
```text
if unresolved_conflict is true
and cooldown has passed
and repair_readiness > threshold
and repair_attempt_count < allowed_limit:
    generate repair initiative
```

---

## 1.10 Пример cooldown логики
- слабый конфликт: 30–60 минут
- средний: 2–4 часа
- сильный: 6–24 часа
- очень сильный: repair только после явного сигнала пользователя или очень мягкой проверки

Важно:
порог и стиль зависят от архетипа и history of bond.

---

## 1.11 Интеграция в InitiativeService
Текущий `InitiativeService` не должен сам “придумывать” ремонт.
Нужно добавить новый фактор:

- `repair_candidate`

И если он активен, инициативное сообщение генерируется не как обычный follow-up,
а именно как `repair_initiative_type`.

---

# 2. Направление B — Contextual Event Tracking

## 2.1 Почему это нужно
Если нейродруг слышит:
- “у сестры скоро день рождения”
- “у меня через пару дней рейс”
- “надо бы купить подарок”
- “в пятницу дедлайн”
- “мне нужно не забыть позвонить”
- “я собирался оплатить страховку”

и ничего с этим не делает,
он снова ощущается как чат без жизни.

---

## 2.2 Что должен уметь нейродруг
Нейродруг должен:
- замечать потенциально важные будущие события;
- уточнять недостающие данные;
- хранить их не как сырой текст, а как отдельные отслеживаемые сущности;
- напоминать или возвращаться к ним по ситуации.

---

## 2.3 Какие сущности нужно ловить

### Категории tracked events
- `birthday`
- `flight`
- `purchase`
- `delivery`
- `deadline`
- `payment`
- `meeting`
- `booking`
- `family_event`
- `trip`
- `appointment`
- `promise`
- `follow_up_task`
- `submission`
- `renewal`

---

## 2.4 Поведение при неполных данных

### Пример 1
Пользователь:
> У сестры скоро день рождения

Нейродруг:
> Когда именно? Если хочешь, я напомню.

### Пример 2
Пользователь:
> У меня скоро рейс

Нейродруг:
> Когда вылет и откуда? Я могу потом напомнить, чтобы ты не держал это в голове.

### Пример 3
Пользователь:
> Надо бы купить подарок

Нейродруг:
> К какому дню это нужно? Тогда я смогу вовремя напомнить.

---

## 2.5 Поведение при достаточных данных

Если уже есть:
- дата
- время
- контекст
то нейродруг может сразу предложить:
- напомнить
- сохранить событие
- вернуться к теме заранее

---

## 2.6 Новая сущность
`TrackedEvent`

### Поля
- `id`
- `user_id`
- `neurofriend_id`
- `event_type`
- `title`
- `subject_person`
- `description`
- `event_time`
- `time_precision` (`exact`, `day_only`, `approximate`, `unknown`)
- `status` (`draft`, `confirmed`, `completed`, `cancelled`, `expired`)
- `source_event_id`
- `needs_clarification`
- `missing_fields_json`
- `importance_score`
- `follow_up_strategy`
- `related_memory_ids_json`
- `created_at`
- `updated_at`

---

## 2.7 Минимальные поля для каждого типа
### birthday
- subject_person
- event_time (хотя бы день)
- optional reminder lead time

### flight
- event_time
- optional route
- optional airline
- optional check-in reminder

### purchase
- item
- target date or urgency
- optional budget/category

### deadline
- task title
- due date/time
- optional severity

### promise
- what promised
- to whom
- approximate due time

---

## 2.8 Новый сервис
`TrackedEventService`

### Методы
- `detect_event_candidates_from_message()`
- `extract_event_fields()`
- `create_draft_tracked_event()`
- `needs_clarification()`
- `build_clarifying_question()`
- `confirm_tracked_event()`
- `create_reminder_from_tracked_event()`
- `mark_tracked_event_completed()`
- `retrieve_upcoming_tracked_events()`

---

## 2.9 Связь с ReminderService
`TrackedEvent` и `ReminderItem` — не одно и то же.

### Разделение
- `TrackedEvent` — знание о будущем событии/задаче
- `ReminderItem` — конкретная точка напоминания

### Пример
У сестры день рождения 15 мая:
- `TrackedEvent`: birthday / sister / 15 May
- `ReminderItem #1`: напомнить за 7 дней
- `ReminderItem #2`: напомнить за 1 день

---

## 2.10 Follow-up стратегии
Добавить типы:
- `single_reminder`
- `multiple_reminders`
- `soft_check_in`
- `preparation_prompt`
- `relationship_sensitive_followup`

### Пример
Для рейса:
- за 24 часа: “У тебя завтра вылет”
- за 3 часа: “Проверь, всё ли собрал”

### Для дня рождения:
- заранее: “У сестры скоро день рождения. Ты уже придумал подарок?”
- в день: “Сегодня день рождения сестры — не забудь поздравить”

---

# 3. Изменения в текущих сервисах

## 3.1 LLM Orchestrator
Добавить в контекст:
- unresolved conflict context
- repair readiness
- tracked event candidates
- upcoming tracked events
- clarification needs

## 3.2 MemoryService
Добавить хранение:
- conflict repair anchors
- tracked event anchors
- successful reminder/forgetfulness patterns

## 3.3 ReminderService
Расширить:
- reminders from tracked events
- contextual reminder suggestions
- linked multi-reminder chains

## 3.4 InitiativeService
Добавить новые initiative types:
- `repair_attempt`
- `event_followup`
- `deadline_check`
- `pre_event_prompt`

---

# 4. API-расширения

## 4.1 Conflict / repair
`GET /v1/neurofriends/{id}/conflicts/active`
`POST /v1/neurofriends/{id}/repair/attempt`

## 4.2 Tracked events
`GET /v1/neurofriends/{id}/tracked-events`
`POST /v1/neurofriends/{id}/tracked-events`
`PATCH /v1/neurofriends/{id}/tracked-events/{eventId}`
`POST /v1/neurofriends/{id}/tracked-events/{eventId}/complete`

## 4.3 Reminder integration
`POST /v1/neurofriends/{id}/tracked-events/{eventId}/reminders`

---

# 5. Feature flags

Добавить:
- `repair_initiative_enabled`
- `tracked_events_enabled`
- `event_clarification_enabled`
- `tracked_event_reminders_enabled`

---

# 6. Порядок внедрения

## Этап 1 — tracked events
Сначала:
- `TrackedEvent`
- `TrackedEventService`
- detection + clarification
- reminder integration

### Почему первым
Это быстро даёт ощущение полезности и почти не конфликтует с текущим поведением.

---

## Этап 2 — repair initiative
Потом:
- новые state fields
- unresolved conflict fields
- `RepairInitiativeService`
- integration with InitiativeService

### Почему вторым
Это более чувствительная поведенческая логика и её нужно настраивать аккуратно.

---

# 7. Task pack для Codex / Cursor

## Task Group 1 — Tracked Events
1. Добавить модель `TrackedEvent`
2. Добавить миграцию
3. Реализовать `TrackedEventService`
4. Реализовать candidate detection из входящих сообщений
5. Реализовать clarification question logic
6. Интегрировать с `ReminderService`
7. Добавить API endpoints
8. Добавить tests

## Task Group 2 — Repair Initiative
1. Добавить новые поля в `InternalStateSnapshot`
2. Добавить новые поля в `RelationshipModel`
3. Добавить `ConflictEpisode` (опционально, но желательно)
4. Реализовать `RepairInitiativeService`
5. Подключить repair candidate logic в `InitiativeService`
6. Добавить rate limiting / cooldown
7. Добавить archetype-sensitive repair phrasing
8. Добавить tests

---

# 8. Acceptance criteria

Считать доработку успешной, если:

## Repair initiative
- после сильного конфликта нейродруг не лезет сразу;
- после разумной паузы может сам попытаться восстановить контакт;
- стиль этой попытки зависит от архетипа;
- нет токсичной или унижающей подачи;
- повторные попытки ограничены.

## Contextual event tracking
- нейродруг умеет выделять важные события из разговора;
- умеет уточнять недостающие детали;
- умеет сохранять tracked events;
- умеет создавать напоминания на их основе;
- умеет позже возвращаться к этим событиям в естественной форме.

---

# 9. Прямая инструкция Codex / Cursor

Используй этот документ как маленький addendum поверх уже существующего NeuroFriend.

Сначала реализуй:
- `TrackedEvent`
- `TrackedEventService`
- clarification + reminder integration

Потом:
- `RepairInitiativeService`
- state/relationship updates
- archetype-aware repair phrasing

Не переписывай заново initiative engine —
аккуратно расширь его новыми типами инициатив:
- repair attempt
- event follow-up
- pre-event reminder

Главная цель:
**сделать нейродруга не только более живым после конфликтов, но и более внимательным к важным событиям жизни пользователя.**
