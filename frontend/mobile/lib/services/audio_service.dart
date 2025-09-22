import 'dart:io';
import 'dart:async';
import 'package:path_provider/path_provider.dart';
import 'package:flutter/foundation.dart';
import 'samsung_call_detector.dart';

class AudioService {
  static const String recordingsFolder = 'call_recordings';
  static const int minFileSize = 1024; // 1KB
  static const Duration fileStableDuration = Duration(seconds: 3);

  final SamsungCallDetector _detector = SamsungCallDetector();
  StreamController<FileSystemEntity>? _fileStreamController;
  StreamSubscription? _directoryWatcher;
  Timer? _pollingTimer;
  final Map<String, FileStat> _fileStats = {};

  // 녹음 폴더 경로 가져오기
  Future<Directory> getRecordingsDirectory() async {
    // SamsungCallDetector를 사용한 정확한 권한 체크와 폴더 확인
    final hasPermission = await _detector.requestStoragePermissions();
    if (!hasPermission) {
      if (kDebugMode) {
        print('⚠️ 저장소 권한이 없습니다');
      }
    }

    final folderExists = await _detector.checkCallRecordingFolder();
    if (folderExists) {
      const samsungCallPath = '/storage/emulated/0/Recordings/Call';
      if (kDebugMode) {
        print('📁 통화 녹음 폴더 발견: $samsungCallPath');
      }
      return Directory(samsungCallPath);
    }

    // 폴더가 없으면 기본 폴더 생성 (폴백)
    if (kDebugMode) {
      print('⚠️ 삼성 통화 녹음 폴더를 찾을 수 없음. 기본 폴더 사용.');
    }
    final appDir = await getExternalStorageDirectory();
    final recordingsDir = Directory('${appDir!.path}/$recordingsFolder');

    if (!await recordingsDir.exists()) {
      await recordingsDir.create(recursive: true);
    }

    return recordingsDir;
  }

  // 폴더 감시 시작
  Future<void> startWatching() async {
    if (kDebugMode) {
      print('📁 폴더 감시 시작');
    }

    _fileStreamController = StreamController<FileSystemEntity>.broadcast();
    final directory = await getRecordingsDirectory();

    // 방법 1: Directory.watch() 사용 (실시간)
    try {
      _directoryWatcher = directory
          .watch(events: FileSystemEvent.create | FileSystemEvent.modify)
          .listen((event) {
        final fileName = event.path.split('/').last;
        // 삼성폰 통화 녹음 패턴: "통화 녹음 [이름]_[YYMMDD]_[HHMMSS].m4a"
        if (_isSamsungCallRecording(fileName)) {
          _handleFileEvent(File(event.path));
        }
      });
    } catch (e) {
      if (kDebugMode) {
        print('Directory watch 실패: $e');
      }
      // 폴백: 폴링 방식 사용
      _startPolling(directory);
    }

    // 방법 2: 폴링 백업 (안정성)
    _startPolling(directory);
  }

  // 폴링 방식 구현
  void _startPolling(Directory directory) {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(Duration(seconds: 30), (timer) async {
      final files = directory.listSync().whereType<File>().where(
            (file) => _isSamsungCallRecording(file.path.split('/').last),
          );

      for (final file in files) {
        await _handleFileEvent(file);
      }
    });
  }

  // 파일 이벤트 처리
  Future<void> _handleFileEvent(File file) async {
    try {
      final stat = await file.stat();
      final previousStat = _fileStats[file.path];

      // 파일 크기 확인
      if (stat.size < minFileSize) {
        return; // 너무 작은 파일 무시
      }

      // 새로운 파일인 경우
      if (previousStat == null) {
        if (kDebugMode) {
          print('🆕 새 파일 감지: ${file.path} (크기: ${stat.size} bytes)');
        }
        // 파일 상태 기록하고 안정화 대기
        _fileStats[file.path] = stat;
        return;
      }

      // 파일이 아직 쓰여지고 있는지 확인
      if (previousStat.size == stat.size) {
        final timeDiff = DateTime.now().difference(previousStat.modified);

        if (timeDiff >= fileStableDuration) {
          // 파일이 완성됨
          if (kDebugMode) {
            print('✅ 완성된 파일 감지: ${file.path}');
          }
          _fileStreamController?.add(file);
          _fileStats.remove(file.path); // 중복 처리 방지
        }
      } else {
        // 파일 크기가 변경됨 - 아직 쓰여지고 있음
        if (kDebugMode) {
          print(
              '📝 파일 쓰기 중: ${file.path} (${previousStat.size} → ${stat.size} bytes)');
        }
        _fileStats[file.path] = stat;
      }
    } catch (e) {
      if (kDebugMode) {
        print('❌ 파일 처리 오류: $e');
      }
    }
  }

  // 파일 스트림 가져오기
  Stream<FileSystemEntity>? get fileStream => _fileStreamController?.stream;

  // 감시 중지
  void stopWatching() {
    if (kDebugMode) {
      print('📁 폴더 감시 중지');
    }
    _directoryWatcher?.cancel();
    _pollingTimer?.cancel();
    _fileStreamController?.close();
    _fileStats.clear();
  }

  // 파일이 완전히 쓰여졌는지 확인
  Future<bool> isFileReady(File file) async {
    try {
      // 파일을 읽기 모드로 열어봄
      final raf = await file.open(mode: FileMode.read);
      await raf.close();
      return true;
    } catch (e) {
      return false; // 파일이 아직 사용 중
    }
  }

  // 삼성폰 통화 녹음 파일 패턴 확인
  bool _isSamsungCallRecording(String fileName) {
    final pattern = RegExp(r'^통화 녹음 .+_\d{6}_\d{6}\.m4a$');
    return pattern.hasMatch(fileName);
  }
}
