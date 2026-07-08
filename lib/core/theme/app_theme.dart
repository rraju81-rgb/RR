import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

/// 6thGear Design System
/// Inspired by India's vibrant energy and automotive culture
class AppColors {
  AppColors._();

  // Primary Palette - Deep Racing Blue
  static const Color primary = Color(0xFF1E3A8A);
  static const Color primaryLight = Color(0xFF3B82F6);
  static const Color primaryDark = Color(0xFF172554);
  static const Color primaryAccent = Color(0xFF60A5FA);

  // Secondary - Saffron Orange (India's identity)
  static const Color secondary = Color(0xFFF97316);
  static const Color secondaryLight = Color(0xFFFDBA74);
  static const Color secondaryDark = Color(0xFFEA580C);

  // Tertiary - Emerald Green (Eco-friendly driving)
  static const Color tertiary = Color(0xFF10B981);
  static const Color tertiaryLight = Color(0xFF6EE7B7);
  static const Color tertiaryDark = Color(0xFF059669);

  // Alert Colors
  static const Color danger = Color(0xFFEF4444);
  static const Color dangerLight = Color(0xFFFCA5A5);
  static const Color warning = Color(0xFFF59E0B);
  static const Color warningLight = Color(0xFFFCD34D);
  static const Color success = Color(0xFF22C55E);
  static const Color info = Color(0xFF3B82F6);

  // Background Colors
  static const Color background = Color(0xFF0A0E21);
  static const Color backgroundLight = Color(0xFF1A1F3C);
  static const Color backgroundCard = Color(0xFF111827);
  static const Color surface = Color(0xFF1E293B);
  static const Color surfaceVariant = Color(0xFF334155);

  // Text Colors
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);
  static const Color textInverse = Color(0xFF0F172A);

  // Gradient Definitions
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primary, primaryLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient secondaryGradient = LinearGradient(
    colors: [secondary, secondaryLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient dangerGradient = LinearGradient(
    colors: [danger, Color(0xFFDC2626)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient darkGradient = LinearGradient(
    colors: [background, backgroundLight],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  static const LinearGradient speedGradient = LinearGradient(
    colors: [tertiary, primary, secondary],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // HUD Colors (Night Mode)
  static const Color hudBackground = Color(0xFF000000);
  static const Color hudPrimary = Color(0xFF00FF88);
  static const Color hudSecondary = Color(0xFF00CCFF);
  static const Color hudWarning = Color(0xFFFF6600);
  static const Color hudDanger = Color(0xFFFF0044);

  // India Theme Accents
  static const Color indiaSaffron = Color(0xFFFF9933);
  static const Color indiaGreen = Color(0xFF138808);
  static const Color indiaWhite = Color(0xFFFFFFFF);
  static const Color indiaBlue = Color(0xFF000080);
}

class AppTypography {
  AppTypography._();

  static TextStyle get displayLarge => GoogleFonts.poppins(
        fontSize: 48,
        fontWeight: FontWeight.w800,
        color: AppColors.textPrimary,
        letterSpacing: -1.5,
        height: 1.1,
      );

  static TextStyle get displayMedium => GoogleFonts.poppins(
        fontSize: 36,
        fontWeight: FontWeight.w700,
        color: AppColors.textPrimary,
        letterSpacing: -1.0,
        height: 1.2,
      );

  static TextStyle get displaySmall => GoogleFonts.poppins(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        color: AppColors.textPrimary,
        letterSpacing: -0.5,
        height: 1.3,
      );

  static TextStyle get headlineLarge => GoogleFonts.poppins(
        fontSize: 24,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
        letterSpacing: -0.5,
        height: 1.3,
      );

  static TextStyle get headlineMedium => GoogleFonts.poppins(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
        letterSpacing: -0.25,
        height: 1.4,
      );

  static TextStyle get headlineSmall => GoogleFonts.poppins(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
        height: 1.4,
      );

  static TextStyle get titleLarge => GoogleFonts.inter(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
        height: 1.4,
      );

  static TextStyle get titleMedium => GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w500,
        color: AppColors.textPrimary,
        height: 1.5,
      );

  static TextStyle get titleSmall => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w500,
        color: AppColors.textSecondary,
        height: 1.5,
      );

  static TextStyle get bodyLarge => GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
        height: 1.6,
      );

  static TextStyle get bodyMedium => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
        height: 1.6,
      );

  static TextStyle get bodySmall => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.textSecondary,
        height: 1.5,
      );

  static TextStyle get labelLarge => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
        letterSpacing: 0.5,
        height: 1.4,
      );

  static TextStyle get labelMedium => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        color: AppColors.textSecondary,
        letterSpacing: 0.5,
        height: 1.4,
      );

  static TextStyle get labelSmall => GoogleFonts.inter(
        fontSize: 10,
        fontWeight: FontWeight.w500,
        color: AppColors.textMuted,
        letterSpacing: 0.5,
        height: 1.4,
      );

  // HUD Typography (Night Mode)
  static TextStyle get hudDisplay => GoogleFonts.poppins(
        fontSize: 72,
        fontWeight: FontWeight.w800,
        color: AppColors.hudPrimary,
        letterSpacing: -2,
        height: 1.0,
      );

  static TextStyle get hudTitle => GoogleFonts.poppins(
        fontSize: 24,
        fontWeight: FontWeight.w700,
        color: AppColors.hudPrimary,
        letterSpacing: 2,
        height: 1.2,
      );

  static TextStyle get hudLabel => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: AppColors.hudSecondary,
        letterSpacing: 3,
        height: 1.4,
      );
}

