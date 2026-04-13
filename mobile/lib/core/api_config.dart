/// Базовый URL backend. Для Android-эмулятора используйте `http://10.0.2.2:8000`.
/// Переопределение при сборке: `--dart-define=API_BASE_URL=http://...`
const String kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000',
);
