'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createUserWithEmailAndPassword } from 'firebase/auth'
import { auth } from '@/lib/firebase'

export default function RegisterPage() {
  // 보호자 정보
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [userPhone, setUserPhone] = useState("");
  const [userBirthDate, setUserBirthDate] = useState("");
  const [userGender, setUserGender] = useState("male");
  const [userAddress, setUserAddress] = useState("");

  // 시니어 정보
  const [seniorName, setSeniorName] = useState("");
  const [seniorPhone, setSeniorPhone] = useState("");
  const [seniorBirthDate, setSeniorBirthDate] = useState("");
  const [seniorGender, setSeniorGender] = useState("male");
  const [seniorAddress, setSeniorAddress] = useState("");
  const [relationship, setRelationship] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    // 필수 필드 검증
    if (
      !email ||
      !password ||
      !name ||
      !userPhone ||
      !userBirthDate ||
      !seniorName ||
      !seniorPhone ||
      !seniorBirthDate ||
      !relationship
    ) {
      setError("모든 필수 필드를 입력해주세요.");
      setLoading(false);
      return;
    }

    // 비밀번호 길이 확인
    if (password.length < 6) {
      setError("비밀번호는 최소 6자 이상이어야 합니다.");
      setLoading(false);
      return;
    }

    // 생년월일 형식 검증
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(userBirthDate) || !dateRegex.test(seniorBirthDate)) {
      setError("생년월일은 YYYY-MM-DD 형식으로 입력해주세요.");
      setLoading(false);
      return;
    }

    try {
      // Firebase 회원가입
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const firebaseUser = userCredential.user;

      // Firebase ID 토큰 획득
      const idToken = await firebaseUser.getIdToken();

      // FCM 토큰 요청 (백그라운드에서)
      const fcmToken = null;
      const deviceId = `web_${Date.now()}`;

      try {
        // fcmToken = await requestFCMToken();
        console.log("FCM 토큰 기능 준비 중...");
      } catch (fcmError) {
        console.warn("FCM 토큰 획득 실패 (선택사항):", fcmError);
      }

      // 백엔드에 사용자 정보 등록
      const registrationData = {
        firebase_uid: firebaseUser.uid,
        email: firebaseUser.email,
        caregiver_name: name,
        caregiver_phone: userPhone,
        caregiver_birth_date: userBirthDate,
        caregiver_gender: userGender,
        caregiver_address: userAddress,
        senior_name: seniorName,
        senior_phone: seniorPhone,
        senior_birth_date: seniorBirthDate,
        senior_gender: seniorGender,
        senior_address: seniorAddress,
        relationship: relationship,
        fcm_token: fcmToken,
        device_type: "web",
        device_id: deviceId
      };

      // 백엔드 API 호출
      const apiResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/users/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`
        },
        body: JSON.stringify(registrationData)
      });

      if (!apiResponse.ok) {
        const errorData = await apiResponse.json();
        throw new Error(errorData.detail || '백엔드 등록에 실패했습니다.');
      }

      const backendResult = await apiResponse.json();
      console.log("백엔드 등록 성공:", backendResult);

      // 회원가입 성공 시 홈페이지로 이동
      router.push("/");
    } catch (error: any) {
      // Firebase Auth 에러 처리
      if (error.code === "auth/email-already-in-use") {
        setError("이미 사용 중인 이메일입니다.");
      } else if (error.code === "auth/invalid-email") {
        setError("올바른 이메일 형식이 아닙니다.");
      } else if (error.code === "auth/weak-password") {
        setError("비밀번호가 너무 약합니다. 더 강한 비밀번호를 사용해주세요.");
      } else {
        setError("회원가입에 실패했습니다. 다시 시도해주세요.");
      }
      console.error("Registration error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header - 기존 디자인과 동일 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">
                시니어 정신건강 모니터링
              </h1>
              <span className="ml-3 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                회원가입
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                href="/login"
                className="text-sm text-blue-600 hover:underline"
              >
                로그인
              </Link>
              <div className="h-8 w-8 bg-gray-300 rounded-full flex items-center justify-center">
                <span className="text-white text-sm">?</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - 기존 구조와 동일 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 🎯 회원가입 섹션 */}
        <section className="mb-12">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              📝 시니어 헬스케어 가입
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              보호자와 시니어 정보를 입력하여 정신건강 모니터링 서비스를
              시작하세요.
            </p>
          </div>

          {/* 회원가입 폼 카드 */}
          <div className="bg-white rounded-lg shadow-sm p-8">
            <form onSubmit={handleRegister}>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* 👤 보호자 정보 섹션 */}
                <div className="space-y-6">
                  <div className="flex items-center mb-6">
                    <div className="p-2 bg-blue-500 rounded-lg mr-3">
                      <svg
                        className="h-6 w-6 text-white"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                        />
                      </svg>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900">
                      보호자 정보
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        이메일 *
                      </label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="caregiver@example.com"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        비밀번호 *
                      </label>
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="6자 이상"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        이름 *
                      </label>
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="김보호자"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        전화번호 *
                      </label>
                      <input
                        type="tel"
                        value={userPhone}
                        onChange={(e) => setUserPhone(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="010-1234-5678"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        생년월일 *
                      </label>
                      <input
                        type="date"
                        value={userBirthDate}
                        onChange={(e) => setUserBirthDate(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        성별 *
                      </label>
                      <select
                        value={userGender}
                        onChange={(e) => setUserGender(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="male">남성</option>
                        <option value="female">여성</option>
                        <option value="other">기타</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      주소
                    </label>
                    <input
                      type="text"
                      value={userAddress}
                      onChange={(e) => setUserAddress(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="서울시 강남구"
                    />
                  </div>
                </div>

                {/* 👴 시니어 정보 섹션 */}
                <div className="space-y-6">
                  <div className="flex items-center mb-6">
                    <div className="p-2 bg-green-500 rounded-lg mr-3">
                      <svg
                        className="h-6 w-6 text-white"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                        />
                      </svg>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900">
                      시니어 정보
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        시니어 이름 *
                      </label>
                      <input
                        type="text"
                        value={seniorName}
                        onChange={(e) => setSeniorName(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                        placeholder="할머니, 어머니"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        관계 *
                      </label>
                      <input
                        type="text"
                        value={relationship}
                        onChange={(e) => setRelationship(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                        placeholder="할머니, 어머니"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        전화번호 *
                      </label>
                      <input
                        type="tel"
                        value={seniorPhone}
                        onChange={(e) => setSeniorPhone(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                        placeholder="010-1234-5678"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        생년월일 *
                      </label>
                      <input
                        type="date"
                        value={seniorBirthDate}
                        onChange={(e) => setSeniorBirthDate(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        성별 *
                      </label>
                      <select
                        value={seniorGender}
                        onChange={(e) => setSeniorGender(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                      >
                        <option value="male">남성</option>
                        <option value="female">여성</option>
                        <option value="other">기타</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      주소
                    </label>
                    <input
                      type="text"
                      value={seniorAddress}
                      onChange={(e) => setSeniorAddress(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                      placeholder="서울시 강남구"
                    />
                  </div>
                </div>
              </div>

              {error && (
                <div className="mt-6 p-4 bg-red-50 rounded-lg">
                  <p className="text-sm text-red-800">
                    <strong>오류 발생:</strong> {error}
                  </p>
                </div>
              )}

              <div className="mt-8 flex justify-center">
                <button
                  type="submit"
                  disabled={loading}
                  className="px-8 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                >
                  {loading ? "가입 처리 중..." : "가입 완료"}
                </button>
              </div>
            </form>
          </div>
        </section>

        {/* 안내 메시지 */}
        <div className="bg-white rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            서비스 안내
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600">
            <div className="flex items-center">
              <div className="h-2 w-2 bg-blue-500 rounded-full mr-2"></div>
              <span>입력하신 정보는 안전하게 암호화되어 저장됩니다</span>
            </div>
            <div className="flex items-center">
              <div className="h-2 w-2 bg-green-500 rounded-full mr-2"></div>
              <span>시니어 정보는 언제든지 수정할 수 있습니다</span>
            </div>
            <div className="flex items-center">
              <div className="h-2 w-2 bg-purple-500 rounded-full mr-2"></div>
              <span>가입 후 즉시 모니터링 서비스를 이용하실 수 있습니다</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