class AppShadows {
  AppShadows._();

  static List<BoxShadow> get small => [
        BoxShadow(
          color: Colors.black.withOpacity(0.1),
          blurRadius: 4,
          offset: const Offset(0, 2),
        ),
      ];

  static List<BoxShadow> get medium => [
        BoxShadow(
          color: Colors.black.withOpacity(0.15),
          blurRadius: 8,
          offset: const Offset(0, 4),
        ),
      ];

  static List<BoxShadow> get large => [
        BoxShadow(
          color: Colors.black.withOpacity(0.2),
          blurRadius: 16,
          offset: const Offset(0, 8),
        ),
      ];

  static List<BoxShadow> get glowPrimary => [
        BoxShadow(
          color: AppColors.primary.withOpacity(0.3),
          blurRadius: 20,
          spreadRadius: 2,
        ),
      ];

  static List<BoxShadow> get glowDanger => [
        BoxShadow(
          color: AppColors.danger.withOpacity(0.4),
          blurRadius: 24,
          spreadRadius: 4,
        ),
      ];

  static List<BoxShadow> get glowSuccess => [
        BoxShadow(
          color: AppColors.success.withOpacity(0.3),
          blurRadius: 20,
          spreadRadius: 2,
        ),
      ];
}

class AppBorders {
  AppBorders._();

  static BorderRadius get small => BorderRadius.circular(8);
  static BorderRadius get medium => BorderRadius.circular(12);
  static BorderRadius get large => BorderRadius.circular(16);
  static BorderRadius get xl => BorderRadius.circular(24);
  static BorderRadius get full => BorderRadius.circular(999);

  static RoundedRectangleBorder get cardShape => RoundedRectangleBorder(
        borderRadius: medium,
      );

  static RoundedRectangleBorder get buttonShape => RoundedRectangleBorder(
        borderRadius: full,
      );
}

class AppTheme {
  AppTheme._();

