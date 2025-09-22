// database/firestore/collections/notifications.ts
// 실시간 알림 시스템 스키마

import { BaseDocument, FirestoreTimestamp } from './index';

export interface NotificationData extends BaseDocument {
  // 수신자 정보
  userId: string; // 수신자 ID
  userType: UserType; // 수신자 타입
  
  // 관련 정보
  seniorId?: string; // 관련 시니어 (있는 경우)
  sessionId?: string; // 관련 세션 (있는 경우)
  
  // 알림 내용
  type: NotificationType;
  title: string;
  message: string;
  priority: NotificationPriority;
  
  // 상태 관리
  readStatus: boolean;
  deliveryStatus: DeliveryStatus;
  actionRequired: boolean;
  
  // 만료 및 스케줄링
  expiresAt?: FirestoreTimestamp;
  scheduledFor?: FirestoreTimestamp;
  
  // 메타데이터
  metadata: NotificationMetadata;
  
  // 액션 정보
  actionData?: ActionData;
  
  // 전달 채널
  channels: DeliveryChannel[];
}

export type UserType = 
  | 'caregiver'
  | 'medical_professional'
  | 'senior'
  | 'admin'
  | 'system';

export type NotificationType = 
  | 'medication_reminder'
  | 'health_alert'
  | 'emergency_alert'
  | 'analysis_complete'
  | 'appointment_reminder'
  | 'system_notification'
  | 'security_alert'
  | 'data_sync_status'
  | 'device_status'
  | 'routine_check';

export type NotificationPriority = 
  | 'low'
  | 'normal'
  | 'high'
  | 'critical'
  | 'emergency';

export type DeliveryStatus = 
  | 'pending'
  | 'sent'
  | 'delivered'
  | 'read'
  | 'failed'
  | 'expired';

export interface NotificationMetadata {
  sourceModule: SourceModule;
  correlationId?: string; // 관련 이벤트/세션 ID
  actionUrl?: string; // 액션 수행 URL
  category: NotificationCategory;
  tags: string[];
  locale: string;
  timezone: string;
  
  // 전달 추적
  sentAt?: FirestoreTimestamp;
  deliveredAt?: FirestoreTimestamp;
  readAt?: FirestoreTimestamp;
  
  // 재시도 정보
  retryCount: number;
  maxRetries: number;
}

export type SourceModule = 
  | 'ai_analysis'
  | 'health_monitoring'
  | 'medication_system'
  | 'appointment_system'
  | 'security_system'
  | 'device_monitoring'
  | 'data_pipeline'
  | 'user_management'
  | 'system';

export type NotificationCategory = 
  | 'health'
  | 'safety'
  | 'medication'
  | 'appointment'
  | 'system'
  | 'security'
  | 'social'
  | 'educational';

export interface ActionData {
  actionType: ActionType;
  actionLabel: string;
  actionUrl?: string;
  actionPayload?: Record<string, any>;
  requiresAuth: boolean;
  expiresAt?: FirestoreTimestamp;
}

export type ActionType = 
  | 'view_details'
  | 'acknowledge'
  | 'call_emergency'
  | 'schedule_appointment'
  | 'update_medication'
  | 'review_analysis'
  | 'contact_caregiver'
  | 'sync_data'
  | 'update_settings';

export type DeliveryChannel = 
  | 'push_notification'
  | 'in_app'
  | 'email'
  | 'sms'
  | 'phone_call'
  | 'web_notification';

// 알림 생성을 위한 입력 타입
export interface CreateNotificationInput {
  userId: string;
  userType: UserType;
  seniorId?: string;
  sessionId?: string;
  type: NotificationType;
  title: string;
  message: string;
  priority: NotificationPriority;
  actionRequired?: boolean;
  expiresAt?: FirestoreTimestamp;
  scheduledFor?: FirestoreTimestamp;
  metadata: Omit<NotificationMetadata, 'sentAt' | 'deliveredAt' | 'readAt' | 'retryCount'>;
  actionData?: ActionData;
  channels: DeliveryChannel[];
}

// 알림 업데이트를 위한 입력 타입
export interface UpdateNotificationInput {
  readStatus?: boolean;
  deliveryStatus?: DeliveryStatus;
  actionRequired?: boolean;
  metadata?: Partial<NotificationMetadata>;
}

// 알림 쿼리 필터 타입
export interface NotificationQueryFilter {
  userId?: string;
  userType?: UserType | UserType[];
  seniorId?: string;
  type?: NotificationType | NotificationType[];
  priority?: NotificationPriority | NotificationPriority[];
  readStatus?: boolean;
  actionRequired?: boolean;
  category?: NotificationCategory | NotificationCategory[];
  dateRange?: {
    start: FirestoreTimestamp;
    end: FirestoreTimestamp;
  };
  deliveryStatus?: DeliveryStatus | DeliveryStatus[];
}

// 알림 배치 처리 타입
export interface NotificationBatch {
  notifications: CreateNotificationInput[];
  batchId: string;
  processingStatus: BatchProcessingStatus;
  createdAt: FirestoreTimestamp;
  processedAt?: FirestoreTimestamp;
  errors: BatchError[];
}

export type BatchProcessingStatus = 
  | 'pending'
  | 'processing'
  | 'completed'
  | 'partially_failed'
  | 'failed';

export interface BatchError {
  notificationIndex: number;
  errorType: string;
  message: string;
  timestamp: FirestoreTimestamp;
}

// 알림 통계 타입
export interface NotificationStats {
  totalSent: number;
  totalDelivered: number;
  totalRead: number;
  totalFailed: number;
  deliveryRate: number; // 0-1
  readRate: number; // 0-1
  averageDeliveryTime: number; // milliseconds
  priorityDistribution: Record<NotificationPriority, number>;
  channelPerformance: Record<DeliveryChannel, {
    sent: number;
    delivered: number;
    failed: number;
    averageDeliveryTime: number;
  }>;
}

// 알림 템플릿 타입
export interface NotificationTemplate {
  id: string;
  name: string;
  type: NotificationType;
  category: NotificationCategory;
  priority: NotificationPriority;
  titleTemplate: string;
  messageTemplate: string;
  supportedChannels: DeliveryChannel[];
  defaultChannel: DeliveryChannel;
  variables: TemplateVariable[];
  localization: Record<string, {
    title: string;
    message: string;
  }>;
}

export interface TemplateVariable {
  name: string;
  type: 'string' | 'number' | 'date' | 'boolean';
  required: boolean;
  description: string;
  defaultValue?: any;
}