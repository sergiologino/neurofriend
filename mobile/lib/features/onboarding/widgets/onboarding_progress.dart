import 'package:flutter/material.dart';

class OnboardingProgress extends StatelessWidget {
  const OnboardingProgress({super.key, required this.step});

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
