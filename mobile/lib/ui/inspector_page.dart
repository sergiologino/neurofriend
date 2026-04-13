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
      if (!mounted) return;
      setState(() {
        _rel = rel;
        _events = events;
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
                      Text('События (последние)', style: Theme.of(context).textTheme.titleMedium),
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
            Text('Отношения (${r.personRef})', style: Theme.of(context).textTheme.titleMedium),
            if (r.displayName != null) Text('Имя: ${r.displayName}'),
            Text('trust: ${r.trust.toStringAsFixed(2)}  '
                'attachment: ${r.attachment.toStringAsFixed(2)}  '
                'warmth: ${r.warmth.toStringAsFixed(2)}'),
            if (r.lastInteractionAt != null)
              Text('Последнее взаимодействие: ${r.lastInteractionAt}'),
          ],
        ),
      ),
    );
  }

  Widget _eventTile(DebugEventItem e) {
    final payload = e.normalizedPayload;
    final preview = payload == null || payload.isEmpty ? '' : '\n${payload.toString()}';
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
