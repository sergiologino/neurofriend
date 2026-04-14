import 'dart:convert';

import 'package:dio/dio.dart';

import '../core/api_config.dart';

class NeuroFriendCreateResult {
  NeuroFriendCreateResult({
    required this.id,
    required this.userId,
    required this.identityLocked,
    required this.firstIntroMessage,
  });

  factory NeuroFriendCreateResult.fromJson(Map<String, dynamic> json) {
    return NeuroFriendCreateResult(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      identityLocked: json['identity_locked'] as bool,
      firstIntroMessage: json['first_intro_message'] as String,
    );
  }

  final String id;
  final String userId;
  final bool identityLocked;
  final String firstIntroMessage;
}

/// Пресет личности из каталога (`GET /v1/meta/personality-presets`).
class PersonalityPreset {
  PersonalityPreset({
    required this.id,
    required this.title,
    required this.archetype,
    required this.description,
    required this.suggestedName,
    this.genderStyle,
    this.lifeLegend,
  });

  factory PersonalityPreset.fromJson(Map<String, dynamic> json) {
    return PersonalityPreset(
      id: json['id'] as String,
      title: json['title'] as String,
      archetype: json['archetype'] as String,
      description: json['description'] as String,
      suggestedName: json['suggested_name'] as String,
      genderStyle: json['gender_style'] as String?,
      lifeLegend: json['life_legend'] as String?,
    );
  }

  final String id;
  final String title;
  final String archetype;
  final String description;
  final String suggestedName;
  /// SRS `gender_style`: neutral / masculine / feminine / …
  final String? genderStyle;
  /// Короткая опорная «биография» для роли.
  final String? lifeLegend;

  /// Подпись пола/манеры для UI (русский).
  String? get genderLabelRu {
    final g = genderStyle?.trim().toLowerCase();
    if (g == null || g.isEmpty) return null;
    switch (g) {
      case 'feminine':
        return 'Женская манера';
      case 'masculine':
        return 'Мужская манера';
      case 'neutral':
        return 'Нейтральная манера';
      default:
        return genderStyle;
    }
  }
}

/// Элемент `GET /v1/meta/tts-voices` — голос OpenAI TTS под манеру пресета.
class TtsVoiceOption {
  TtsVoiceOption({required this.id, required this.label, required this.gender});

  factory TtsVoiceOption.fromJson(Map<String, dynamic> json) {
    return TtsVoiceOption(
      id: json['id'] as String,
      label: json['label'] as String,
      gender: json['gender'] as String,
    );
  }

  final String id;
  final String label;
  final String gender;
}

class ChatMessage {
  ChatMessage({
    required this.id,
    required this.direction,
    required this.role,
    required this.text,
    required this.source,
    required this.createdAt,
    this.eventId,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] as String,
      direction: json['direction'] as String,
      role: json['role'] as String,
      text: json['text'] as String,
      source: json['source'] as String? ?? '',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      eventId: json['event_id'] as String?,
    );
  }

  final String id;
  final String direction;
  final String role;
  final String text;
  final String source;
  final DateTime createdAt;
  final String? eventId;
}

class ActiveThreadMessages {
  ActiveThreadMessages({this.threadId, required this.messages});

  factory ActiveThreadMessages.fromJson(Map<String, dynamic> json) {
    final raw = json['messages'];
    final list = <ChatMessage>[];
    if (raw is List) {
      for (final e in raw) {
        if (e is Map<String, dynamic>) {
          list.add(ChatMessage.fromJson(e));
        }
      }
    }
    return ActiveThreadMessages(
      threadId: json['thread_id'] as String?,
      messages: list,
    );
  }

  final String? threadId;
  final List<ChatMessage> messages;
}

class VoiceTurnResult {
  VoiceTurnResult({
    required this.transcript,
    required this.replyText,
    required this.audioBase64,
    required this.neurofriendId,
  });

  factory VoiceTurnResult.fromJson(Map<String, dynamic> json) {
    return VoiceTurnResult(
      transcript: json['transcript'] as String,
      replyText: json['reply_text'] as String,
      audioBase64: json['audio_base64'] as String,
      neurofriendId: json['neurofriend_id'] as String,
    );
  }

  final String transcript;
  final String replyText;
  final String audioBase64;
  final String neurofriendId;
}

class TextReplyResult {
  TextReplyResult({required this.replyText});

  factory TextReplyResult.fromJson(Map<String, dynamic> json) {
    return TextReplyResult(replyText: json['reply_text'] as String);
  }

  final String replyText;
}

/// Ответ `POST /v1/perception/tts` — озвучка готового текста (intro, чат, повтор).
class TtsResult {
  TtsResult({required this.audioBase64, this.meta});

  factory TtsResult.fromJson(Map<String, dynamic> json) {
    return TtsResult(
      audioBase64: json['audio_base64'] as String,
      meta: json['meta'] as Map<String, dynamic>?,
    );
  }

  final String audioBase64;
  final Map<String, dynamic>? meta;
}

class DebugEventItem {
  DebugEventItem({
    required this.id,
    required this.timestamp,
    required this.eventType,
    required this.source,
    this.importanceScore,
    this.normalizedPayload,
  });

  factory DebugEventItem.fromJson(Map<String, dynamic> json) {
    return DebugEventItem(
      id: json['id'] as String,
      timestamp: DateTime.tryParse(json['timestamp'] as String? ?? '') ?? DateTime.now(),
      eventType: json['event_type'] as String,
      source: json['source'] as String,
      importanceScore: (json['importance_score'] as num?)?.toDouble(),
      normalizedPayload: json['normalized_payload_json'] as Map<String, dynamic>?,
    );
  }

