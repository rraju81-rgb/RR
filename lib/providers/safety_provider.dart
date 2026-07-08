import 'package:flutter/foundation.dart';

class EmergencyContact {
  final String id;
  final String name;
  final String phone;
  final String relation;
  final bool isPrimary;

  EmergencyContact({
    required this.id,
    required this.name,
    required this.phone,
    required this.relation,
    this.isPrimary = false,
  });
}

class SafetyProvider extends ChangeNotifier {
  bool _sosActive = false;
  int _sosCountdown = 5;
  bool _liveSharing = false;
  List<EmergencyContact> _contacts = [];
  List<Map<String, dynamic>> _nearbyAlerts = [];

  bool get sosActive => _sosActive;
  int get sosCountdown => _sosCountdown;
  bool get liveSharing => _liveSharing;
  List<EmergencyContact> get contacts => _contacts;
  List<Map<String, dynamic>> get nearbyAlerts => _nearbyAlerts;

  SafetyProvider() {
    _loadDemoData();
  }

  void _loadDemoData() {
    _contacts = [
      EmergencyContact(
        id: '1',
        name: 'Papa',
        phone: '+91 98765 43210',
        relation: 'Father',
        isPrimary: true,
      ),
      EmergencyContact(
        id: '2',
        name: 'Mummy',
        phone: '+91 98765 43211',
        relation: 'Mother',
      ),
      EmergencyContact(
        id: '3',
        name: 'Bhai',
        phone: '+91 98765 43212',
        relation: 'Brother',
      ),
    ];

    _nearbyAlerts = [
      {
        'type': 'speed_camera',
        'distance': 850,
        'location': 'NH48, Khandala Ghat',
        'severity': 'medium',
      },
      {
        'type': 'pothole',
        'distance': 320,
        'location': 'Mumbai-Pune Expressway',
        'severity': 'high',
      },
      {
        'type': 'traffic',
        'distance': 1200,
        'location': 'Lonavala Entry',
        'severity': 'low',
      },
      {
        'type': 'accident',
        'distance': 2100,
        'location': 'Khopoli Toll Plaza',
        'severity': 'high',
      },
    ];
    notifyListeners();
  }

  void triggerSOS() {
    _sosActive = true;
    _sosCountdown = 5;
    notifyListeners();
  }

  void cancelSOS() {
    _sosActive = false;
    _sosCountdown = 5;
    notifyListeners();
  }

  void decrementCountdown() {
    if (_sosCountdown > 0) {
      _sosCountdown--;
      notifyListeners();
    }
  }

  void toggleLiveSharing() {
    _liveSharing = !_liveSharing;
    notifyListeners();
  }

  void addContact(EmergencyContact contact) {
    _contacts.add(contact);
    notifyListeners();
  }

  void removeContact(String id) {
    _contacts.removeWhere((c) => c.id == id);
    notifyListeners();
  }
}
