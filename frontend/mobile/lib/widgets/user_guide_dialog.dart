import 'package:flutter/material.dart';

class UserGuideDialog extends StatelessWidget {
  const UserGuideDialog({super.key});
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('통화 녹음 가이드'),
      content: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildStep(
              '1단계',
              '통화 녹음 앱 설치',
              '구글 플레이에서 통화 녹음 앱을 설치하세요.',
            ),
            _buildStep(
              '2단계',
              '녹음 폴더 설정',
              '녹음 파일이 "call_recordings" 폴더에 저장되도록 설정하세요.',
            ),
            _buildStep(
              '3단계',
              '모니터링 시작',
              '시니어 헬스케어 앱에서 모니터링을 시작하세요.',
            ),
            _buildStep(
              '4단계',
              '자동 업로드',
              '통화 녹음이 완료되면 자동으로 업로드됩니다.',
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text('확인'),
        ),
      ],
    );
  }
  
  Widget _buildStep(String step, String title, String description) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: Colors.blue,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                step.replaceAll('단계', ''),
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                SizedBox(height: 4),
                Text(
                  description,
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}