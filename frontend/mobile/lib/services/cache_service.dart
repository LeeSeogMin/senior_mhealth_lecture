import 'package:cloud_firestore/cloud_firestore.dart';
import 'log_service.dart';

/// Firestore를 캐시로 활용하는 서비스
class CacheService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  static const int _cacheExpiryHours = 24; // 캐시 유효 시간 (24시간)

  /// API 결과를 Firestore에 캐시
  Future<void> cacheAnalysisResult(String id, Map<String, dynamic> data) async {
    try {
      await _firestore.collection('cache_analyses').doc(id).set({
        ...data,
        'cached_at': FieldValue.serverTimestamp(),
        'cache_version': '1.0',
      });
      LogService.info('CacheService', '✅ 분석 결과 캐시 저장: $id');
    } catch (e) {
      LogService.error('CacheService', '❌ 캐시 저장 오류: $e');
    }
  }

  /// 캐시에서 분석 결과 조회
  Future<Map<String, dynamic>?> getCachedAnalysis(String id) async {
    try {
      final cache = await _firestore.collection('cache_analyses').doc(id).get();

      if (cache.exists && cache.data() != null) {
        final data = cache.data()!;
        final cachedAt = data['cached_at'] as Timestamp?;

        // 캐시 유효성 검사
        if (cachedAt != null) {
          final now = DateTime.now();
          final cacheTime = cachedAt.toDate();
          final difference = now.difference(cacheTime).inHours;

          if (difference < _cacheExpiryHours) {
            LogService.info('CacheService', '✅ 유효한 캐시 발견: $id');
            return data;
          } else {
            LogService.info('CacheService', '⏰ 캐시 만료: $id (${difference}시간 경과)');
            // 만료된 캐시 삭제
            await _firestore.collection('cache_analyses').doc(id).delete();
          }
        }
      }

      LogService.info('CacheService', '❌ 캐시 없음: $id');
      return null;
    } catch (e) {
      LogService.error('CacheService', '❌ 캐시 조회 오류: $e');
      return null;
    }
  }

  /// 시니어 정보 캐시
  Future<void> cacheSeniorInfo(String seniorId, Map<String, dynamic> data) async {
    try {
      await _firestore.collection('cache_seniors').doc(seniorId).set({
        ...data,
        'cached_at': FieldValue.serverTimestamp(),
        'cache_version': '1.0',
      });
      LogService.info('CacheService', '✅ 시니어 정보 캐시 저장: $seniorId');
    } catch (e) {
      LogService.error('CacheService', '❌ 시니어 캐시 저장 오류: $e');
    }
  }

  /// 캐시에서 시니어 정보 조회
  Future<Map<String, dynamic>?> getCachedSenior(String seniorId) async {
    try {
      final cache = await _firestore.collection('cache_seniors').doc(seniorId).get();

      if (cache.exists && cache.data() != null) {
        final data = cache.data()!;
        final cachedAt = data['cached_at'] as Timestamp?;

        // 캐시 유효성 검사
        if (cachedAt != null) {
          final now = DateTime.now();
          final cacheTime = cachedAt.toDate();
          final difference = now.difference(cacheTime).inHours;

          if (difference < _cacheExpiryHours) {
            LogService.info('CacheService', '✅ 유효한 시니어 캐시 발견: $seniorId');
            return data;
          } else {
            LogService.info('CacheService', '⏰ 시니어 캐시 만료: $seniorId');
            await _firestore.collection('cache_seniors').doc(seniorId).delete();
          }
        }
      }

      return null;
    } catch (e) {
      LogService.error('CacheService', '❌ 시니어 캐시 조회 오류: $e');
      return null;
    }
  }

  /// 통화 목록 캐시
  Future<void> cacheCallList(String seniorId, List<Map<String, dynamic>> calls) async {
    try {
      await _firestore.collection('cache_calls').doc(seniorId).set({
        'calls': calls,
        'cached_at': FieldValue.serverTimestamp(),
        'cache_version': '1.0',
      });
      LogService.info('CacheService', '✅ 통화 목록 캐시 저장: $seniorId (${calls.length}개)');
    } catch (e) {
      LogService.error('CacheService', '❌ 통화 목록 캐시 저장 오류: $e');
    }
  }

  /// 캐시에서 통화 목록 조회
  Future<List<Map<String, dynamic>>?> getCachedCallList(String seniorId) async {
    try {
      final cache = await _firestore.collection('cache_calls').doc(seniorId).get();

      if (cache.exists && cache.data() != null) {
        final data = cache.data()!;
        final cachedAt = data['cached_at'] as Timestamp?;

        // 캐시 유효성 검사 (통화 목록은 더 짧은 유효 시간)
        if (cachedAt != null) {
          final now = DateTime.now();
          final cacheTime = cachedAt.toDate();
          final difference = now.difference(cacheTime).inMinutes;

          if (difference < 30) { // 30분 유효
            LogService.info('CacheService', '✅ 유효한 통화 목록 캐시 발견: $seniorId');
            final calls = data['calls'] as List<dynamic>?;
            return calls?.map((e) => e as Map<String, dynamic>).toList();
          } else {
            LogService.info('CacheService', '⏰ 통화 목록 캐시 만료: $seniorId');
            await _firestore.collection('cache_calls').doc(seniorId).delete();
          }
        }
      }

      return null;
    } catch (e) {
      LogService.error('CacheService', '❌ 통화 목록 캐시 조회 오류: $e');
      return null;
    }
  }

  /// 모든 캐시 삭제
  Future<void> clearAllCache() async {
    try {
      // 분석 캐시 삭제
      final analyses = await _firestore.collection('cache_analyses').get();
      for (var doc in analyses.docs) {
        await doc.reference.delete();
      }

      // 시니어 캐시 삭제
      final seniors = await _firestore.collection('cache_seniors').get();
      for (var doc in seniors.docs) {
        await doc.reference.delete();
      }

      // 통화 목록 캐시 삭제
      final calls = await _firestore.collection('cache_calls').get();
      for (var doc in calls.docs) {
        await doc.reference.delete();
      }

      LogService.info('CacheService', '✅ 모든 캐시 삭제 완료');
    } catch (e) {
      LogService.error('CacheService', '❌ 캐시 삭제 오류: $e');
    }
  }

  /// 오프라인 지원을 위한 Firestore 설정
  void enableOfflineSupport() {
    try {
      _firestore.settings = const Settings(
        persistenceEnabled: true,
        cacheSizeBytes: Settings.CACHE_SIZE_UNLIMITED,
      );
      LogService.info('CacheService', '✅ 오프라인 지원 활성화');
    } catch (e) {
      LogService.error('CacheService', '❌ 오프라인 지원 설정 오류: $e');
    }
  }
}