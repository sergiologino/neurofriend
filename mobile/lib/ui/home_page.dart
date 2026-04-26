import 'dart:async';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../providers.dart';
import '../services/neurofriend_api.dart';
import '../utils/api_error.dart';
import 'inspector_page.dart';

const _prefsNeurofriendIdKey = 'neurofriend_id';

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  final _nameController = TextEditingController();
  final _archetypeController = TextEditingController();
  final _textController = TextEditingController();

  String? _neurofriendId;
  bool _prefsLoaded = false;
  bool _busy = false;
  String? _status;

  List<PersonalityPreset>? _presets;
  bool _presetsLoading = false;
  String? _presetsError;
  String? _selectedPresetId;
  int _onboardingStep = 0;
  bool _identityLockConfirmed = false;
  double _softnessDelta = 0;
  double _directnessDelta = 0;
  double _initiativeDelta = 0;
  double _emotionalityDelta = 0;
  double _humorDelta = 0;
  String _replyLengthPreference = 'medium';
  String _closenessPreference = 'warm_equal';

  List<TtsVoiceOption> _ttsVoices = <TtsVoiceOption>[];
  bool _ttsVoicesLoading = false;
  String? _ttsVoicesError;
  String? _selectedTtsVoiceId;
  bool _voicePreviewBusy = false;

  final _recorder = AudioRecorder();
  final _audioPlayer = AudioPlayer();
  Timer? _pollTimer;
  bool _isRecording = false;
  bool _handsFreeListening = false;
  bool _handsFreeChunkActive = false;
  bool _assistantAudioPlaying = false;
  String? _lastAssistantSpokenText;
  DateTime? _lastAssistantSpokenAt;
  /// Авто-озвучка ответов ассистента (intro и текст); голосовой ход и так возвращает MP3.
  bool _voiceRepliesEnabled = true;
  String? _voiceProcessingLabel;

  List<ChatMessage> _messages = <ChatMessage>[];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadPrefs());
  }

  Future<void> _loadPrefs() async {
    final p = await SharedPreferences.getInstance();
    final id = p.getString(_prefsNeurofriendIdKey);
    if (!mounted) return;
    setState(() {
      _neurofriendId = id;
      _prefsLoaded = true;
    });
    if (id != null) {
      await _refreshMessages();
      _startPolling();
    } else {
      await _loadPresetsCatalog();
    }
  }

  void _startPolling() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (_neurofriendId != null && mounted && !_busy) {
        unawaited(_refreshMessages(silent: true));
      }
    });
  }

  Future<void> _loadPresetsCatalog() async {
    setState(() {
      _presetsLoading = true;
      _presetsError = null;
    });
    final api = ref.read(neuroFriendApiProvider);
    try {
      final list = await api.getPersonalityPresets();
      if (!mounted) return;
      if (list.isEmpty) {
        setState(() {
          _presets = list;
          _presetsLoading = false;
          _nameController.text = 'Нейродруг';
          _archetypeController.text = 'companion';
        });
        await _refreshTtsVoicesForGender(null);
        return;
      }
      final first = list.first;
      setState(() {
        _presets = list;
        _presetsLoading = false;
        _selectedPresetId = first.id;
        _nameController.text = first.suggestedName;
        _archetypeController.text = first.archetype;
      });
      await _refreshTtsVoicesForGender(first.genderStyle);
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _presetsLoading = false;
        _presetsError = formatDioError(e);
        _nameController.text = 'Нейродруг';
        _archetypeController.text = 'companion';
      });
      await _refreshTtsVoicesForGender(null);
    }
  }

  Future<void> _refreshTtsVoicesForGender(String? genderStyle) async {
    if (!mounted) return;
    setState(() {
      _ttsVoicesLoading = true;
      _ttsVoicesError = null;
    });
    final api = ref.read(neuroFriendApiProvider);
    try {
      final list = await api.getTtsVoices(genderStyle: genderStyle);
      if (!mounted) return;
      setState(() {
        _ttsVoices = list;
        _ttsVoicesLoading = false;
        if (list.isNotEmpty) {
          final cur = _selectedTtsVoiceId;
          if (cur == null || !list.any((e) => e.id == cur)) {
            _selectedTtsVoiceId = list.first.id;
          }
        } else {
          _selectedTtsVoiceId = null;
        }
      });
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _ttsVoicesLoading = false;
        _ttsVoicesError = formatDioError(e);
        _ttsVoices = <TtsVoiceOption>[];
        _selectedTtsVoiceId = null;
      });
    }
  }

  void _applyPreset(PersonalityPreset p) {
    setState(() {
      _selectedPresetId = p.id;
      _nameController.text = p.suggestedName;
      _archetypeController.text = p.archetype;
    });
    unawaited(_refreshTtsVoicesForGender(p.genderStyle));
  }

  String? _genderStyleForSelectedPreset() {
    final presets = _presets;
    final id = _selectedPresetId;
    if (presets == null || id == null) return null;
    for (final p in presets) {
      if (p.id == id) return p.genderStyle;
    }
    return null;
  }

  Future<void> _previewVoiceSample() async {
    final voice = _selectedTtsVoiceId;
    if (voice == null || _busy) return;
    setState(() => _voicePreviewBusy = true);
    final api = ref.read(neuroFriendApiProvider);
    try {
      final t = await api.previewTts(
        ttsVoice: voice,
        genderStyle: _genderStyleForSelectedPreset(),
      );
      if (!mounted) return;
      await _playReplyMp3(t.audioBase64);
    } on DioException catch (e) {
      if (mounted) _snack('Прослушивание: ${formatDioError(e)}');
    } catch (e) {
      if (mounted) _snack('Прослушивание: $e');
    } finally {
      if (mounted) setState(() => _voicePreviewBusy = false);
    }
  }

  Future<void> _saveNeurofriendId(String id) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_prefsNeurofriendIdKey, id);
    setState(() => _neurofriendId = id);
    _startPolling();
  }

  Future<void> _clearNeurofriend() async {
    final p = await SharedPreferences.getInstance();
    await p.remove(_prefsNeurofriendIdKey);
    _pollTimer?.cancel();
    setState(() {
      _neurofriendId = null;
      _messages = <ChatMessage>[];
    });
    await _loadPresetsCatalog();
  }

  Future<void> _refreshMessages({bool silent = false}) async {
    final id = _neurofriendId;
    if (id == null) return;
    final api = ref.read(neuroFriendApiProvider);
    try {
      final thread = await api.getActiveMessages(id);
      if (!mounted) return;
      setState(() => _messages = thread.messages);
    } on DioException catch (e) {
      if (!mounted) return;
      if (!silent) _snack('Чат: ${formatDioError(e)}');
    }
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Map<String, dynamic> _buildPersonalizationPayload() {
    return <String, dynamic>{
      'softness_delta': _softnessDelta,
      'directness_delta': _directnessDelta,
      'initiative_delta': _initiativeDelta,
      'emotionality_delta': _emotionalityDelta,
      'humor_delta': _humorDelta,
      'reply_length_preference': _replyLengthPreference,
      'closeness_preference': _closenessPreference,
    };
  }

  PersonalityPreset? _selectedPreset() {
    final presets = _presets ?? <PersonalityPreset>[];
    for (final p in presets) {
      if (p.id == _selectedPresetId) return p;
    }
    return presets.isEmpty ? null : presets.first;
  }

  Future<void> _createNeurofriend() async {
    setState(() {
      _busy = true;
      _status = null;
    });
    final api = ref.read(neuroFriendApiProvider);
    try {
      final r = await api.createNeurofriend(
        name: _nameController.text.trim(),
        archetype: _archetypeController.text.trim(),
        presetId: _selectedPresetId,
        ttsVoice: _selectedTtsVoiceId,
        personalization: _buildPersonalizationPayload(),
      );
      await _saveNeurofriendId(r.id);
      if (!mounted) return;
      _snack('Создан нейродруг, intro в ленте');
      await _refreshMessages();
      if (mounted && _voiceRepliesEnabled && r.firstIntroMessage.trim().isNotEmpty) {
        unawaited(_playAssistantVoice(r.firstIntroMessage));
      }
    } on DioException catch (e) {
      if (!mounted) return;
      _snack('Ошибка: ${formatDioError(e)}');
    } catch (e) {
      if (!mounted) return;
      _snack('Ошибка: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sendText() async {
    final id = _neurofriendId;
    final text = _textController.text.trim();
    if (id == null || text.isEmpty) return;
    setState(() => _busy = true);
    final api = ref.read(neuroFriendApiProvider);
    try {
      final reply = await api.sendTextMessage(id, text);
      _textController.clear();
      await _refreshMessages();
      if (_voiceRepliesEnabled && reply.replyText.trim().isNotEmpty) {
        if (mounted && _handsFreeListening) {
          setState(() => _busy = false);
        }
        await _playAssistantVoice(reply.replyText);
      }
    } on DioException catch (e) {
      _snack('Текст: ${formatDioError(e)}');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _toggleRecording() async {
    final id = _neurofriendId;
    if (id == null) return;

    if (_isRecording) {
      final path = await _recorder.stop();
      setState(() => _isRecording = false);
      if (path == null || path.isEmpty) {
        _snack('Запись пуста');
        return;
      }
      await _uploadVoice(path, id);
      return;
    }

    if (!await _recorder.hasPermission()) {
      _snack('Нет разрешения на микрофон');
      return;
    }

    final dir = await getTemporaryDirectory();
    final filePath =
        '${dir.path}/nf_voice_${DateTime.now().millisecondsSinceEpoch}.wav';
    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.wav),
      path: filePath,
    );
    setState(() => _isRecording = true);
  }

  Future<void> _toggleHandsFreeListening() async {
    final id = _neurofriendId;
    if (id == null) return;
    if (_handsFreeListening) {
      setState(() {
        _handsFreeListening = false;
        _voiceProcessingLabel = null;
      });
      return;
    }
    if (!await _recorder.hasPermission()) {
      _snack('Нет разрешения на микрофон');
      return;
    }
    setState(() {
      _handsFreeListening = true;
      _voiceProcessingLabel = 'Слушаю обращение по имени короткими фрагментами...';
    });
    unawaited(_handsFreeLoop(id));
  }

  Future<void> _handsFreeLoop(String neurofriendId) async {
    while (mounted && _handsFreeListening) {
      if (_busy || _isRecording || _handsFreeChunkActive) {
        await Future<void>.delayed(const Duration(milliseconds: 500));
        continue;
      }
      _handsFreeChunkActive = true;
      String? path;
      try {
        final dir = await getTemporaryDirectory();
        path = '${dir.path}/nf_wake_${DateTime.now().millisecondsSinceEpoch}.wav';
        await _recorder.start(
          const RecordConfig(encoder: AudioEncoder.wav),
          path: path,
        );
        if (mounted) {
          setState(() => _voiceProcessingLabel = 'Слушаю: можно позвать по имени...');
        }
        await Future<void>.delayed(const Duration(seconds: 4));
        final stopped = await _recorder.stop();
        if (!_handsFreeListening || stopped == null || stopped.isEmpty) {
          continue;
        }
        await _uploadVoice(stopped, neurofriendId, wakeCheck: true);
      } catch (e) {
        if (mounted && _handsFreeListening) _snack('Слушание: $e');
        try {
          await _recorder.stop();
        } catch (_) {}
        await Future<void>.delayed(const Duration(seconds: 2));
      } finally {
        if (path != null) {
          try {
            final f = File(path);
            if (await f.exists()) await f.delete();
          } catch (_) {}
        }
        _handsFreeChunkActive = false;
        if (mounted && _handsFreeListening && !_busy) {
          setState(() => _voiceProcessingLabel = 'Слушаю обращение по имени...');
        }
      }
      await Future<void>.delayed(const Duration(milliseconds: 300));
    }
  }

  Future<void> _uploadVoice(String path, String neurofriendId, {bool wakeCheck = false}) async {
    setState(() {
      _busy = true;
      _voiceProcessingLabel = wakeCheck
          ? 'Проверяю, было ли обращение к нейродругу...'
          : 'Обработка голоса: распознавание → ответ → озвучка';
    });
    final api = ref.read(neuroFriendApiProvider);
    try {
      final guardText = _recentPlaybackGuardText();
      final turn = await api.sendVoiceAudio(
        neurofriendId,
        path,
        wakeCheck: wakeCheck,
        playbackGuardText: guardText,
      );
      if (!turn.addressedToNeurofriend) {
        if (mounted && _handsFreeListening) {
          setState(() => _voiceProcessingLabel = 'Слушаю обращение по имени...');
        }
        return;
      }
      if (mounted) {
        setState(() => _voiceProcessingLabel = 'Озвучиваю ответ...');
      }
      if (turn.audioBase64.trim().isNotEmpty) {
        if (_assistantAudioPlaying) {
          await _audioPlayer.stop();
        }
        if (mounted && _handsFreeListening) {
          setState(() => _busy = false);
        }
        await _playReplyMp3(turn.audioBase64, spokenText: turn.replyText);
      }
      await _refreshMessages();
      try {
        final f = File(path);
        if (await f.exists()) await f.delete();
      } catch (_) {}
    } on DioException catch (e) {
      _snack('Голос: ${formatDioError(e)}');
    } catch (e) {
      _snack('Голос: $e');
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _voiceProcessingLabel = _handsFreeListening ? 'Слушаю обращение по имени...' : null;
        });
      }
    }
  }

  Future<void> _playReplyMp3(String audioBase64, {String? spokenText}) async {
    final bytes = NeuroFriendApi.decodeReplyMp3(audioBase64);
    final dir = await getTemporaryDirectory();
    final out = File('${dir.path}/reply_${DateTime.now().millisecondsSinceEpoch}.mp3');
    await out.writeAsBytes(bytes);
    await _audioPlayer.stop();
    _lastAssistantSpokenText = spokenText;
    _lastAssistantSpokenAt = DateTime.now();
    if (mounted) {
      setState(() {
        _assistantAudioPlaying = true;
        if (_handsFreeListening) {
          _voiceProcessingLabel = 'Нейродруг говорит; можно перебить голосом.';
        }
      });
    } else {
      _assistantAudioPlaying = true;
    }
    try {
      final completed = _audioPlayer.onPlayerComplete.first;
      await _audioPlayer.play(DeviceFileSource(out.path));
      await Future.any<void>([
        completed.then((_) {}),
        Future<void>.delayed(const Duration(seconds: 45)),
      ]);
    } finally {
      _assistantAudioPlaying = false;
      if (mounted && _handsFreeListening) {
        setState(() => _voiceProcessingLabel = 'Слушаю обращение по имени...');
      } else if (mounted) {
        setState(() {});
      }
    }
  }

  String? _recentPlaybackGuardText() {
    final text = _lastAssistantSpokenText;
    final at = _lastAssistantSpokenAt;
    if (text == null || text.trim().isEmpty || at == null) return null;
    final age = DateTime.now().difference(at);
    if (_assistantAudioPlaying || age <= const Duration(seconds: 20)) {
      return text;
    }
    return null;
  }

  /// Озвучка через `POST /v1/perception/tts`. [allowWithoutTtsToggle] — для кнопки «ещё раз», когда переключатель выкл.
  Future<void> _playAssistantVoice(String text, {bool allowWithoutTtsToggle = false}) async {
    if (text.trim().isEmpty) return;
    if (!allowWithoutTtsToggle && !_voiceRepliesEnabled) return;
    final id = _neurofriendId;
    if (id == null) return;
    final api = ref.read(neuroFriendApiProvider);
    try {
      final tts = await api.synthesizeSpeech(id, text);
      await _playReplyMp3(tts.audioBase64, spokenText: text);
    } on DioException catch (e) {
      if (mounted) _snack('Озвучка: ${formatDioError(e)}');
    } catch (e) {
      if (mounted) _snack('Озвучка: $e');
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _archetypeController.dispose();
    _textController.dispose();
    _pollTimer?.cancel();
    _handsFreeListening = false;
    _assistantAudioPlaying = false;
    _recorder.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_prefsLoaded) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final id = _neurofriendId;

    return Scaffold(
      appBar: AppBar(
        title: const Text('NeuroFriend'),
        actions: [
          if (id != null)
            IconButton(
              tooltip: 'Инспектор',
              icon: const Icon(Icons.bug_report_outlined),
              onPressed: _busy
                  ? null
                  : () {
                      Navigator.of(context).push<void>(
                        MaterialPageRoute<void>(
                          builder: (context) => InspectorPage(neurofriendId: id),
                        ),
                      );
                    },
            ),
        ],
      ),
      body: Column(
        children: [
          Expanded(child: id == null ? _buildCreatePanel() : _buildChat()),
          if (id != null) _buildComposer(),
        ],
      ),
    );
  }

  Widget _buildCreatePanel() {
    if (_presetsLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_presetsError != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('Не удалось загрузить пресеты: $_presetsError', textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton(onPressed: _loadPresetsCatalog, child: const Text('Повторить')),
            ],
          ),
        ),
      );
    }

    final selected = _selectedPreset();
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _OnboardingProgress(step: _onboardingStep),
          const SizedBox(height: 16),
          _buildOnboardingStep(selected),
          const SizedBox(height: 16),
          _buildOnboardingNav(selected),
          if (_status != null) Text(_status!, textAlign: TextAlign.center),
        ],
      ),
    );
  }

  Widget _buildOnboardingStep(PersonalityPreset? selected) {
    switch (_onboardingStep) {
      case 0:
        return _WelcomeStep(onStart: () => setState(() => _onboardingStep = 1));
      case 1:
        return _PresetGalleryStep(
          presets: _presets ?? <PersonalityPreset>[],
          selectedPresetId: _selectedPresetId,
          onSelect: _applyPreset,
        );
      case 2:
        return _PresetPreviewStep(preset: selected);
      case 3:
        return _NameAndVoiceStep(
          nameController: _nameController,
          archetypeController: _archetypeController,
          ttsVoices: _ttsVoices,
          selectedTtsVoiceId: _selectedTtsVoiceId,
          ttsVoicesLoading: _ttsVoicesLoading,
          ttsVoicesError: _ttsVoicesError,
          voicePreviewBusy: _voicePreviewBusy,
          genderStyle: selected?.genderStyle,
          onNameChanged: (_) => setState(() {}),
          onVoiceChanged: (v) => setState(() => _selectedTtsVoiceId = v),
          onPreviewVoice: _previewVoiceSample,
        );
      case 4:
        return _PersonalizationStep(
          softnessDelta: _softnessDelta,
          directnessDelta: _directnessDelta,
          initiativeDelta: _initiativeDelta,
          emotionalityDelta: _emotionalityDelta,
          humorDelta: _humorDelta,
          replyLengthPreference: _replyLengthPreference,
          closenessPreference: _closenessPreference,
          onSoftnessChanged: (v) => setState(() => _softnessDelta = v),
          onDirectnessChanged: (v) => setState(() => _directnessDelta = v),
          onInitiativeChanged: (v) => setState(() => _initiativeDelta = v),
          onEmotionalityChanged: (v) => setState(() => _emotionalityDelta = v),
          onHumorChanged: (v) => setState(() => _humorDelta = v),
          onReplyLengthChanged: (v) => setState(() => _replyLengthPreference = v),
          onClosenessChanged: (v) => setState(() => _closenessPreference = v),
        );
      case 5:
        return _IdentityLockStep(
          selected: selected,
          confirmed: _identityLockConfirmed,
          onChanged: (v) => setState(() => _identityLockConfirmed = v),
        );
      default:
        return _BirthStep(selected: selected, busy: _busy);
    }
  }

  Widget _buildOnboardingNav(PersonalityPreset? selected) {
    final isLast = _onboardingStep >= 6;
    final canContinue = switch (_onboardingStep) {
      1 => selected != null,
      3 => _nameController.text.trim().isNotEmpty,
      5 => _identityLockConfirmed,
      _ => true,
    };
    return Row(
      children: [
        if (_onboardingStep > 0)
          TextButton(
            onPressed: _busy ? null : () => setState(() => _onboardingStep -= 1),
            child: const Text('Назад'),
          ),
        const Spacer(),
        FilledButton(
          onPressed: (_busy || !canContinue)
              ? null
              : () {
                  if (isLast) {
                    _createNeurofriend();
                  } else {
                    setState(() => _onboardingStep += 1);
                  }
                },
          child: _busy
              ? const SizedBox(
                  height: 22,
                  width: 22,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(isLast ? 'Создать и начать' : 'Дальше'),
        ),
      ],
    );
  }

  Widget _buildChat() {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  'ID: $_neurofriendId',
                  style: Theme.of(context).textTheme.bodySmall,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              TextButton(onPressed: _busy ? null : _clearNeurofriend, child: const Text('Сбросить')),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
          child: Tooltip(
            message:
                'Включено: после создания нейродруга и при ответе на текст автоматически воспроизводится речь (TTS). '
                'Выключено: звук только после голосовой записи; любую реплику ассистента можно озвучить кнопкой динамика.',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.graphic_eq, size: 18, color: Theme.of(context).colorScheme.primary),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Озвучивать ответы (TTS)',
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                    ),
                    Switch(
                      value: _voiceRepliesEnabled,
                      onChanged: _busy ? null : (v) => setState(() => _voiceRepliesEnabled = v),
                    ),
                  ],
                ),
                Padding(
                  padding: const EdgeInsets.only(left: 26, top: 2),
                  child: Text(
                    _voiceRepliesEnabled
                        ? 'Авто-озвучка intro и текстовых ответов включена.'
                        : 'Авто-озвучка выключена; запись голоса и кнопка у сообщения работают.',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                  ),
                ),
              ],
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
          child: Row(
            children: [
              Icon(
                _handsFreeListening ? Icons.hearing : Icons.hearing_disabled_outlined,
                size: 18,
                color: _handsFreeListening ? Theme.of(context).colorScheme.primary : null,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _handsFreeListening
                      ? 'Режим имени включён: можно позвать «${_displayNameForWake()}».'
                      : 'Режим имени выключен: голос отправляется кнопкой микрофона.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              Switch(
                value: _handsFreeListening,
                onChanged: _busy && !_handsFreeListening ? null : (_) => _toggleHandsFreeListening(),
              ),
            ],
          ),
        ),
        if (_voiceProcessingLabel != null) _buildVoiceProcessingBanner(),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _refreshMessages,
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, i) {
                final m = _messages[i];
                final mine = m.direction == 'in' || m.role == 'user';
                return Align(
                  alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.fromLTRB(12, 12, 4, 12),
                    constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.85),
                    decoration: BoxDecoration(
                      color: mine
                          ? Theme.of(context).colorScheme.primaryContainer
                          : Theme.of(context).colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Flexible(
                          child: SelectableText(
                            m.text,
                            style: Theme.of(context).textTheme.bodyLarge,
                          ),
                        ),
                        if (!mine)
                          IconButton(
                            tooltip: 'Озвучить ещё раз',
                            icon: const Icon(Icons.volume_up_outlined, size: 20),
                            onPressed: _busy ? null : () => _playAssistantVoice(m.text, allowWithoutTtsToggle: true),
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildVoiceProcessingBanner() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.secondaryContainer.withValues(alpha: 0.55),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _voiceProcessingLabel!,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _displayNameForWake() {
    final name = _nameController.text.trim();
    return name.isEmpty ? 'по имени' : name;
  }

  Widget _buildComposer() {
    return Material(
      elevation: 8,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 8, 8, 8),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              IconButton(
                tooltip: _isRecording ? 'Остановить и отправить' : 'Ручная запись WAV',
                icon: Icon(_isRecording ? Icons.stop_circle : Icons.mic),
                color: _isRecording ? Colors.red : null,
                onPressed: _busy || _handsFreeChunkActive ? null : _toggleRecording,
              ),
              Expanded(
                child: TextField(
                  controller: _textController,
                  minLines: 1,
                  maxLines: 4,
                  decoration: const InputDecoration(
                    hintText: 'Сообщение (текстовый fallback)',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  onSubmitted: (_) {
                    if (!_busy) _sendText();
                  },
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.send),
                onPressed: _busy ? null : _sendText,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _OnboardingProgress extends StatelessWidget {
  const _OnboardingProgress({required this.step});

  final int step;

  @override
  Widget build(BuildContext context) {
    final labels = ['Идея', 'Личность', 'Preview', 'Имя', 'Настройка', 'Ядро', 'Рождение'];
    final safeStep = step.clamp(0, labels.length - 1);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Создание нейродруга', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        LinearProgressIndicator(value: (safeStep + 1) / labels.length),
        const SizedBox(height: 8),
        Text(labels[safeStep], style: Theme.of(context).textTheme.labelLarge),
      ],
    );
  }
}

class _WelcomeStep extends StatelessWidget {
  const _WelcomeStep({required this.onStart});

  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    return _StepCard(
      title: 'Создай нейродруга, который будет рядом',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Ты выбираешь не набор параметров и не чат-бота. У нейродруга будет свой характер, память, голос и постепенно появляющаяся история рядом с тобой.',
          ),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onStart, child: const Text('Выбрать личность')),
        ],
      ),
    );
  }
}

