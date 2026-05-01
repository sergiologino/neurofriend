import 'package:flutter/material.dart';

import 'step_card.dart';

class WelcomeStep extends StatelessWidget {
  const WelcomeStep({super.key, required this.onStart});

  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    return OnboardingStepCard(
      title: 'Создай нейродруга, который будет рядом',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Ты выбираешь не набор параметров и не чат-бота. У нейродруга будет свой характер, память, голос и постепенно появляющаяся история рядом с тобой.',
          ),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onStart, child: const Text('Выбрать личность')),
        ],
      ),
    );
  }
}
