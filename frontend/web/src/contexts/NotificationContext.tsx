'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { EnhancedAnalysis } from '../hooks/useApiData';
import { getRiskLevel } from '../utils/chartDataTransformers';

interface Notification {
  id: string;
  type: 'danger' | 'warning' | 'info';
  title: string;
  message: string;
  analysisId?: string;
  seniorName?: string;
  timestamp: Date;
  read: boolean;
}

interface NotificationContextType {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  unreadCount: number;
  checkForAlerts: (analyses: EnhancedAnalysis[]) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const previousAnalysesRef = useRef<Map<string, any>>(new Map());
  const processedAnalysesRef = useRef<Set<string>>(new Set()); // 이미 처리한 분석 ID 추적

  // 알림 추가
  const addNotification = useCallback((notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: Notification = {
      ...notification,
      id: Date.now().toString(),
      timestamp: new Date(),
      read: false
    };

    setNotifications(prev => [newNotification, ...prev]);

    // 브라우저 알림 (사용자 권한이 있는 경우)
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.message,
        icon: '/favicon.ico'
      });
    }
  }, []);

  // 위험 상태 감지 및 알림 생성
  const checkForAlerts = useCallback((analyses: EnhancedAnalysis[]) => {
    // 개발 중에는 알림 비활성화
    if (process.env.NODE_ENV === 'development') {
      return;
    }

    analyses.forEach(analysis => {
      // 이미 처리한 분석인지 확인
      const alertKey = `${analysis.analysisId}_${analysis.recordedAt}`;
      if (processedAnalysesRef.current.has(alertKey)) {
        return; // 이미 처리했으므로 건너뛰기
      }

      const mentalHealth = analysis.result?.mentalHealthAnalysis;
      if (!mentalHealth) return;

      const mentalHealthAny = mentalHealth as any;
      const depression = mentalHealthAny.depression?.score || 0;
      const cognitive = mentalHealthAny.cognitive?.score || 0;
      const anxiety = mentalHealthAny.anxiety?.score || 0;
      const averageScore = (depression + cognitive + anxiety) / 3;
      const currentRiskLevel = getRiskLevel(averageScore);

      // 이전 분석 결과와 비교
      const previousAnalysis = previousAnalysesRef.current.get(analysis.analysisId);
      if (previousAnalysis) {
        const previousRiskLevel = previousAnalysis.riskLevel;

        // 상태가 악화된 경우만 알림 (이미 처리하지 않은 경우)
        if (
          (previousRiskLevel === 'normal' && currentRiskLevel !== 'normal') ||
          (previousRiskLevel === 'warning' && currentRiskLevel === 'critical')
        ) {
          addNotification({
            type: currentRiskLevel === 'critical' ? 'danger' : 'warning',
            title: `상태 변화 감지 - ${analysis.seniorName || '시니어'}`,
            message: `이전: ${previousRiskLevel === 'normal' ? '정상' : '주의'} → 현재: ${currentRiskLevel === 'critical' ? '위험' : '주의'}`,
            analysisId: analysis.analysisId,
            seniorName: analysis.seniorName
          });
          // 알림 생성했으므로 처리됨으로 표시
          processedAnalysesRef.current.add(alertKey);
        }
      } else if (!previousAnalysis && !processedAnalysesRef.current.has(alertKey)) {
        // 첫 번째 분석이고 위험 상태인 경우 (한 번만 알림)
        if (currentRiskLevel === 'critical') {
          addNotification({
            type: 'danger',
            title: `위험 상태 감지 - ${analysis.seniorName || '시니어'}`,
            message: '정신건강 점수가 위험 수준입니다. 즉시 확인이 필요합니다.',
            analysisId: analysis.analysisId,
            seniorName: analysis.seniorName
          });
          processedAnalysesRef.current.add(alertKey);
        } else if (currentRiskLevel === 'warning') {
          addNotification({
            type: 'warning',
            title: `주의 상태 감지 - ${analysis.seniorName || '시니어'}`,
            message: '정신건강 점수가 주의 수준입니다. 모니터링이 필요합니다.',
            analysisId: analysis.analysisId,
            seniorName: analysis.seniorName
          });
          processedAnalysesRef.current.add(alertKey);
        }
      }

      // 현재 분석 결과 저장 (useRef 사용)
      previousAnalysesRef.current.set(analysis.analysisId, {
        riskLevel: currentRiskLevel,
        averageScore,
        timestamp: analysis.recordedAt
      });
    });
  }, [addNotification]);

  // 연속 악화 감지 (비활성화됨 - 중복 알림 방지)
  const checkConsecutiveDeterioration = useCallback((analyses: EnhancedAnalysis[]) => {
    // 현재 비활성화됨 - 중복 알림 문제 해결 필요
    return;

    /*
    const sortedAnalyses = analyses
      .filter(a => a.seniorName)
      .sort((a, b) => {
        const dateA = a.recordedAt ? new Date(a.recordedAt).getTime() : 0;
        const dateB = b.recordedAt ? new Date(b.recordedAt).getTime() : 0;
        return dateB - dateA;
      });

    const seniorGroups = new Map<string, EnhancedAnalysis[]>();

    sortedAnalyses.forEach(analysis => {
      const seniorName = analysis.seniorName!;
      if (!seniorGroups.has(seniorName)) {
        seniorGroups.set(seniorName, []);
      }
      seniorGroups.get(seniorName)!.push(analysis);
    });

    seniorGroups.forEach((seniorAnalyses, seniorName) => {
      if (seniorAnalyses.length < 3) return;

      const recentAnalyses = seniorAnalyses.slice(0, 3);
      const scores = recentAnalyses.map(analysis => {
        const mentalHealth = analysis.result?.mentalHealthAnalysis;
        if (!mentalHealth) return null;

        const mentalHealthAny = mentalHealth as any;
        const depression = mentalHealthAny.depression?.score || 0;
        const cognitive = mentalHealthAny.cognitive?.score || 0;
        const anxiety = mentalHealthAny.anxiety?.score || 0;
        return (depression + cognitive + anxiety) / 3;
      }).filter(score => score !== null);

      if (scores.length >= 3) {
        // 연속 3회 악화 감지
        const isDeteriorating = scores.every((score, index) => {
          if (index === 0) return true;
          return score! > scores[index - 1]!;
        });

        if (isDeteriorating) {
          const alertKey = `consecutive_${seniorName}_${Date.now()}`;
          if (!processedAnalysesRef.current.has(alertKey)) {
            addNotification({
              type: 'danger',
              title: `연속 악화 감지 - ${seniorName}`,
              message: '정신건강 점수가 연속 3회 악화되고 있습니다. 긴급 조치가 필요합니다.',
              analysisId: recentAnalyses[0].analysisId,
              seniorName
            });
            processedAnalysesRef.current.add(alertKey);
          }
        }
      }
    });
    */
  }, [addNotification]);

  // 알림 관리 함수들
  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => 
      prev.map(notification => 
        notification.id === id 
          ? { ...notification, read: true }
          : notification
      )
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => 
      prev.map(notification => ({ ...notification, read: true }))
    );
  }, []);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  // 브라우저 알림 권한 요청
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  const value: NotificationContextType = {
    notifications,
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    unreadCount,
    checkForAlerts
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
} 