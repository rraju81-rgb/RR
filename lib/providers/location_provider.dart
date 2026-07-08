import 'package:flutter/foundation.dart';

class LocationProvider extends ChangeNotifier {
  double _latitude = 0.0;
  double _longitude = 0.0;
  double _speed = 0.0;
  double _heading = 0.0;
  double _altitude = 0.0;
  String _address = 'Locating...';
  bool _isTracking = false;
  bool _hasPermission = false;

  double get latitude => _latitude;
  double get longitude => _longitude;
  double get speed => _speed;
  double get speedKmh => _speed * 3.6;
  double get heading => _heading;
  double get altitude => _altitude;
  String get address => _address;
  bool get isTracking => _isTracking;
  bool get hasPermission => _hasPermission;

  void updateLocation({
    required double lat,
    required double lng,
    double speed = 0.0,
    double heading = 0.0,
    double altitude = 0.0,
    String address = '',
  }) {
    _latitude = lat;
    _longitude = lng;
    _speed = speed;
    _heading = heading;
    _altitude = altitude;
    _address = address.isEmpty ? _address : address;
    notifyListeners();
  }

  void setTracking(bool tracking) {
    _isTracking = tracking;
    notifyListeners();
  }

  void setPermission(bool granted) {
    _hasPermission = granted;
    notifyListeners();
  }

  void simulateSpeed(double kmh) {
    _speed = kmh / 3.6;
    notifyListeners();
  }
}
