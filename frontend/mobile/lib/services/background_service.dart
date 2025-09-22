import 'package:flutter_background/flutter_background.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter/foundation.dart';

class BackgroundService {
  static const String notificationChannelId = 'senior_health_recording';
  static const String notificationChannelName = '통화 녹음 모니터링';

  final FlutterLocalNotificationsPlugin _notifications =
      FlutterLocalNotificationsPlugin();

  bool _isRunning = false;

  // 백그라운드 서비스 초기화
  Future<bool> initialize() async {
    // Android 설정
    const androidConfig = FlutterBackgroundAndroidConfig(
      notificationTitle: "시니어 헬스케어",
      notificationText: "통화 녹음 폴더를 모니터링 중입니다",
      notificationImportance: AndroidNotificationImportance.normal,
      notificationIcon: AndroidResource(
        name: 'ic_notification',
        defType: 'drawable',
      ),
    );

    // 백그라운드 실행 권한 요청
    bool hasPermissions = await FlutterBackground.hasPermissions;
    if (!hasPermissions) {
      hasPermissions = await FlutterBackground.initialize(
        androidConfig: androidConfig,
      );
    }

    // 알림 초기화
    await _initializeNotifications();

    return hasPermissions;
  }

  // 알림 설정
  Future<void> _initializeNotifications() async {
    const androidSettings = AndroidInitializationSettings('app_icon');
    const iosSettings = DarwinInitializationSettings();

    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _notifications.initialize(initSettings);

    // Android 알림 채널 생성
    const androidChannel = AndroidNotificationChannel(
      notificationChannelId,
      notificationChannelName,
      description: '통화 녹음 파일 감지 알림',
      importance: Importance.high,
    );

    await _notifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(androidChannel);
  }

  // 백그라운드 모드 시작
  Future<bool> startBackground() async {
    if (_isRunning) return true;

    try {
      final success = await FlutterBackground.enableBackgroundExecution();
      _isRunning = success;

      if (success) {
        if (kDebugMode) {
          print('✅ 백그라운드 서비스 시작됨');
        }
        _showPersistentNotification();
      }

      return success;
    } catch (e) {
      if (kDebugMode) {
        print('❌ 백그라운드 서비스 시작 실패: $e');
      }
      return false;
    }
  }

  // 백그라운드 모드 중지
  Future<void> stopBackground() async {
    if (!_isRunning) return;

    try {
      await FlutterBackground.disableBackgroundExecution();
      _isRunning = false;
      await _cancelNotification();
      if (kDebugMode) {
        print('✅ 백그라운드 서비스 중지됨');
      }
    } catch (e) {
      if (kDebugMode) {
        print('❌ 백그라운드 서비스 중지 실패: $e');
      }
    }
  }

  // 지속적인 알림 표시
  void _showPersistentNotification() async {
    const androidDetails = AndroidNotificationDetails(
      notificationChannelId,
      notificationChannelName,
      channelDescription: '통화 녹음 파일 감지 알림',
      importance: Importance.low,
      priority: Priority.low,
      ongoing: true, // 스와이프로 제거 불가
      showWhen: false,
    );

    const notificationDetails = NotificationDetails(
      android: androidDetails,
    );

    await _notifications.show(
      0,
      '시니어 헬스케어 실행 중',
      '통화 녹음 폴더를 모니터링하고 있습니다',
      notificationDetails,
    );
  }

  // 파일 감지 알림
  Future<void> showFileDetectedNotification(String fileName) async {
    const androidDetails = AndroidNotificationDetails(
      notificationChannelId,
      notificationChannelName,
      importance: Importance.high,
      priority: Priority.high,
    );

    const notificationDetails = NotificationDetails(
      android: androidDetails,
    );

    await _notifications.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      '새 녹음 파일 감지',
      '파일명: $fileName',
      notificationDetails,
    );
  }

  // 알림 취소
  Future<void> _cancelNotification() async {
    await _notifications.cancel(0);
  }

  bool get isRunning => _isRunning;
}