class _PresetGalleryStep extends StatelessWidget {
  const _PresetGalleryStep({
    required this.presets,
    required this.selectedPresetId,
    required this.onSelect,
  });

  final List<PersonalityPreset> presets;
  final String? selectedPresetId;
  final ValueChanged<PersonalityPreset> onSelect;

  @override
  Widget build(BuildContext context) {
    return _StepCard(
      title: 'Выбери живой характер',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Сначала выбери образ. Настройка будет позже, в пределах его природы.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 12),
          ...presets.map(
            (p) => Padding(
              key: ValueKey(p.id),
              padding: const EdgeInsets.only(bottom: 10),
              child: _PresetCard(
                preset: p,
                selected: p.id == selectedPresetId,
                onTap: () => onSelect(p),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PresetPreviewStep extends StatelessWidget {
  const _PresetPreviewStep({required this.preset});

  final PersonalityPreset? preset;

  @override
  Widget build(BuildContext context) {
    final p = preset;
    if (p == null) {
      return const _StepCard(title: 'Preview', child: Text('Выбери пресет на предыдущем шаге.'));
    }
    return _StepCard(
      title: p.title,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (p.genderLabelRu != null) Text(p.genderLabelRu!, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          Text(p.description),
          if (p.lifeLegend != null && p.lifeLegend!.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text('Опорная биография', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 4),
            Text(p.lifeLegend!),
          ],
          const SizedBox(height: 12),
          Text('Как будет начинать общение', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 4),
          const Text('Первое сообщение будет сгенерировано из выбранного характера, а не из общего шаблона.'),
        ],
      ),
    );
  }
}

class _NameAndVoiceStep extends StatelessWidget {
  const _NameAndVoiceStep({
    required this.nameController,
    required this.archetypeController,
    required this.ttsVoices,
    required this.selectedTtsVoiceId,
    required this.ttsVoicesLoading,
    required this.ttsVoicesError,
    required this.voicePreviewBusy,
    required this.genderStyle,
    required this.onNameChanged,
    required this.onVoiceChanged,
    required this.onPreviewVoice,
  });

  final TextEditingController nameController;
  final TextEditingController archetypeController;
  final List<TtsVoiceOption> ttsVoices;
  final String? selectedTtsVoiceId;
  final bool ttsVoicesLoading;
  final String? ttsVoicesError;
  final bool voicePreviewBusy;
  final String? genderStyle;
  final ValueChanged<String> onNameChanged;
  final ValueChanged<String?> onVoiceChanged;
  final VoidCallback onPreviewVoice;

  @override
  Widget build(BuildContext context) {
    final nameWarning = _nameGenderWarning(nameController.text, genderStyle);
    return _StepCard(
      title: 'Дай имя и выбери голос',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: nameController,
            decoration: const InputDecoration(labelText: 'Имя'),
            onChanged: onNameChanged,
          ),
          if (nameWarning != null) ...[
            const SizedBox(height: 6),
            Text(
              nameWarning,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: 8),
          TextField(
            controller: archetypeController,
            decoration: const InputDecoration(
              labelText: 'Архетип',
              helperText: 'Код роли фиксируется в ядре личности.',
            ),
          ),
          const SizedBox(height: 16),
          if (ttsVoicesLoading && ttsVoices.isEmpty) const LinearProgressIndicator(),
          if (ttsVoicesError != null)
            Text('Голоса: $ttsVoicesError', style: TextStyle(color: Theme.of(context).colorScheme.error)),
          if (ttsVoices.isNotEmpty) ...[
            DropdownButtonFormField<String>(
              initialValue: selectedTtsVoiceId,
              decoration: const InputDecoration(labelText: 'Голос', border: OutlineInputBorder()),
              items: ttsVoices
                  .map((v) => DropdownMenuItem<String>(value: v.id, child: Text(v.label)))
                  .toList(),
              onChanged: onVoiceChanged,
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: selectedTtsVoiceId == null ? null : onPreviewVoice,
              icon: voicePreviewBusy
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.play_arrow_outlined),
              label: Text(voicePreviewBusy ? 'Генерация...' : 'Прослушать голос'),
            ),
          ],
        ],
      ),
    );
  }

  String? _nameGenderWarning(String rawName, String? genderStyle) {
    final style = genderStyle?.trim().toLowerCase();
    if (style != 'feminine' && style != 'masculine') return null;
    final name = rawName.trim().toLowerCase();
    if (name.isEmpty) return null;
    const masculineNames = {'вася', 'василий', 'денис', 'олег', 'антон', 'иван', 'сергей', 'алексей', 'дмитрий'};
    const feminineNames = {'аня', 'анна', 'марина', 'алиса', 'елена', 'ольга', 'катя', 'екатерина', 'ирина'};
    if (style == 'feminine' && masculineNames.contains(name)) {
      return 'Похоже на мужское имя для женской манеры. Можно оставить, но проверь, так ли задумано.';
    }
    if (style == 'masculine' && feminineNames.contains(name)) {
      return 'Похоже на женское имя для мужской манеры. Можно оставить, но проверь, так ли задумано.';
    }
    return null;
  }
}

class _PersonalizationStep extends StatelessWidget {
  const _PersonalizationStep({
    required this.softnessDelta,
    required this.directnessDelta,
    required this.initiativeDelta,
    required this.emotionalityDelta,
    required this.humorDelta,
    required this.replyLengthPreference,
    required this.closenessPreference,
    required this.onSoftnessChanged,
    required this.onDirectnessChanged,
    required this.onInitiativeChanged,
    required this.onEmotionalityChanged,
    required this.onHumorChanged,
    required this.onReplyLengthChanged,
    required this.onClosenessChanged,
  });

