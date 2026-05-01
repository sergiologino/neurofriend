import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers.dart';
import '../services/neurofriend_api.dart';

class InspectorPage extends ConsumerStatefulWidget {
  const InspectorPage({super.key, required this.neurofriendId});

  final String neurofriendId;

  @override
  ConsumerState<InspectorPage> createState() => _InspectorPageState();
}

class _InspectorPageState extends ConsumerState<InspectorPage> {
  bool _loading = true;
  String? _error;
  RelationshipSnapshot? _rel;
  List<DebugEventItem> _events = <DebugEventItem>[];
  List<ParticipantDebugItem> _participants = <ParticipantDebugItem>[];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final api = ref.read(neuroFriendApiProvider);
    try {
      final rel = await api.getPrimaryRelationship(widget.neurofriendId);
      final events = await api.getDebugEvents(widget.neurofriendId, limit: 80);
      final participants = await api.getDebugParticipants(widget.neurofriendId);
      if (!mounted) return;
      setState(() {
        _rel = rel;
        _events = events;
        _participants = participants;
        _loading = false;
      });
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.response?.data?.toString() ?? e.message ?? '$e';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = '$e';
      });
    }
  }

  String _consentRu(String code) {
    switch (code) {
      case 'implicit_conversation':
        return 'Как в диалоге';
      case 'explicit_allow':
        return 'Дообучение разрешено';
      case 'declined':
        return 'Без дообучения отпечатка';
      case 'system_internal':
        return 'Системный';
      default:
        return code;
    }
  }

  Future<void> _patchParticipant({
    required ParticipantDebugItem p,
    String? displayName,
    String? consentStatus,
  }) async {
    final api = ref.read(neuroFriendApiProvider);
    try {
      await api.patchDebugParticipant(
        widget.neurofriendId,
        p.id,
        displayName: displayName,
        consentStatus: consentStatus,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Участник обновлён')),
      );
      await _load();
    } on DioException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(e.response?.data?.toString() ?? e.message ?? '$e')),
      );
    }
  }

  Future<void> _showRenameDialog(ParticipantDebugItem p) async {
    final controller = TextEditingController(text: p.displayName ?? '');
    try {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Отображаемое имя'),
          content: TextField(
            controller: controller,
            decoration: const InputDecoration(labelText: 'Имя участника'),
            autofocus: true,
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Отмена')),
            FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Сохранить')),
          ],
        ),
      );
      if (ok == true && mounted) {
        await _patchParticipant(p: p, displayName: controller.text.trim());
      }
    } finally {
      controller.dispose();
    }
  }

  Future<void> _showConsentSheet(ParticipantDebugItem p) async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
              child: Text(
                'Согласие на MVP-отпечаток голоса',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            ListTile(
              leading: const Icon(Icons.chat_outlined),
              title: Text(_consentRu('implicit_conversation')),
              subtitle: const Text('Поведение по умолчанию для диалога'),
              onTap: () {
                Navigator.pop(ctx);
                _patchParticipant(p: p, consentStatus: 'implicit_conversation');
              },
            ),
            ListTile(
              leading: const Icon(Icons.verified_outlined),
              title: Text(_consentRu('explicit_allow')),
              subtitle: const Text(
                  'Явно разрешить подстройку отпечатка при новых фразах'),
              onTap: () {
                Navigator.pop(ctx);
                _patchParticipant(p: p, consentStatus: 'explicit_allow');
              },
            ),
            ListTile(
              leading: const Icon(Icons.cancel_outlined),
              title: Text(_consentRu('declined')),
              subtitle: const Text(
                  'Не обновлять отпечаток (идентификация может сохраниться)'),
              onTap: () {
                Navigator.pop(ctx);
                _patchParticipant(p: p, consentStatus: 'declined');
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Инспектор'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loading ? null : _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: SelectableText(_error!, textAlign: TextAlign.center),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (_rel != null) _relationshipCard(_rel!),
                      const SizedBox(height: 16),
                      _participantsSection(),
                      const SizedBox(height: 16),
                      Text('События (последние)',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      ..._events.map(_eventTile),
                    ],
                  ),
                ),
    );
  }

  Widget _relationshipCard(RelationshipSnapshot r) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Отношения (${r.personRef})',
                style: Theme.of(context).textTheme.titleMedium),
            if (r.displayName != null) Text('Имя: ${r.displayName}'),
            Text(
              'trust: ${r.trust.toStringAsFixed(2)}  '
              'attachment: ${r.attachment.toStringAsFixed(2)}  '
              'warmth: ${r.warmth.toStringAsFixed(2)}',
            ),
            Text(
              'bond: ${r.bondType} · affection: ${r.affectionScore.toStringAsFixed(2)} · '
              'intimacy: ${r.emotionalIntimacyScore.toStringAsFixed(2)} · '
              'romantic tension: ${r.romanticTensionScore.toStringAsFixed(2)}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            Text(
              'conflict_mem: ${r.conflictMemoryScore.toStringAsFixed(2)} · '
              'boundary_safety: ${r.boundarySafetyScore.toStringAsFixed(2)}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            if (r.lastInteractionAt != null)
              Text('Последнее взаимодействие: ${r.lastInteractionAt}'),
          ],
        ),
      ),
    );
  }

  Widget _participantsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Голосовые участники',
            style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        if (_participants.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                'Пока нет записей участников. Появятся после голоса или текста в чате.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          )
        else
          ..._participants.map(_participantCard),
      ],
    );
  }

  Widget _participantCard(ParticipantDebugItem p) {
    final algo = p.voiceprintAlgorithm ?? '—';
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        title: Text(p.displayName ?? p.personRef),
        subtitle: Text(
          '${p.personRef} · ${p.participantKind}\n'
          'согласие: ${_consentRu(p.consentStatus)} · confidence: ${p.voiceprintConfidence.toStringAsFixed(2)}\n'
          'алгоритм: $algo · реплик учтено: ${p.turnsSeen}',
          style: const TextStyle(fontSize: 12),
        ),
        isThreeLine: true,
        trailing: p.isAssistantSelf
            ? Tooltip(
                message: 'Системный участник (эхо TTS)',
                child: Icon(Icons.smart_toy_outlined,
                    color: Theme.of(context).colorScheme.secondary),
              )
            : PopupMenuButton<String>(
                onSelected: (value) {
                  switch (value) {
                    case 'rename':
                      _showRenameDialog(p);
                      break;
                    case 'consent':
                      _showConsentSheet(p);
                      break;
                  }
                },
                itemBuilder: (ctx) => [
                  const PopupMenuItem(
                      value: 'rename', child: Text('Переименовать')),
                  const PopupMenuItem(
                      value: 'consent', child: Text('Согласие на отпечаток…')),
                ],
              ),
      ),
    );
  }

  Widget _eventTile(DebugEventItem e) {
    final payload = e.normalizedPayload;
    final preview =
        payload == null || payload.isEmpty ? '' : '\n${payload.toString()}';
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        title: Text('${e.eventType} · ${e.source}'),
        subtitle: Text(
          '${e.timestamp.toIso8601String()}\nid: ${e.id}$preview',
          style: const TextStyle(fontSize: 12),
        ),
        isThreeLine: preview.isNotEmpty,
      ),
    );
  }
}
