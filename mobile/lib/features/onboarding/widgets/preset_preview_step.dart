import 'package:flutter/material.dart';

import '../../../services/neurofriend_api.dart';
import 'step_card.dart';

class PresetPreviewStep extends StatelessWidget {
  const PresetPreviewStep({super.key, required this.preset});

  final PersonalityPreset? preset;

  @override
  Widget build(BuildContext context) {
    final p = preset;
    if (p == null) {
      return const OnboardingStepCard(
        title: 'Preview',
        child: Text('Выбери пресет на предыдущем шаге.'),
      );
    }
    return OnboardingStepCard(
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
          if (p.biographyPreview != null && p.biographyPreview!.trim().isNotEmpty) ...[
            const SizedBox(height: 12),
            Text('Как это хранится в памяти', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 4),
            Text(p.biographyPreview!, style: Theme.of(context).textTheme.bodyMedium),
          ],
          if (p.expertisePreview != null && p.expertisePreview!.trim().isNotEmpty) ...[
            const SizedBox(height: 12),
            Text('Экспертиза и темы', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 4),
            Text(p.expertisePreview!, style: Theme.of(context).textTheme.bodyMedium),
          ],
          if (p.expertiseProfile != null) ..._presetExpertiseTopics(context, p.expertiseProfile!),
          const SizedBox(height: 12),
          Text('Как будет начинать общение', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 4),
          const Text(
            'Первое сообщение будет сгенерировано из выбранного характера, а не из общего шаблона.',
          ),
        ],
      ),
    );
  }
}

List<Widget> _presetExpertiseTopics(BuildContext context, ExpertisePresetSeed ep) {
  if (ep.coreExpertise.isEmpty && ep.strongFamiliarity.isEmpty && ep.weakOrNeutral.isEmpty) {
    return <Widget>[];
  }
  TextStyle chipStyle = Theme.of(context).textTheme.labelSmall ?? const TextStyle(fontSize: 11);
  Widget row(String title, List<String> topics) {
    if (topics.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 10),
        Text(title, style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 6),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: topics
              .map(
                (t) => Chip(
                  visualDensity: VisualDensity.compact,
                  label: Text(t.replaceAll('_', ' '), style: chipStyle),
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              )
              .toList(),
        ),
      ],
    );
  }

  return <Widget>[
    const SizedBox(height: 12),
    Text('Темы в памяти (из каталога)', style: Theme.of(context).textTheme.titleSmall),
    row('Ядро', ep.coreExpertise),
    row('Хорошо знакомо', ep.strongFamiliarity),
    row('Осторожно / не специалист', ep.weakOrNeutral),
  ];
}
