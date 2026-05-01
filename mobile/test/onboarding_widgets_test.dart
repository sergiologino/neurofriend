import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:neurofriend_mobile/features/onboarding/onboarding.dart';
import 'package:neurofriend_mobile/services/neurofriend_api.dart';

void main() {
  testWidgets('OnboardingProgress shows label for step', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: OnboardingProgress(step: 2))),
    );
    expect(find.text('Preview'), findsOneWidget);
  });

  testWidgets('PresetPreviewStep shows biography and expertise preview sections', (tester) async {
    final preset = PersonalityPreset(
      id: 't',
      title: 'Test',
      archetype: 'companion',
      description: 'Desc',
      suggestedName: 'N',
      lifeLegend: 'Legend line',
      biographyPreview: 'Bio prev',
      expertisePreview: 'Exp prev',
    );
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: PresetPreviewStep(preset: preset),
          ),
        ),
      ),
    );
    expect(find.text('Опорная биография'), findsOneWidget);
    expect(find.text('Legend line'), findsOneWidget);
    expect(find.text('Как это хранится в памяти'), findsOneWidget);
    expect(find.text('Bio prev'), findsOneWidget);
    expect(find.text('Экспертиза и темы'), findsOneWidget);
    expect(find.text('Exp prev'), findsOneWidget);
  });

  testWidgets('WelcomeStep invokes onStart', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: WelcomeStep(onStart: () => tapped = true),
        ),
      ),
    );
    await tester.tap(find.text('Выбрать личность'));
    expect(tapped, isTrue);
  });
}