  static ThemeData get lightTheme => ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        colorScheme: const ColorScheme.light(
          primary: AppColors.primary,
          secondary: AppColors.secondary,
          surface: Colors.white,
          background: Color(0xFFF8FAFC),
          error: AppColors.danger,
          onPrimary: Colors.white,
          onSecondary: Colors.white,
          onSurface: AppColors.textInverse,
          onBackground: AppColors.textInverse,
          onError: Colors.white,
        ),
        scaffoldBackgroundColor: const Color(0xFFF8FAFC),
        textTheme: TextTheme(
          displayLarge: AppTypography.displayLarge.copyWith(color: AppColors.textInverse),
          displayMedium: AppTypography.displayMedium.copyWith(color: AppColors.textInverse),
          headlineLarge: AppTypography.headlineLarge.copyWith(color: AppColors.textInverse),
          headlineMedium: AppTypography.headlineMedium.copyWith(color: AppColors.textInverse),
          titleLarge: AppTypography.titleLarge.copyWith(color: AppColors.textInverse),
          bodyLarge: AppTypography.bodyLarge.copyWith(color: AppColors.textInverse),
          bodyMedium: AppTypography.bodyMedium.copyWith(color: AppColors.textInverse),
          labelLarge: AppTypography.labelLarge.copyWith(color: AppColors.textInverse),
        ),
        cardTheme: CardTheme(
          elevation: 0,
          shape: AppBorders.cardShape,
          color: Colors.white,
          shadowColor: Colors.black.withOpacity(0.05),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: AppBorders.full),
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            textStyle: AppTypography.labelLarge,
            elevation: 0,
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.primary,
            shape: RoundedRectangleBorder(borderRadius: AppBorders.full),
            side: const BorderSide(color: AppColors.primary, width: 1.5),
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            textStyle: AppTypography.labelLarge,
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: AppBorders.medium,
            borderSide: BorderSide(color: Colors.grey.shade300),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: AppBorders.medium,
            borderSide: BorderSide(color: Colors.grey.sh300),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: AppBorders.medium,
            borderSide: const BorderSide(color: AppColors.primary, width: 2),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: AppBorders.medium,
            borderSide: const BorderSide(color: AppColors.danger),
          ),
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        ),
        appBarTheme: AppBarTheme(
          elevation: 0,
          centerTitle: true,
          backgroundColor: Colors.white,
          foregroundColor: AppColors.textInverse,
          titleTextStyle: AppTypography.headlineSmall.copyWith(color: AppColors.textInverse),
          systemOverlayStyle: SystemUiOverlayStyle.dark,
        ),
        bottomNavigationBarTheme: const BottomNavigationBarThemeData(
          backgroundColor: Colors.white,
          selectedItemColor: AppColors.primary,
          unselectedItemColor: AppColors.textMuted,
          type: BottomNavigationBarType.fixed,
          elevation: 8,
        ),
      );

  static ThemeData get darkTheme => ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: const ColorScheme.dark(
          primary: AppColors.primaryLight,
          secondary: AppColors.secondary,
          surface: AppColors.surface,
          background: AppColors.background,
          error: AppColors.danger,
          onPrimary: Colors.white,
          onSecondary: Colors.white,
          onSurface: AppColors.textPrimary,
          onBackground: AppColors.textPrimary,
          onError: Colors.white,
        ),
        scaffoldBackgroundColor: AppColors.background,
        textTheme: TextTheme(
          displayLarge: AppTypography.displayLarge,
          displayMedium: AppTypography.displayMedium,
          headlineLarge: AppTypography.headlineLarge,
          headlineMedium: AppTypography.headlineMedium,
          titleLarge: AppTypography.titleLarge,
          bodyLarge: AppTypography.bodyLarge,
          bodyMedium: AppTypography.bodyMedium,
          labelLarge: AppTypography.labelLarge,
        ),
        cardTheme: CardTheme(
          elevation: 0,
          shape: AppBorders.cardShape,
          color: AppColors.backgroundCard,
          shadowColor: Colors.black.withOpacity(0.2),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: AppBorders.full),
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            textStyle: AppTypography.labelLarge,
            elevation: 0,
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.primaryLight,
            shape: RoundedRectangleBorder(borderRadius: AppBorders.full),
            side: const BorderSide(color: AppColors.primaryLight, width: 1.5),
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            textStyle: AppTypography.labelLarge,
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: AppColors.surface,
          border: OutlineInputBorder(
            borderRadius: AppBorders.medium,
            borderSide: BorderSide(color: Colors.grey.shade700),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: AppBorders.medium,
            borderSide: BorderSide(color: Colors.grey.shade700),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: AppBorders.medium,
            borderSide: const BorderSide(color: AppColors.primaryLight, width: 2),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: AppBorders.medium,
            borderSide: const BorderSide(color: AppColors.danger),
          ),
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          hintStyle: AppTypography.bodyMedium.copyWith(color: AppColors.textMuted),
        ),
        appBarTheme: AppBarTheme(
          elevation: 0,
          centerTitle: true,
          backgroundColor: AppColors.background,
          foregroundColor: AppColors.textPrimary,
          titleTextStyle: AppTypography.headlineSmall,
          systemOverlayStyle: SystemUiOverlayStyle.light,
        ),
        bottomNavigationBarTheme: const BottomNavigationBarThemeData(
          backgroundColor: AppColors.background,
          selectedItemColor: AppColors.primaryLight,
          unselectedItemColor: AppColors.textMuted,
          type: BottomNavigationBarType.fixed,
          elevation: 8,
        ),
      );
}
