import 'dart:io';
import 'package:permission_handler/permission_handler.dart';
import 'package:flutter/foundation.dart';
import 'package:device_info_plus/device_info_plus.dart';

class SamsungCallDetector {
  // Samsung 통화 녹음 기본 경로
  static const String callRecordingPath = '/storage/emulated/0/Recordings/Call';

  /// Android API 레벨 확인
  Future<int?> _getAndroidApiLevel() async {
    if (!Platform.isAndroid) return null;

    try {
      final deviceInfo = DeviceInfoPlugin();
      final androidInfo = await deviceInfo.androidInfo;
      return androidInfo.version.sdkInt;
    } catch (e) {
      if (kDebugMode) {
        print('❌ Android API 레벨 확인 실패: $e');
      }
      return null;
    }
  }

  /// Android 버전에 따른 저장소 권한 요청
  Future<bool> requestStoragePermissions() async {
    if (kIsWeb) {
      if (kDebugMode) print('🌐 웹 환경: 권한 요청 스킵');
      return false;
    }

    try {
      final apiLevel = await _getAndroidApiLevel();
      if (apiLevel == null) {
        if (kDebugMode) print('❌ Android API 레벨을 확인할 수 없음');
        return false;
      }

      final isAndroid11Plus = apiLevel >= 30;

      if (kDebugMode) {
        print('📱 Android API 레벨: $apiLevel (Android 11+: $isAndroid11Plus)');
      }

      PermissionStatus status;

      if (isAndroid11Plus) {
        // Android 11+: MANAGE_EXTERNAL_STORAGE 권한 체크
        status = await Permission.manageExternalStorage.status;

        if (kDebugMode) {
          print(
              '📁 Android 11+ MANAGE_EXTERNAL_STORAGE 권한 상태: ${status.toString()}');
        }
      } else {
        // Android 10 이하: 일반 storage 권한 체크
        status = await Permission.storage.status;

        if (kDebugMode) {
          print('📁 Android 10 이하 storage 권한 상태: ${status.toString()}');
        }
      }

      final isGranted = status.isGranted;

      if (kDebugMode) {
        print('📁 최종 저장소 권한 상태: $isGranted');
        if (!isGranted && isAndroid11Plus) {
          print(
              '⚠️ Android 11+에서 MANAGE_EXTERNAL_STORAGE 권한이 필요합니다. 시스템 설정에서 수동으로 허용해야 합니다.');
        }
      }

      return isGranted;
    } catch (e) {
      if (kDebugMode) {
        print('❌ 저장소 권한 확인 오류: $e');
      }
      return false;
    }
  }

  /// Samsung 통화 녹음 폴더 존재 여부 확인
  Future<bool> checkCallRecordingFolder() async {
    try {
      final directory = Directory(callRecordingPath);
      final exists = await directory.exists();

      if (kDebugMode) {
        print('📁 통화 녹음 폴더 존재: $exists');
        print('📁 경로: $callRecordingPath');
      }

      return exists;
    } catch (e) {
      if (kDebugMode) {
        print('❌ 폴더 확인 오류: $e');
      }
      return false;
    }
  }

  /// Samsung 통화 녹음 파일인지 확인
  /// 패턴: "통화 녹음 [이름]_[YYMMDD]_[HHMMSS].m4a" 또는 ".wav"
  bool isSamsungCallRecording(String fileName) {
    final pattern = RegExp(r'^통화 녹음 .+_\d{6}_\d{6}\.(m4a|wav)$');
    return pattern.hasMatch(fileName);
  }

  /// 파일명에서 이름 추출
  /// "통화 녹음 정연이_250727_114239.m4a" → "정연이"
  String? extractNameFromFileName(String fileName) {
    if (!isSamsungCallRecording(fileName)) return null;

    try {
      // "통화 녹음 " 제거하고 첫 번째 "_" 앞까지가 이름
      final withoutPrefix = fileName.replaceFirst('통화 녹음 ', '');
      final parts = withoutPrefix.split('_');
      return parts.isNotEmpty ? parts[0] : null;
    } catch (e) {
      if (kDebugMode) print('❌ 이름 추출 오류: $e');
      return null;
    }
  }

