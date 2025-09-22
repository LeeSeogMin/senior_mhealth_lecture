import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'firebase_options.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/setup_wizard_screen.dart';
import 'services/auth_service.dart';
import 'services/samsung_call_detector.dart';
import 'services/fcm_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 환경변수 로드 (비동기로 처리)
  await dotenv.load(fileName: ".env");
  if (kDebugMode) {
    print('✅ 환경변수 로드 완료');
  }

  // Firebase 초기화 - try-catch로 완전히 감싸기
  try {
    // 먼저 현재 앱 목록 확인
    final apps = Firebase.apps;
    if (kDebugMode) {
      print('🔍 현재 Firebase 앱 개수: ${apps.length}');
      for (var app in apps) {
        print('  - 앱 이름: ${app.name}');
      }
    }

    // 앱이 없을 때만 초기화
    if (apps.isEmpty) {
      await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform,
      );
      if (kDebugMode) {
        print('🔥 Firebase 초기화 완료');
        print('📦 Storage Bucket: ${DefaultFirebaseOptions.currentPlatform.storageBucket}');
      }
    } else {
      if (kDebugMode) {
        print('🔥 Firebase 이미 초기화됨');
      }
    }
  } catch (e) {
    // 중복 초기화 오류 포함 모든 오류 처리
    if (kDebugMode) {
      print('⚠️ Firebase 초기화 처리: $e');
      // 중복 앱 오류면 무시하고 계속 진행
      if (e.toString().contains('duplicate-app')) {
        print('✅ Firebase 이미 초기화되어 있음 - 계속 진행');
      }
    }
  }

  // FCM 서비스 초기화
  try {
    await FCMService().initialize();
    if (kDebugMode) {
      print('📱 FCM 서비스 초기화 완료');
    }
  } catch (e) {
    if (kDebugMode) {
      print('⚠️ FCM 초기화 실패 (나중에 재시도): $e');
    }
  }

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Senior Health Monitor',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      routes: {
        '/home': (context) => const HomeScreen(),
        '/setup': (context) => const SetupWizardScreen(),
        '/login': (context) => const LoginScreen(),
      },
      home: const AuthChecker(),
    );
  }
}

class AuthChecker extends StatefulWidget {
  const AuthChecker({super.key});

  @override
  State<AuthChecker> createState() => _AuthCheckerState();
}

class _AuthCheckerState extends State<AuthChecker> {
  final AuthService _authService = AuthService();
  final SamsungCallDetector _detector = SamsungCallDetector();

  bool _isLoading = true;
  bool _isLoggedIn = false;
  bool _isSetupCompleted = false;
  bool _hasRequiredPermissions = false;

  @override
  void initState() {
    super.initState();
    _checkAppStatus();
  }

  Future<void> _checkAppStatus() async {
    // 로그인 상태 확인
    final loggedIn = _authService.isLoggedIn;

    // 설정 완료 여부 확인 (SharedPreferences)
    final prefs = await SharedPreferences.getInstance();
    var setupCompleted = prefs.getBool('setup_completed') ?? false;

    // **새로 설치된 앱인 경우 모든 통화 파일 기억 데이터 초기화**
    if (!setupCompleted) {
      if (kDebugMode) {
        print('🆕 새로 설치된 앱 - 모든 통화 파일 데이터 초기화');
      }
      await prefs.remove('last_uploaded_file');
      await prefs.remove('last_upload_time');
      await prefs.remove('last_processed_file');
      await prefs.remove('last_processed_time');
      if (kDebugMode) {
        print('🧹 통화 파일 관련 데이터 초기화 완료');
      }
    }

    // **핵심 개선**: 실제 권한 상태 확인
    var hasPermissions = false;
    try {
      hasPermissions = await _detector.requestStoragePermissions();
      if (kDebugMode) {
        print('🔑 실제 권한 상태 확인: $hasPermissions');
      }
    } catch (e) {
      if (kDebugMode) {
        print('❌ 권한 확인 중 오류: $e');
      }
      hasPermissions = false;
    }

    // **권한이 없으면 설정 미완료로 처리**
    if (!hasPermissions && setupCompleted) {
      if (kDebugMode) {
        print('⚠️ 권한이 없어서 온보딩 재실행 필요');
      }
      await prefs.setBool('setup_completed', false);
      setupCompleted = false;

      // 온보딩 재실행 시에도 통화 파일 데이터 초기화
      if (kDebugMode) {
        print('🧹 온보딩 재실행으로 인한 통화 파일 데이터 초기화');
      }
      await prefs.remove('last_uploaded_file');
      await prefs.remove('last_upload_time');
      await prefs.remove('last_processed_file');
      await prefs.remove('last_processed_time');
    }

    if (kDebugMode) {
      print('🔐 로그인 상태: $loggedIn');
      print('⚙️ 설정 완료 상태: $setupCompleted');
      print('🔑 권한 상태: $hasPermissions');

      // 🔧 개발자 전용: 온보딩 재테스트가 필요한 경우에만 활성화
      // .env에 FORCE_ONBOARDING=true 추가하면 온보딩 강제 실행
      final forceOnboarding = dotenv.env['FORCE_ONBOARDING'] == 'true';
      if (forceOnboarding) {
        await prefs.setBool('setup_completed', false);
        setupCompleted = false;
        print('🔄 온보딩 강제 초기화됨 (FORCE_ONBOARDING=true)');

        // 강제 온보딩 시에도 통화 파일 데이터 초기화
        print('🧹 강제 온보딩으로 인한 통화 파일 데이터 초기화');
        await prefs.remove('last_uploaded_file');
        await prefs.remove('last_upload_time');
        await prefs.remove('last_processed_file');
        await prefs.remove('last_processed_time');
      }
    }

    setState(() {
      _isLoggedIn = loggedIn;
      _isSetupCompleted = setupCompleted;
      _hasRequiredPermissions = hasPermissions;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 16),
              Text('앱을 준비하는 중...'),
              SizedBox(height: 8),
              Text('권한 상태를 확인하고 있습니다.',
                  style: TextStyle(fontSize: 12, color: Colors.grey)),
            ],
          ),
        ),
      );
    }

    // 1순위: 앱 기본 설정(권한)이 완료되지 않은 경우 → 온보딩 화면
    if (!_isSetupCompleted || !_hasRequiredPermissions) {
      return const SetupWizardScreen();
    }

    // 2순위: 설정은 완료되었지만 로그인이 안된 경우 → 로그인 화면
    if (!_isLoggedIn) {
      return const LoginScreen();
    }

    // 모든 설정이 완료된 경우 → 홈 화면
    return const HomeScreen();
  }
}
