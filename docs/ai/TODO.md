
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
| 6 — Память / семантика | Частично: Qdrant + SQL `memory_items` retrieval в LLM при наличии сессии; консолидация all/profiles + воркер-флаг; push и полировка decay — дальше |
| 7 — Инициатива, gap, push | Частично: status, sweep, LLM-пинг, SQL+Qdrant snippets в пинге; polling Flutter; push и отдельный долгоживущий воркер без HTTP — дальше |
| 8 — Observability, смена голоса | Не начато / точечно |
| v4.3 — Biography, expertise, boundaries, romance, capabilities, reminders | Stage A–C первая итерация реализована; Stage D–E впереди |

## Ближайший порядок реализации

1. **Полировка voice participants:** заменить MVP audio hash на реальные speaker embeddings/voiceprint, добавить явное согласие/управление участниками в UI.
2. **Полировка памяти и инициативы:** retrieval из SQL рядом с Qdrant, consolidate-all и `--consolidate-memory-first` у воркера — сделано; дальше — scheduler под деплой (не только локальный скрипт), push вместо polling, углубление decay и лимиты объёма памяти.
3. **Полировка SRS-onboarding:** экраны в `mobile/lib/features/onboarding/`, preview биографии/экспертизы и **`expertise_profile`** из каталога — сделано; дальше — расширение widget coverage.
4. **Полировка Stage C (романтическая динамика):** LLM-классификатор сигнала (флаг **`ROMANTIC_SIGNAL_CLASSIFIER_LLM_ENABLED`**, default off), модуляция TTS **`tts_speed`** по `bond_type`, улучшенный инспектор — сделано; дальше — углубление промптов классификатора и отдельная просодическая разметка текста (если понадобится сверх `speed`).
5. **Full-stack smoke с медиа:** базовый HTTP smoke пройден; отдельно проверить TTS/voice с `OPENAI_API_KEY`, аудиофайлом и Qdrant retrieval в окружении с ключами.
6. **Observability:** request id, timing middleware, метрики OpenAI/Qdrant/DB и стоимость LLM/STT/TTS.

## Голосовое обращение и участники беседы

Статус: первая MVP-итерация реализована 2026-04-26.

Сделано:
- feature flags `speaker_recognition_enabled`, `voice_addressing_enabled`;
- таблица `conversation_participants` + Alembic migration `20260426_6`;
- первый услышанный голос становится `user_main`;
- новые голоса сохраняются как `guest_*`;
- если новый голос сам представился (`меня зовут ...`), имя сохраняется, участник становится `known_guest`;
- voice events и chat message metadata получают `speaker_person_ref`, `display_name`, `participant_kind`, `is_new_voice`, `addressing_required`;
- orchestrator получает speaker context: при одном участнике имя не требуется, при нескольких можно обращаться по имени, при новом голосе нужно культурно познакомиться;
- backend `wake_check` policy: ручная запись всегда обрабатывается, hands-free запись игнорирует неадресованные фразы; при одном участнике можно без имени, при нескольких нужен вызов по имени или новый голос для знакомства;
- Flutter hands-free режим "слушать имя": короткие аудио-фрагменты отправляются с `wake_check=true`, неадресованные фразы не вызывают LLM/TTS;
- hands-free во время TTS не глушится: backend получает `playback_guard_text`, отбрасывает совпадающее эхо собственной реплики как `assistant_self`, но оставляет возможность перебить нейродруга другой фразой;
- self-echo guard также сравнивает входящий voice transcript с последними assistant messages из chat history, поэтому intro/ответы ловятся даже если клиент ещё не успел передать `playback_guard_text`;
- `sha256_audio_mvp` заменён на `wav_acoustic_mvp`: dependency-free акустический профиль WAV-фрагмента для первичного различения голосов между участниками;
- если эхо нейродруга поймано по `playback_guard_text`, backend запоминает его WAV-профиль как системного участника `assistant_self`; следующие похожие фрагменты отбрасываются до Whisper/LLM и не считаются людьми;
- `assistant_self` исключён из подсчёта человеческих участников, поэтому он не ломает правило "если собеседник один, имя не обязательно";
- STT hallucination guard: hands-free WAV с низкой голосовой активностью отбрасывается до Whisper, а типичные hallucination-фразы вроде `thank you for watching` / `subscribe to my channel` после Whisper логируются как `voice_stt_hallucination_guard` и не попадают в чат;
- STT hallucination guard применяется ко всему voice flow до speaker/person logic, чтобы артефакты не могли стать именем/участником;
- onboarding показывает мягкое предупреждение, если выбранная gender-style манера и имя выглядят несовместимыми по базовому списку русских имён;
- debug endpoint `GET /v1/neurofriends/{id}/debug/participants`, `PATCH .../debug/participants/{participant_id}` (имя, согласие на дообучение MVP-отпечатка; при `declined` не смешивать новые признаки в отпечаток при совпадении);
- Flutter инспектор: список участников голоса, переименование и выбор согласия (bottom sheet);
- service tests + HTTP voice e2e.

