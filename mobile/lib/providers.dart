import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/api_config.dart';
import 'services/neurofriend_api.dart';

final neuroFriendApiProvider = Provider<NeuroFriendApi>((ref) {
  return NeuroFriendApi(baseUrl: kApiBaseUrl);
});
