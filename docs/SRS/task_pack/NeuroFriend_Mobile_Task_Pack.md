# NeuroFriend — Mobile Task Pack for Cursor

> Цель: дать Cursor отдельный, детальный и практический пакет задач по mobile-части MVP.
> Этот файл предполагает, что backend делается по `NeuroFriend — Backend Task Pack for Cursor`.

---

# 0. Главная цель mobile MVP

Собрать мобильное приложение, в котором пользователь:

- создаёт нейродруга как личность;
- получает первое живое сообщение от него;
- общается с ним в чате;
- ощущает характер, память и непрерывность;
- может управлять уровнем инициативы;
- воспринимает нейродруга как присутствующего спутника, а не как обычный AI-чат.

---

# 1. Общие правила для Cursor

## Обязательно
- использовать **Flutter**
- использовать **Dart**
- использовать **Riverpod**
- использовать **go_router**
- использовать чистую feature-based структуру
- отделять API layer от UI layer
- использовать типизированные модели
- подготовить проект под iOS и Android
- заложить расширение под voice/camera later

## Нельзя
- делать всё в одном giant screen
- смешивать бизнес-логику и widgets
- захардкодить onboarding choices без моделей
- делать UI как “ещё один generic AI chat”
- позволять менять immutable personality core после создания

---

# 2. Целевая структура mobile проекта

```text
mobile/
  lib/
    app/
      app.dart
      router.dart
    core/
      api/
      config/
      theme/
      storage/
      utils/
    shared/
      widgets/
      models/
      providers/
    features/
      onboarding/
        data/
        domain/
        presentation/
      chat/
        data/
        domain/
        presentation/
      neurofriend_profile/
        data/
        domain/
        presentation/
      settings/
        data/
        domain/
        presentation/
      state_view/
      relationship_view/
```

---

# 3. Задача 1 — Создать Flutter app skeleton

## Что сделать
1. Создать Flutter project.
2. Настроить `go_router`.
3. Настроить `Riverpod`.
4. Настроить theme.
5. Настроить API client.
6. Настроить secure/local storage.
7. Подготовить environment config.

## Библиотеки
- `flutter_riverpod`
- `go_router`
- `dio`
- `freezed` / `json_serializable` (желательно)
- `flutter_secure_storage`
- `hive` или `isar`
- `intl`

## Acceptance criteria
- приложение стартует
- роутинг работает
- API layer готов
- проект не является хаотичным single-file приложением

---

# 4. Задача 2 — Реализовать app theme и визуальный язык

## Цель
UI должен ощущаться как пространство живого спутника, а не техпанель.

## Требования
- мягкий, тёплый, спокойный интерфейс
- минимум визуального шума
- акцент на диалог и присутствие
- хорошие отступы
- приятная типографика
- не делать “неоновый AI”

## Экранные элементы
- чат должен быть центральным
- имя нейродруга и краткое ощущение его характера в header
- сообщения — читаемые, не перегруженные
- время сообщений — доступно, но не кричит

## Acceptance criteria
- визуально чувствуется “личный спутник”, а не admin-панель

---

# 5. Задача 3 — Реализовать onboarding flow

## Цель
Сделать процесс создания нейродруга как личности, а не как набора настроек.

## Экраны onboarding

### Экран 1 — Welcome
Передать идею:
- ты создаёшь не бота, а цифрового спутника
- у него будет свой характер
- он будет помнить и жить во времени

### Экран 2 — Имя
Пользователь задаёт имя нейродруга.

### Экран 3 — Базовый образ
Поля:
- gender_style
- age_style

### Экран 4 — Архетип
Пользователь выбирает неизменяемый архетип.
Примеры:
- тёплый эмпат
- интеллигент-наблюдатель
- ироничный городской
- прямой практик
- авантюрный тёплый

### Экран 5 — Характер
Слайдеры / селекторы:
- мягкость ↔ прямота
- эмоциональность ↔ спокойствие
- ирония ↔ серьёзность
- инициативность ↔ тактичность
- мечтательность ↔ практичность

### Экран 6 — Стиль общения
- короткие / длинные ответы
- книжный / бытовой стиль
- тёплый / ровный тон
- юмор / почти без юмора

