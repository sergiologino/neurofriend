import 'package:flutter/material.dart';

import '../../../services/neurofriend_api.dart';

String legendExcerpt(String text, {int maxChars = 160}) {
  final t = text.trim();
  if (t.isEmpty) return '';
  if (t.length <= maxChars) return t;
  return '${t.substring(0, maxChars).trimRight()}…';
}

class PresetCard extends StatelessWidget {
  const PresetCard({
    super.key,
    required this.preset,
    required this.selected,
    required this.onTap,
  });

  final PersonalityPreset preset;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final gender = preset.genderLabelRu;
    final legend = preset.lifeLegend;

    return Semantics(
      button: true,
      selected: selected,
      label: '${preset.title}${gender == null ? '' : ', $gender'}',
      child: ExcludeSemantics(
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(12),
            child: Ink(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: selected ? scheme.primary : scheme.outlineVariant,
                  width: selected ? 2 : 1,
                ),
                color: selected
                    ? scheme.primaryContainer.withValues(alpha: 0.35)
                    : scheme.surfaceContainerHighest.withValues(alpha: 0.45),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      preset.title,
                      style: textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    if (gender != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        gender,
                        style: textTheme.labelMedium?.copyWith(
                          color: scheme.secondary,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                    if (legend != null && legend.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        legendExcerpt(legend),
                        style: textTheme.bodySmall?.copyWith(height: 1.35),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
