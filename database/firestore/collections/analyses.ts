// database/firestore/collections/analyses.ts
// AI 분석 결과 실시간 캐시 스키마

import { BaseDocument, FirestoreTimestamp } from './index';

export interface AnalysisResult extends BaseDocument {
  // 연관 식별자
  sessionId: string;
  seniorId: string;
  caregiverId?: string;
  
  // AI 분석 메타데이터
  aiProvider: AIProvider;
  analysisType: AnalysisType;
  modelVersion: string;
  confidence: number; // 0-1 overall confidence
  
  // 분석 결과
  results: AnalysisResultData;
  
  // 위험 신호 및 알림
  alerts: HealthAlert[];
  recommendations: Recommendation[];
  
  // 처리 메타데이터
  processingMetadata: ProcessingMetadata;
  
  // 동기화 상태
  syncStatus: SyncStatus;
  
  // 품질 지표
  qualityMetrics: QualityMetrics;
}

export type AIProvider = 
  | 'vertex_ai'
  | 'openai'
  | 'azure_cognitive'
  | 'google_cloud_speech'
  | 'custom_model';

export type AnalysisType = 
  | 'voice_emotion'
  | 'health_indicators'
  | 'risk_assessment'
  | 'cognitive_function'
  | 'speech_patterns'
  | 'comprehensive'
  | 'emergency_detection';

export interface AnalysisResultData {
  // 감정 분석
  emotion: EmotionAnalysis;
  
  // 건강 지표
  healthIndicators: HealthIndicators;
  
  // 언어적 특성
  linguisticFeatures: LinguisticFeatures;
  
  // 음성 특성
  voiceFeatures: VoiceFeatures;
  
  // 위험 신호
  riskSignals: RiskSignal[];
  
  // 인지 기능 평가
  cognitiveAssessment?: CognitiveAssessment;
  
  // 종합 점수
  overallScores: OverallScores;
}

export interface EmotionAnalysis {
  primary: PrimaryEmotion;
  confidence: number; // 0-1
  details: Record<EmotionType, number>; // 세부 감정 스코어 0-100
  valence: number; // -1 to 1 (negative to positive)
  arousal: number; // 0-1 (calm to excited)
  trends: EmotionTrend[];
}

export type PrimaryEmotion = 
  | 'positive'
  | 'neutral'
  | 'negative'
  | 'mixed'
  | 'uncertain';

export type EmotionType = 
  | 'happiness'
  | 'sadness'
  | 'anger'
  | 'fear'
  | 'surprise'
  | 'disgust'
  | 'anxiety'
  | 'contentment'
  | 'frustration'
  | 'confusion';

export interface EmotionTrend {
  timeSegment: number; // seconds from start
  emotion: EmotionType;
  intensity: number; // 0-100
}

export interface HealthIndicators {
  stressLevel: number; // 0-100
  depressionRisk: number; // 0-100
  anxietyLevel: number; // 0-100
  cognitiveFunction: number; // 0-100
  energyLevel: number; // 0-100
  socialEngagement: number; // 0-100
  painIndicators: PainIndicators;
  sleepQuality?: SleepQualityIndicators;
}

export interface PainIndicators {
  overallPainLevel: number; // 0-100
  painFrequency: number; // 0-100
  painDescriptors: string[];
  affectedAreas: string[];
}

export interface SleepQualityIndicators {
  sleepQuality: number; // 0-100
  fatigueLevel: number; // 0-100
  sleepDisturbances: string[];
}

export interface LinguisticFeatures {
  speechRate: number; // words per minute
  pauseFrequency: number; // pauses per minute
  pauseDuration: number; // average pause duration in seconds
  vocabularyComplexity: number; // 0-100
  sentenceLength: number; // average words per sentence
  wordFindingDifficulty: number; // 0-100
  repetitivePatterns: number; // 0-100
  keyPhrases: string[];
  topicCoherence: number; // 0-100
}

export interface VoiceFeatures {
  fundamentalFrequency: number; // Hz
  jitter: number; // frequency variation
  shimmer: number; // amplitude variation
  harmonicToNoiseRatio: number;
  voiceQuality: VoiceQualityMetrics;
  speechClarity: number; // 0-100
  volume: VolumeMetrics;
}

export interface VoiceQualityMetrics {
  breathiness: number; // 0-100
  roughness: number; // 0-100
  strain: number; // 0-100
  tremor: number; // 0-100
}

export interface VolumeMetrics {
  averageVolume: number; // dB
  volumeVariation: number; // dB
  whisperSegments: number; // percentage
  loudSegments: number; // percentage
}

export interface RiskSignal {
  type: RiskType;
  severity: RiskSeverity;
  confidence: number; // 0-1
  indicators: string[];
  timeFrame: TimeFrame;
  actionRequired: boolean;
  relatedMetrics: Record<string, number>;
}

export type RiskType = 
  | 'depression'
  | 'anxiety'
  | 'cognitive_decline'
  | 'social_isolation'
  | 'medication_adherence'
  | 'fall_risk'
  | 'emergency_situation'
  | 'pain_management'
  | 'sleep_disorder';

export type RiskSeverity = 
  | 'low'
  | 'medium'
  | 'high'
  | 'critical'
  | 'emergency';

export type TimeFrame = 
  | 'immediate'
  | 'short_term'
  | 'medium_term'
  | 'long_term'
  | 'trend_based';

