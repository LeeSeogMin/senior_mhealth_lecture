import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'samsung_call_detector.dart';
import 'api_service.dart';

/// 단순하고 안정적인 자동 모니터링 서비스
/// SamsungCallDetector의 검증된 로직을 재사용
class SimpleAudioService {
  Timer? _monitoringTimer;
  String? _lastProcessedFile;
  final SamsungCallDetector _detector = SamsungCallDetector();
  final ApiService _apiService = ApiService();
  StreamController<File>? _fileStreamController;

  Stream<File>? get fileStream => _fileStreamController?.stream;

  /// 스트림 초기화 (구독 설정용)
  void initializeStream() {
    if (kDebugMode) {
      debugPrint('📡 SimpleAudioService 스트림 초기화 중...');
    }
    _fileStreamController ??= StreamController<File>.broadcast();
    if (kDebugMode) {
      debugPrint('📡 SimpleAudioService 스트림 초기화 완료');
    }
  }

  /// 자동 모니터링 시작
  Future<void> startMonitoring() async {
    debugPrint('🔄 단순 자동 모니터링 시작');

    try {
      debugPrint('📍 1단계: 스트림 컨트롤러 확인 중...');
      // 스트림 컨트롤러가 없으면 초기화
      _fileStreamController ??= StreamController<File>.broadcast();
      debugPrint('✅ 1단계: 스트림 컨트롤러 확인 완료');

      debugPrint('📍 2단계: 마지막 처리된 파일 로드 중...');
      // 마지막 처리된 파일 로드
      await _loadLastProcessedFile();
      debugPrint('✅ 2단계: 마지막 처리된 파일 로드 완료');

      debugPrint('📍 3단계: 타이머 설정 중...');
      // 30초마다 새 파일 확인
      _monitoringTimer = Timer.periodic(Duration(seconds: 30), (timer) async {
        debugPrint('⏰ 타이머 실행: 새 파일 확인 시작');
        await _checkForNewFileWithTimeout();
        debugPrint('⏰ 타이머 실행: 새 파일 확인 완료');
      });
      debugPrint('✅ 3단계: 타이머 설정 완료');

      debugPrint('📍 4단계: 첫 번째 파일 확인 시작...');
      // 첫 번째 체크 - 타임아웃 적용
      await _checkForNewFileWithTimeout();
      debugPrint('✅ 4단계: 첫 번째 파일 확인 완료');

      debugPrint('✅ 단순 자동 모니터링 시작 완료');
    } catch (e) {
      debugPrint('❌ SimpleAudioService 시작 중 오류: $e');
      rethrow;
    }
  }

  /// 타임아웃이 적용된 새 파일 확인
  Future<void> _checkForNewFileWithTimeout() async {
    try {
      // 10초 타임아웃 적용
      await _checkForNewFile().timeout(Duration(seconds: 10));
    } on TimeoutException {
      debugPrint('⏰ 파일 확인 타임아웃 (10초) - 다음 체크에서 재시도');
    } catch (e) {
      debugPrint('❌ 파일 확인 중 오류: $e');
    }
  }

  /// 시니어 이름 가져오기 (수동 업로드와 동일한 방식 사용)
  Future<String?> _getSeniorName() async {
    // 무조건 출력되어야 하는 로그
    debugPrint('🚨🚨🚨 [SimpleAudioService] _getSeniorName() 메서드 진입!!!');
    debugPrint('🚨🚨🚨 [SimpleAudioService] 빌드 타임스탬프: ${DateTime.now()}');

    try {
      debugPrint('🔍 [SimpleAudioService] ApiService를 통해 시니어 정보 조회 시작...');

      // ApiService 인스턴스 확인
      debugPrint('🔍 [SimpleAudioService] _apiService 인스턴스: $_apiService');
      debugPrint(
          '🔍 [SimpleAudioService] _apiService 타입: ${_apiService.runtimeType}');

      debugPrint(
          '🔍 [SimpleAudioService] _apiService.getCurrentSenior() 호출 중...');
      final currentSenior = await _apiService.getCurrentSenior();
      debugPrint(
        '🔍 [SimpleAudioService] _apiService.getCurrentSenior() 응답: $currentSenior',
      );

      if (currentSenior == null) {
        debugPrint('❌ [SimpleAudioService] 시니어 정보를 찾을 수 없음');
        return null;
      }

      final seniorName = currentSenior['name'] as String?;
      debugPrint('👴 [SimpleAudioService] 추출된 시니어 이름: ${seniorName ?? "null"}');
      return seniorName;
    } catch (e, stackTrace) {
      debugPrint('❌ [SimpleAudioService] 시니어 이름 가져오기 실패: $e');
      debugPrint('❌ [SimpleAudioService] 스택 트레이스: $stackTrace');
      debugPrint('❌ [SimpleAudioService] 예외 타입: ${e.runtimeType}');
      return null;
    }
  }