Осталось на будущую полировку:
- заменить `wav_acoustic_mvp` на реальные speaker embeddings / voiceprint matching + diarization;
- добавить echo cancellation/VAD на клиенте, чтобы barge-in работал устойчивее при громком TTS;
- расширить consent/enrollment: отдельный пользовательский экран (не только инспектор), политики для гостей;
- улучшить hands-free UX: VAD/тишина, локальная wake-word модель вместо отправки коротких чанков на backend;
- добавить merge участников и обработку ложных совпадений (rename через PATCH уже есть).

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
- unit/e2e tests;
- пользовательский preview: поля каталога `biography_preview` / `expertise_preview`, `GET /v1/neurofriends/{id}/character-preview`, экран preview онбординга и «О персонаже» в чате Flutter.

Осталось на будущую полировку:
- расширить canonical presets (биография seed помимо `life_legend`, дополнительные нишевые темы и алиасы);
- добавить более точную topic classification для expertise.

Сделано дополнительно:
- полноценный **`expertise_profile`** в `personality_presets.json` и приоритет при `build_initial_expertise_profile`.

## v4.3 Stage B — Conflict & Boundaries

Статус: первая итерация реализована 2026-04-26.

Сделано:
- feature flag `boundary_response_enabled`;
- новые state fields: `friction`, `respect_signal`, `self_respect_activation`, `boundary_alert`;
- новые relationship fields: `conflict_memory_score`, `repair_receptivity`, `respect_baseline`, `boundary_safety_score`;
- `BoundaryResponseService`: disrespect/repair detection, boundary mode, prompt context;
- `affect_lite` обновляет conflict/boundary state после входящего текста;
- `RelationshipModel` накапливает conflict/repair/boundary safety;
- initiative score подавляется при активном конфликте;
- LLM orchestrator получает boundary context и анти-лесть rule;
- unit tests + initiative cooldown tests.

Осталось на будущую полировку:
- более точная классификация тона через LLM/модель вместо словарей;
- UI-индикатор состояния границ в инспекторе;
- связать boundary mode с голосовой интонацией/TTS.

## v4.3 Stage C — Romantic Dynamics

Статус: первая итерация реализована 2026-05-01.

Сделано:
- feature flag `romantic_dynamics_enabled` (Settings / env);
- поля в `InternalStateSnapshot`: `affection`, `romantic_interest`, `flirt_comfort`, `emotional_intimacy`;
- поля в `RelationshipModel`: `bond_type`, `affection_score`, `romantic_tension_score`, `emotional_intimacy_score`; миграция `20260426_7`;
- модуль `attachment_dynamics_service`: `update_affection_after_event`, `evaluate_romantic_signal`, `evaluate_warmth_signal`, `boundary_check`, `should_allow_flirtation`, `update_bond_type`, `compute_bond_type`, `archetype_romantic_baseline`, `romantic_prompt_context`;
- ограничение прироста за один ход пользователя + гейт по `emotional_intimacy`/`affection` перед ростом `romantic_tension`; тип связи `bond_type` (platonic → … → romantic_soft) без мгновенного скачка из дефолта;
- учёт конфликта/границ и режима `repair_opening`; контекст в LLM для ответа и инициативного пинга;
- `tests/test_attachment_dynamics.py`.

Осталось на будущую полировку:
- уточнять классификатор (few-shot, безопасность, языки);
- более тонкая просодия TTS (разметка текста, отдельный pipeline), если `speed` недостаточно.

Сделано дополнительно:
- **`romantic_signal_classifier_llm_enabled`** (по умолчанию **true**) + `romantic_signal_llm_hint`, смешивание с эвристикой в `update_affection_after_event`;
- **`stage_c_tts_prosody_enabled`** и `tts_speed` в meta/log voice out;
- Flutter-инспектор: русские подписи bond и шкалы метрик.

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
