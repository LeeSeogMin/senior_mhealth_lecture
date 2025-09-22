import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../services/auth_service.dart';
import '../services/messaging_service.dart';
import 'home_screen.dart';
import 'integrated_signup_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final AuthService _authService = AuthService();
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _isLoading = false;
  bool _obscurePassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
    });

    try {
      if (kDebugMode) {
        print('🔐 로그인 시작: ${_emailController.text.trim()}');
      }

      await _authService.signIn(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );

      if (kDebugMode) {
        print('✅ 로그인 성공');
        print('🔍 === FCM 토큰 상태 확인 시작 ===');
      }

      // FCM 토큰 상태 확인
      try {
        final messagingService = MessagingService();
        if (kDebugMode) {
          print('📱 MessagingService 인스턴스 생성 완료');
          print('📱 FCM 초기화 상태: ${messagingService.isInitialized}');
          print('📱 FCM 토큰: ${messagingService.fcmToken}');
        }

        // 토큰이 없으면 잠시 대기 후 재확인
        if (messagingService.fcmToken == null) {
          if (kDebugMode) {
            print('⚠️ FCM 토큰이 아직 준비되지 않음 - 3초 후 재확인');
          }
          await Future.delayed(const Duration(seconds: 3));
          if (kDebugMode) {
            print('📱 지연된 FCM 토큰 확인: ${messagingService.fcmToken}');
          }
        }
      } catch (e) {
        if (kDebugMode) {
          print('❌ FCM 토큰 확인 중 오류: $e');
        }
      }

      if (kDebugMode) {
        print('🔍 === FCM 토큰 상태 확인 완료 ===');
      }

      _showSnackBar('로그인 성공!');

      // 홈 화면으로 이동
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const HomeScreen()),
        );
      }
    } catch (error) {
      if (kDebugMode) {
        print('❌ 로그인 실패: $error');
      }

      String errorMessage = '로그인에 실패했습니다';
      if (error is FirebaseAuthException) {
        switch (error.code) {
          case 'user-not-found':
            errorMessage = '등록되지 않은 이메일입니다';
            break;
          case 'wrong-password':
            errorMessage = '비밀번호가 올바르지 않습니다';
            break;
          case 'invalid-email':
            errorMessage = '올바른 이메일 형식이 아닙니다';
            break;
          case 'user-disabled':
            errorMessage = '비활성화된 계정입니다';
            break;
          default:
            errorMessage = '로그인 중 오류가 발생했습니다: ${error.message}';
        }
      }

      _showSnackBar(errorMessage);
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _handleDevelopmentLogin() async {
    setState(() {
      _isLoading = true;
    });

    try {
      if (kDebugMode) {
        print('🔧 프로덕션 계정 자동 로그인 시작');
      }

      await _authService.signIn(
        email: 'seokmin.lee@gmail.com',
        password: 'TempPassword123!',
      );

      if (kDebugMode) {
        print('✅ 프로덕션 계정 로그인 성공');
      }

      _showSnackBar('프로덕션 계정으로 로그인되었습니다');

      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const HomeScreen()),
        );
      }
    } catch (error) {
      if (kDebugMode) {
        print('❌ 프로덕션 계정 로그인 실패: $error');
      }
      _showSnackBar('프로덕션 계정 로그인에 실패했습니다: ${error.toString()}');
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.blue.shade50,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(height: 60),

                // 로고 및 제목
                const Icon(
                  Icons.health_and_safety,
                  size: 80,
                  color: Colors.blue,
                ),

                const SizedBox(height: 24),

                const Text(
                  '시니어 헬스케어',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: Colors.blue,
                  ),
                ),

                const SizedBox(height: 8),

                const Text(
                  '사랑하는 가족의 건강을 지켜보세요',
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.grey,
                  ),
                  textAlign: TextAlign.center,
                ),

                const SizedBox(height: 48),

                // 이메일 입력
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: '이메일',
                    hintText: 'example@example.com',
                    prefixIcon: Icon(Icons.email),
                    border: OutlineInputBorder(),
                    filled: true,
                    fillColor: Colors.white,
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return '이메일을 입력해주세요';
                    }
                    if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$')
                        .hasMatch(value)) {
                      return '올바른 이메일 형식을 입력해주세요';
                    }
                    return null;
                  },
                ),

                const SizedBox(height: 16),

                // 비밀번호 입력
                TextFormField(
                  controller: _passwordController,
                  obscureText: _obscurePassword,
                  decoration: InputDecoration(
                    labelText: '비밀번호',
                    hintText: '비밀번호를 입력하세요',
                    prefixIcon: const Icon(Icons.lock),
                    suffixIcon: IconButton(
                      icon: Icon(_obscurePassword
                          ? Icons.visibility
                          : Icons.visibility_off),
                      onPressed: () {
                        setState(() {
                          _obscurePassword = !_obscurePassword;
                        });
                      },
                    ),
                    border: const OutlineInputBorder(),
                    filled: true,
                    fillColor: Colors.white,
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return '비밀번호를 입력해주세요';
                    }
                    return null;
                  },
                ),

                const SizedBox(height: 24),

                // 로그인 버튼
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _handleLogin,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                    child: _isLoading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor:
                                  AlwaysStoppedAnimation<Color>(Colors.white),
                            ),
                          )
                        : const Text(
                            '로그인',
                            style: TextStyle(fontSize: 16),
                          ),
                  ),
                ),

                const SizedBox(height: 16),

                // 통합 회원가입 버튼
                TextButton(
                  onPressed: _isLoading
                      ? null
                      : () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => const IntegratedSignupScreen(),
                            ),
                          );
                        },
                  child: const Text('계정이 없으신가요? 회원가입'),
                ),

                const SizedBox(height: 32),

                // 구분선
                const Divider(),

                const SizedBox(height: 16),

                // 개발용 로그인 버튼
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: _isLoading ? null : _handleDevelopmentLogin,
                    child: const Text('프로덕션 계정으로 로그인'),
                  ),
                ),

                const SizedBox(height: 16),

                // 도움말 텍스트
                const Text(
                  '프로덕션 계정(seokmin.lee@gmail.com)으로 자동 로그인됩니다.',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
