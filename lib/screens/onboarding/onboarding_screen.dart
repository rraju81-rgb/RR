import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:smooth_page_indicator/smooth_page_indicator.dart';

import '../../core/theme/app_theme.dart';
import '../../core/router/app_router.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  final List<Map<String, dynamic>> _pages = [
    {
      'icon': Icons.explore,
      'title': 'Smart Navigation',
      'description': 'Real-time traffic, speed cameras, potholes & accident alerts. Navigate India like a pro.',
      'color': AppColors.primary,
    },
    {
      'icon': Icons.shield,
      'title': 'Safety First',
      'description': 'One-tap SOS, fake call, live location sharing & women safety features. Drive with confidence.',
      'color': AppColors.danger,
    },
    {
      'icon': Icons.analytics,
      'title': 'Drive Analytics',
      'description': 'Track your driving score, fuel efficiency, trip history & get personalized tips.',
      'color': AppColors.tertiary,
    },
    {
      'icon': Icons.local_gas_station,
      'title': 'Fuel & Tolls',
      'description': 'Live fuel prices across India, toll calculator with FASTag support & route optimization.',
      'color': AppColors.secondary,
    },
    {
      'icon': Icons.nights_stay,
      'title': 'Night Mode HUD',
      'description': 'Heads-up display for night driving. Speed, drowsiness alerts & animal crossing warnings.',
      'color': AppColors.hudPrimary,
    },
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _onNext() {
    if (_currentPage < _pages.length - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOut,
      );
    } else {
      context.go(AppRoutes.auth);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            // Skip Button
            Align(
              alignment: Alignment.topRight,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: TextButton(
                  onPressed: () => context.go(AppRoutes.auth),
                  child: Text(
                    'Skip',
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.textMuted,
                    ),
                  ),
                ),
              ),
            ),
            // Page View
            Expanded(
              child: PageView.builder(
                controller: _pageController,
                onPageChanged: (index) {
                  setState(() => _currentPage = index);
                },
                itemCount: _pages.length,
                itemBuilder: (context, index) {
                  return _buildPage(_pages[index]);
                },
              ),
            ),
            // Page Indicator
            SmoothPageIndicator(
              controller: _pageController,
              count: _pages.length,
              effect: ExpandingDotsEffect(
                activeDotColor: AppColors.primaryLight,
                dotColor: AppColors.surfaceVariant,
                dotHeight: 8,
                dotWidth: 8,
                expansionFactor: 4,
                spacing: 8,
              ),
            ),
            const SizedBox(height: 32),
            // Next / Get Started Button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
              child: SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _onNext,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    elevation: 0,
                  ),
                  child: Text(
                    _currentPage == _pages.length - 1 ? 'Get Started' : 'Next',
                    style: AppTypography.labelLarge.copyWith(
                      fontSize: 16,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPage(Map<String, dynamic> page) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Icon Container
          Container(
            width: 160,
            height: 160,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  page['color'].withOpacity(0.2),
                  page['color'].withOpacity(0.05),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(40),
              border: Border.all(
                color: page['color'].withOpacity(0.3),
                width: 2,
              ),
            ),
            child: Icon(
              page['icon'],
              size: 72,
              color: page['color'],
            ),
          ),
          const SizedBox(height: 48),
          // Title
          Text(
            page['title'],
            style: AppTypography.displaySmall.copyWith(
              color: AppColors.textPrimary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          // Description
          Text(
            page['description'],
            style: AppTypography.bodyLarge.copyWith(
              color: AppColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
