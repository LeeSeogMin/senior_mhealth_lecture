import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'dart:io';
import '../services/samsung_call_detector.dart';

class SetupWizardScreen extends StatefulWidget {
  const SetupWizardScreen({super.key});

  @override
  State<SetupWizardScreen> createState() => _SetupWizardScreenState();
}

class _SetupWizardScreenState extends State<SetupWizardScreen>
    with WidgetsBindingObserver {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  // Android 버전 정보
  int? _androidApiLevel;
  bool get _isAndroid11Plus =>
      _androidApiLevel != null && _androidApiLevel! >= 30;

  // 권한 상태
  bool _storagePermissionGranted = false;
  bool _microphonePermissionGranted = false;
  bool _manageStoragePermissionGranted = false;
  bool _samsungRecordingEnabled = false;

  // 모든 기본 권한이 허용되었는지 확인
  bool get _allBasicPermissionsGranted =>
      _storagePermissionGranted && _microphonePermissionGranted;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeSetup();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    if (state == AppLifecycleState.resumed) {
      _checkAllPermissions();
    }
  }

  Future<void> _initializeSetup() async {
    await _detectAndroidVersion();
    await _checkAllPermissions();
  }

  Future<void> _detectAndroidVersion() async {
    if (Platform.isAndroid) {
      try {
        final deviceInfo = DeviceInfoPlugin();
        final androidInfo = await deviceInfo.androidInfo;
        setState(() {
          _androidApiLevel = androidInfo.version.sdkInt;
        });

        if (kDebugMode) {
          print('🔍 Android API Level: $_androidApiLevel');
          print('🔍 Android 11+ 감지: $_isAndroid11Plus');
        }
      } catch (e) {
        if (kDebugMode) {
          print('⚠️ Android 버전 감지 실패: $e');
        }
        // 기본값으로 최신 버전 가정
        setState(() {
          _androidApiLevel = 33;
        });
      }
    }
  }

  Future<void> _checkAllPermissions() async {
    await _checkBasicPermissions();
    await _checkManageStoragePermission();
    await _checkSamsungRecording();
  }

  Future<void> _checkBasicPermissions() async {
    if (_androidApiLevel == null) return;

    try {
      if (_isAndroid11Plus) {
        // Android 11+: manageExternalStorage + microphone
        final manageStorage = await Permission.manageExternalStorage.status;
        final microphone = await Permission.microphone.status;

        setState(() {
          _storagePermissionGranted = manageStorage.isGranted;
          _microphonePermissionGranted = microphone.isGranted;
        });

        if (kDebugMode) {
          print('🔐 Android 11+ 권한 확인:');
          print(
              '  모든파일관리: $_storagePermissionGranted (${manageStorage.name}) - ${manageStorage.toString()}');
          print(
              '  마이크: $_microphonePermissionGranted (${microphone.name}) - ${microphone.toString()}');
          print(
              '  ⚠️ 중요: Android $_androidApiLevel에서 MANAGE_EXTERNAL_STORAGE는 시스템 설정에서만 허용 가능!');
        }
      } else {
        // Android 10 이하: storage + microphone
        final storage = await Permission.storage.status;
        final microphone = await Permission.microphone.status;

        setState(() {
          _storagePermissionGranted = storage.isGranted;
          _microphonePermissionGranted = microphone.isGranted;
        });

        if (kDebugMode) {
          print('🔐 Android 10 이하 권한 확인:');
          print(
              '  저장소: $_storagePermissionGranted (${storage.name}) - ${storage.toString()}');
          print(
              '  마이크: $_microphonePermissionGranted (${microphone.name}) - ${microphone.toString()}');
        }
      }
    } catch (e) {
      if (kDebugMode) {
        print('⚠️ 권한 확인 중 오류: $e');
      }
    }
  }

  Future<void> _requestBasicPermissionsAutomatically() async {
    if (kDebugMode) {
      print('🔐 자동 권한 요청 시작');
    }

    try {
      // 마이크 권한은 모든 Android 버전에서 자동 요청 가능
      if (!_microphonePermissionGranted) {
        final microphoneStatus = await Permission.microphone.request();
        setState(() {
          _microphonePermissionGranted = microphoneStatus.isGranted;
        });

        if (kDebugMode) {
          print('🔐 마이크 권한 요청 결과: ${microphoneStatus.name}');
        }
      }

      // Android 10 이하에서는 저장소 권한도 자동 요청 가능
      if (!_isAndroid11Plus && !_storagePermissionGranted) {
        final storageStatus = await Permission.storage.request();
        setState(() {
          _storagePermissionGranted = storageStatus.isGranted;
        });

        if (kDebugMode) {
          print('🔐 저장소 권한 요청 결과: ${storageStatus.name}');
        }
      }

      // Android 11+에서는 MANAGE_EXTERNAL_STORAGE만 수동 처리
      if (_isAndroid11Plus && !_storagePermissionGranted) {
        if (kDebugMode) {
          print('🔐 Android 11+: 모든 파일 관리 권한은 수동 설정 필요');
        }
      }

      // 권한 요청 후 스낵바 표시
      if (_microphonePermissionGranted &&
          (_storagePermissionGranted || _isAndroid11Plus)) {
        _showSnackBar('✅ 자동 권한 설정이 완료되었습니다');
      }
    } catch (e) {
      if (kDebugMode) {
        print('⚠️ 자동 권한 요청 중 오류: $e');
      }
      _showSnackBar('⚠️ 권한 요청 중 오류가 발생했습니다');
    }
  }

  Future<void> _requestManageStoragePermission() async {
    final status = await Permission.manageExternalStorage.request();
    setState(() {
      _manageStoragePermissionGranted = status.isGranted;
    });

    if (status.isGranted) {
      _showSnackBar('✅ 모든 파일 관리 권한이 허용되었습니다');
    } else {
      _showManageStorageGuide();
    }
  }

  Future<void> _checkManageStoragePermission() async {
    final status = await Permission.manageExternalStorage.status;
    setState(() {
      _manageStoragePermissionGranted = status.isGranted;
    });

    if (kDebugMode) {
      print(
          '🔐 모든 파일 관리 권한 확인: $_manageStoragePermissionGranted (${status.name}) - ${status.toString()}');
      if (_isAndroid11Plus && status.isGranted) {
        print(
            '✅ Android $_androidApiLevel에서 MANAGE_EXTERNAL_STORAGE 권한이 허용되어 있습니다!');
      } else if (_isAndroid11Plus && !status.isGranted) {
        print(
            '❌ Android $_androidApiLevel에서 MANAGE_EXTERNAL_STORAGE 권한이 거부되어 있습니다. 시스템 설정 필요!');
      }
    }
  }

  Future<void> _checkSamsungRecording() async {
    final detector = SamsungCallDetector();
    final folderExists = await detector.checkCallRecordingFolder();
    setState(() {
      _samsungRecordingEnabled = folderExists;
    });
  }

  void _showManageStorageGuide() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            Icon(Icons.folder, color: Colors.orange),
            SizedBox(width: 8),
            Text('모든 파일 관리 권한'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '통화 녹음 파일 접근을 위해 "모든 파일 관리" 권한이 필요합니다:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 16),
            _buildGuideStep('1', '"시스템 설정 열기" 버튼 클릭'),
            _buildGuideStep('2', '"파일 및 미디어" → "모든 파일 관리"'),
            _buildGuideStep('3', '"허용" 선택'),
            _buildGuideStep('4', '뒤로가기로 앱 복귀'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text('취소'),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Navigator.of(context).pop();
              openAppSettings();
            },
            icon: Icon(Icons.settings),
            label: Text('시스템 설정 열기'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.orange,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGuideStep(String number, String description) {
    return Padding(
      padding: EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: Colors.blue,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Center(
              child: Text(
                number,
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              description,
              style: TextStyle(fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        duration: Duration(seconds: 2),
      ),
    );
  }

  Future<void> _completeSetup() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('setup_completed', true);

    if (mounted) {
      Navigator.pushReplacementNamed(context, '/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // 페이지 인디케이터
            if (_androidApiLevel != null) _buildPageIndicator(),

            // 페이지 뷰
            Expanded(
              child: _androidApiLevel == null
                  ? _buildLoadingScreen()
                  : PageView(
                      controller: _pageController,
                      onPageChanged: (index) {
                        setState(() {
                          _currentPage = index;
                        });
                      },
                      children: [
                        _buildWelcomePage(),
                        _buildBasicPermissionsPage(),
                        _buildManageStoragePage(),
                        _buildSamsungRecordingPage(),
                        _buildCompletePage(),
                      ],
                    ),
            ),

            // 네비게이션 버튼
            if (_androidApiLevel != null) _buildNavigationButtons(),
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingScreen() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 24),
          Text('Android 버전을 확인하는 중...'),
        ],
      ),
    );
  }

  Widget _buildPageIndicator() {
    return Container(
      padding: EdgeInsets.symmetric(vertical: 20),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(5, (index) {
          return Container(
            margin: EdgeInsets.symmetric(horizontal: 4),
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: index == _currentPage ? Colors.blue : Colors.grey[300],
            ),
          );
        }),
      ),
    );
  }

  Widget _buildWelcomePage() {
    return SingleChildScrollView(
      padding: EdgeInsets.all(32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(height: 60),
          Icon(
            Icons.phone_callback,
            size: 120,
            color: Colors.blue,
          ),
          SizedBox(height: 40),
          Text(
            '통화분석 앱에 오신 것을 환영합니다',
            style: TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
            ),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 24),
          Text(
            '통화 녹음을 자동으로 분석하여\n건강 상태를 모니터링합니다',
            style: TextStyle(
              fontSize: 18,
              color: Colors.grey[600],
              height: 1.5,
            ),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 40),
          Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.blue[50],
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    Icon(Icons.info, color: Colors.blue),
                    SizedBox(width: 12),
                    Text(
                      'Android $_androidApiLevel 감지됨',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.blue[800],
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 8),
                Text(
                  _isAndroid11Plus
                      ? 'Android 11+ 버전에 최적화된 설정을 제공합니다'
                      : 'Android 10 이하 버전에 최적화된 설정을 제공합니다',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.blue[700],
                  ),
                ),
              ],
            ),
          ),
          SizedBox(height: 40),
          Text(
            '👈 좌우로 스와이프하거나 아래 버튼을 사용하세요',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[500],
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildBasicPermissionsPage() {
    return SingleChildScrollView(
      padding: EdgeInsets.all(24),
      child: Column(
        children: [
          SizedBox(height: 20),

          // 제목
          Text(
            '기본 권한 설정',
            style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),

          SizedBox(height: 16),

          // 설명
          Text(
            _isAndroid11Plus
                ? 'Android $_androidApiLevel: 마이크 권한을 자동으로 요청합니다'
                : 'Android $_androidApiLevel: 마이크 및 저장소 권한을 자동으로 요청합니다',
            style: TextStyle(fontSize: 16, color: Colors.grey[600]),
            textAlign: TextAlign.center,
          ),

          SizedBox(height: 32),

          // 권한 상태 표시
          Container(
            padding: EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.grey[50],
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey[300]!),
            ),
            child: Column(
              children: [
                Text(
                  '현재 권한 상태',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                SizedBox(height: 16),

                // 마이크 권한 상태
                _buildPermissionStatusRow(
                  '🎤 마이크 권한',
                  _microphonePermissionGranted,
                  '통화 녹음 감지에 필요',
                ),

                // Android 10 이하에서만 저장소 권한 표시
                if (!_isAndroid11Plus) ...[
                  SizedBox(height: 12),
                  _buildPermissionStatusRow(
                    '📁 저장소 권한',
                    _storagePermissionGranted,
                    '통화 녹음 파일 읽기에 필요',
                  ),
                ],
              ],
            ),
          ),

          SizedBox(height: 24),

          // 권한 요청 버튼 (상태에 따라 다른 버튼 표시)
          if (_needsPermissionRequest())
            SizedBox(
              width: double.infinity,
              height: 80,
              child: ElevatedButton.icon(
                onPressed: () async {
                  await _requestBasicPermissionsAutomatically();
                  await _checkAllPermissions(); // 상태 업데이트
                },
                icon: Icon(Icons.security, size: 28),
                label: Text(
                  '권한 요청하기',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20),
                  ),
                  elevation: 10,
                ),
              ),
            )
          else
            Container(
              width: double.infinity,
              height: 80,
              decoration: BoxDecoration(
                color: Colors.green[50],
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.green[300]!, width: 2),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.check_circle, color: Colors.green, size: 32),
                  SizedBox(width: 12),
                  Text(
                    '기본 권한 설정 완료',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.green[700],
                    ),
                  ),
                ],
              ),
            ),

          SizedBox(height: 24),

          // 자동 설정 내용 안내
          Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.blue[50],
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.blue[200]!),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.info, color: Colors.blue),
                    SizedBox(width: 8),
                    Text(
                      '자동 설정 내용',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.blue[700],
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 12),
                Text(
                  _isAndroid11Plus
                      ? '• 🎤 마이크 권한: 자동 요청 (시스템 다이얼로그)\n• 📁 파일 접근: 다음 단계에서 수동 설정'
                      : '• 🎤 마이크 권한: 자동 요청 (시스템 다이얼로그)\n• 📁 저장소 권한: 자동 요청 (시스템 다이얼로그)',
                  style: TextStyle(fontSize: 14, color: Colors.blue[700]),
                ),
              ],
            ),
          ),

          // 디버그 모드에서만 표시 (간소화)
          if (kDebugMode) ...[
            SizedBox(height: 24),

            // 디버그 정보 박스만 유지
            Container(
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.grey[400]!),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '🐛 디버그 정보',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 8),
                  Text('Android API: $_androidApiLevel'),
                  Text('Android 11+: $_isAndroid11Plus'),
                  Text('마이크 권한: $_microphonePermissionGranted'),
                  Text('저장소 권한: $_storagePermissionGranted'),
                  Text('권한 요청 필요: ${_needsPermissionRequest()}'),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  // 권한 상태 행 생성 헬퍼 함수
  Widget _buildPermissionStatusRow(
      String title, bool isGranted, String description) {
    return Row(
      children: [
        Icon(
          isGranted ? Icons.check_circle : Icons.cancel,
          color: isGranted ? Colors.green : Colors.red,
          size: 24,
        ),
        SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: isGranted ? Colors.green[700] : Colors.red[700],
                ),
              ),
              Text(
                description,
                style: TextStyle(fontSize: 12, color: Colors.grey[600]),
              ),
            ],
          ),
        ),
        Text(
          isGranted ? '허용됨' : '필요함',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: isGranted ? Colors.green[700] : Colors.red[700],
          ),
        ),
      ],
    );
  }

  // 권한 요청이 필요한지 확인하는 헬퍼 함수
  bool _needsPermissionRequest() {
    if (_isAndroid11Plus) {
      // Android 11+: 마이크 권한만 확인
      return !_microphonePermissionGranted;
    } else {
      // Android 10 이하: 마이크 또는 저장소 권한 확인
      return !_microphonePermissionGranted || !_storagePermissionGranted;
    }
  }

  Widget _buildManageStoragePage() {
    return SingleChildScrollView(
      padding: EdgeInsets.all(32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            _manageStoragePermissionGranted
                ? Icons.check_circle
                : Icons.folder_special,
            size: 100,
            color:
                _manageStoragePermissionGranted ? Colors.green : Colors.orange,
          ),
          SizedBox(height: 30),
          Text(
            '모든 파일 관리 권한',
            style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 20),
          Text(
            _isAndroid11Plus
                ? 'Android 11+에서는 시스템 설정에서\n수동으로 허용해야 하는 특별 권한입니다'
                : '통화 녹음 파일에 접근하기 위해\n추가 권한이 필요합니다',
            style: TextStyle(fontSize: 16, color: Colors.grey[600]),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 40),
          if (!_manageStoragePermissionGranted) ...[
            SizedBox(
              width: double.infinity,
              height: 80,
              child: ElevatedButton.icon(
                onPressed: _requestManageStoragePermission,
                icon: Icon(Icons.folder_special, size: 28),
                label: Text(
                  '모든 파일 관리 권한 설정',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20),
                  ),
                  elevation: 10,
                ),
              ),
            ),
            SizedBox(height: 20),
            Container(
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.orange[50],
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  Row(
                    children: [
                      Icon(Icons.info, color: Colors.orange),
                      SizedBox(width: 8),
                      Text(
                        '수동 설정이 필요한 이유',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Colors.orange[800],
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 12),
                  Text(
                    '• Android 보안 정책으로 앱에서 자동 허용 불가\n'
                    '• 시스템 설정에서 사용자가 직접 허용해야 함\n'
                    '• 버튼을 누르면 상세한 설정 가이드를 제공합니다',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.orange[700],
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ] else ...[
            Container(
              padding: EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.green[100],
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.check_circle, color: Colors.green, size: 32),
                      SizedBox(width: 12),
                      Text(
                        '권한 설정 완료!',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: Colors.green[800],
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 8),
                  Text(
                    '모든 파일 관리 권한이 허용되었습니다',
                    style: TextStyle(fontSize: 16, color: Colors.green[700]),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSamsungRecordingPage() {
    return SingleChildScrollView(
      padding: EdgeInsets.all(32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            _samsungRecordingEnabled
                ? Icons.check_circle
                : Icons.phone_callback,
            size: 100,
            color: _samsungRecordingEnabled ? Colors.green : Colors.blue,
          ),
          SizedBox(height: 30),
          Text(
            '통화 녹음 설정',
            style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 20),
          Text(
            _samsungRecordingEnabled
                ? '통화 녹음이 이미 활성화되어 있습니다'
                : '통화 녹음 설정은 나중에도 할 수 있습니다',
            style: TextStyle(fontSize: 16, color: Colors.grey[600]),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 40),
          if (!_samsungRecordingEnabled) ...[
            Container(
              padding: EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.blue[50],
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  Row(
                    children: [
                      Icon(Icons.info, color: Colors.blue),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          '통화 녹음을 위한 추가 설정',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Colors.blue[800],
                          ),
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 12),
                  Text(
                    '• 전화 앱에서 통화 녹음 기능 활성화\n'
                    '• 녹음된 파일이 지정된 폴더에 저장되는지 확인\n'
                    '• 이 설정은 선택사항이며 나중에 할 수 있습니다',
                    style: TextStyle(fontSize: 14, color: Colors.blue[700]),
                  ),
                ],
              ),
            ),
            SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: _checkSamsungRecording,
              icon: Icon(Icons.refresh),
              label: Text('상태 다시 확인'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.blue,
                side: BorderSide(color: Colors.blue),
                padding: EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              ),
            ),
          ] else ...[
            Container(
              padding: EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.green[100],
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.check_circle, color: Colors.green, size: 32),
                      SizedBox(width: 12),
                      Text(
                        '통화 녹음 준비 완료!',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: Colors.green[800],
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 8),
                  Text(
                    '통화 녹음 파일을 자동으로 분석할 준비가 되었습니다',
                    style: TextStyle(fontSize: 16, color: Colors.green[700]),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCompletePage() {
    final allReady =
        _allBasicPermissionsGranted && _manageStoragePermissionGranted;

    return SingleChildScrollView(
      padding: EdgeInsets.all(32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            allReady ? Icons.celebration : Icons.settings,
            size: 120,
            color: allReady ? Colors.green : Colors.orange,
          ),
          SizedBox(height: 40),
          Text(
            allReady ? '설정 완료!' : '설정 거의 완료',
            style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 24),
          Text(
            allReady
                ? '모든 필수 설정이 완료되었습니다.\n이제 앱을 사용할 준비가 되었습니다!'
                : '몇 가지 권한이 아직 허용되지 않았습니다.\n이전 단계로 돌아가서 권한을 허용해주세요.',
            style: TextStyle(
              fontSize: 18,
              color: Colors.grey[600],
              height: 1.5,
            ),
            textAlign: TextAlign.center,
          ),
          SizedBox(height: 40),

          // 설정 상태 요약
          _buildStatusSummary(),

          SizedBox(height: 40),

          if (allReady) ...[
            SizedBox(
              width: double.infinity,
              height: 80,
              child: ElevatedButton.icon(
                onPressed: _completeSetup,
                icon: Icon(Icons.login, size: 28),
                label: Text(
                  '로그인하러 가기',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20),
                  ),
                  elevation: 10,
                ),
              ),
            ),
          ] else ...[
            Text(
              '⚠️ 모든 필수 권한을 허용한 후 다음 단계로 진행할 수 있습니다.',
              style: TextStyle(
                fontSize: 16,
                color: Colors.orange[700],
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatusSummary() {
    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey[300]!),
      ),
      child: Column(
        children: [
          Text(
            '설정 상태',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 16),
          _buildStatusItem(
            '저장소 권한',
            _storagePermissionGranted,
            _isAndroid11Plus ? '모든 파일 관리' : '저장소 접근',
          ),
          _buildStatusItem('마이크 권한', _microphonePermissionGranted, '마이크 접근'),
          _buildStatusItem(
              '모든 파일 관리', _manageStoragePermissionGranted, '특별 권한'),
          _buildStatusItem('통화 녹음', _samsungRecordingEnabled, '선택사항',
              isOptional: true),
        ],
      ),
    );
  }

  Widget _buildStatusItem(String title, bool isGranted, String subtitle,
      {bool isOptional = false}) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Icon(
            isGranted
                ? Icons.check_circle
                : (isOptional ? Icons.help_outline : Icons.cancel),
            color: isGranted
                ? Colors.green
                : (isOptional ? Colors.orange : Colors.red),
            size: 24,
          ),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: isGranted ? Colors.green[800] : Colors.black87,
                  ),
                ),
                Text(
                  subtitle,
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                ),
              ],
            ),
          ),
          if (!isGranted && !isOptional)
            Text(
              '필수',
              style: TextStyle(
                fontSize: 12,
                color: Colors.red,
                fontWeight: FontWeight.bold,
              ),
            ),
          if (isOptional)
            Text(
              '선택',
              style: TextStyle(
                fontSize: 12,
                color: Colors.orange,
                fontWeight: FontWeight.bold,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildNavigationButtons() {
    final allReady =
        _allBasicPermissionsGranted && _manageStoragePermissionGranted;

    return Container(
      padding: EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 10,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // 이전 버튼
          SizedBox(
            width: 120,
            height: 60,
            child: _currentPage > 0
                ? OutlinedButton.icon(
                    onPressed: () {
                      _pageController.previousPage(
                        duration: Duration(milliseconds: 300),
                        curve: Curves.easeInOut,
                      );
                    },
                    icon: Icon(Icons.arrow_back),
                    label: Text('이전'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.blue,
                      side: BorderSide(color: Colors.blue),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(15),
                      ),
                    ),
                  )
                : SizedBox(),
          ),

          // 다음 버튼
          SizedBox(
            width: 120,
            height: 60,
            child: _currentPage < 4
                ? ElevatedButton.icon(
                    onPressed: () {
                      _pageController.nextPage(
                        duration: Duration(milliseconds: 300),
                        curve: Curves.easeInOut,
                      );
                    },
                    icon: Icon(Icons.arrow_forward),
                    label: Text('다음'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(15),
                      ),
                      elevation: 5,
                    ),
                  )
                : (allReady
                    ? ElevatedButton.icon(
                        onPressed: _completeSetup,
                        icon: Icon(Icons.login),
                        label: Text('완료'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.green,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(15),
                          ),
                          elevation: 5,
                        ),
                      )
                    : OutlinedButton.icon(
                        onPressed: null,
                        icon: Icon(Icons.block),
                        label: Text('대기중'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.grey,
                          side: BorderSide(color: Colors.grey),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(15),
                          ),
                        ),
                      )),
          ),
        ],
      ),
    );
  }
}
