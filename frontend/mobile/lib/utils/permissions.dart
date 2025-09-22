import 'package:permission_handler/permission_handler.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/foundation.dart';
import 'dart:io';

class PermissionManager {
  // 필요한 권한 목록
  static final List<Permission> requiredPermissions = [
    Permission.storage,
    Permission.manageExternalStorage, // Android 11+
    Permission.notification,
    Permission.ignoreBatteryOptimizations,
  ];
  
  // 권한 요청
  static Future<bool> requestAllPermissions() async {
    Map<Permission, PermissionStatus> statuses = 
      await requiredPermissions.request();
    
    // 모든 권한이 허용되었는지 확인
    bool allGranted = true;
    statuses.forEach((permission, status) {
      if (status != PermissionStatus.granted) {
        allGranted = false;
        if (kDebugMode) {
          print('❌ 권한 거부됨: $permission');
        }
      }
    });
    
    return allGranted;
  }
  
  // 저장소 권한 확인 (Android 버전별 처리)
  static Future<bool> checkStoragePermission() async {
    if (Platform.isAndroid) {
      final androidInfo = await DeviceInfoPlugin().androidInfo;
      
      if (androidInfo.version.sdkInt >= 33) {
        // Android 13+
        return await Permission.manageExternalStorage.isGranted;
      } else if (androidInfo.version.sdkInt >= 30) {
        // Android 11+
        return await Permission.manageExternalStorage.isGranted;
      } else {
        // Android 10 이하
        return await Permission.storage.isGranted;
      }
    }
    
    return true; // iOS는 별도 처리
  }
  
  // 배터리 최적화 제외 요청
  static Future<void> requestBatteryOptimizationExemption() async {
    if (await Permission.ignoreBatteryOptimizations.isDenied) {
      // 설정 화면으로 이동
      await openAppSettings();
    }
  }
}