  final double softnessDelta;
  final double directnessDelta;
  final double initiativeDelta;
  final double emotionalityDelta;
  final double humorDelta;
  final String replyLengthPreference;
  final String closenessPreference;
  final ValueChanged<double> onSoftnessChanged;
  final ValueChanged<double> onDirectnessChanged;
  final ValueChanged<double> onInitiativeChanged;
  final ValueChanged<double> onEmotionalityChanged;
  final ValueChanged<double> onHumorChanged;
  final ValueChanged<String> onReplyLengthChanged;
  final ValueChanged<String> onClosenessChanged;

  @override
  Widget build(BuildContext context) {
    return _StepCard(
      title: 'Сделать своим',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Это не пересоздаёт личность, а слегка сдвигает выбранный характер.', style: Theme.of(context).textTheme.bodySmall),
          _DeltaSlider(label: 'Мягче ↔ твёрже', value: softnessDelta, onChanged: onSoftnessChanged),
          _DeltaSlider(label: 'Деликатнее ↔ прямее', value: directnessDelta, onChanged: onDirectnessChanged),
          _DeltaSlider(label: 'Тише ↔ инициативнее', value: initiativeDelta, onChanged: onInitiativeChanged),
          _DeltaSlider(label: 'Спокойнее ↔ эмоциональнее', value: emotionalityDelta, onChanged: onEmotionalityChanged),
          _DeltaSlider(label: 'Серьёзнее ↔ ироничнее', value: humorDelta, onChanged: onHumorChanged),
          const SizedBox(height: 12),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'short', label: Text('Коротко')),
              ButtonSegment(value: 'medium', label: Text('Средне')),
              ButtonSegment(value: 'long', label: Text('Развёрнуто')),
            ],
            selected: {replyLengthPreference},
            onSelectionChanged: (v) => onReplyLengthChanged(v.first),
          ),
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'calm_distance', label: Text('Дистанция')),
              ButtonSegment(value: 'warm_equal', label: Text('Тепло')),
            ],
            selected: {closenessPreference},
            onSelectionChanged: (v) => onClosenessChanged(v.first),
          ),
        ],
      ),
    );
  }
}

