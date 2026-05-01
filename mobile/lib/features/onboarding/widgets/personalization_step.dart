import 'package:flutter/material.dart';

import 'step_card.dart';

class PersonalizationStep extends StatelessWidget {
  const PersonalizationStep({
    super.key,
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
    return OnboardingStepCard(
      title: 'Сделать своим',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Это не пересоздаёт личность, а слегка сдвигает выбранный характер.', style: Theme.of(context).textTheme.bodySmall),
          OnboardingDeltaSlider(label: 'Мягче ↔ твёрже', value: softnessDelta, onChanged: onSoftnessChanged),
          OnboardingDeltaSlider(label: 'Деликатнее ↔ прямее', value: directnessDelta, onChanged: onDirectnessChanged),
          OnboardingDeltaSlider(label: 'Тише ↔ инициативнее', value: initiativeDelta, onChanged: onInitiativeChanged),
          OnboardingDeltaSlider(label: 'Спокойнее ↔ эмоциональнее', value: emotionalityDelta, onChanged: onEmotionalityChanged),
          OnboardingDeltaSlider(label: 'Серьёзнее ↔ ироничнее', value: humorDelta, onChanged: onHumorChanged),
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

class OnboardingDeltaSlider extends StatelessWidget {
  const OnboardingDeltaSlider({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
  });

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
