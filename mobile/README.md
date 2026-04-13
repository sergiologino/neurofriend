# NeuroFriend — Flutter client

На машине разработчика нужен установленный [Flutter](https://docs.flutter.dev/get-started/install) (Dart SDK входит в состав).

**Windows:** путь к проекту не должен содержать символ **`!`** (и ряд других) — иначе `flutter run -d windows` завершится ошибкой *invalid characters in path*. Переименуйте родительские папки или см. `docs/LOCAL_SETUP_WINDOWS.md`.

Базовый URL API задаётся в `lib/core/api_config.dart` (`kApiBaseUrl`) или через `--dart-define=API_BASE_URL=...`.

## Текущий функционал

- Каталог пресетов (`GET /v1/meta/personality-presets`), выбор карточкой образа (название, подпись пола, фрагмент легенды); при создании уходит `preset_id` — на backend подмешиваются стиль, легенда и темперамент.
- Создание нейродруга (`POST /v1/neurofriends`), сохранение `neurofriend_id` в `shared_preferences`.
- Лента чата из активного треда (`GET .../threads/active/messages`), pull-to-refresh.
- Текстовый ввод → `POST .../messages`.
- Запись WAV → `POST /v1/perception/audio`, воспроизведение ответа TTS (MP3 base64).
- Экран **Инспектор** (события + primary relationship) через debug API.

Зависимости: `dio`, `flutter_riverpod`, `record`, `path_provider`, `audioplayers`, `shared_preferences`.

## Инициализация проекта (если клон без платформенных папок)

В каталоге `mobile/`:

```bash
flutter create . --project-name neurofriend_mobile --org com.neurofriend --platforms=android,ios,web,windows
flutter pub get
```

## Запуск

Из `mobile/`: `flutter run -d windows` / `-d chrome` / устройство Android. Backend должен быть доступен по `kApiBaseUrl`; для голоса и ответов нужен `OPENAI_API_KEY` на сервере.

**Android-эмулятор:** `API_BASE_URL=http://10.0.2.2:8000`. **Физическое устройство:** IP ПК в локальной сети.
