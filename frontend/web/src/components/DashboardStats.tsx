'use client';

import { useState, useMemo } from 'react';
import { useApiData } from '../hooks/useApiData';
import { useNotifications } from '../contexts/NotificationContext';
import { calculateOverallStats, getRiskLevel } from '../utils/chartDataTransformers';
import { formatDate } from '../utils/dateHelpers';
import LoadingSpinner from './LoadingSpinner';

interface DashboardStatsProps {
  className?: string;
}

export default function DashboardStats({ className = '' }: DashboardStatsProps) {
  const { analyses, seniors, isLoading, refreshData } = useApiData();
  const { notifications } = useNotifications();
  const [selectedPeriod, setSelectedPeriod] = useState<'all' | 'week' | 'month'>('all');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // 필터링된 분석 데이터
  const filteredAnalyses = useMemo(() => {
    if (!analyses.length) return [];
    
    const now = new Date();
    const filterDate = new Date();
    
    switch (selectedPeriod) {
      case 'week':
        filterDate.setDate(now.getDate() - 7);
        break;
      case 'month':
        filterDate.setMonth(now.getMonth() - 1);
        break;
      case 'all':
      default:
        return analyses;
    }
    
    return analyses.filter(analysis => 
      analysis.recordedAt && new Date(analysis.recordedAt) >= filterDate
    );
  }, [analyses, selectedPeriod]);

  // 통계 계산
  const stats = useMemo(() => {
    const overallStats = calculateOverallStats(filteredAnalyses);
    
    // 평균 점수 계산
    const averageScores = filteredAnalyses.reduce((acc, analysis) => {
      const mentalHealth = analysis.result?.mentalHealthAnalysis;
      if (mentalHealth) {
        const mentalHealthAny = mentalHealth as any;
        const depression = mentalHealthAny.depression?.score || 0;
        const cognitive = mentalHealthAny.cognitive?.score || 0;
        const anxiety = mentalHealthAny.anxiety?.score || 0;
        acc.depression += depression;
        acc.cognitive += cognitive;
        acc.anxiety += anxiety;
        acc.count++;
      }
      return acc;
    }, { depression: 0, cognitive: 0, anxiety: 0, count: 0 });

    const avgDepression = averageScores.count > 0 ? averageScores.depression / averageScores.count : 0;
    const avgCognitive = averageScores.count > 0 ? averageScores.cognitive / averageScores.count : 0;
    const avgAnxiety = averageScores.count > 0 ? averageScores.anxiety / averageScores.count : 0;

    return {
      ...overallStats,
      totalAnalyses: filteredAnalyses.length,
      averageScores: {
        depression: Math.round(avgDepression),
        cognitive: Math.round(avgCognitive),
        anxiety: Math.round(avgAnxiety)
      },
      totalSeniors: seniors.length
    };
  }, [filteredAnalyses, seniors]);

  // 최근 알림
  const recentNotifications = useMemo(() => {
    return notifications
      .filter(n => !n.read)
      .slice(0, 5)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [notifications]);

  // 데이터 새로고침
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await refreshData();
    } finally {
      setIsRefreshing(false);
    }
  };

  if (isLoading) {
    return (
      <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
        <div className="h-64 flex items-center justify-center">
          <LoadingSpinner 
            type="dots" 
            message="통계를 불러오는 중..." 
            size="lg"
          />
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">대시보드 통계</h2>
        <div className="flex items-center space-x-4">
          {/* 기간 필터 */}
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value as any)}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">전체 기간</option>
            <option value="week">최근 7일</option>
            <option value="month">최근 1개월</option>
          </select>
          
          {/* 새로고침 버튼 */}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="px-3 py-1 bg-blue-500 text-white rounded-md text-sm hover:bg-blue-600 disabled:opacity-50 flex items-center space-x-1"
          >
            {isRefreshing ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>새로고침 중...</span>
              </>
            ) : (
              <>
                <span>🔄</span>
                <span>새로고침</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 요약 통계 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-600">총 시니어</p>
              <p className="text-2xl font-bold text-blue-900">{stats.totalSeniors}</p>
            </div>
            <div className="text-3xl">👥</div>
          </div>
        </div>

        <div className="bg-green-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-600">정상 상태</p>
              <p className="text-2xl font-bold text-green-900">{stats.normalCount}</p>
            </div>
            <div className="text-3xl">✅</div>
          </div>
        </div>

        <div className="bg-yellow-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-yellow-600">주의 필요</p>
              <p className="text-2xl font-bold text-yellow-900">{stats.warningCount}</p>
            </div>
            <div className="text-3xl">⚠️</div>
          </div>
        </div>

        <div className="bg-red-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-red-600">위험 상태</p>
              <p className="text-2xl font-bold text-red-900">{stats.criticalCount}</p>
            </div>
            <div className="text-3xl">🚨</div>
          </div>
        </div>
      </div>

      {/* 평균 점수 */}
      <div className="mb-6">
        <h3 className="text-lg font-medium text-gray-900 mb-3">평균 점수</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">우울증</span>
              <span className="text-lg font-bold text-gray-900">{stats.averageScores.depression}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full ${
                  stats.averageScores.depression < 30 ? 'bg-green-500' :
                  stats.averageScores.depression < 70 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${stats.averageScores.depression}%` }}
              />
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">인지능력</span>
              <span className="text-lg font-bold text-gray-900">{stats.averageScores.cognitive}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full ${
                  stats.averageScores.cognitive < 30 ? 'bg-green-500' :
                  stats.averageScores.cognitive < 70 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${stats.averageScores.cognitive}%` }}
              />
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">불안</span>
              <span className="text-lg font-bold text-gray-900">{stats.averageScores.anxiety}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className={`h-2 rounded-full ${
                  stats.averageScores.anxiety < 30 ? 'bg-green-500' :
                  stats.averageScores.anxiety < 70 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${stats.averageScores.anxiety}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 최근 알림 */}
      {recentNotifications.length > 0 && (
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-3">최근 알림</h3>
          <div className="space-y-2">
            {recentNotifications.map((notification) => (
              <div
                key={notification.id}
                className={`p-3 rounded-lg border-l-4 ${
                  notification.type === 'danger' ? 'bg-red-50 border-red-400' :
                  notification.type === 'warning' ? 'bg-yellow-50 border-yellow-400' :
                  'bg-blue-50 border-blue-400'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{notification.title}</p>
                    <p className="text-xs text-gray-600 mt-1">{notification.message}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {formatDate(new Date(notification.timestamp))}
                    </p>
                  </div>
                  <div className="text-lg ml-2">
                    {notification.type === 'danger' ? '🚨' : 
                     notification.type === 'warning' ? '⚠️' : 'ℹ️'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 데이터 없음 상태 */}
      {filteredAnalyses.length === 0 && (
        <div className="text-center py-8">
          <div className="text-4xl mb-2">📊</div>
          <p className="text-lg font-medium text-gray-900 mb-2">분석 데이터가 없습니다</p>
          <p className="text-sm text-gray-600">통화 기록을 추가하면 통계를 확인할 수 있습니다</p>
        </div>
      )}
    </div>
  );
} 