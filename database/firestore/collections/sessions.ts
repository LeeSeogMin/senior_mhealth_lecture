// database/firestore/collections/sessions.ts
// 실시간 음성 세션 관리 스키마

import { BaseDocument, FirestoreTimestamp } from './index';

export interface VoiceSession extends BaseDocument {
  // 관계 식별자
  seniorId: string;
  caregiverId: string;
  
  // 세션 메타데이터
  type: SessionType;
  status: SessionStatus;
  priority: SessionPriority;
  
  // 오디오 파일 정보
  audioFile: AudioFileData;
  
  // 실시간 모니터링 데이터
  realTimeData: RealTimeMetrics;
  
  // 기술적 메타데이터
  metadata: SessionMetadata;
  
  // 처리 상태 추적
  processingStatus: ProcessingStatus;
  
  // 동기화 상태
  syncStatus: SyncStatus;
}

export type SessionType = 
  | 'voice_call'
  | 'emergency'
  | 'routine_check'
  | 'ai_analysis'
  | 'health_monitoring';

export type SessionStatus = 
  | 'active'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type SessionPriority = 
  | 'low'
  | 'normal'
  | 'high'
  | 'critical'
  | 'emergency';

export interface AudioFileData {
  bucket: string;
  path: string;
  filename: string;
  size: number;
  contentType: string;
  duration?: number; // seconds
  quality: AudioQuality;
  uploadedAt: FirestoreTimestamp;
  checksum?: string;
}

export type AudioQuality = 
  | 'excellent'
  | 'good'
  | 'acceptable'
  | 'poor'
  | 'unusable';

export interface RealTimeMetrics {
  // 생체 신호 (옵셔널, 디바이스 연동 시)
  heartRate?: number;
  bloodPressure?: {
    systolic: number;
    diastolic: number;
  };
  
  // 음성 분석 실시간 지표
  emotionScore?: number; // 0-100
  stressLevel?: number; // 0-100
  voiceQuality: VoiceQuality;
  backgroundNoise: NoiseLevel;
  
  // 즉시 위험 신호
  emergencyFlags: EmergencyFlag[];
  
  // 측정 시점
  measurementTime: FirestoreTimestamp;
}

export type VoiceQuality = 
  | 'clear'
  | 'slightly_unclear'
  | 'unclear'
  | 'very_unclear'
  | 'background_noise';

export type NoiseLevel = 
  | 'silent'
  | 'quiet'
  | 'moderate'
  | 'loud'
  | 'very_loud';

export interface EmergencyFlag {
  type: EmergencyType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number; // 0-1
  detectedAt: FirestoreTimestamp;
  description: string;
}

export type EmergencyType = 
  | 'health_emergency'
  | 'fall_detected'
  | 'distress_call'
  | 'medication_alert'
  | 'cognitive_concern';

export interface SessionMetadata {
  deviceType: string;
  appVersion: string;
  osVersion: string;
  networkQuality: NetworkQuality;
  location?: {
    latitude: number;
    longitude: number;
    accuracy: number;
  };
  timezone: string;
  language: string;
}

export type NetworkQuality = 
  | 'excellent'
  | 'good'
  | 'fair'
  | 'poor'
  | 'offline';

export interface ProcessingStatus {
  transcriptionComplete: boolean;
  emotionAnalysisComplete: boolean;
  healthAssessmentComplete: boolean;
  riskAnalysisComplete: boolean;
  processingStartedAt?: FirestoreTimestamp;
  processingCompletedAt?: FirestoreTimestamp;
  processingErrors: ProcessingError[];
}

export interface ProcessingError {
  stage: ProcessingStage;
  errorType: string;
  message: string;
  timestamp: FirestoreTimestamp;
  retryCount: number;
}

export type ProcessingStage = 
  | 'upload'
  | 'transcription'
  | 'emotion_analysis'
  | 'health_assessment'
  | 'risk_analysis'
  | 'notification';

export interface SyncStatus {
  cloudSqlSynced: boolean;
  bigquerySynced: boolean;
  lastSyncAt?: FirestoreTimestamp;
  syncErrors: string[];
}

// 세션 생성을 위한 입력 타입
export interface CreateSessionInput {
  seniorId: string;
  caregiverId: string;
  type: SessionType;
  audioFile: Omit<AudioFileData, 'uploadedAt'>;
  metadata: SessionMetadata;
  priority?: SessionPriority;
}

// 세션 업데이트를 위한 입력 타입
export interface UpdateSessionInput {
  status?: SessionStatus;
  realTimeData?: Partial<RealTimeMetrics>;
  processingStatus?: Partial<ProcessingStatus>;
  syncStatus?: Partial<SyncStatus>;
}

// 쿼리 필터 타입
export interface SessionQueryFilter {
  seniorId?: string;
  caregiverId?: string;
  status?: SessionStatus | SessionStatus[];
  type?: SessionType | SessionType[];
  priority?: SessionPriority | SessionPriority[];
  dateRange?: {
    start: FirestoreTimestamp;
    end: FirestoreTimestamp;
  };
  hasEmergencyFlags?: boolean;
}

// 세션 통계 타입
export interface SessionStats {
  totalSessions: number;
  activeSessions: number;
  completedSessions: number;
  failedSessions: number;
  averageProcessingTime: number; // milliseconds
  emergencyCount: number;
  qualityDistribution: Record<AudioQuality, number>;
}