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

  final _recorder = AudioRecorder();
  final _audioPlayer = AudioPlayer();
  bool _isRecording = false;
  /// Авто-озвучка ответов ассистента (intro и текст); голосовой ход и так возвращает MP3.
  bool _voiceRepliesEnabled = true;

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
    } else {
      await _loadPresetsCatalog();
    }
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
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _presetsLoading = false;
        _presetsError = formatDioError(e);
        _nameController.text = 'Нейродруг';
        _archetypeController.text = 'companion';
      });
    }
  }

  void _applyPreset(PersonalityPreset p) {
    setState(() {
      _selectedPresetId = p.id;
      _nameController.text = p.suggestedName;
      _archetypeController.text = p.archetype;
    });
  }

  Future<void> _saveNeurofriendId(String id) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_prefsNeurofriendIdKey, id);
    setState(() => _neurofriendId = id);
  }

  Future<void> _clearNeurofriend() async {
    final p = await SharedPreferences.getInstance();
    await p.remove(_prefsNeurofriendIdKey);
    setState(() {
      _neurofriendId = null;
      _messages = <ChatMessage>[];
    });
    await _loadPresetsCatalog();
  }

  Future<void> _refreshMessages() async {
    final id = _neurofriendId;
    if (id == null) return;
    final api = ref.read(neuroFriendApiProvider);
    try {
      final thread = await api.getActiveMessages(id);
      if (!mounted) return;
      setState(() => _messages = thread.messages);
    } on DioException catch (e) {
      if (!mounted) return;
      _snack('Чат: ${formatDioError(e)}');
    }
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
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

  Future<void> _uploadVoice(String path, String neurofriendId) async {
    setState(() => _busy = true);
    final api = ref.read(neuroFriendApiProvider);
    try {
      final turn = await api.sendVoiceAudio(neurofriendId, path);
      await _playReplyMp3(turn.audioBase64);
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
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _playReplyMp3(String audioBase64) async {
    final bytes = NeuroFriendApi.decodeReplyMp3(audioBase64);
    final dir = await getTemporaryDirectory();
    final out = File('${dir.path}/reply_${DateTime.now().millisecondsSinceEpoch}.mp3');
    await out.writeAsBytes(bytes);
    await _audioPlayer.stop();
    await _audioPlayer.play(DeviceFileSource(out.path));
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
      await _playReplyMp3(tts.audioBase64);
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
          if (id == null) _buildCreatePanel() else Expanded(child: _buildChat()),
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

    final presets = _presets ?? <PersonalityPreset>[];
    PersonalityPreset? selected;
    if (_selectedPresetId != null && presets.isNotEmpty) {
      for (final p in presets) {
        if (p.id == _selectedPresetId) {
          selected = p;
          break;
        }
      }
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Создать нейродруга', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'Выберите образ — подставятся имя и архетип; их можно изменить. Ядро личности фиксируется при создании.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          if (presets.isNotEmpty) ...[
            Text('Пресет', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            ...presets.map((p) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _PresetCard(
                    preset: p,
                    selected: p.id == _selectedPresetId,
                    onTap: () => _applyPreset(p),
                  ),
                )),
            if (selected != null) ...[
              const SizedBox(height: 4),
              Text(selected.description, style: Theme.of(context).textTheme.bodyMedium),
            ],
            const SizedBox(height: 16),
          ],
          TextField(
            controller: _nameController,
            decoration: const InputDecoration(labelText: 'Имя'),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _archetypeController,
            decoration: const InputDecoration(
              labelText: 'Архетип',
              helperText: 'Короткий код роли (например companion)',
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _busy ? null : _createNeurofriend,
            child: _busy
                ? const SizedBox(
                    height: 22,
                    width: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Создать и начать'),
          ),
          if (_status != null) Text(_status!, textAlign: TextAlign.center),
        ],
      ),
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
          child: Row(
            children: [
              Icon(Icons.graphic_eq, size: 18, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Озвучивать ответы (TTS)',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              Switch(
                value: _voiceRepliesEnabled,
                onChanged: _busy ? null : (v) => setState(() => _voiceRepliesEnabled = v),
              ),
            ],
          ),
        ),
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
                tooltip: _isRecording ? 'Остановить и отправить' : 'Запись WAV',
                icon: Icon(_isRecording ? Icons.stop_circle : Icons.mic),
                color: _isRecording ? Colors.red : null,
                onPressed: _busy ? null : _toggleRecording,
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

    return Material(
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
    );
  }
}
