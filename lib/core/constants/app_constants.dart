class AppConstants {
  AppConstants._();

  static const String appName = '6thGear';
  static const String appTagline = 'Bharat ka apna drive companion';
  static const String appVersion = '1.0.0';
  static const String appBuild = '1';

  // API Endpoints
  static const String baseUrl = 'https://api.6thgear.app/v1';
  static const String websocketUrl = 'wss://ws.6thgear.app/v1';

  // Feature Flags
  static const bool enableAnalytics = true;
  static const bool enableCrashlytics = true;
  static const bool enablePushNotifications = true;
  static const bool enableBackgroundLocation = true;
  static const bool enableMLModels = true;

  // Speed Limits (km/h)
  static const double citySpeedLimit = 50;
  static const double highwaySpeedLimit = 100;
  static const double expresswaySpeedLimit = 120;

  // Safety
  static const int sosCountdownSeconds = 5;
  static const int fakeCallDelaySeconds = 10;
  static const double drowsinessThreshold = 0.7;

  // Cache
  static const int cacheMaxAgeHours = 24;
  static const int maxCacheSizeMB = 100;
}
