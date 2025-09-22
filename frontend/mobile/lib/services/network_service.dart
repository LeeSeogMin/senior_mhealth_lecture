import 'package:connectivity_plus/connectivity_plus.dart';
import 'dart:async';

class NetworkService {
  final Connectivity _connectivity = Connectivity();
  StreamSubscription? _connectivitySubscription;

  Future<bool> isConnected() async {
    final result = await _connectivity.checkConnectivity();
    return result != ConnectivityResult.none;
  }

  Stream<bool> get connectivityStream {
    return _connectivity.onConnectivityChanged
        .map((result) => result != ConnectivityResult.none);
  }

  void startMonitoring(Function(bool) onConnectivityChanged) {
    _connectivitySubscription =
        _connectivity.onConnectivityChanged.listen((result) {
      final isConnected = result != ConnectivityResult.none;
      onConnectivityChanged(isConnected);
    });
  }

  void stopMonitoring() {
    _connectivitySubscription?.cancel();
  }

  Future<bool> isWifiConnected() async {
    final result = await _connectivity.checkConnectivity();
    return result == ConnectivityResult.wifi;
  }

  Future<String> getConnectionType() async {
    final result = await _connectivity.checkConnectivity();
    if (result == ConnectivityResult.wifi) {
      return 'WiFi';
    } else if (result == ConnectivityResult.mobile) {
      return '모바일 데이터';
    } else if (result == ConnectivityResult.ethernet) {
      return '이더넷';
    } else {
      return '연결 없음';
    }
  }
}
