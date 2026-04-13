import 'package:dio/dio.dart';

/// Текст ошибки из ответа FastAPI (`detail`) или запасной вариант.
String formatDioError(DioException e) {
  final data = e.response?.data;
  if (data is Map<String, dynamic>) {
    final d = data['detail'];
    if (d == null) return e.message ?? '$e';
    if (d is String) return d;
    return d.toString();
  }
  if (data is String && data.isNotEmpty) {
    return data.length > 200 ? '${data.substring(0, 200)}…' : data;
  }
  return e.message ?? '$e';
}
