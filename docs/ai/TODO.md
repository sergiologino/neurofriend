
# TODO — единый рабочий бэклог

Канонический поэтапный план: `ROADMAP.md`. SRS: `docs/SRS/`. Delta-spec v4.3: `E:\1_MyProjects\1_Human_robofriend\NeuroFriend_Addendum_v4_3.md`.

Здесь — **конкретные следующие шаги** и отложенные инициативы. По мере выполнения пункты переносить в `CHANGELOG_AI.md`, кратко отражать в `CURRENT_STATE.md`; архитектурные решения — в `DECISIONS.md`.

## Текущий статус

| Этап | Статус |
|------|--------|
| 1 — Каркас, БД, health | Сделано |
| 2 — Голос Whisper + LLM + TTS | Реализовано на backend (`/v1/perception/audio`, `/v1/perception/tts`) |
| 3 — Чат-дубликат, 500 / архив / 10 | Реализовано на backend; при доработках закрепить e2e/интеграционными тестами rollover |
| 4 — UI инспектора | Базовый Flutter-экран: события + primary relationship |
| 5 — Онбординг, пресеты | Первая SRS-итерация: go_router, пошаговый onboarding, preview, имя/голос, personalization, identity lock; backend принимает `selected_preset_id` и валидирует deltas |
| 6 — Память / семантика | Частично: Qdrant + embeddings + retrieval + индексация; консолидация/decay впереди |
| 7 — Инициатива, gap, push | Частично: status, sweep, LLM-пинг, чат, Redis; push, TZ пользователя, worker без HTTP впереди |
| 8 — Observability, смена голоса | Не начато / точечно |
| v4.3 — Biography, expertise, boundaries, romance, capabilities, reminders | Stage A первая итерация реализована; Stage B–E впереди |

## Ближайший порядок реализации

1. **v4.3 Stage B — конфликтность и границы:** следующий инкремент addendum после Stage A.
2. **Голосовое обращение и участники беседы:** определить wake/addressing policy: если нейродруг один в диалоге, реплики пользователя считаются обращёнными к нему без имени; если в окружении несколько участников/ассистентов — поддержать обращение по имени. Добавить speaker recognition: отличать основной голос пользователя от других голосов; при новом голосе культурно представиться, спросить имя, сохранить участника и дальше узнавать его по голосовому отпечатку/профилю.
3. **Полировка памяти и инициативы:** подключить consolidation worker к реальному scheduler/deployment, добавить retrieval из SQL memory в orchestrator рядом с Qdrant, расширить push вместо polling.
4. **Полировка SRS-onboarding:** вынести экраны из `HomePage` в feature-based структуру, добавить widget tests и пользовательский biography/expertise preview.
5. **Full-stack smoke с медиа:** базовый HTTP smoke пройден; отдельно проверить TTS/voice с `OPENAI_API_KEY`, аудиофайлом и Qdrant retrieval в окружении с ключами.
6. **Observability:** request id, timing middleware, метрики OpenAI/Qdrant/DB и стоимость LLM/STT/TTS.

## v4.3 Stage A — Biography + Expertise

Статус: первая итерация реализована 2026-04-26.

Сделано:
- feature flags `biography_profile_enabled`, `expertise_profile_enabled`;
- `BiographyProfile` + Alembic migration;
- `BiographyService` с initial biography, snapshot, consistency validation и low-risk detail commit;
- `expertise_profile_json` в `IdentityCore`;
- `ExpertiseService` с level/confidence/response shaping;
- создание нейродруга создаёт biography/expertise из preset/archetype;
- LLM orchestrator получает biography + expertise context;
- debug API чтения biography/expertise;
- unit/e2e tests.

Осталось на будущую полировку:
- расширить canonical presets под полноценные `expertise_profile` и biography seed вместо эвристик;
- вывести biography preview в обычный пользовательский UI, а не только debug;
- добавить более точную topic classification для expertise.

## v4.3 Stage B — Conflict & Boundaries

Цель: зрелая конфликтность без токсичности.

1. Добавить feature flag `boundary_response_enabled`.
2. Расширить `InternalStateSnapshot`: `friction`, `respect_signal`, `self_respect_activation`, `boundary_alert`.
3. Расширить `RelationshipModel`: `conflict_memory_score`, `repair_receptivity`, `respect_baseline`, `boundary_safety_score`.
4. Расширить `AffectService` / `affect_lite`:
   - disrespect detection;
   - insult detection;
   - tension escalation;
   - repair detection.
5. Реализовать `BoundaryResponseService`:
   - `evaluate_disrespect_level()`
   - `select_boundary_mode()`
   - `apply_cooldown_to_initiative()`
   - `release_cooldown_after_repair()`
6. Подключить boundary mode в orchestrator и initiative:
   - уровни 0–4: спокойно, суховатость, явная граница, краткий отказ, временное охлаждение;
   - без оскорблений, унижения, guilt manipulation, threat of abandonment.
7. Тесты:
   - disrespect/repair classification;
   - cooldown инициативы;
   - prompt context получает boundary mode.

## v4.3 Stage C — Romantic Dynamics

