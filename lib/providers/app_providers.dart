import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import '../providers/location_provider.dart';
import '../providers/trip_provider.dart';
import '../providers/safety_provider.dart';
import '../providers/settings_provider.dart';

class AppProviders {
  AppProviders._();

  static List<ChangeNotifierProvider> get providers => [
    ChangeNotifierProvider(create: (_) => AuthProvider()),
    ChangeNotifierProvider(create: (_) => LocationProvider()),
    ChangeNotifierProvider(create: (_) => TripProvider()),
    ChangeNotifierProvider(create: (_) => SafetyProvider()),
    ChangeNotifierProvider(create: (_) => SettingsProvider()),
  ];
}
