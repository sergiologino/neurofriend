import 'package:flutter/material.dart';

import '../../../services/neurofriend_api.dart';
import 'preset_card.dart';
import 'step_card.dart';

class PresetGalleryStep extends StatelessWidget {
  const PresetGalleryStep({
    super.key,
    required this.presets,
    required this.selectedPresetId,
    required this.onSelect,
  });

  final List<PersonalityPreset> presets;
  final String? selectedPresetId;
  final ValueChanged<PersonalityPreset> onSelect;

  @override
  Widget build(BuildContext context) {
    return OnboardingStepCard(
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
              child: PresetCard(
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
