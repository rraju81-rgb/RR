import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

class SettingsProvider extends ChangeNotifier {
  bool _darkMode = true;
  bool _notifications = true;
  bool _locationTracking = true;
  bool _crashReporting = true;
  bool _analytics = true;
  String _language = 'en';
  String _distanceUnit = 'km';
  String _fuelUnit = 'L';
  String _currency = '₹';

  bool get darkMode => _darkMode;
  bool get notifications => _notifications;
  bool get locationTracking => _locationTracking;
  bool get crashReporting => _crashReporting;
  bool get analytics => _analytics;
  String get language => _language;
  String get distanceUnit => _distanceUnit;
  String get fuelUnit => _fuelUnit;
  String get currency => _currency;

  ThemeMode get themeMode => _darkMode ? ThemeMode.dark : ThemeMode.light;

  void toggleDarkMode() {
    _darkMode = !_darkMode;
    notifyListeners();
  }

  void toggleNotifications() {
    _notifications = !_notifications;
    notifyListeners();
  }

  void toggleLocationTracking() {
    _locationTracking = !_locationTracking;
    notifyListeners();
  }

  void setLanguage(String lang) {
    _language = lang;
    notifyListeners();
  }

  void setDistanceUnit(String unit) {
    _distanceUnit = unit;
    notifyListeners();
  }

  void setCurrency(String currency) {
    _currency = currency;
    notifyListeners();
  }
}