export interface CognitiveAssessment {
  overallFunction: number; // 0-100
  memoryFunction: number; // 0-100
  attentionSpan: number; // 0-100
  executiveFunction: number; // 0-100
  languageFunction: number; // 0-100
  orientationLevel: number; // 0-100
  declineIndicators: string[];
  preservedFunctions: string[];
}

export interface OverallScores {
  healthScore: number; // 0-100
  wellbeingScore: number; // 0-100
  riskScore: number; // 0-100
  engagementScore: number; // 0-100
  communicationQuality: number; // 0-100
}

export interface HealthAlert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  message: string;
  actionRequired: boolean;
  urgencyLevel: UrgencyLevel;
  recommendedAction: string;
  triggerMetrics: Record<string, number>;
  generatedAt: FirestoreTimestamp;
  expiresAt?: FirestoreTimestamp;
}

export type AlertType = 
  | 'health_concern'
  | 'emergency'
  | 'trend_change'
  | 'medication_alert'
  | 'cognitive_concern'
  | 'emotional_distress'
  | 'social_concern'
  | 'safety_alert';

export type AlertSeverity = 
  | 'info'
  | 'warning'
  | 'critical'
  | 'emergency';

export type UrgencyLevel = 
  | 'low'
  | 'medium'
  | 'high'
  | 'immediate';

export interface Recommendation {
  id: string;
  category: RecommendationCategory;
  priority: RecommendationPriority;
  title: string;
  description: string;
  actionItems: ActionItem[];
  targetAudience: TargetAudience[];
  validUntil?: FirestoreTimestamp;
  relatedMetrics: string[];
}

export type RecommendationCategory = 
  | 'lifestyle'
  | 'medical'
  | 'social'
  | 'cognitive'
  | 'emotional'
  | 'safety'
  | 'medication'
  | 'monitoring';

export type RecommendationPriority = 
  | 'low'
  | 'medium'
  | 'high'
  | 'urgent';

export interface ActionItem {
  description: string;
  responsible: TargetAudience;
  timeline: string;
  resources?: string[];
}

export type TargetAudience = 
  | 'senior'
  | 'caregiver'
  | 'medical_professional'
  | 'family'
  | 'system';

export interface ProcessingMetadata {
  processedAt: FirestoreTimestamp;
  processingTime: number; // milliseconds
  modelVersion: string;
  qualityScore: number; // 0-1
  processingStages: ProcessingStage[];
  computeResources: ComputeResourceUsage;
}

export interface ProcessingStage {
  stage: string;
  startTime: FirestoreTimestamp;
  endTime: FirestoreTimestamp;
  duration: number; // milliseconds
  success: boolean;
  errorMessage?: string;
}

export interface ComputeResourceUsage {
  cpuTime: number; // milliseconds
  memoryUsage: number; // MB
  gpuTime?: number; // milliseconds
  apiCalls: number;
  cost?: number; // USD
}

export interface SyncStatus {
  cloudSqlSynced: boolean;
  bigquerySynced: boolean;
  notificationsSent: boolean;
  lastSyncAt?: FirestoreTimestamp;
  syncErrors: SyncError[];
}

export interface SyncError {
  target: 'cloud_sql' | 'bigquery' | 'notifications';
  errorType: string;
  message: string;
  timestamp: FirestoreTimestamp;
  retryCount: number;
}

export interface QualityMetrics {
  dataCompleteness: number; // 0-1
  analysisConfidence: number; // 0-1
  audioQuality: number; // 0-1
  transcriptionAccuracy: number; // 0-1
  modelReliability: number; // 0-1
  outlierFlags: string[];
}

// 분석 결과 생성을 위한 입력 타입
export interface CreateAnalysisInput {
  sessionId: string;
  seniorId: string;
  caregiverId?: string;
  aiProvider: AIProvider;
  analysisType: AnalysisType;
  modelVersion: string;
  results: AnalysisResultData;
  alerts?: HealthAlert[];
  recommendations?: Recommendation[];
  processingMetadata: ProcessingMetadata;
  qualityMetrics: QualityMetrics;
}

// 분석 결과 쿼리 필터 타입
export interface AnalysisQueryFilter {
  seniorId?: string;
  caregiverId?: string;
  sessionId?: string;
  analysisType?: AnalysisType | AnalysisType[];
  aiProvider?: AIProvider | AIProvider[];
  hasAlerts?: boolean;
  alertSeverity?: AlertSeverity | AlertSeverity[];
  riskLevel?: RiskSeverity | RiskSeverity[];
  dateRange?: {
    start: FirestoreTimestamp;
    end: FirestoreTimestamp;
  };
  confidenceThreshold?: number;
  qualityThreshold?: number;
}

// 분석 통계 타입
export interface AnalysisStats {
  totalAnalyses: number;
  averageConfidence: number;
  averageProcessingTime: number;
  alertDistribution: Record<AlertSeverity, number>;
  riskDistribution: Record<RiskSeverity, number>;
  providerPerformance: Record<AIProvider, {
    count: number;
    averageConfidence: number;
    averageProcessingTime: number;
    successRate: number;
  }>;
  qualityMetrics: {
    averageDataCompleteness: number;
    averageAudioQuality: number;
    averageTranscriptionAccuracy: number;
  };
}