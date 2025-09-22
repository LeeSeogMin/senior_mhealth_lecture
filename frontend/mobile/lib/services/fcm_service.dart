import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'package:logging/logging.dart';
import 'dart:convert';

class FCMService {
  static final FCMService _instance = FCMService._internal();
  factory FCMService() => _instance;
  FCMService._internal();

  final _logger = Logger('FCMService');
  final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  String? _token;
  String? get token => _token;

  Future<void> initialize() async {
    try {
      _logger.info('FCM 초기화 시작...');

      // 알림 권한 요청
      _logger.info('알림 권한 요청 중...');
      NotificationSettings settings = await _messaging.requestPermission(
        alert: true,
        announcement: false,
        badge: true,
        carPlay: false,
        criticalAlert: false,
        provisional: false,
        sound: true,
      );

      _logger.info('알림 권한 상태: ${settings.authorizationStatus}');

      if (settings.authorizationStatus == AuthorizationStatus.authorized) {
        _logger.info('사용자가 알림 권한을 허용했습니다');

        // Local notifications 초기화
        await _initializeLocalNotifications();

        // FCM 토큰 가져오기
        _logger.info('FCM 토큰 요청 중...');
        _token = await _messaging.getToken();

        if (_token != null) {
          _logger.info('FCM 토큰 획득 성공!');
          _logger.info('FCM 토큰 길이: ${_token!.length}');
          _logger.info('FCM 토큰 앞 50자: ${_token!.substring(0, _token!.length > 50 ? 50 : _token!.length)}...');

          // 토큰을 백엔드에 등록
          await _registerTokenToBackend(_token!);
        } else {
          _logger.warning('FCM 토큰이 null입니다!');
        }

        // 토큰 갱신 리스너
        _messaging.onTokenRefresh.listen((String token) {
          _logger.info('토큰이 갱신되었습니다: $token');
          _token = token;
          _registerTokenToBackend(token);
        });

        // 포그라운드 메시지 핸들러
        FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

        // 백그라운드 메시지 핸들러
        FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

        // 알림 탭 핸들러
        FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);

        // 앱이 종료된 상태에서 알림으로 실행된 경우
        RemoteMessage? initialMessage =
            await FirebaseMessaging.instance.getInitialMessage();
        if (initialMessage != null) {
          _handleNotificationTap(initialMessage);
        }
      } else {
        _logger.warning('사용자가 알림 권한을 거부했습니다');
      }
    } catch (e, stackTrace) {
      _logger.severe('FCM 초기화 실패', e, stackTrace);
      rethrow; // 오류를 상위로 전파하여 재시도 가능하게 함
    }
  }

  // FCM 토큰 강제 새로고침
  Future<void> refreshToken() async {
    try {
      _logger.info('FCM 토큰 확인 중...');

      // 먼저 현재 토큰 확인
      _token = await _messaging.getToken();

      if (_token != null) {
        _logger.info('기존 FCM 토큰 사용: ${_token?.substring(0, 20)}...');
        // 기존 토큰을 백엔드에 등록 (중복 방지 로직은 백엔드에서 처리)
        await _registerTokenToBackend(_token!);
      } else {
        // 토큰이 없는 경우에만 새로 생성
        _logger.info('토큰이 없어서 새로 생성');
        _token = await _messaging.getToken();
        if (_token != null) {
          await _registerTokenToBackend(_token!);
        }
      }
    } catch (e, stackTrace) {
      _logger.severe('FCM 토큰 처리 실패', e, stackTrace);
    }
  }

  Future<void> _initializeLocalNotifications() async {
    const AndroidInitializationSettings initializationSettingsAndroid =
        AndroidInitializationSettings('@mipmap/ic_launcher');

    const DarwinInitializationSettings initializationSettingsIOS =
        DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const InitializationSettings initializationSettings =
        InitializationSettings(
      android: initializationSettingsAndroid,
      iOS: initializationSettingsIOS,
    );

    await _localNotifications.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: (NotificationResponse response) {
        _logger.info('로컬 알림 탭: ${response.payload}');
        // 알림 탭 처리
      },
    );
  }

  Future<void> _registerTokenToBackend(String token) async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        _logger.warning('로그인된 사용자가 없습니다');
        return;
      }

      final response = await http.post(
        Uri.parse('https://asia-northeast3-senior-mhealth-472007.cloudfunctions.net/registerFCMToken'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'userId': user.uid,
          'token': token,
          'platform': 'mobile',
          'email': user.email,
        }),
      );

      if (response.statusCode == 200) {
        _logger.info('토큰이 성공적으로 등록되었습니다');
      } else {
        _logger.warning('토큰 등록 실패: ${response.body}');
      }
    } catch (e, stackTrace) {
      _logger.severe('토큰 등록 중 오류', e, stackTrace);
    }
  }

  void _handleForegroundMessage(RemoteMessage message) async {
    _logger.info('포그라운드 메시지 수신: ${message.messageId}');

    // 로컬 알림 표시
    if (message.notification != null) {
      await _showLocalNotification(
        title: message.notification!.title ?? '알림',
        body: message.notification!.body ?? '',
        payload: json.encode(message.data),
      );
    }
  }

  Future<void> _showLocalNotification({
    required String title,
    required String body,
    String? payload,
  }) async {
    const AndroidNotificationDetails androidPlatformChannelSpecifics =
        AndroidNotificationDetails(
      'senior_mhealth_channel',
      'Senior MHealth 알림',
      channelDescription: '음성 분석 완료 및 건강 알림',
      importance: Importance.high,
      priority: Priority.high,
      showWhen: true,
    );

    const DarwinNotificationDetails iOSPlatformChannelSpecifics =
        DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    const NotificationDetails platformChannelSpecifics = NotificationDetails(
      android: androidPlatformChannelSpecifics,
      iOS: iOSPlatformChannelSpecifics,
    );

    await _localNotifications.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title,
      body,
      platformChannelSpecifics,
      payload: payload,
    );
  }

  void _handleNotificationTap(RemoteMessage message) {
    _logger.info('알림 탭: ${message.data}');

    // 분석 결과 화면으로 이동
    if (message.data.containsKey('analysisId')) {
      final analysisId = message.data['analysisId'];
      final seniorId = message.data['seniorId'];
      // TODO: Navigator를 통해 분석 결과 화면으로 이동
      _logger.info('분석 결과 화면으로 이동: analysisId=$analysisId, seniorId=$seniorId');
    }
  }
}

// Top-level function for background message handling
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  Logger('FCMBackground').info('백그라운드 메시지 수신: ${message.messageId}');
}