// database/firestore/collections/index.ts
// 독립적 데이터 레이어 - Firestore 컬렉션 스키마 정의

export * from './sessions';
export * from './notifications';
export * from './analyses'; 
export * from './users';
export * from './medical-records';

// Common types used across collections
export interface FirestoreTimestamp {
  seconds: number;
  nanoseconds: number;
}

export interface BaseDocument {
  id: string;
  createdAt: FirestoreTimestamp;
  updatedAt: FirestoreTimestamp;
}

export interface AuditTrail {
  userId: string;
  action: string;
  timestamp: FirestoreTimestamp;
  details?: Record<string, any>;
}

// Collection names constants
export const COLLECTIONS = {
  SESSIONS: 'sessions',
  NOTIFICATIONS: 'notifications', 
  ANALYSES: 'analyses',
  USERS: 'users',
  MEDICAL_RECORDS: 'medical_records',
  LIVE_METRICS: 'live_metrics',
  CACHE_LAYERS: 'cache_layers'
} as const;

// Data validation utilities
export const ValidationRules = {
  requiresAuth: (userId?: string) => userId != null,
  isValidSeniorId: (seniorId: string) => /^senior_\w+$/.test(seniorId),
  isValidCaregiverId: (caregiverId: string) => /^caregiver_\w+$/.test(caregiverId),
  isValidMedicalId: (medicalId: string) => /^medical_\w+$/.test(medicalId)
};