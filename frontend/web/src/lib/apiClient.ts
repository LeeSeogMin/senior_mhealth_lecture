import { getAuth } from 'firebase/auth';
import { initializeFirebase } from './firebase';
import { firestoreService } from './firestoreService';

// API 응답 타입
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// 시니어 타입 (백엔드와 일치)
export interface Senior {
  id?: string;  // seniorId에서 id로 변경
  name: string;
  birthDate: string; // YYYY-MM-DD
  gender: "male" | "female" | "other";
  contactPhone?: string;
  address?: string;
  emergencyContact?: {
    name: string;
    relationship: string;
    phone: string;
  };
  medicalInfo?: {
    conditions?: string[];
    medications?: string[];
    allergies?: string[];
    bloodType?: string;
    notes?: string;
  };
  caregivers: string[]; // 보호자 사용자 ID 목록
  createdAt: string;
  updatedAt: string;
  active: boolean;
  profileImageUrl?: string;
  baselineEstablished?: boolean;
  languagePreference?: string;
  accessibilityNeeds?: string[];
  // 웹 앱에서 사용하는 추가 필드들
  age?: number; // birthDate에서 계산
  phoneNumber?: string; // contactPhone과 동일
  lastCallAt?: string | null;
  totalCalls?: number;
  analysisCount?: number;
  recentScores?: {
    depression?: number;
    cognitive?: number;
  } | null;
}

// 통화 타입 (통합 스키마)
export interface Call {
  // 식별자
  callId: string;
  userId: string;  // caregiverId 대신 userId 사용
  seniorId: string;
  
  // 파일 정보
  fileName: string;
  storagePath: string;
  downloadUrl?: string;
  fileSize: number;
  duration: number;
  mimeType: string;
  
  // 상태 정보
  status: 'uploaded' | 'processing' | 'completed' | 'error';
  hasAnalysis: boolean;
  analysisCompletedAt?: Date | null;
  
  // 타임스탬프
  createdAt: Date;
  updatedAt: Date;
  recordedAt: Date;
  
  // 메타데이터
  metadata?: {
    source: 'mobile' | 'web' | 'api';
    version?: string;
    deviceInfo?: any;
  };
  
  // 분석 결과 (선택적)
  analysis?: {
    summary: string;
    score: number;
    recommendations: string[];
  };
}

// 분석 결과 타입
export interface Analysis {
  analysisId: string;
  callId: string;
  result: any & {
    transcription: {
      text: string;
      confidence: number;
    };
    mentalHealthAnalysis: {
      depression: {
        score: number;
        riskLevel: string;
        indicators?: string[];
      };
      cognitive: {
        score: number;
        riskLevel: string;
      };
    };
    voicePatterns: {
      energy: number;
      pitch_variation: number;
    };
    summary: string;
    recommendations: string[];
  };
  metadata: {
    processingTime: number;
    confidence: number;
    version: string;
  };
  createdAt?: Date;
  recordedAt?: Date;
}

// 분석 해석 결과 타입
export interface AnalysisInterpretation {
  [key: string]: any; // Allow additional properties
  overallAssessment: string;
  detailedAnalysis: {
    mentalHealth: {
      depression: string;
      cognitive: string;
      anxiety: string;
    };
    voicePatterns: string;
    conversationContent: string;
  };
  sincnetAnalysis?: {
    depression?: {
      score: number;
      level: string;
      confidence: number;
    };
    insomnia?: {
      score: number;
      level: string;
      confidence: number;
    };
    anxiety?: {
      score: number;
      level: string;
      confidence: number;
    };
    cognitive?: {
      score: number;
      level: string;
      confidence: number;
    };
    overall?: {
      risk_score: number;
      risk_level: string;
      confidence: number;
    };
  };
  timeSeriesAnalysis?: {
    summary: string;
    trends: {
      depression: number;
      cognitive: number;
      anxiety: number;
    };
    dataPoints: number;
  };
  recommendedActions: string[];
  alertLevel?: "정상" | "보통" | "높음";
  summary?: string;
  generatedAt?: string;
  confidence: number;
}

class ApiClient {
  private baseUrl: string;
  
    constructor() {
    // 환경변수에서 API 베이스 URL 가져오기 (올바른 방법)
    // 사용자 API URL 사용 (deploy-web2.md 참조)
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://senior-mhealth-api-1054806937473.asia-northeast3.run.app';
    this.baseUrl = baseUrl;

    // 개발 환경에서 API URL 확인
    if (process.env.NODE_ENV === 'development') {
      console.log('API Base URL:', this.baseUrl);
      console.log('Environment Variable:', process.env.NEXT_PUBLIC_API_BASE_URL);
    }
    
    // Firebase 초기화
    try {
      initializeFirebase();
    } catch (error) {
      console.error('Firebase 초기화 실패:', error);
    }
  }
  