  final String id;
  final DateTime timestamp;
  final String eventType;
  final String source;
  final double? importanceScore;
  final Map<String, dynamic>? normalizedPayload;
}

class RelationshipSnapshot {
  RelationshipSnapshot({
    required this.personRef,
    this.displayName,
    required this.trust,
    required this.attachment,
    required this.warmth,
    this.lastInteractionAt,
  });

  factory RelationshipSnapshot.fromJson(Map<String, dynamic> json) {
    return RelationshipSnapshot(
      personRef: json['person_ref'] as String,
      displayName: json['display_name'] as String?,
      trust: (json['trust'] as num).toDouble(),
      attachment: (json['attachment'] as num).toDouble(),
      warmth: (json['warmth'] as num).toDouble(),
      lastInteractionAt: json['last_interaction_at'] != null
          ? DateTime.tryParse(json['last_interaction_at'] as String)
          : null,
    );
  }

  final String personRef;
  final String? displayName;
  final double trust;
  final double attachment;
  final double warmth;
  final DateTime? lastInteractionAt;
}

/// HTTP-клиент к NeuroFriend API (пути с префиксом `/v1`).
class NeuroFriendApi {
  NeuroFriendApi({String? baseUrl})
      : _dio = Dio(
          BaseOptions(
            baseUrl: baseUrl ?? kApiBaseUrl,
            connectTimeout: const Duration(seconds: 30),
            receiveTimeout: const Duration(seconds: 120),
            sendTimeout: const Duration(seconds: 120),
          ),
        );

  final Dio _dio;

  Future<NeuroFriendCreateResult> createNeurofriend({
    required String name,
    required String archetype,
    String? presetId,
    String? ttsVoice,
  }) async {
    final data = <String, dynamic>{
      'name': name,
      'archetype': archetype,
      'identity_lock_confirmed': true,
    };
    if (presetId != null && presetId.isNotEmpty) {
      data['preset_id'] = presetId;
    }
    if (ttsVoice != null && ttsVoice.isNotEmpty) {
      data['tts_voice'] = ttsVoice;
    }
    final response = await _dio.post<Map<String, dynamic>>(
      '/v1/neurofriends',
      data: data,
    );
    return NeuroFriendCreateResult.fromJson(response.data!);
  }

  Future<ActiveThreadMessages> getActiveMessages(String neurofriendId) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/v1/conversations/$neurofriendId/threads/active/messages',
    );
    return ActiveThreadMessages.fromJson(response.data!);
  }

  Future<TextReplyResult> sendTextMessage(String neurofriendId, String text) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/v1/conversations/$neurofriendId/messages',
      data: <String, dynamic>{'text': text},
    );
    return TextReplyResult.fromJson(response.data!);
  }

  Future<TtsResult> synthesizeSpeech(String neurofriendId, String text) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/v1/perception/tts',
      data: <String, dynamic>{
        'neurofriend_id': neurofriendId,
        'text': text,
      },
    );
    return TtsResult.fromJson(response.data!);
  }

  Future<VoiceTurnResult> sendVoiceAudio(String neurofriendId, String audioFilePath) async {
    final formData = FormData.fromMap(<String, dynamic>{
      'neurofriend_id': neurofriendId,
      'audio': await MultipartFile.fromFile(audioFilePath, filename: 'audio.wav'),
    });
    final response = await _dio.post<Map<String, dynamic>>(
      '/v1/perception/audio',
      data: formData,
    );
    return VoiceTurnResult.fromJson(response.data!);
  }

  Future<List<DebugEventItem>> getDebugEvents(String neurofriendId, {int limit = 50}) async {
    final response = await _dio.get<dynamic>(
      '/v1/neurofriends/$neurofriendId/debug/events',
      queryParameters: <String, dynamic>{'limit': limit},
    );
    final data = response.data;
    if (data is! List) return <DebugEventItem>[];
    return data
        .whereType<Map>()
        .map((e) => DebugEventItem.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  Future<RelationshipSnapshot> getPrimaryRelationship(String neurofriendId) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/v1/neurofriends/$neurofriendId/debug/relationships/primary',
    );
    return RelationshipSnapshot.fromJson(response.data!);
  }

  Future<List<PersonalityPreset>> getPersonalityPresets() async {
    final response = await _dio.get<dynamic>('/v1/meta/personality-presets');
    final data = response.data;
    if (data is! List) return <PersonalityPreset>[];
    return data
        .whereType<Map>()
        .map((e) => PersonalityPreset.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  /// Список голосов TTS для [genderStyle] пресета (`masculine` / `feminine` / `neutral` или null).
  Future<List<TtsVoiceOption>> getTtsVoices({String? genderStyle}) async {
    final response = await _dio.get<dynamic>(
      '/v1/meta/tts-voices',
      queryParameters: <String, dynamic>{
        if (genderStyle != null && genderStyle.isNotEmpty) 'gender_style': genderStyle,
      },
    );
    final data = response.data;
    if (data is! List) return <TtsVoiceOption>[];
    return data
        .whereType<Map>()
        .map((e) => TtsVoiceOption.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  /// Декодирует MP3 из ответа TTS (base64) во временный файл; вызывающий удаляет файл после воспроизведения.
  static List<int> decodeReplyMp3(String audioBase64) => base64Decode(audioBase64);
}