Цель: медленная межличностная динамика, не «эротический режим» и не fast-forward близости.

1. Добавить feature flag `romantic_dynamics_enabled`.
2. Расширить `InternalStateSnapshot`: `affection`, `romantic_interest`, `flirt_comfort`, `emotional_intimacy`.
3. Расширить `RelationshipModel`: `bond_type`, `affection_score`, `romantic_tension_score`, `emotional_intimacy_score`.
4. Реализовать `AttachmentDynamicsService`:
   - `update_affection_after_event()`
   - `evaluate_romantic_signal()`
   - `update_bond_type()`
   - `should_allow_flirtation()`
   - `boundary_check()`
5. Подключить gradual progression rules:
   - комфорт → тёплая привычность → мягкие комплименты → эмоциональная значимость → осторожная романтическая окраска;
   - только по истории и отклику пользователя.
6. Тесты:
   - невозможность мгновенного перехода в romantic state;
   - учёт границ и repair;
   - разные архетипы имеют разные baseline tendencies.

## v4.3 Stage D — Device Assistance / Capabilities

Цель: помощь с ресурсами устройства только по явному разрешению.

1. Добавить feature flag `device_capabilities_enabled`.
2. Добавить `CapabilityGrant` + migration:
   - `user_id`, `neurofriend_id`, `capability_type`, `scope_json`, `granted_at`, `expires_at`, `revoked_at`, `requires_confirmation_each_use`, `audit_log_enabled`.
3. Реализовать `CapabilityService`:
   - `request_capability()`
   - `check_capability()`
   - `revoke_capability()`
   - `log_capability_use()`
4. Добавить orchestrator / agent rule:
   - перед агентным действием проверить capability;
   - проверить confirmation policy;
   - запросить подтверждение, если нужно;
   - логировать использование.
5. MVP+ capabilities:
   - `filesystem_read` через file picker;
   - `email_compose` как draft assistance;
   - `browser_assist`;
   - `screen_observe` read-only, только с явным consent;
   - `reminder_create`.
6. UX:
   - звучать как помощник, не malware;
   - объяснять зачем нужен доступ и какой scope.
7. Тесты:
   - denied/no grant блокирует действие;
   - grant с expiry/revoke;
   - audit log пишется;
   - confirmation required срабатывает.

## v4.3 Stage E — Reminders

Цель: умные напоминания и поручения как часть отношений и повседневной помощи.

1. Добавить feature flag `reminders_enabled`.
2. Добавить `ReminderItem` + migration:
   - `user_id`, `neurofriend_id`, `title`, `description`, `trigger_time`, `source_type`, `status`, `needs_confirmation`, `created_from_event_id`, `created_at`.
3. Реализовать `ReminderService`:
   - `create_explicit_reminder()`
   - `suggest_reminder_from_context()`
   - `confirm_inferred_reminder()`
   - `deliver_reminder()`
   - `link_reminder_to_memory()`
4. Подключить reminders к initiative layer:
   - explicit reminders;
   - context suggestions только с подтверждением;
   - relational follow-up;
   - practical follow-up.
5. Добавить delivery:
   - сначала polling/debug/manual sweep;
   - затем push/worker.
6. Тесты:
   - explicit reminder создаётся;
   - inferred reminder требует подтверждения;
   - delivery меняет status;
   - initiative учитывает due reminders.

## Сквозные задачи качества

1. **Качество диалога:** улучшать промпты по мере готовности доменных слоёв; fallback LLM должен ясно отличаться от целевого поведения и не маскировать отсутствие `OPENAI_API_KEY`.
2. **Observability:** request id, latency, OpenAI/Qdrant/DB errors, стоимость Whisper/TTS/LLM, retrieval stats, initiative stats.
3. **Safety:** не проектировать зависимость как цель; не добавлять скрытую агентность; не копировать токсичность пользователя; не ломать immutable identity.
4. **Тестовая дисциплина:** каждая новая feature — unit/integration tests + стандартная сборка; при падении исправить и повторить.
5. **Документация:** после каждой завершённой фичи обновлять `CURRENT_STATE.md`, `CHANGELOG_AI.md`, при необходимости `ARCHITECTURE.md` и `DECISIONS.md`.

## Отказы и отложено

| Тема | Решение | Где зафиксировано |
|------|---------|-------------------|
| Отдельный веб-стек (React/Next) только для web | Не делаем на MVP: дублирование UI и контрактов | D-001 `DECISIONS.md` |
| Микросервисы на старте | Модульный монолит FastAPI | D-002 |
| Docker Postgres как обязательный dev | Приоритет локальный PostgreSQL на хосте | D-008, `infra/README.md` |
| Чат как единственный источник истины | Отклонено: истина в событиях/памяти | D-005 |
| Встроенная системная ложь о себе | Не делаем; биография консистентна и ограничена | Addendum v4.3 |
| Токсичная ответная агрессия | Не делаем; только границы, охлаждение, repair | Addendum v4.3 |
| Скрытый доступ к устройству | Не делаем; capabilities только по явному согласию и scope | Addendum v4.3 |

*(Новые отказы добавлять сюда таблицей и при необходимости дублировать запись в `DECISIONS.md`.)*
