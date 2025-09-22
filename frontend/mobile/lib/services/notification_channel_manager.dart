import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:logging/logging.dart';

/// Android Notification Channel 관리자
/// 백엔드에서 사용하는 모든 채널을 미리 생성
class NotificationChannelManager {
  static final Logger _logger = Logger('NotificationChannelManager');
  static final FlutterLocalNotificationsPlugin _localNotifications = 
      FlutterLocalNotificationsPlugin();

  /// 모든 필요한 Android Notification Channel 생성
  static Future<void> createAllChannels() async {
    try {
      // Android 플랫폼인지 확인
      final android = _localNotifications
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>();
      
      if (android == null) {
        _logger.info('Android 플랫폼이 아니므로 채널 생성 건너뜀');
        return;
      }

      // 1. 분석 완료 채널 (백엔드에서 사용)
      const analysisCompleteChannel = AndroidNotificationChannel(
        'analysis_complete_channel',
        '분석 완료 알림',
        description: 'AI 분석이 완료되었을 때 표시되는 알림',
        importance: Importance.high,
        playSound: true,
        enableVibration: true,
        enableLights: true,
      );
      await android.createNotificationChannel(analysisCompleteChannel);
      _logger.info('분석 완료 채널 생성: analysis_complete_channel');

      // 2. 녹음 채널 (기존 BackgroundService에서 사용)
      const recordingChannel = AndroidNotificationChannel(
        'senior_health_recording',
        '녹음 서비스',
        description: '음성 녹음 중 표시되는 알림',
        importance: Importance.low,
        playSound: false,
        enableVibration: false,
      );
      await android.createNotificationChannel(recordingChannel);
      _logger.info('녹음 서비스 채널 생성: senior_health_recording');

      // 3. 일반 알림 채널
      const defaultChannel = AndroidNotificationChannel(
        'default_channel',
        '일반 알림',
        description: '앱의 일반적인 알림',
        importance: Importance.defaultImportance,
        playSound: true,
        enableVibration: true,
      );
      await android.createNotificationChannel(defaultChannel);
      _logger.info('일반 알림 채널 생성: default_channel');

      // 4. 긴급 알림 채널 (위험 수준 알림용)
      const criticalChannel = AndroidNotificationChannel(
        'critical_channel',
        '긴급 알림',
        description: '즉시 확인이 필요한 중요 알림',
        importance: Importance.max,
        playSound: true,
        enableVibration: true,
        enableLights: true,
      );
      await android.createNotificationChannel(criticalChannel);
      _logger.info('긴급 알림 채널 생성: critical_channel');

      _logger.info('모든 Android Notification Channel 생성 완료');
    } catch (e) {
      _logger.severe('Android Notification Channel 생성 실패: $e');
    }
  }

  /// 로컬 알림 플러그인 초기화
  static Future<void> initialize() async {
    try {
      const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
      const iosSettings = DarwinInitializationSettings(
        requestAlertPermission: true,
        requestBadgePermission: true,
        requestSoundPermission: true,
      );
      
      const initSettings = InitializationSettings(
        android: androidSettings,
        iOS: iosSettings,
      );

      await _localNotifications.initialize(
        initSettings,
        onDidReceiveNotificationResponse: _onNotificationTapped,
      );

      _logger.info('로컬 알림 플러그인 초기화 완료');
      
      // 채널 생성
      await createAllChannels();
    } catch (e) {
      _logger.severe('로컬 알림 초기화 실패: $e');
    }
  }

  /// 알림 탭 처리
  static void _onNotificationTapped(NotificationResponse response) {
    _logger.info('알림 탭됨: ${response.payload}');
    // TODO: 알림 탭 시 앱 내 화면 이동 처리
  }

  /// 포그라운드에서 분석 완료 알림 표시
  static Future<void> showAnalysisCompleteNotification({
    required String title,
    required String body,
    String? payload,
  }) async {
    try {
      const androidDetails = AndroidNotificationDetails(
        'analysis_complete_channel',
        '분석 완료 알림',
        channelDescription: 'AI 분석이 완료되었을 때 표시되는 알림',
        importance: Importance.high,
        priority: Priority.high,
        showWhen: true,
        enableVibration: true,
        playSound: true,
      );

      const iosDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
      );

      const details = NotificationDetails(
        android: androidDetails,
        iOS: iosDetails,
      );

      await _localNotifications.show(
        DateTime.now().millisecondsSinceEpoch ~/ 1000, // ID로 timestamp 사용
        title,
        body,
        details,
        payload: payload,
      );

      _logger.info('로컬 알림 표시 완료: $title');
    } catch (e) {
      _logger.severe('로컬 알림 표시 실패: $e');
    }
  }
}