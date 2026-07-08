import 'package:flutter/foundation.dart';

class Trip {
  final String id;
  final String startLocation;
  final String endLocation;
  final double distance;
  final double duration;
  final double fuelCost;
  final double tollCost;
  final double drivingScore;
  final DateTime date;
  final List<Map<String, dynamic>> routePoints;

  Trip({
    required this.id,
    required this.startLocation,
    required this.endLocation,
    required this.distance,
    required this.duration,
    required this.fuelCost,
    required this.tollCost,
    required this.drivingScore,
    required this.date,
    this.routePoints = const [],
  });
}

class TripProvider extends ChangeNotifier {
  List<Trip> _trips = [];
  Trip? _currentTrip;
  bool _isRecording = false;
  double _currentDistance = 0.0;
  double _currentDuration = 0.0;

  List<Trip> get trips => _trips;
  Trip? get currentTrip => _currentTrip;
  bool get isRecording => _isRecording;
  double get currentDistance => _currentDistance;
  double get currentDuration => _currentDuration;

  TripProvider() {
    _loadDemoTrips();
  }

  void _loadDemoTrips() {
    _trips = [
      Trip(
        id: '1',
        startLocation: 'Mumbai, Maharashtra',
        endLocation: 'Pune, Maharashtra',
        distance: 152.3,
        duration: 2.5,
        fuelCost: 1245.0,
        tollCost: 320.0,
        drivingScore: 87.5,
        date: DateTime.now().subtract(const Duration(days: 1)),
      ),
      Trip(
        id: '2',
        startLocation: 'Bangalore, Karnataka',
        endLocation: 'Mysore, Karnataka',
        distance: 143.8,
        duration: 3.2,
        fuelCost: 1180.0,
        tollCost: 150.0,
        drivingScore: 92.0,
        date: DateTime.now().subtract(const Duration(days: 3)),
      ),
      Trip(
        id: '3',
        startLocation: 'Delhi, NCR',
        endLocation: 'Jaipur, Rajasthan',
        distance: 281.5,
        duration: 4.8,
        fuelCost: 2310.0,
        tollCost: 480.0,
        drivingScore: 78.5,
        date: DateTime.now().subtract(const Duration(days: 5)),
      ),
    ];
    notifyListeners();
  }

  void startTrip(String startLocation) {
    _isRecording = true;
    _currentTrip = Trip(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      startLocation: startLocation,
      endLocation: 'In Progress...',
      distance: 0,
      duration: 0,
      fuelCost: 0,
      tollCost: 0,
      drivingScore: 100,
      date: DateTime.now(),
    );
    _currentDistance = 0;
    _currentDuration = 0;
    notifyListeners();
  }

  void updateTripProgress(double distance, double duration) {
    _currentDistance = distance;
    _currentDuration = duration;
    notifyListeners();
  }

  void endTrip(String endLocation, double fuelCost, double tollCost) {
    if (_currentTrip != null) {
      final completedTrip = Trip(
        id: _currentTrip!.id,
        startLocation: _currentTrip!.startLocation,
        endLocation: endLocation,
        distance: _currentDistance,
        duration: _currentDuration,
        fuelCost: fuelCost,
        tollCost: tollCost,
        drivingScore: 85.0 + (DateTime.now().millisecond % 15),
        date: DateTime.now(),
      );
      _trips.insert(0, completedTrip);
    }
    _isRecording = false;
    _currentTrip = null;
    _currentDistance = 0;
    _currentDuration = 0;
    notifyListeners();
  }

  double get totalDistance => _trips.fold(0, (sum, t) => sum + t.distance);
  double get totalFuelCost => _trips.fold(0, (sum, t) => sum + t.fuelCost);
  double get totalTollCost => _trips.fold(0, (sum, t) => sum + t.tollCost);
  double get averageScore => _trips.isEmpty
      ? 0
      : _trips.fold(0.0, (sum, t) => sum + t.drivingScore) / _trips.length;
}