  /// 파일명에서 통화 날짜/시간을 DateTime으로 변환
  /// "통화 녹음 정연이_250727_114239.m4a" → DateTime(2025, 7, 27, 11, 42, 39)
  DateTime? extractDateTimeFromFileName(String fileName) {
    if (!isSamsungCallRecording(fileName)) return null;

    try {
      final withoutPrefix = fileName.replaceFirst('통화 녹음 ', '');
      final parts = withoutPrefix.split('_');

      if (parts.length < 3) return null;

      final dateStr = parts[1]; // "250727"
      final timeStr = parts[2].replaceAll(RegExp(r'\.(m4a|wav)$'), ''); // "114239"

      if (dateStr.length != 6 || timeStr.length != 6) return null;

      // 날짜 파싱: YYMMDD → YYYY-MM-DD
      final year = 2000 + int.parse(dateStr.substring(0, 2)); // 25 → 2025
      final month = int.parse(dateStr.substring(2, 4)); // 07
      final day = int.parse(dateStr.substring(4, 6)); // 27

      // 시간 파싱: HHMMSS → HH:MM:SS
      final hour = int.parse(timeStr.substring(0, 2)); // 11
      final minute = int.parse(timeStr.substring(2, 4)); // 42
      final second = int.parse(timeStr.substring(4, 6)); // 39

      return DateTime(year, month, day, hour, minute, second);
    } catch (e) {
      if (kDebugMode) print('❌ 날짜시간 추출 오류 ($fileName): $e');
      return null;
    }
  }

  /// 파일명에서 날짜/시간 정보 추출 (Map 형태)
  Map<String, String>? extractDateTimeInfo(String fileName) {
    if (!isSamsungCallRecording(fileName)) return null;

    try {
      final withoutPrefix = fileName.replaceFirst('통화 녹음 ', '');
      final parts = withoutPrefix.split('_');

      if (parts.length < 3) return null;

      return {
        'date': parts[1], // "250727"
        'time': parts[2].replaceAll(RegExp(r'\.(m4a|wav)$'), ''), // "114239"
      };
    } catch (e) {
      if (kDebugMode) print('❌ 날짜시간 정보 추출 오류: $e');
      return null;
    }
  }

  /// 가장 최근 통화 녹음 파일 찾기 (파일명 날짜/시간 기준)
  Future<File?> findLatestCallRecording({String? seniorName}) async {
    try {
      final hasPermission = await requestStoragePermissions();
      if (!hasPermission) {
        if (kDebugMode) print('❌ 저장소 권한 없음');
        return null;
      }

      final folderExists = await checkCallRecordingFolder();
      if (!folderExists) {
        if (kDebugMode) print('❌ 통화 녹음 폴더 없음');
        return null;
      }

      final directory = Directory(callRecordingPath);
      final fileList = await directory.list().toList();

      if (kDebugMode) {
        print('📁 폴더 내 전체 파일 수: ${fileList.length}');
        for (var entity in fileList) {
          if (entity is File) {
            final fileName = entity.path.split('/').last;
            print('📄 파일: $fileName');
          }
        }
      }

      // Samsung 통화 녹음 파일만 필터링
      List<File> callRecordings = [];

      for (var entity in fileList) {
        if (entity is File) {
          final fileName = entity.path.split('/').last;

          if (kDebugMode) {
            print('🔍 파일 검사: $fileName');
            print('   → Samsung 패턴 매치: ${isSamsungCallRecording(fileName)}');
          }

          if (isSamsungCallRecording(fileName)) {
            if (kDebugMode) {
              print('   ✅ Samsung 통화 녹음 파일로 인식됨');
            }

            // 시니어 이름 필터링 (선택적)
            if (seniorName != null) {
              final extractedName = extractNameFromFileName(fileName);
              if (kDebugMode) {
                print('   🔍 시니어 이름 추출: $extractedName');
                print('   🔍 찾는 시니어: $seniorName');
              }
              if (extractedName == null ||
                  !extractedName.contains(seniorName)) {
                if (kDebugMode) {
                  print('   ❌ 시니어 이름 매치 실패');
                }
                continue;
              }
              if (kDebugMode) {
                print('   ✅ 시니어 이름 매치 성공');
              }
            }

            callRecordings.add(entity);
            if (kDebugMode) {
              print('   ✅ 파일 목록에 추가됨');
            }
          } else {
            if (kDebugMode) {
              print('   ❌ Samsung 통화 녹음 패턴과 맞지 않음');
            }
          }
        }
      }

      if (callRecordings.isEmpty) {
        if (kDebugMode) {
          print(
            '❌ 통화 녹음 파일 없음${seniorName != null ? ' (시니어: $seniorName)' : ''}',
          );
        }
        return null;
      }

      // 🎯 핵심: 파일명의 실제 날짜/시간으로 정렬
      callRecordings.sort((a, b) {
        final fileNameA = a.path.split('/').last;
        final fileNameB = b.path.split('/').last;

        final dateTimeA = extractDateTimeFromFileName(fileNameA);
        final dateTimeB = extractDateTimeFromFileName(fileNameB);

        // DateTime이 null인 경우 처리
        if (dateTimeA == null && dateTimeB == null) return 0;
        if (dateTimeA == null) return 1; // A를 뒤로
        if (dateTimeB == null) return -1; // B를 뒤로

        // 최신 순 정렬 (내림차순)
        return dateTimeB.compareTo(dateTimeA);
      });

      final latestFile = callRecordings.first;

      if (kDebugMode) {
        final fileName = latestFile.path.split('/').last;
        final dateTime = extractDateTimeFromFileName(fileName);
        print('✅ 가장 최근 통화 파일: $fileName');
        print('📅 통화 날짜/시간: $dateTime');
      }

      return latestFile;
    } catch (e) {
      if (kDebugMode) {
        print('❌ 최신 통화 녹음 찾기 오류: $e');
      }
      return null;
    }
  }

