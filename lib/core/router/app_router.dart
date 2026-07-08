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
    navigatorKey: _rootNavigatorKey,
    initialLocation: AppRoutes.splash,
    debugLogDiagnostics: true,
    routes: [
      // Splash Screen
      GoRoute(
        path: AppRoutes.splash,
        builder: (context, state) => const SplashScreen(),
      ),

      // Onboarding
      GoRoute(
        path: AppRoutes.onboarding,
        builder: (context, state) => const OnboardingScreen(),
      ),

      // Auth
      GoRoute(
        path: AppRoutes.auth,
        builder: (context, state) => const AuthScreen(),
      ),

      // Main App Shell with Bottom Navigation
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) {
          return MainShell(navigationShell: navigationShell);
        },
        branches: [
          // Home Branch
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.home,
                builder: (context, state) => const HomeScreen(),
              ),
            ],
          ),
          // Trips Branch
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.trips,
                builder: (context, state) => const TripsScreen(),
              ),
            ],
          ),
          // Safety Branch
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.safety,
                builder: (context, state) => const SafetyScreen(),
              ),
            ],
          ),
          // Analytics Branch
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.analytics,
                builder: (context, state) => const AnalyticsScreen(),
              ),
            ],
          ),
          // Profile Branch
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.profile,
                builder: (context, state) => const ProfileScreen(),
              ),
            ],
          ),
        ],
      ),

      // Feature Screens (outside shell)
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

class MainShell extends StatelessWidget {
  final StatefulNavigationShell navigationShell;

  const MainShell({
    super.key,
    required this.navigationShell,
  });

  void _onTap(BuildContext context, int index) {
    navigationShell.goBranch(
      index,
      initialLocation: index == navigationShell.currentIndex,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.background,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 10,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildNavItem(Icons.explore_outlined, Icons.explore, 'Home', 0),
                _buildNavItem(Icons.route_outlined, Icons.route, 'Trips', 1),
                _buildNavItem(Icons.shield_outlined, Icons.shield, 'Safety', 2),
                _buildNavItem(Icons.analytics_outlined, Icons.analytics, 'Stats', 3),
                _buildNavItem(Icons.person_outline, Icons.person, 'Profile', 4),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem(IconData icon, IconData activeIcon, String label, int index) {
    final isSelected = navigationShell.currentIndex == index;
    return GestureDetector(
      onTap: () => _onTap(navigationShell.context, index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF1E3A8A).withOpacity(0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isSelected ? activeIcon : icon,
              color: isSelected ? const Color(0xFF3B82F6) : const Color(0xFF64748B),
              size: 24,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                color: isSelected ? const Color(0xFF3B82F6) : const Color(0xFF64748B),
                fontSize: 10,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