class _IdentityLockStep extends StatelessWidget {
  const _IdentityLockStep({
    required this.selected,
    required this.confirmed,
    required this.onChanged,
  });

  final PersonalityPreset? selected;
  final bool confirmed;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return _StepCard(
      title: 'Зафиксировать ядро',
      child: CheckboxListTile(
        value: confirmed,
        onChanged: (v) => onChanged(v ?? false),
        title: Text('Я понимаю, что ${selected?.title ?? 'выбранный характер'} останется собой'),
        subtitle: const Text(
          'Он сможет учиться, помнить и меняться в нюансах, но архетип и базовая природа не будут переписываться.',
        ),
      ),
    );
  }
}

class _BirthStep extends StatelessWidget {
  const _BirthStep({required this.selected, required this.busy});

  final PersonalityPreset? selected;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    return _StepCard(
      title: 'Первый разговор',
      child: Row(
        children: [
          if (busy) const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2)),
          if (busy) const SizedBox(width: 12),
          Expanded(
            child: Text(
              busy
                  ? 'Нейродруг собирает первое представление о себе и готовится начать разговор.'
                  : 'Готово. Сейчас ${selected?.suggestedName ?? 'нейродруг'} появится в чате и напишет первым.',
            ),
          ),
        ],
      ),
    );
  }
}