  /// 새 파일 확인
  Future<void> _checkForNewFile() async {
    try {
      debugPrint('🔍 새 통화 녹음 파일 확인 중...');
      debugPrint('🚨 빌드 버전: v2.0.0 - ${DateTime.now()}'); // 버전 확인용

      // 시니어 이름 가져오기 (필터링에 사용)
      debugPrint('🚨 _getSeniorName() 호출 직전...');
      final seniorName = await _getSeniorName();
      debugPrint('🚨 _getSeniorName() 호출 완료, 결과: ${seniorName ?? "null"}');
      debugPrint('👴 시니어 이름: ${seniorName ?? "알 수 없음"}');

      debugPrint('📞 SamsungCallDetector.findLatestCallRecording() 호출...');
      // 시니어 이름으로 필터링하여 통화 파일 검색
      // 시니어와 관련된 통화만 자동으로 업로드
      final latestFile = await _detector.findLatestCallRecording(
        seniorName: seniorName, // 시니어 이름 필터링 활성화
      );
      debugPrint(
        '📞 SamsungCallDetector.findLatestCallRecording() 응답: ${latestFile?.path ?? "null"}',
      );

      if (latestFile != null) {
        final fileName = latestFile.path.split('/').last;

        // 새 파일인지 확인
        if (_lastProcessedFile != fileName) {
          debugPrint('🆕 새 파일 발견: $fileName');

          // 마지막 처리된 파일 업데이트
          _lastProcessedFile = fileName;
          await _saveLastProcessedFile(fileName);

          // 스트림에 새 파일 추가
          debugPrint('📡 스트림에 파일 추가 중: ${latestFile.path}');
          _fileStreamController?.add(latestFile);
          debugPrint('📡 스트림에 파일 추가 완료');
        } else {
          debugPrint('📄 기존 파일: $fileName (이미 처리됨)');
        }
      } else {
        debugPrint('📂 ${seniorName ?? "시니어"}님의 통화 녹음 파일 없음');
      }
    } catch (e, stackTrace) {
      debugPrint('❌ 파일 확인 중 오류: $e');
      debugPrint('❌ 스택 트레이스: $stackTrace');
      rethrow; // 타임아웃 처리를 위해 다시 던짐
    }
  }

  /// 마지막 처리된 파일 로드
  Future<void> _loadLastProcessedFile() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _lastProcessedFile = prefs.getString('last_processed_file');

      debugPrint('📋 마지막 처리된 파일: ${_lastProcessedFile ?? "없음"}');
    } catch (e) {
      debugPrint('⚠️ 마지막 처리된 파일 로드 실패: $e');
    }
  }

  /// 마지막 처리된 파일 저장
  Future<void> _saveLastProcessedFile(String fileName) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('last_processed_file', fileName);
      await prefs.setString(
        'last_processed_time',
        DateTime.now().toIso8601String(),
      );

      debugPrint('💾 마지막 처리된 파일 저장: $fileName');
    } catch (e) {
      debugPrint('⚠️ 마지막 처리된 파일 저장 실패: $e');
    }
  }

  /// 자동 모니터링 중지
  void stopMonitoring() {
    debugPrint('⏹️ 단순 자동 모니터링 중지');

    _monitoringTimer?.cancel();
    _monitoringTimer = null;

    _fileStreamController?.close();
    _fileStreamController = null;
  }

  /// 리소스 정리
  void dispose() {
    stopMonitoring();
  }
}
