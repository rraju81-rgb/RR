import 'package:flutter/foundation.dart';

class AuthProvider extends ChangeNotifier {
  bool _isAuthenticated = false;
  bool _isLoading = false;
  String? _userName;
  String? _userEmail;
  String? _userPhone;
  String? _userAvatar;

  bool get isAuthenticated => _isAuthenticated;
  bool get isLoading => _isLoading;
  String? get userName => _userName;
  String? get userEmail => _userEmail;
  String? get userPhone => _userPhone;
  String? get userAvatar => _userAvatar;

  Future<void> signInWithPhone(String phone) async {
    _isLoading = true;
    notifyListeners();

    // Simulate API call
    await Future.delayed(const Duration(seconds: 2));

    _isAuthenticated = true;
    _userPhone = phone;
    _userName = 'Rider';
    _isLoading = false;
    notifyListeners();
  }

  Future<void> signOut() async {
    _isLoading = true;
    notifyListeners();

    await Future.delayed(const Duration(milliseconds: 500));

    _isAuthenticated = false;
    _userName = null;
    _userEmail = null;
    _userPhone = null;
    _userAvatar = null;
    _isLoading = false;
    notifyListeners();
  }

  void updateProfile({String? name, String? email, String? avatar}) {
    _userName = name ?? _userName;
    _userEmail = email ?? _userEmail;
    _userAvatar = avatar ?? _userAvatar;
    notifyListeners();
  }
}
