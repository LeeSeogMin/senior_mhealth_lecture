/**
 * Firestore Database Schema - Single Source of Truth Architecture
 * Senior MHealth Project (2025.09.13)
 *
 * 핵심 원칙:
 * 1. 단일 소스 원칙 (Single Source of Truth)
 * 2. 계층적 데이터 구조
 * 3. 세션 중심 데이터 저장
 * 4. 명확한 권한 경계
 */

import { Timestamp } from 'firebase-admin/firestore';

export interface UserProfile {
  email: string;
  name: string;
  role: "caregiver" | "admin";
  phone: string;
  gender: "male" | "female" | "other";
  age: number;
  address: string;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

export interface SeniorProfile {
  name: string;
  phone: string;
  age: number;
  gender: "male" | "female" | "other";
  address: string;
  relationship: string; // "할머니", "어머니", "아버지" 등
  caregivers: string[]; // [userId]
  active: boolean;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

export interface SessionMetadata {
  startTime: FirebaseFirestore.Timestamp;
  endTime?: FirebaseFirestore.Timestamp;
  duration: number; // seconds
  status: "uploading" | "analyzing" | "completed" | "failed";
  audioFileRef: string; // Firebase Storage 경로
  fileName: string;
  fileSize: number; // bytes
}

export interface CoreIndicators {
  DRI: CoreIndicator; // Depression Risk Index
  SDI: CoreIndicator; // Sleep Disorder Index  
  CFL: CoreIndicator; // Cognitive Function Level
  ES: CoreIndicator;  // Emotional Stability
  OV: CoreIndicator;  // Overall Vitality
}

export interface CoreIndicator {
  value: number;      // 0.0 - 1.0
  confidence: number; // 0.0 - 1.0
  status: "low" | "medium" | "high";
  description?: string;
}

export interface VoiceFeatures {
  speechRate: number;        // 발화 속도
  pauseRatio: number;        // 휴지 비율  
  energyLevel: number;       // 에너지 레벨
  pitch: {
    mean: number;
    std: number;
    range: number;
  };
  formants: {
    f1: number;
    f2: number;
    f3: number;
  };
  spectralFeatures: {
    mfcc: number[];
    spectralCentroid: number;
    spectralRolloff: number;
  };
}

export interface TextAnalysis {
  transcription: string;
  sentiment: "positive" | "neutral" | "negative";
  emotions: {
    joy: number;
    sadness: number;
    anger: number;
    fear: number;
    surprise: number;
    disgust: number;
  };
  keywords: string[];
  topics: string[];
  linguisticFeatures: {
    wordCount: number;
    sentenceCount: number;
    avgWordsPerSentence: number;
    complexityScore: number;
  };
}

export interface DeepLearningAnalysis {
  depression: number;    // 0.0 - 1.0
  anxiety: number;       // 0.0 - 1.0
  insomnia: number;      // 0.0 - 1.0
  cognitive: number;     // 0.0 - 1.0
  stress: number;        // 0.0 - 1.0
  modelVersion: string;
  confidence: number;
}

export interface AnalysisResult {
  coreIndicators: CoreIndicators;
  voiceFeatures: VoiceFeatures;
  textAnalysis: TextAnalysis;
  deepLearning: DeepLearningAnalysis;
  summary: string;
  recommendations: string[];
  alertLevel: "low" | "medium" | "high";
  overallRisk: number; // 0.0 - 1.0
  metadata: {
    processingTime: number; // milliseconds
    confidence: number;     // 0.0 - 1.0
    version: string;        // AI 모델 버전
    analyzedAt: Timestamp;
    analysisType: "comprehensive" | "voice-only" | "text-only";
  };
}

// 메인 세션 문서 구조
export interface Session {
  metadata: SessionMetadata;
  analysis?: AnalysisResult; // 분석 완료 후에만 존재
}

// 알림 설정
export interface NotificationSettings {
  email: {
    enabled: boolean;
    threshold: number; // 0.0 - 1.0
  };
  push: {
    enabled: boolean;
    threshold: number;
  };
  sms: {
    enabled: boolean;
    threshold: number;
  };
}

// Firestore 컬렉션 구조
export interface FirestoreSchema {
  users: {
    [userId: string]: {
      profile: UserProfile;
      seniors: {
        [seniorId: string]: {
          profile: SeniorProfile;
          sessions: {
            [sessionId: string]: Session;
          };
        };
      };
      settings: {
        notifications: NotificationSettings;
      };
    };
  };
}

// 유틸리티 타입들
export type SessionStatus = SessionMetadata['status'];
export type AlertLevel = AnalysisResult['alertLevel'];
export type UserRole = UserProfile['role'];
export type Gender = UserProfile['gender'];

// Storage 경로 헬퍼
export const StoragePaths = {
  audioFile: (userId: string, seniorId: string, sessionId: string, fileName: string) =>
    `audio-files/${userId}/${seniorId}/${sessionId}/${fileName}`,
};

// 컬렉션 경로 헬퍼
export const COLLECTION_PATHS = {
  users: 'users',
  userProfile: (userId: string) => `users/${userId}/profile`,
  seniors: (userId: string) => `users/${userId}/seniors`,
  seniorProfile: (userId: string, seniorId: string) => 
    `users/${userId}/seniors/${seniorId}/profile`,
  sessions: (userId: string, seniorId: string) => 
    `users/${userId}/seniors/${seniorId}/sessions`,
  session: (userId: string, seniorId: string, sessionId: string) => 
    `users/${userId}/seniors/${seniorId}/sessions/${sessionId}`,
  settings: (userId: string) => `users/${userId}/settings`,
  notifications: (userId: string) => `users/${userId}/settings/notifications`
} as const;