### Экран 7 — Отношение к близости
- быстро привязывается / медленно
- легко прощает / дольше переживает
- чаще уточняет / умеет отступить

### Экран 8 — Identity lock confirmation
Очень важный экран:
- объяснить, что ядро личности фиксируется навсегда
- дать явное подтверждение

### Экран 9 — Создание
Отправить payload на backend, показать состояние загрузки.

### Экран 10 — Первое сообщение
Показать первое intro-сообщение нейродруга.

## Acceptance criteria
- пользователь может пройти onboarding без сбоев
- payload создания нейродруга корректно уходит на backend
- первое сообщение отображается сразу после создания

---

# 6. Задача 4 — Реализовать models / DTO на mobile

## Основные DTO
- `NeuroFriendCreateRequest`
- `NeuroFriendCreateResponse`
- `MessageDto`
- `SendMessageRequest`
- `StateSnapshotDto`
- `MemorySummaryDto`
- `RelationshipDto`
- `InitiativePolicyDto`

## Acceptance criteria
- модели типизированы
- json parsing не разваливается
- нет ad-hoc map access по всему проекту

---

# 7. Задача 5 — Реализовать onboarding state management

## Цель
Хранить выборы пользователя до отправки на backend.

## Что сделать
- provider / notifier для onboarding state
- методы обновления шагов
- валидация обязательных полей
- сбор итогового payload

## Acceptance criteria
- состояние onboarding не теряется между шагами
- итоговый payload всегда консистентен

---

# 8. Задача 6 — Реализовать create neurofriend API flow

## Что сделать
1. Экран финального подтверждения отправляет create request.
2. При успехе:
   - сохранить `neurofriendId`
   - сохранить краткие данные профиля
   - открыть chat screen
3. При ошибке:
   - показать понятное сообщение
   - не терять onboarding state

## Acceptance criteria
- создание нейродруга работает end-to-end

---

# 9. Задача 7 — Реализовать chat screen

## Цель
Главный экран продукта — живой чат с ощущением непрерывности.

## Что должно быть
- header:
  - имя нейродруга
  - краткий архетип / настроение
- список сообщений
- поле ввода текста
- send button
- typing indicator
- pull-to-refresh / initial load
- отображение intro message

## Желательно
- date separators
- time on message bubbles
- small presence hint
- мягкая анимация появления сообщений

## Acceptance criteria
- можно читать историю
- можно отправлять текст
- ответы приходят и красиво отображаются

---

# 10. Задача 8 — Реализовать chat state management

## Что сделать
- provider/notifier для thread state
- загрузка истории
- optimistic append входящего user message
- loading / typing states
- получение ответа от backend
- обработка сетевых ошибок

## Acceptance criteria
- чат не рвётся
- история не теряется
- состояние загрузки отображается корректно

---

# 11. Задача 9 — Реализовать API layer

## Что сделать
Создать typed API client:
- `createNeuroFriend()`
- `sendMessage()`
- `getState()`
- `getMemorySummary()`
- `getPrimaryRelationship()`
- `updateInitiativePolicy()`

## Правила
- `dio` interceptor для логов и auth later
- единый error mapping
- no raw HTTP logic in widgets

## Acceptance criteria
- UI не делает запросы напрямую
- API слой переиспользуем

---

# 12. Задача 10 — Реализовать local persistence

## Цель
Сохранить минимум контекста локально.

## Что хранить локально
- neurofriendId
- краткий профиль
- текущий initiative mode
- последние сообщения thread (опционально)
- theme/user local settings

## Acceptance criteria
- после перезапуска приложения базовый контекст не исчезает
- можно быстро открыть чат без полного cold-start ощущения

---

# 13. Задача 11 — Реализовать settings screen

## Что должно быть на MVP
- режим инициативы:
  - Active
  - Balanced
  - Quiet
  - Manual only
- push notifications on/off
- timezone
- locale
- будущие voice/camera permissions placeholders

## Важно
Пользователь НЕ должен мочь менять:
- archetype
- immutable core
- исходную базовую природу нейродруга

## Acceptance criteria
- настройки обновляются через backend
- immutable поля не редактируются

---

