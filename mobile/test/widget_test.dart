import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:neurofriend_mobile/main.dart';

void main() {
  testWidgets('NeuroFriend app builds', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: NeuroFriendApp()));
    await tester.pump();
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
