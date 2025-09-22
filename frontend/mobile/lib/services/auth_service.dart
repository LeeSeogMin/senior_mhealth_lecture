import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'log_service.dart';
import 'messaging_service.dart';
import 'fcm_service.dart';

class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  // Using custom LogService for logging

  static const String _userKey = 'user_data';

  // 현재 사용자 가져오기
  User? get currentUser => _auth.currentUser;

  // 로그인 상태 확인
  bool get isLoggedIn => _auth.currentUser != null;

  // 사용자 스트림 (실시간 인증 상태 변경 감지)
  Stream<User?> get userStream => _auth.authStateChanges();

  // 회원가입
  Future<UserCredential?> signUp({
    required String email,
    required String password,
    required String name,
    required String role, // 'caregiver' or 'admin'
  }) async {
    UserCredential? userCredential;

    try {
      LogService.info('AuthService', '회원가입 시작: $email');

      // Firebase Auth로 사용자 생성
      userCredential = await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );

      LogService.info(
          'AuthService', 'Firebase Auth 계정 생성 완료: ${userCredential.user?.uid}');

      try {
        // 사용자 정보를 Firestore에 저장
        await _firestore.collection('users').doc(userCredential.user!.uid).set({
          'email': email,
          'name': name,
          'role': role,
          'createdAt': FieldValue.serverTimestamp(),
          'lastLoginAt': FieldValue.serverTimestamp(),
        });

        LogService.info('AuthService', 'Firestore 사용자 정보 저장 완료');

        // 사용자 프로필 업데이트
        await userCredential.user!.updateDisplayName(name);

        LogService.info('AuthService', '회원가입 완료: $email');

        // FCM 토큰 서버로 전송
        _sendFCMTokenAsync();

        return userCredential;
      } catch (firestoreError) {
        // Firestore 저장 실패 시 생성된 Auth 계정 삭제
        LogService.error(
            'AuthService', 'Firestore 저장 실패, Auth 계정 삭제 시도: $firestoreError');

        try {
          await userCredential.user?.delete();
          LogService.info('AuthService', 'Auth 계정 삭제 완료');
        } catch (deleteError) {
          LogService.error('AuthService', 'Auth 계정 삭제 실패: $deleteError');
        }

        throw Exception('사용자 정보 저장 중 오류가 발생했습니다. 다시 시도해주세요.');
      }
    } catch (e) {
      LogService.error('AuthService', '회원가입 오류: $e');

      if (e is FirebaseAuthException) {
        LogService.error('AuthService', 'Firebase Auth 오류 코드: ${e.code}');
      }

      rethrow;
    }
  }

  // 통합 회원가입 (사용자 + 시니어 정보)
  Future<UserCredential?> integratedSignUp({
    // 사용자 정보
    required String email,
    required String password,
    required String name,
    required String role,
    required String userPhone,
    required String userGender,
    required int userAge,
    required String userAddress,
    // 시니어 정보
    required String seniorName,
    required String seniorPhone,
    required int seniorAge,
    required String seniorGender,
    required String seniorAddress,
    required String relationship,
  }) async {
    UserCredential? userCredential;

    try {
      LogService.info('AuthService', '통합 회원가입 시작: $email');

      // 1. Firebase Auth로 사용자 생성
      userCredential = await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );

      LogService.info(
          'AuthService', 'Firebase Auth 계정 생성 완료: ${userCredential.user?.uid}');

      try {
        // 2. 사용자 정보를 Firestore에 저장
        await _firestore.collection('users').doc(userCredential.user!.uid).set({
          'email': email,
          'name': name,
          'role': role,
          'phoneNumber': userPhone,
          'gender': userGender,
          'age': userAge,
          'address': userAddress,
          'createdAt': FieldValue.serverTimestamp(),
          'lastLoginAt': FieldValue.serverTimestamp(),
        });

        LogService.info('AuthService', 'Firestore 사용자 정보 저장 완료');

        // 3. 시니어 정보를 Firestore에 저장
        final seniorId = 'senior_${DateTime.now().millisecondsSinceEpoch}';

        await _firestore
            .collection('users')
            .doc(userCredential.user!.uid)
            .collection('seniors')
            .doc(seniorId)
            .set({
          'seniorId': seniorId,
          'userId': userCredential.user!.uid,
          'name': seniorName,
          'phoneNumber': seniorPhone,
          'age': seniorAge,
          'gender': seniorGender,
          'address': seniorAddress,
          'relationship': relationship,
          'caregivers': [userCredential.user!.uid],
          'createdAt': FieldValue.serverTimestamp(),
          'updatedAt': FieldValue.serverTimestamp(),
          'active': true,
          'callStats': {
            'totalCalls': 0,
            'completedAnalyses': 0,
            'lastCallDate': null
          }
        });

        LogService.info('AuthService', 'Firestore 시니어 정보 저장 완료');

        // 4. 사용자 프로필 업데이트
        await userCredential.user!.updateDisplayName(name);

        LogService.info('AuthService', '통합 회원가입 완료: $email');

        // 5. FCM 토큰 서버로 전송 (비동기적으로 처리)
        _sendFCMTokenAsync();

        return userCredential;
      } catch (firestoreError) {
        // Firestore 저장 실패 시 생성된 Auth 계정 삭제
        LogService.error(
            'AuthService', 'Firestore 저장 실패, Auth 계정 삭제 시도: $firestoreError');

        try {
          await userCredential.user?.delete();
          LogService.info('AuthService', 'Auth 계정 삭제 완료');
        } catch (deleteError) {
          LogService.error('AuthService', 'Auth 계정 삭제 실패: $deleteError');
        }

        throw Exception('통합 회원가입 중 오류가 발생했습니다. 다시 시도해주세요.');
      }
    } catch (e) {
      LogService.error('AuthService', '통합 회원가입 오류: $e');

      if (e is FirebaseAuthException) {
        LogService.error('AuthService', 'Firebase Auth 오류 코드: ${e.code}');
      }

      rethrow;
    }
  }

  // 로그인
  Future<UserCredential?> signIn({
    required String email,
    required String password,
  }) async {
    try {
      LogService.info('AuthService', '로그인 시도: $email');

      final UserCredential userCredential =
          await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );

      LogService.info('AuthService', '로그인 성공: ${userCredential.user?.uid}');

      // 마지막 로그인 시간 업데이트
      try {
        await _firestore
            .collection('users')
            .doc(userCredential.user!.uid)
            .update({
          'lastLoginAt': FieldValue.serverTimestamp(),
        });
        LogService.info('AuthService', '마지막 로그인 시간 업데이트 완료');
      } catch (updateError) {
        // Firestore 업데이트 실패는 로그인 실패로 처리하지 않음
        LogService.warning('AuthService', '마지막 로그인 시간 업데이트 실패: $updateError');
      }

      // FCM 토큰 서버로 전송
      try {
        LogService.info('AuthService', '로그인 후 FCM 토큰 전송 시작');

        // FCM 서비스 초기화 및 토큰 등록
        final fcmService = FCMService();
        await fcmService.initialize();

        if (fcmService.token != null) {
          LogService.info('AuthService', 'FCM 토큰 획득 성공: ${fcmService.token?.substring(0, 20)}...');
          // 토큰이 이미 FCMService.initialize()에서 백엔드에 등록됨
          LogService.info('AuthService', 'FCM 토큰이 백엔드에 등록되었습니다');
        } else {
          LogService.warning('AuthService', 'FCM 토큰을 가져올 수 없습니다');

          // 토큰 새로고침 시도
          await fcmService.refreshToken();

          if (fcmService.token != null) {
            LogService.info('AuthService', '새로고침 후 FCM 토큰 획득 성공');
          }
        }
      } catch (fcmError) {
        // FCM 토큰 전송 실패는 로그인 실패로 처리하지 않음
        LogService.warning('AuthService', 'FCM 토큰 전송 실패 (로그인은 성공): $fcmError');
      }

      return userCredential;
    } catch (e) {
      LogService.error('AuthService', '로그인 오류: $e');

      if (e is FirebaseAuthException) {
        LogService.error('AuthService', 'Firebase Auth 오류 코드: ${e.code}');
        LogService.error('AuthService', 'Firebase Auth 오류 메시지: ${e.message}');
      }

      rethrow;
    }
  }

  // 로그아웃
  Future<void> signOut() async {
    try {
      await _auth.signOut();

      // 로컬 저장소에서 사용자 데이터 삭제
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_userKey);
    } catch (e) {
      LogService.warning('AuthService', '로그아웃 오류: $e');
      rethrow;
    }
  }

  // 현재 사용자 정보 가져오기 (Firestore에서)
  Future<Map<String, dynamic>?> getCurrentUserData() async {
    try {
      final User? user = _auth.currentUser;
      if (user == null) return null;

      final DocumentSnapshot doc =
          await _firestore.collection('users').doc(user.uid).get();

      if (doc.exists) {
        return doc.data() as Map<String, dynamic>;
      }

      return null;
    } catch (e) {
      LogService.warning('AuthService', '사용자 정보 가져오기 오류: $e');
      return null;
    }
  }

  // 사용자 정보 업데이트
  Future<void> updateUserData(Map<String, dynamic> userData) async {
    try {
      final User? user = _auth.currentUser;
      if (user == null) throw Exception('사용자가 로그인되지 않았습니다');

      await _firestore.collection('users').doc(user.uid).update(userData);
    } catch (e) {
      LogService.warning('AuthService', '사용자 정보 업데이트 오류: $e');
      rethrow;
    }
  }

  // 비밀번호 재설정
  Future<void> resetPassword(String email) async {
    try {
      await _auth.sendPasswordResetEmail(email: email);
    } catch (e) {
      LogService.warning('AuthService', '비밀번호 재설정 오류: $e');
      rethrow;
    }
  }

  // 사용자 ID 토큰 가져오기 (Firebase Functions 인증용)
  Future<String?> getIdToken() async {
    try {
      final User? user = _auth.currentUser;
      if (user == null) return null;

      return await user.getIdToken();
    } catch (e) {
      LogService.warning('AuthService', 'ID 토큰 가져오기 오류: $e');
      return null;
    }
  }

  // 오류 메시지 변환 (사용자 친화적)
  String getErrorMessage(FirebaseAuthException e) {
    switch (e.code) {
      case 'user-not-found':
        return '등록되지 않은 사용자입니다.';
      case 'wrong-password':
        return '비밀번호가 잘못되었습니다.';
      case 'invalid-credential':
        return '인증 정보가 올바르지 않습니다. 이메일과 비밀번호를 다시 확인해주세요.';
      case 'email-already-in-use':
        return '이미 사용 중인 이메일입니다.';
      case 'weak-password':
        return '비밀번호가 너무 약합니다.';
      case 'invalid-email':
        return '유효하지 않은 이메일입니다.';
      case 'network-request-failed':
        return '네트워크 연결을 확인해주세요.';
      case 'too-many-requests':
        return '너무 많은 시도가 있었습니다. 잠시 후 다시 시도해주세요.';
      case 'user-disabled':
        return '이 계정은 비활성화되었습니다.';
      default:
        LogService.warning(
            'AuthService', '처리되지 않은 Firebase 오류: ${e.code} - ${e.message}');
        return '오류가 발생했습니다: ${e.message}';
    }
  }

  // 개발/테스트용 임시 로그인 (프로덕션 계정 사용)
  Future<bool> developmentLogin() async {
    try {
      // 프로덕션 계정으로 로그인
      await signIn(
        email: 'seokmin.lee@gmail.com',
        password: 'seokmin123',
      );

      // FCM 토큰 서버로 전송 (signIn에서 이미 처리하지만 명시적으로 한번 더)
      try {
        LogService.info('AuthService', '개발 로그인 후 FCM 토큰 재전송 시도');
        final messagingService = MessagingService();
        await messagingService.sendTokenToServer();
        LogService.info('AuthService', 'FCM 토큰 재전송 완료');
      } catch (fcmError) {
        LogService.warning('AuthService', 'FCM 토큰 재전송 실패: $fcmError');
      }

      return true;
    } catch (e) {
      LogService.warning('AuthService', '프로덕션 로그인 실패: $e');
      return false;
    }
  }

  // FCM 토큰을 비동기적으로 서버에 전송 (성능 최적화)
  void _sendFCMTokenAsync() {
    Future.delayed(Duration(seconds: 1), () async {
      try {
        LogService.info('AuthService', '비동기 FCM 토큰 전송 시작');

        // FCM 서비스 초기화 및 토큰 등록
        final fcmService = FCMService();
        await fcmService.initialize();

        if (fcmService.token != null) {
          LogService.info('AuthService', '비동기 FCM 토큰 획득 성공: ${fcmService.token?.substring(0, 20)}...');
          LogService.info('AuthService', '비동기 FCM 토큰이 백엔드에 등록되었습니다');
        } else {
          LogService.warning('AuthService', '비동기 FCM 토큰을 가져올 수 없습니다');

          // 토큰 새로고침 시도
          await fcmService.refreshToken();

          if (fcmService.token != null) {
            LogService.info('AuthService', '비동기 새로고침 후 FCM 토큰 획득 성공');
          }
        }
      } catch (e) {
        LogService.warning('AuthService', '비동기 FCM 토큰 전송 오류: $e');
      }
    });
  }
}
