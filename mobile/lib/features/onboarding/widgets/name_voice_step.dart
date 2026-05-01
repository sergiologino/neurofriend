import 'package:flutter/material.dart';

import '../../../services/neurofriend_api.dart';
import 'step_card.dart';

class NameAndVoiceStep extends StatelessWidget {
  const NameAndVoiceStep({
    super.key,
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
    final nameWarning = nameGenderWarning(nameController.text, genderStyle);
    return OnboardingStepCard(
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
}

String? nameGenderWarning(String rawName, String? genderStyle) {
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