  // 인증 토큰 얻기
  private async getAuthToken(): Promise<string> {
    try {
      const auth = getAuth();
      
      // Firebase Auth 초기화 완료까지 대기 (FCM → 웹 이동 시 필요)
      let user = auth.currentUser;
      
      // 사용자가 없으면 최대 5초까지 대기
      if (!user) {
        console.log('사용자 인증 상태 대기 중...');
        
        for (let i = 0; i < 10; i++) { // 0.5초씩 10번 = 5초
          await new Promise(resolve => setTimeout(resolve, 500));
          user = auth.currentUser;
          
          if (user) {
            console.log('사용자 인증 확인됨:', user.email);
            break;
          }
        }
      }
      
      if (!user) {
        throw new Error('사용자가 로그인되어 있지 않습니다.');
      }
      
      return await user.getIdToken();
    } catch (error) {
      console.error('인증 토큰 획득 실패:', error);
      throw error;
    }
  }
  
  // API 호출 함수
  private async fetchApi<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const token = await this.getAuthToken();
      const url = `${this.baseUrl}${endpoint}`;
      
      console.log('API 요청:', url); // 디버깅용
      
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers,
      };
      
      const response = await fetch(url, {
        ...options,
        headers,
        // CORS 및 네트워크 오류 방지
        mode: 'cors',
        credentials: 'omit',
      });
      
      // 응답 상태 체크
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`API 오류 (${response.status}):`, errorText);
        
        return {
          success: false,
          error: `서버 오류 (${response.status}): ${errorText || response.statusText}`
        };
      }
      
      const data = await response.json();
      
      return {
        success: true,
        data: data.data || data,
        message: data.message
      };
      
    } catch (error) {
      console.error('API 요청 에러:', error);
      
      // 네트워크 오류 처리
      if (error instanceof TypeError && error.message.includes('fetch')) {
        return {
          success: false,
          error: '네트워크 연결을 확인해주세요.'
        };
      }
      
      return {
        success: false,
        error: error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'
      };
    }
  }
  
  // GET 요청
  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.fetchApi<T>(endpoint, { method: 'GET' });
  }
  
  // POST 요청
  async post<T>(endpoint: string, body: any): Promise<ApiResponse<T>> {
    return this.fetchApi<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }
  
  // PUT 요청
  async put<T>(endpoint: string, body: any): Promise<ApiResponse<T>> {
    return this.fetchApi<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }
  
  // DELETE 요청
  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.fetchApi<T>(endpoint, { method: 'DELETE' });
  }
  
  // 파일 업로드
  async uploadFile<T>(endpoint: string, file: File, formData: Record<string, string>): Promise<ApiResponse<T>> {
    try {
      const token = await this.getAuthToken();
      const url = `${this.baseUrl}${endpoint}`;
      
      const form = new FormData();
      form.append('file', file);
      
      // 추가 폼 데이터 추가
      Object.entries(formData).forEach(([key, value]) => {
        form.append(key, value);
      });
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: form,
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || '파일 업로드 실패');
      }
      
      return data;
    } catch (error) {
      console.error('파일 업로드 에러:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '알 수 없는 에러',
      };
    }
  }
  
  // API 메소드들

  // 사용자 관련 API
  async registerUser(userData: {
    email: string;
    name: string;
    phone: string;
    role?: string;
    fcm_token?: string;
  }): Promise<ApiResponse<any>> {
    return this.post<any>('/api/v1/users/register', {
      ...userData,
      role: userData.role || 'caregiver',
      device_type: 'web'
    });
  }

  async getUserProfile(): Promise<ApiResponse<{
    user_id: string;
    email: string;
    name: string;
    phone: string;
    role: string;
    created_at: string;
    updated_at: string;
  }>> {
    return this.get<any>('/api/v1/users/profile');
  }

  async updateUserProfile(profileData: {
    name?: string;
    phone?: string;
  }): Promise<ApiResponse<any>> {
    return this.put<any>('/api/v1/users/profile', profileData);
  }

  // 시니어 관련 API
  async getSeniors(): Promise<ApiResponse<{ seniors: Senior[]; total: number }>> {
    const auth = getAuth();
    const user = auth.currentUser;
    if (!user) {
      return {
        success: false,
        error: '사용자가 로그인되어 있지 않습니다.'
      };
    }
    return this.get<{ seniors: Senior[]; total: number }>(`/api/v1/users/${user.uid}/seniors`);
  }
  
  async getSeniorDetail(seniorId: string): Promise<ApiResponse<Senior>> {
    return this.get<Senior>(`/api/v1/seniors/${seniorId}`);
  }
  
  async createSenior(senior: { name: string; birthDate: string; gender: "male" | "female" | "other"; contactPhone?: string; address?: string; emergencyContact?: any; medicalInfo?: any; caregivers: string[] }): Promise<ApiResponse<Senior>> {
    const auth = getAuth();
    const user = auth.currentUser;
    if (!user) {
      return {
        success: false,
        error: '사용자가 로그인되어 있지 않습니다.'
      };
    }
    return this.post<Senior>(`/api/v1/users/${user.uid}/seniors`, senior);
  }
  
  async updateSenior(seniorId: string, senior: Partial<Senior>): Promise<ApiResponse<Senior>> {
    return this.put<Senior>(`/api/v1/seniors/${seniorId}`, senior);
  }
  
  async deleteSenior(seniorId: string): Promise<ApiResponse<void>> {
    return this.delete<void>(`/api/v1/seniors/${seniorId}`);
  }
  
  // 통화 관련 API
  async getCallsByseniorId(seniorId: string): Promise<ApiResponse<Call[]>> {
    return this.get<Call[]>(`/api/v1/seniors/${seniorId}/calls`);
  }
  
  async getCallDetail(callId: string): Promise<ApiResponse<Call>> {
    return this.get<Call>(`/api/v1/calls/detail/${callId}`);
  }
  
  async uploadCall(seniorId: string, file: File, duration: number): Promise<ApiResponse<{ callId: string; uploadUrl: string }>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('duration', duration.toString());
    formData.append('clientType', 'web');

    return this.post<{ callId: string; uploadUrl: string }>(`/api/v1/seniors/${seniorId}/calls`, formData);
  }
  
  // 분석 관련 API
  async getAnalysisByCallId(callId: string): Promise<ApiResponse<Analysis>> {
    return this.get<Analysis>(`/api/v1/analyses/call/${callId}`);
  }

  async getAnalysisDetail(analysisId: string): Promise<ApiResponse<Analysis>> {
    return this.get<Analysis>(`/api/v1/analyses/${analysisId}`);
  }

  // 음성 분석 직접 요청 API (Backend API와 통일)
  async requestVoiceAnalysis(audioFile: File, seniorId: string): Promise<ApiResponse<{
    analysis_id: string;
    status: string;
    message: string;
  }>> {
    try {
      const token = await this.getAuthToken();
      const url = `${this.baseUrl}/api/v1/analysis/voice`;

      console.log('🎤 음성 분석 직접 요청:', { url, seniorId });

      const formData = new FormData();
      formData.append('audio_file', audioFile);
      formData.append('senior_id', seniorId);

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`음성 분석 API 오류 (${response.status}):`, errorText);

        return {
          success: false,
          error: `서버 오류 (${response.status}): ${errorText || response.statusText}`
        };
      }

      const data = await response.json();

      if (data.success) {
        console.log('✅ 음성 분석 요청 성공:', data.data);
        return {
          success: true,
          data: data.data,
          message: data.message
        };
      } else {
        return {
          success: false,
          error: data.error || '음성 분석 요청 실패'
        };
      }

    } catch (error) {
      console.error('❌ 음성 분석 요청 에러:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '음성 분석 요청 실패',
      };
    }
  }

  // 분석 결과 폴링 (분석 완료까지 대기)
  async pollAnalysisResult(analysisId: string, maxAttempts: number = 30): Promise<ApiResponse<Analysis>> {
    console.log('⏳ 분석 결과 폴링 시작:', analysisId);

    for (let i = 0; i < maxAttempts; i++) {
      const result = await this.getAnalysisDetail(analysisId);

      if (result.success && result.data) {
        const status = (result.data as any).status;

        if (status === 'completed') {
          console.log('✅ 분석 완료:', result.data);
          return result;
        } else if (status === 'error' || status === 'failed') {
          console.error('❌ 분석 실패:', result.data);
          return {
            success: false,
            error: '분석 처리 중 오류가 발생했습니다.'
          };
        }
      }

      // 3초 대기 후 재시도
      await new Promise(resolve => setTimeout(resolve, 3000));
    }

    return {
      success: false,
      error: '분석 시간 초과 (최대 90초)'
    };
  }

  // 분석 해석 관련 API
  async generateAnalysisInterpretation(callId: string, seniorId: string): Promise<ApiResponse<AnalysisInterpretation>> {
    console.log('🧠 분석 해석 생성 요청:', { callId, seniorId });
    return this.post<AnalysisInterpretation>(`/api/v1/analyses/${callId}/interpretation/${seniorId}`, {});
  }

  async getAnalysisInterpretation(callId: string): Promise<ApiResponse<AnalysisInterpretation>> {
    console.log('🔍 분석 해석 조회 요청:', { callId });
    return this.get<AnalysisInterpretation>(`/api/v1/analyses/${callId}/interpretation`);
  }

  // 공개 분석 결과 조회 (인증 없음)
  async getPublicAnalysis(callId: string): Promise<ApiResponse<any>> {
    try {
      console.log('🌐 공개 분석 결과 조회:', callId);
      
      // 인증 없이 직접 fetch 사용
      const response = await fetch(`${this.baseUrl}/api/v1/calls/public/analysis/${callId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success) {
        console.log('✅ 공개 분석 결과 조회 성공');
        return {
          success: true,
          data: data.data,
        };
      } else {
        throw new Error(data.message || '공개 분석 결과 조회 실패');
      }
    } catch (error) {
      console.error('❌ 공개 분석 결과 조회 오류:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '알 수 없는 오류',
      };
    }
  }

  // 통합 음성 업로드 및 분석 메서드 (새로운 직접 API 사용)
  async uploadAndAnalyzeAudio(audioFile: File, seniorId: string, useDirectAPI: boolean = true): Promise<ApiResponse<{
    analysisId?: string;
    callId?: string;
    status: string;
    message: string;
  }>> {
    try {
      if (useDirectAPI) {
        // 새로운 직접 분석 API 사용
        console.log('🎯 직접 분석 API 사용');
        const result = await this.requestVoiceAnalysis(audioFile, seniorId);

        if (result.success && result.data) {
          return {
            success: true,
            data: {
              analysisId: result.data.analysis_id,
              status: result.data.status,
              message: result.data.message || '분석 요청이 접수되었습니다.'
            }
          };
        }

        return result as any;
      } else {
        // 기존 통화 업로드 방식 (폴백)
        console.log('📞 기존 통화 업로드 방식 사용');
        const duration = 0; // 실제 오디오 파일에서 추출 필요
        const uploadResult = await this.uploadCall(seniorId, audioFile, duration);

        if (uploadResult.success && uploadResult.data) {
          return {
            success: true,
            data: {
              callId: uploadResult.data.callId,
              status: 'uploaded',
              message: '파일이 업로드되었습니다. 분석이 자동으로 시작됩니다.'
            }
          };
        }

        return uploadResult as any;
      }
    } catch (error) {
      console.error('❌ 음성 업로드/분석 에러:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '업로드 실패',
      };
    }
  }

  // 통화 및 분석 데이터 통합 조회 (API 실패 시 Firestore 직접 조회)
  async getCallsWithAnalyses(): Promise<ApiResponse<{ calls: Call[]; analyses: any[] }>> {
    try {
      console.log('🔍 ApiClient: 통화 및 분석 데이터 조회 시작...');

      // API 대신 Firestore 직접 조회
      console.log('🔥 ApiClient: Firestore 직접 조회 시작...');
      const firestoreData = await firestoreService.getCallsWithAnalyses();

      if (firestoreData.calls.length > 0 || firestoreData.analyses.length > 0) {
        console.log('✅ Firestore 데이터 조회 성공:', {
          totalCalls: firestoreData.calls.length,
          analysesCount: firestoreData.analyses.length,
        });

        return {
          success: true,
          data: firestoreData,
        };
      }

      console.warn('⚠️ Firestore에서도 데이터를 찾을 수 없음');
      return {
        success: true,
        data: { calls: [], analyses: [] }
      };

    } catch (error) {
      console.error('❌ getCallsWithAnalyses 에러:', error);
      // 오류 시에도 빈 데이터를 반환하여 UI가 정상 작동하도록 함
      console.warn('⚠️ 오류로 인해 빈 데이터 반환');
      return {
        success: true,
        data: { calls: [], analyses: [] }
      };
    }
  }
}

// 싱글톤 인스턴스 생성
const apiClient = new ApiClient();

export default apiClient;
