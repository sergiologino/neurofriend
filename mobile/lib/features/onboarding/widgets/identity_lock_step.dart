import 'package:flutter/material.dart';

import '../../../services/neurofriend_api.dart';
import 'step_card.dart';

class IdentityLockStep extends StatelessWidget {
  const IdentityLockStep({
    super.key,
    required this.selected,
    required this.confirmed,
    required this.onChanged,
  });

  final PersonalityPreset? selected;
  final bool confirmed;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return OnboardingStepCard(
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
