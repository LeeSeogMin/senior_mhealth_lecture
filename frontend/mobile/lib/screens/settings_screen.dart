import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/messaging_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  bool _notificationEnabled = true;
  final MessagingService _messagingService = MessagingService();

  @override
  void initState() {
    super.initState();
    _loadSeniorInfo();
    _loadNotificationSettings();
  }

  // 기존 시니어 정보 불러오기
  Future<void> _loadSeniorInfo() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _nameController.text = prefs.getString('senior_name') ?? '';
      _phoneController.text = prefs.getString('senior_phone') ?? '';
    });
  }

  // 알림 설정 불러오기
  Future<void> _loadNotificationSettings() async {
    final enabled = await _messagingService.isNotificationEnabled();
    setState(() {
      _notificationEnabled = enabled;
    });
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  // 알림 설정 업데이트
  Future<void> _updateNotificationSettings(bool value) async {
    setState(() {
      _notificationEnabled = value;
    });

    try {
      await _messagingService.setNotificationEnabled(value);
      _showMessage(value ? '알림이 활성화되었습니다' : '알림이 비활성화되었습니다');
    } catch (e) {
      _showMessage('알림 설정 변경 중 오류가 발생했습니다');
      // 오류 발생 시 상태 롤백
      setState(() {
        _notificationEnabled = !value;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('설정', style: TextStyle(fontWeight: FontWeight.w600)),
        backgroundColor: Colors.white,
        foregroundColor: Colors.grey[800],
        elevation: 0,
      ),
      backgroundColor: Colors.grey[50],
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 알림 설정 섹션
            const SizedBox(height: 20),
            const Text(
              '알림 설정',
              style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w600,
                  color: Colors.black87),
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.05),
                    blurRadius: 10,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.blue[50],
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(
                      Icons.notifications,
                      color: Colors.blue[600],
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '푸시 알림',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: Colors.grey[800],
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '통화 분석 완료 시 알림을 받습니다',
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                  ),
                  Switch(
                    value: _notificationEnabled,
                    onChanged: _updateNotificationSettings,
                    activeColor: Colors.blue[600],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    super.dispose();
  }
}
