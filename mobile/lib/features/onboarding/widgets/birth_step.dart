import 'package:flutter/material.dart';

import '../../../services/neurofriend_api.dart';
import 'step_card.dart';

class BirthStep extends StatelessWidget {
  const BirthStep({super.key, required this.selected, required this.busy});

  final PersonalityPreset? selected;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    return OnboardingStepCard(
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