  /// 특정 시니어의 모든 통화 녹음 파일 찾기 (최신 순)
  Future<List<File>> findAllCallRecordingsForSenior(String seniorName) async {
    List<File> result = [];

    try {
      final hasPermission = await requestStoragePermissions();
      if (!hasPermission) return result;

      final folderExists = await checkCallRecordingFolder();
      if (!folderExists) return result;

      final directory = Directory(callRecordingPath);
      final fileList = await directory.list().toList();

      for (var entity in fileList) {
        if (entity is File) {
          final fileName = entity.path.split('/').last;

          if (isSamsungCallRecording(fileName)) {
            final extractedName = extractNameFromFileName(fileName);
            if (extractedName != null && extractedName.contains(seniorName)) {
              result.add(entity);
            }
          }
        }
      }

      // 파일명 날짜/시간으로 최신 순 정렬
      result.sort((a, b) {
        final fileNameA = a.path.split('/').last;
        final fileNameB = b.path.split('/').last;

        final dateTimeA = extractDateTimeFromFileName(fileNameA);
        final dateTimeB = extractDateTimeFromFileName(fileNameB);

        if (dateTimeA == null && dateTimeB == null) return 0;
        if (dateTimeA == null) return 1;
        if (dateTimeB == null) return -1;

        return dateTimeB.compareTo(dateTimeA);
      });

      return result;
    } catch (e) {
      if (kDebugMode) {
        print('❌ 시니어 통화 녹음 목록 조회 오류: $e');
      }
      return result;
    }
  }

  /// 모든 통화 녹음 파일 목록 조회 (최신 순)
  Future<List<Map<String, dynamic>>> getAllCallRecordings() async {
    List<Map<String, dynamic>> result = [];

    try {
      final hasPermission = await requestStoragePermissions();
      if (!hasPermission) return result;

      final folderExists = await checkCallRecordingFolder();
      if (!folderExists) return result;

      final directory = Directory(callRecordingPath);
      final fileList = await directory.list().toList();

      List<File> callRecordings = [];

      for (var entity in fileList) {
        if (entity is File) {
          final fileName = entity.path.split('/').last;
          if (isSamsungCallRecording(fileName)) {
            callRecordings.add(entity);
          }
        }
      }

      // 파일명 날짜/시간으로 최신 순 정렬
      callRecordings.sort((a, b) {
        final fileNameA = a.path.split('/').last;
        final fileNameB = b.path.split('/').last;

        final dateTimeA = extractDateTimeFromFileName(fileNameA);
        final dateTimeB = extractDateTimeFromFileName(fileNameB);

        if (dateTimeA == null && dateTimeB == null) return 0;
        if (dateTimeA == null) return 1;
        if (dateTimeB == null) return -1;

        return dateTimeB.compareTo(dateTimeA);
      });

      // 파일 정보를 Map으로 변환
      for (var file in callRecordings) {
        final fileName = file.path.split('/').last;
        final name = extractNameFromFileName(fileName);
        final dateTime = extractDateTimeFromFileName(fileName);
        final fileStat = await file.stat();

        result.add({
          'file': file,
          'fileName': fileName,
          'seniorName': name,
          'callDateTime': dateTime,
          'fileSize': fileStat.size,
          'filePath': file.path,
        });
      }

      return result;
    } catch (e) {
      if (kDebugMode) {
        print('❌ 전체 통화 녹음 목록 조회 오류: $e');
      }
      return result;
    }
  }
}
