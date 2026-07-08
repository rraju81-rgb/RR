import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../screens/splash/splash_screen.dart';
import '../../screens/onboarding/onboarding_screen.dart';
import '../../screens/auth/auth_screen.dart';
import '../../screens/home/home_screen.dart';
import '../../screens/trips/trips_screen.dart';
import '../../screens/safety/safety_screen.dart';
import '../../screens/analytics/analytics_screen.dart';
import '../../screens/profile/profile_screen.dart';
import '../../screens/women_safety/women_safety_screen.dart';
import '../../screens/fuel_prices/fuel_prices_screen.dart';
import '../../screens/toll_calculator/toll_calculator_screen.dart';
import '../../screens/rto_docs/rto_docs_screen.dart';
import '../../screens/night_mode/night_mode_screen.dart';
import '../../screens/settings/settings_screen.dart';
import '../../screens/about/about_screen.dart';

class AppRoutes {
  AppRoutes._();

  static const String splash = '/';
  static const String onboarding = '/onboarding';
  static const String auth = '/auth';
  static const String home = '/home';
  static const String trips = '/trips';
  static const String safety = '/safety';
  static const String analytics = '/analytics';
  static const String profile = '/profile';
  static const String womenSafety = '/women-safety';
  static const String fuelPrices = '/fuel-prices';
  static const String tollCalculator = '/toll-calculator';
  static const String rtoDocs = '/rto-docs';
  static const String nightMode = '/night-mode';
  static const String settings = '/settings';
  static const String about = '/about';
}

class AppRouter {
  AppRouter._();

  static final _rootNavigatorKey = GlobalKey<NavigatorState>();
  static final _shellNavigatorKey = GlobalKey<NavigatorState>();

  static final router = GoRouter(
    initialLocation: AppRoutes.splash,
    debugLogDiagnostics: true,
    routes: [
      GoRoute(
        path: AppRoutes.splash,
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: AppRoutes.onboarding,
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: AppRoutes.auth,
        builder: (context, state) => const AuthScreen(),
      ),
      GoRoute(
        path: AppRoutes.home,
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: AppRoutes.trips,
        builder: (context, state) => const TripsScreen(),
      ),
      GoRoute(
        path: AppRoutes.safety,
        builder: (context, state) => const SafetyScreen(),
      ),
      GoRoute(
        path: AppRoutes.analytics,
        builder: (context, state) => const AnalyticsScreen(),
      ),
      GoRoute(
        path: AppRoutes.profile,
        builder: (context, state) => const ProfileScreen(),
      ),
      GoRoute(
        path: AppRoutes.womenSafety,
        builder: (context, state) => const WomenSafetyScreen(),
      ),
      GoRoute(
        path: AppRoutes.fuelPrices,
        builder: (context, state) => const FuelPricesScreen(),
      ),
      GoRoute(
        path: AppRoutes.tollCalculator,
        builder: (context, state) => const TollCalculatorScreen(),
      ),
      GoRoute(
        path: AppRoutes.rtoDocs,
        builder: (context, state) => const RtoDocsScreen(),
      ),
      GoRoute(
        path: AppRoutes.nightMode,
        builder: (context, state) => const NightModeScreen(),
      ),
      GoRoute(
        path: AppRoutes.settings,
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: AppRoutes.about,
        builder: (context, state) => const AboutScreen(),
      ),
    ],
  );
}