class _StepCard extends StatelessWidget {
  const _StepCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          key: ValueKey(title),
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            child,
          ],
        ),
      ),
    );
  }
}

class _DeltaSlider extends StatelessWidget {
  const _DeltaSlider({required this.label, required this.value, required this.onChanged});

  final String label;
  final double value;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 8),
        Text(label, style: Theme.of(context).textTheme.labelLarge),
        Slider(
          min: -0.15,
          max: 0.15,
          divisions: 6,
          value: value,
          label: value.toStringAsFixed(2),
          onChanged: onChanged,
        ),
      ],
    );
  }
}

String _legendExcerpt(String text, {int maxChars = 160}) {
  final t = text.trim();
  if (t.isEmpty) return '';
  if (t.length <= maxChars) return t;
  return '${t.substring(0, maxChars).trimRight()}…';
}

class _PresetCard extends StatelessWidget {
  const _PresetCard({
    required this.preset,
    required this.selected,
    required this.onTap,
  });

  final PersonalityPreset preset;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final gender = preset.genderLabelRu;
    final legend = preset.lifeLegend;

    return Semantics(
      button: true,
      selected: selected,
      label: '${preset.title}${gender == null ? '' : ', $gender'}',
      child: ExcludeSemantics(
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(12),
            child: Ink(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: selected ? scheme.primary : scheme.outlineVariant,
                  width: selected ? 2 : 1,
                ),
                color: selected
                    ? scheme.primaryContainer.withValues(alpha: 0.35)
                    : scheme.surfaceContainerHighest.withValues(alpha: 0.45),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      preset.title,
                      style: textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    if (gender != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        gender,
                        style: textTheme.labelMedium?.copyWith(
                          color: scheme.secondary,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                    if (legend != null && legend.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        _legendExcerpt(legend),
                        style: textTheme.bodySmall?.copyWith(height: 1.35),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
