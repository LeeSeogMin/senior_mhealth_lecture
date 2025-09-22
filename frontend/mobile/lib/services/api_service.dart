import 'dart:io';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:path/path.dart';
import 'log_service.dart';
import './auth_service.dart';
import './cache_service.dart';

class ApiService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseStorage _storage = FirebaseStorage.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final AuthService _authService = AuthService();
  final CacheService _cacheService = CacheService();
  // Using custom LogService for logging

  // Backend API 엔드포인트 (Cloud Run)
  String get _functionsBaseUrl {
    final url = dotenv.env['API_BASE_URL'] ??
        'https://senior-mhealth-api-1054806937473.asia-northeast3.run.app';
    LogService.info('ApiService', '🌐 API URL: $url');
    return url;
  }

  /// 사용자 등록 (Firebase Auth 후 백엔드에 프로필 생성)
  Future<bool> registerUser({
    required String email,
    required String name,
    required String phone,
    String? fcmToken,
  }) async {
    try {
      LogService.info('ApiService', '👤 사용자 등록 시작...');

      final user = _auth.currentUser;
      if (user == null) {
        throw Exception('Firebase Auth 로그인이 필요합니다');
      }

      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('인증 토큰을 가져올 수 없습니다');
      }

      final registerUrl = '$_functionsBaseUrl/api/v1/users/register';
      final requestBody = {
        'email': email,
        'name': name,
        'phone': phone,
        'role': 'caregiver',
        'fcm_token': fcmToken,
        'device_type': 'mobile',
      };

      final response = await http.post(
        Uri.parse(registerUrl),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
        body: jsonEncode(requestBody),
      );

      LogService.info('ApiService', '📡 사용자 등록 응답: ${response.statusCode}');

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body);
        LogService.info('ApiService', '✅ 사용자 등록 성공');
        return true;
      } else {
        LogService.warning('ApiService', '❌ 사용자 등록 실패: ${response.body}');
        return false;
      }
    } catch (e) {
      LogService.warning('ApiService', '❌ 사용자 등록 오류: $e');
      return false;
    }
  }

  /// 사용자 프로필 조회
  Future<Map<String, dynamic>?> getUserProfile() async {
    try {
      LogService.info('ApiService', '👤 사용자 프로필 조회 중...');

      final user = _auth.currentUser;
      if (user == null) {
        throw Exception('로그인이 필요합니다');
      }

      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('인증 토큰을 가져올 수 없습니다');
      }

      final profileUrl = '$_functionsBaseUrl/api/v1/users/profile';
      final response = await http.get(
        Uri.parse(profileUrl),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
      );

      LogService.info('ApiService', '📡 프로필 조회 응답: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['data'] != null) {
          LogService.info('ApiService', '✅ 프로필 조회 성공');
          return data['data'];
        }
      }

      return null;
    } catch (e) {
      LogService.warning('ApiService', '❌ 프로필 조회 실패: $e');
      return null;
    }
  }

  /// Backend에서 Senior 등록 또는 기존 Senior 조회
  Future<String?> getOrCreateSenior() async {
    try {
      LogService.info('ApiService', '👴 Senior ID 확인 중...');

      final user = _auth.currentUser;
      if (user == null) {
        throw Exception('로그인이 필요합니다');
      }

      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('인증 토큰을 가져올 수 없습니다');
      }

      // 1. 먼저 기존 Senior 목록 조회
      final getSeniorsUrl = '$_functionsBaseUrl/api/v1/users/${user.uid}/seniors';
      final getSeniorsResponse = await http.get(
        Uri.parse(getSeniorsUrl),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
      );

      LogService.info(
          'ApiService', '📡 기존 Senior 목록 조회: ${getSeniorsResponse.statusCode}');

      if (getSeniorsResponse.statusCode == 200) {
        final getSeniorsData = jsonDecode(getSeniorsResponse.body);
        if (getSeniorsData['success'] == true &&
            getSeniorsData['data'] != null &&
            getSeniorsData['data']['seniors'] != null &&
            getSeniorsData['data']['seniors'].isNotEmpty) {
          final existingSenior = getSeniorsData['data']['seniors'][0];
          // senior_id 또는 seniorId 둘 다 처리
          final seniorId = existingSenior['senior_id'] ?? existingSenior['seniorId'];
          LogService.info('ApiService', '✅ 기존 Senior 발견: $seniorId');
          return seniorId;
        }
      }

      // 2. 기존 Senior가 없으면 null 반환 (사용자가 직접 생성하도록)
      LogService.info('ApiService', '⚠️ Senior가 없음 - 사용자가 직접 생성해야 함');
      return null;
    } catch (e) {
      LogService.warning('ApiService', '❌ Senior ID 획득 실패: $e');
      return null;
    }
  }

  /// 오디오 파일을 Firebase Storage에 업로드하고 AI 분석 요청
  Future<String> uploadAndAnalyzeAudio(File audioFile) async {
    try {
      LogService.info('ApiService', '📼 오디오 업로드 및 AI 분석 시작');

      // 1. 사용자 인증 확인
      final user = _auth.currentUser;
      if (user == null) {
        throw Exception('로그인이 필요합니다');
      }

      // 2. 파일 정보 준비
      final fileSize = await audioFile.length();
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final fileName =
          'call_${DateTime.now().toString().substring(0, 19).replaceAll(RegExp(r'[:\s-]'), '')}.m4a';

      // Backend API를 통해 Senior ID 획득
      final seniorId = await getOrCreateSenior();
      if (seniorId == null) {
        throw Exception('시니어 정보가 없습니다. 먼저 시니어를 등록해주세요.');
      }
      final callId = 'call_$timestamp';

      LogService.info(
          'ApiService', '💾 파일 정보: ${audioFile.path}, ${fileSize}B');
      LogService.info(
          'ApiService', '📡 스토리지 경로: calls/${user.uid}/$seniorId/$callId/$fileName');
      LogService.info('ApiService', '📞 통화 ID: $callId');
      LogService.info('ApiService', '📁 파일명: $fileName');

      // 3. Firebase Storage에 업로드
      await _uploadToStorage(audioFile, user.uid, seniorId, callId, fileName);

      // 4. Firestore에 통화 기록 저장
      await _saveToFirestore(callId, user.uid, seniorId, fileName, fileSize);

      // 5. Storage 트리거 방식으로 변경 - HTTP API 호출 제거
      // Firebase Storage 업로드가 완료되면 자동으로 processAudioFile 트리거가 실행됨
      LogService.info('ApiService', '✅ Storage 업로드 완료 - 자동 분석 대기 중...');
      LogService.info('ApiService', '🎉 === 업로드 프로세스 완료 ===');

      return '''
📁 파일 업로드 완료

📁 파일명: $fileName
📞 통화 ID: $callId
🔄 상태: 업로드 완료, AI 분석 대기 중

⏳ AI 분석이 시작됩니다.
완료되면 알림으로 결과를 확인할 수 있습니다.
      ''';
    } catch (e) {
      LogService.warning('ApiService', '❌ 업로드/분석 오류: $e');
      rethrow;
    }
  }

  /// 분석 상태를 실시간으로 모니터링하는 메서드
  Stream<Map<String, dynamic>> monitorAnalysisStatus(String callId) {
    try {
      LogService.info('ApiService', '👀 분석 상태 모니터링 시작: $callId');

      return _firestore
          .collection('calls')
          .doc(callId)
          .snapshots()
          .map((snapshot) {
        final data = snapshot.data() ?? {};
        LogService.info('ApiService',
            '📊 분석 상태 업데이트: ${data['analysisStatus'] ?? 'unknown'}');
        return data;
      });
    } catch (e) {
      LogService.warning('ApiService', '❌ 분석 상태 모니터링 오류: $e');
      // 빈 스트림 반환
      return Stream.value(<String, dynamic>{});
    }
  }

  /// Firebase Storage에 파일 업로드
  Future<void> _uploadToStorage(File file, String userId, String seniorId,
      String callId, String fileName) async {
    try {
      LogService.info('ApiService', '📤 Firebase Storage 업로드 시작...');

      // 새로운 경로 구조: calls/{userId}/{seniorId}/{callId}/fileName
      final storageRef =
          _storage.ref().child('calls/$userId/$seniorId/$callId/$fileName');

      // 메타데이터 설정
      final metadata = SettableMetadata(
        contentType: 'audio/m4a',
        customMetadata: {
          'userId': userId,
          'seniorId': seniorId,
          'callId': callId,
          'uploadedAt': DateTime.now().toIso8601String(),
        },
      );

      LogService.info('ApiService',
          '📡 업로드 메타데이터: userId=$userId, seniorId=$seniorId, callId=$callId, fileName=$fileName');

      // 업로드 실행
      final uploadTask = storageRef.putFile(file, metadata);

      // 업로드 진행률 모니터링
      uploadTask.snapshotEvents.listen((TaskSnapshot snapshot) {
        final progress = snapshot.bytesTransferred / snapshot.totalBytes;
        LogService.info(
            'ApiService', '업로드 진행률: ${(progress * 100).toStringAsFixed(1)}%');
      });

      await uploadTask;
      LogService.info('ApiService', '✅ Firebase Storage 업로드 완료');
    } catch (e) {
      LogService.warning('ApiService', '❌ Storage 업로드 오류: $e');
      throw Exception('Firebase Storage 업로드 실패: $e');
    }
  }

  /// Firestore에 통화 기록 저장
  Future<void> _saveToFirestore(String callId, String userId, String seniorId,
      String fileName, int fileSize) async {
    try {
      LogService.info('ApiService', '📝 Firestore 통화 문서 생성 시작...');

      await _firestore
          .collection('users')
          .doc(userId)
          .collection('calls')
          .doc(callId)
          .set({
        'callId': callId,
        'caregiverId': userId, // 🔧 백엔드 호환용
        'userId': userId, // 🔧 기존 호환성 유지
        'seniorId': seniorId,
        'fileName': fileName,
        'filePath': 'calls/$userId/$callId/$fileName',
        'fileSize': fileSize,
        'status': 'uploaded',
        'analysisStatus': 'pending',
        'createdAt': FieldValue.serverTimestamp(),
        'updatedAt': FieldValue.serverTimestamp(),
      });

      LogService.info('ApiService', '✅ Firestore 통화 문서 생성 완료');
    } catch (e) {
      LogService.warning('ApiService', '❌ Firestore 저장 오류: $e');
      throw Exception('Firestore 저장 실패: $e');
    }
  }

  /// Backend API를 통한 음성 분석 요청
  Future<String> requestVoiceAnalysis(
      File audioFile, String seniorId) async {
    try {
      LogService.info('ApiService', '🎤 음성 분석 API 요청 시작...');

      final user = _auth.currentUser;
      if (user == null) {
        throw Exception('로그인이 필요합니다');
      }

      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('인증 토큰을 가져올 수 없습니다');
      }

      // 음성 분석 엔드포인트
      final analysisUrl = '$_functionsBaseUrl/api/v1/analysis/voice';

      // 멀티파트 요청 생성
      var request = http.MultipartRequest('POST', Uri.parse(analysisUrl));
      request.headers['Authorization'] = 'Bearer $idToken';

      // 파일 추가
      var stream = http.ByteStream(audioFile.openRead());
      var length = await audioFile.length();
      var multipartFile = http.MultipartFile(
        'audio_file',
        stream,
        length,
        filename: basename(audioFile.path),
      );
      request.files.add(multipartFile);

      // 시니어 ID 추가
      request.fields['senior_id'] = seniorId;

      LogService.info('ApiService', '📡 분석 요청 URL: $analysisUrl');
      LogService.info('ApiService', '📁 파일 크기: $length bytes');

      // 요청 전송
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      LogService.info('ApiService', '📡 분석 응답 상태: ${response.statusCode}');
      LogService.info('ApiService', '📡 분석 응답: ${response.body}');

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        if (responseData['success'] == true) {
          final analysisId = responseData['data']['analysis_id'];
          LogService.info('ApiService', '✅ 분석 요청 성공: $analysisId');
          return analysisId;
        } else {
          throw Exception('분석 요청 실패: ${responseData['error']}');
        }
      } else {
        throw Exception('서버 오류 (${response.statusCode}): ${response.body}');
      }
    } catch (e) {
      LogService.warning('ApiService', '❌ 음성 분석 요청 오류: $e');
      throw Exception('음성 분석 요청 실패: $e');
    }
  }

  /// 분석 결과 조회 (캐시 활용)
  Future<Map<String, dynamic>?> getAnalysisResult(String analysisId) async {
    try {
      LogService.info('ApiService', '📊 분석 결과 조회 중: $analysisId');

      // 1. 캐시에서 먼저 확인
      final cachedResult = await _cacheService.getCachedAnalysis(analysisId);
      if (cachedResult != null) {
        LogService.info('ApiService', '📦 캐시에서 분석 결과 반환');
        return cachedResult;
      }

      // 2. API에서 조회
      final user = _auth.currentUser;
      if (user == null) {
        throw Exception('로그인이 필요합니다');
      }

      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('인증 토큰을 가져올 수 없습니다');
      }

      final resultUrl = '$_functionsBaseUrl/api/v1/analyses/$analysisId';
      final response = await http.get(
        Uri.parse(resultUrl),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
      );

      LogService.info('ApiService', '📡 결과 조회 응답: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['data'] != null) {
          LogService.info('ApiService', '✅ 분석 결과 조회 성공');

          // 3. 캐시에 저장
          await _cacheService.cacheAnalysisResult(analysisId, data['data']);

          return data['data'];
        }
      }

      LogService.warning('ApiService', '❌ 분석 결과를 찾을 수 없습니다');
      return null;
    } catch (e) {
      LogService.warning('ApiService', '❌ 분석 결과 조회 오류: $e');
      return null;
    }
  }

  /// Firebase Functions에 AI 분석 요청 (레거시 - Storage 트리거 방식)
  // ignore: unused_element
  Future<String> _requestAnalysisLegacy(
      String callId, String userId, String seniorId, String fileName) async {
    try {
      LogService.info('ApiService', '👴 통화 기록 분석 중...');

      // ID 토큰 가져오기
      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('인증 토큰을 가져올 수 없습니다');
      }

      // 🔍 토큰 디버깅 정보
      final user = _auth.currentUser;
      LogService.info('ApiService', '🔑 === 인증 토큰 디버깅 ===');
      LogService.info('ApiService', '🔑 현재 사용자 UID: ${user?.uid}');
      LogService.info('ApiService', '🔑 사용자 이메일: ${user?.email}');
      LogService.info('ApiService', '🔑 토큰 존재: ${idToken.isNotEmpty}');
      LogService.info('ApiService', '🔑 토큰 길이: ${idToken.length}');
      if (idToken.length > 50) {
        LogService.info(
            'ApiService', '🔑 토큰 앞부분: ${idToken.substring(0, 50)}...');
        LogService.info('ApiService',
            '🔑 토큰 뒷부분: ...${idToken.substring(idToken.length - 30)}');
      }

      // HTTP 요청 준비
      final requestUrl = '$_functionsBaseUrl/api/v1/analyses/process-call';
      final requestBody = {
        'callId': callId,
        'userId': userId,
        'seniorId': seniorId,
        'fileName': fileName,
        'filePath': 'calls/$userId/$seniorId/$callId/$fileName',
        'clientType': 'mobile',
      };

      LogService.info('ApiService', '📡 요청 URL: $requestUrl');
      LogService.info('ApiService', '📦 요청 데이터: ${jsonEncode(requestBody)}');

      // HTTP 요청 실행
      final response = await http.post(
        Uri.parse(requestUrl),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
        body: jsonEncode(requestBody),
      );

      LogService.info('ApiService', '📡 응답 상태 코드: ${response.statusCode}');
      LogService.info('ApiService', '📡 응답 헤더: ${response.headers}');
      LogService.info('ApiService', '📡 응답 본문: ${response.body}');

      // 응답 처리
      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        if (responseData['success'] == true) {
          LogService.info('ApiService', '✅ 분석 요청 완료');
          return responseData['data']['message'] ?? '분석이 시작되었습니다';
        } else {
          throw Exception('분석 요청 실패: ${responseData['error']}');
        }
      } else if (response.statusCode == 401) {
        throw Exception('인증 오류 (401): 토큰이 유효하지 않습니다\n응답: ${response.body}');
      } else if (response.statusCode == 404) {
        throw Exception(
            '엔드포인트를 찾을 수 없음 (404): $_functionsBaseUrl/api/v1/analyses/process-call');
      } else {
        throw Exception('서버 오류 (${response.statusCode}): ${response.body}');
      }
    } catch (e) {
      LogService.warning('ApiService', '❌ 분석 요청 오류: $e');
      throw Exception('AI 분석 요청 실패: $e');
    }
  }

  /// 통합된 음성 업로드 및 분석 (Backend API 사용)
  Future<String> uploadAndAnalyzeViaAPI(File audioFile) async {
    try {
      LogService.info('ApiService', '🎯 통합 API 업로드/분석 시작');

      // 1. Senior ID 획득
      final seniorId = await getOrCreateSenior();
      if (seniorId == null) {
        throw Exception('시니어 정보가 없습니다. 먼저 시니어를 등록해주세요.');
      }
      LogService.info('ApiService', '👴 Senior ID: $seniorId');

      // 2. Backend API로 직접 분석 요청
      final analysisId = await requestVoiceAnalysis(audioFile, seniorId);
      LogService.info('ApiService', '📊 분석 ID: $analysisId');

      // 3. 분석 결과 폴링 (옵션)
      // 필요시 분석 완료까지 대기하고 결과 반환
      // final result = await pollAnalysisResult(analysisId);

      return '''
📁 파일 업로드 및 분석 시작됨

📊 분석 ID: $analysisId
👴 시니어 ID: $seniorId
🔄 상태: 분석 진행 중

⏳ AI 분석이 진행 중입니다.
완료되면 알림으로 결과를 확인할 수 있습니다.
      ''';
    } catch (e) {
      LogService.warning('ApiService', '❌ 통합 API 업로드/분석 오류: $e');
      throw Exception('통합 API 업로드/분석 실패: $e');
    }
  }

  /// 분석 결과 폴링 (분석 완료까지 대기)
  Future<Map<String, dynamic>?> pollAnalysisResult(String analysisId, {int maxAttempts = 30}) async {
    for (int i = 0; i < maxAttempts; i++) {
      final result = await getAnalysisResult(analysisId);
      if (result != null && result['status'] == 'completed') {
        return result;
      }

      // 3초 대기 후 재시도
      await Future.delayed(Duration(seconds: 3));
    }
    return null;
  }

  /// 수동 업로드/분석 (레거시 - Storage 트리거 방식)
  Future<String> manualUploadAndAnalyze(File audioFile) async {
    try {
      LogService.info('ApiService', '🎯 수동 업로드/분석 시작 (레거시)');
      final result = await uploadAndAnalyzeAudio(audioFile);
      LogService.info('ApiService', '🎯 수동 업로드/분석 완료: $result');
      return result;
    } catch (e) {
      LogService.warning('ApiService', '❌ 수동 업로드/분석 오류: $e');
      throw Exception('수동 업로드/분석 실패: $e');
    }
  }

  /// 시니어 정보 수정
  Future<bool> updateSenior(String seniorId, Map<String, dynamic> data) async {
    try {
      LogService.info('ApiService', '👴 시니어 정보 수정 중: $seniorId');

      final user = _auth.currentUser;
      if (user == null) {
        throw Exception('로그인이 필요합니다');
      }

      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('인증 토큰을 가져올 수 없습니다');
      }

      final response = await http.put(
        Uri.parse('$_functionsBaseUrl/api/v1/users/${user.uid}/seniors/$seniorId'),
        headers: {
          'Authorization': 'Bearer $idToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode(data),
      );

      LogService.info('ApiService', '📡 시니어 수정 응답: ${response.statusCode}');

      if (response.statusCode == 200) {
        LogService.info('ApiService', '✅ 시니어 정보 수정 성공');
        return true;
      }

      LogService.warning('ApiService', '❌ 시니어 정보 수정 실패: ${response.body}');
      return false;
    } catch (e) {
      LogService.error('ApiService', '시니어 정보 수정 오류: $e');
      return false;
    }
  }

  /// 시니어 삭제
  Future<bool> deleteSenior(String seniorId) async {
    try {
      LogService.info('ApiService', '🗑️ 시니어 삭제 중: $seniorId');

      final user = _auth.currentUser;
      if (user == null) {
        throw Exception('로그인이 필요합니다');
      }

      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('인증 토큰을 가져올 수 없습니다');
      }

      final response = await http.delete(
        Uri.parse('$_functionsBaseUrl/api/v1/users/${user.uid}/seniors/$seniorId'),
        headers: {
          'Authorization': 'Bearer $idToken',
        },
      );

      LogService.info('ApiService', '📡 시니어 삭제 응답: ${response.statusCode}');

      if (response.statusCode == 200) {
        LogService.info('ApiService', '✅ 시니어 삭제 성공');
        return true;
      }

      LogService.warning('ApiService', '❌ 시니어 삭제 실패: ${response.body}');
      return false;
    } catch (e) {
      LogService.error('ApiService', '시니어 삭제 오류: $e');
      return false;
    }
  }

  /// 분석 해석 생성
  Future<Map<String, dynamic>?> generateAnalysisInterpretation(
      String callId, String seniorId) async {
    try {
      LogService.info('ApiService', '🧠 분석 해석 생성 중: $callId');

      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('인증 토큰을 가져올 수 없습니다');
      }

      final response = await http.post(
        Uri.parse('$_functionsBaseUrl/api/v1/analyses/$callId/interpretation/$seniorId'),
        headers: {
          'Authorization': 'Bearer $idToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({}),
      );

      LogService.info('ApiService', '📡 해석 생성 응답: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['data'] != null) {
          LogService.info('ApiService', '✅ 분석 해석 생성 성공');
          return data['data'];
        }
      }

      LogService.warning('ApiService', '❌ 분석 해석 생성 실패: ${response.body}');
      return null;
    } catch (e) {
      LogService.error('ApiService', '분석 해석 생성 오류: $e');
      return null;
    }
  }

  /// 분석 해석 조회
  Future<Map<String, dynamic>?> getAnalysisInterpretation(String callId) async {
    try {
      LogService.info('ApiService', '🔍 분석 해석 조회 중: $callId');

      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('인증 토큰을 가져올 수 없습니다');
      }

      final response = await http.get(
        Uri.parse('$_functionsBaseUrl/api/v1/analyses/$callId/interpretation'),
        headers: {
          'Authorization': 'Bearer $idToken',
        },
      );

      LogService.info('ApiService', '📡 해석 조회 응답: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['data'] != null) {
          LogService.info('ApiService', '✅ 분석 해석 조회 성공');
          return data['data'];
        }
      }

      LogService.warning('ApiService', '❌ 분석 해석을 찾을 수 없습니다');
      return null;
    } catch (e) {
      LogService.error('ApiService', '분석 해석 조회 오류: $e');
      return null;
    }
  }

  /// 공개 분석 결과 조회 (인증 없음)
  Future<Map<String, dynamic>?> getPublicAnalysis(String callId) async {
    try {
      LogService.info('ApiService', '🌐 공개 분석 결과 조회 중: $callId');

      // 인증 없이 직접 요청
      final response = await http.get(
        Uri.parse('$_functionsBaseUrl/api/v1/calls/public/analysis/$callId'),
      );

      LogService.info('ApiService', '📡 공개 분석 조회 응답: ${response.statusCode}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['data'] != null) {
          LogService.info('ApiService', '✅ 공개 분석 결과 조회 성공');
          return data['data'];
        }
      }

      LogService.warning('ApiService', '❌ 공개 분석 결과를 찾을 수 없습니다');
      return null;
    } catch (e) {
      LogService.error('ApiService', '공개 분석 결과 조회 오류: $e');
      return null;
    }
  }

  /// 현재 사용자의 시니어 정보 조회
  Future<Map<String, dynamic>?> getCurrentSenior() async {
    try {
      final user = _auth.currentUser;
      if (user == null) {
        throw Exception('로그인이 필요합니다');
      }

      LogService.info('ApiService', '=== 시니어 정보 조회 시작 ===');
      LogService.info('ApiService', '🔑 현재 사용자 UID: ${user.uid}');
      LogService.info('ApiService', '📧 현재 사용자 이메일: ${user.email}');

      final idToken = await _authService.getIdToken();
      if (idToken == null) {
        throw Exception('인증 토큰을 가져올 수 없습니다');
      }

      // 올바른 엔드포인트: /api/v1/users/{user_id}/seniors
      final getSeniorsUrl = '$_functionsBaseUrl/api/v1/users/${user.uid}/seniors';
      LogService.info('ApiService', '📡 API 호출 URL: $getSeniorsUrl');
      LogService.info('ApiService', '🔐 토큰 앞 20자: ${idToken.substring(0, 20)}...');

      final response = await http.get(
        Uri.parse(getSeniorsUrl),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $idToken',
        },
      );

      LogService.info('ApiService', '📡 응답 상태 코드: ${response.statusCode}');
      LogService.info('ApiService', '📡 응답 본문: ${response.body}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        LogService.info('ApiService', '📡 파싱된 데이터: $data');

        if (data['success'] == true &&
            data['data'] != null &&
            data['data']['seniors'] != null &&
            data['data']['seniors'].isNotEmpty) {
          final senior = data['data']['seniors'][0];
          LogService.info('ApiService', '✅ 시니어 정보 조회 성공: ${senior['name']}');
          LogService.info('ApiService', '✅ 시니어 ID: ${senior['senior_id']}');
          return senior;
        } else {
          LogService.warning('ApiService', '⚠️ seniors 배열이 비어있거나 null입니다');
          LogService.warning('ApiService', '⚠️ data.seniors: ${data['data']?['seniors']}');
        }
      } else {
        LogService.warning('ApiService', '❌ API 오류 응답: ${response.statusCode}');
      }

      LogService.warning('ApiService', '❌ 시니어 정보를 찾을 수 없습니다');
      LogService.warning('ApiService', '응답 전체: ${response.body}');

      // 시니어가 없으면 생성 시도
      final seniorId = await getOrCreateSenior();
      if (seniorId != null) {
        // 생성 후 다시 조회
        final retryResponse = await http.get(
          Uri.parse(getSeniorsUrl),
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $idToken',
          },
        );

        if (retryResponse.statusCode == 200) {
          final retryData = jsonDecode(retryResponse.body);
          if (retryData['success'] == true &&
              retryData['data'] != null &&
              retryData['data']['seniors'] != null &&
              retryData['data']['seniors'].isNotEmpty) {
            return retryData['data']['seniors'][0];
          }
        }
      }

      return null;
    } catch (e) {
      LogService.error('ApiService', '시니어 정보 조회 오류: $e');
      return null;
    }
  }
}