# 14. Задача 12 — Реализовать neurofriend profile preview

## Цель
Показать пользователю, что у нейродруга есть устойчивый образ.

## Что показать
- имя
- базовый архетип
- стиль общения
- уровень инициативности
- краткое описание личности

## Формат
Лёгкая карточка, не tech-debug экран.

## Acceptance criteria
- пользователь видит, кто перед ним
- экран усиливает ощущение “это личность”

---

# 15. Задача 13 — Реализовать memory/state views (lite)

## Цель
Дать минимальную прозрачность без превращения приложения в debug panel.

## Можно показать
### Memory summary lite
- важные темы
- краткие “что он помнит о вас”
- незавершённые линии

### State lite
- не numeric debug vars
- а мягкие человекопонятные формулировки:
  - “сейчас открыт к разговору”
  - “чувствует дистанцию”
  - “разговоры с вами для него важны”

## Acceptance criteria
- пользователь получает ощущение прозрачности
- UI не выглядит как панель разработчика

---

# 16. Задача 14 — Реализовать receiving initiatives UX

## Цель
Подготовить приложение к исходящим сообщениям нейродруга.

## На MVP
Можно сделать:
- polling / refresh
- local mock hook под push
- позже реальный push

## Что показать
- входящее сообщение от нейродруга
- небольшую нативную нотификацию
- открытие в чат

## Acceptance criteria
- инициативное сообщение может дойти до пользователя
- UX не ломается, если пользователь открывает чат позже

---

# 17. Задача 15 — Реализовать loading / failure / empty UX

## Обязательно предусмотреть
- создание нейродруга грузится
- чат грузится
- сообщение отправляется
- backend недоступен
- пустая история невозможна после intro, но fallback всё равно нужен

## Acceptance criteria
- нет “мертвых” экранов
- пользователь понимает, что происходит

---

# 18. Задача 16 — Подготовить hooks под voice/camera

## Что сделать
Сделать в UI и навигации заранее:
- placeholder voice action
- placeholder camera action
- permission explanation screens
- feature flags / disabled buttons

## Важно
Не реализовывать полностью, но подготовить расширяемую структуру.

## Acceptance criteria
- later voice/camera можно встроить без рефакторинга root flow

---

# 19. Задача 17 — Добавить тесты

## Widget tests
- onboarding steps
- identity lock confirmation
- chat screen initial render
- settings screen render

## Unit tests
- onboarding state notifier
- chat state notifier
- mapping dto -> ui models

## Acceptance criteria
- критические UI flows минимально защищены

---

# 20. Задача 18 — Продумать UX copy

## Важно
Тексты в приложении должны усиливать ощущение личности.

## Примеры правильного тона
- “Создай нейродруга, который будет рядом”
- “Его характер задаётся в начале и остаётся с ним”
- “Он сможет меняться, но не потеряет свою природу”

## Нельзя
- “Настрой AI-помощника”
- “Выбери режим чат-бота”
- “Сгенерировать персонажа”

## Acceptance criteria
- вся копирайтинг-линия поддерживает идею живого спутника

---

# 21. Задача 19 — Priority order для Cursor

## P0
- app skeleton
- router
- theme
- API layer
- onboarding screens
- create neurofriend flow
- chat screen

## P1
- state management
- local persistence
- settings screen
- profile preview

## P2
- memory/state lite views
- initiative receiving UX
- better empty/loading/failure states

## P3
- hooks for voice/camera
- widget tests
- polish

---

# 22. Final success criteria for mobile MVP

Mobile считается готовым, если:
- пользователь создаёт нейродруга через onboarding
- подтверждает immutable identity
- получает первое сообщение
- может вести чат
- видит устойчивый образ нейродруга
- может регулировать инициативу
- приложение ощущается как дом для цифрового спутника, а не как generic AI chat

---

# 23. Прямая инструкция Cursor

Начни с app skeleton, routing и theme.
Потом сделай onboarding как основной вход в продукт.
Затем реализуй create neurofriend flow и chat screen.
После этого — settings, local persistence и profile preview.
Поддерживай идею живого спутника во всех экранах и текстах.
Не превращай UI в обычный AI-мессенджер.
