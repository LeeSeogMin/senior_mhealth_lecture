'use client';

import { useState, useEffect, useMemo, memo } from 'react';
import { useApiData } from '../hooks/useApiData';
import AdvancedTrendChart from './AdvancedTrendChart';
import { TrendChart } from './TrendChart';
import AdvancedStatusDistribution from './AdvancedStatusDistribution';
import { AnalysisList } from './AnalysisCard';
import LoadingSpinner from './LoadingSpinner';
import { 
  generateTrendData, 
  generateStatusDistributionData,
  calculateOverallStats,
  TrendData,
  StatusDistributionData
} from '../utils/chartDataTransformers';

interface TimeSeriesSectionProps {
  className?: string;
}

type TimeRange = 'week' | 'month' | 'quarter' | 'year' | 'all';

const TimeSeriesSection = memo(function TimeSeriesSection({ 
  className = '' 
}: TimeSeriesSectionProps) {
  const { analyses, isLoading, error } = useApiData();
  const [selectedTimeRange, setSelectedTimeRange] = useState<TimeRange>('month');
  const [showAdvancedCharts, setShowAdvancedCharts] = useState(true);
  const [isClient, setIsClient] = useState(false);

  // 클라이언트 사이드 렌더링
  useEffect(() => {
    setIsClient(true);
  }, []);

  // 기간별 데이터 필터링
  const filteredAnalyses = useMemo(() => {
    if (!analyses.length) return [];
    
    const now = new Date();
    const cutoffDate = new Date();
    
    switch (selectedTimeRange) {
      case 'week':
        cutoffDate.setDate(now.getDate() - 7);
        break;
      case 'month':
        cutoffDate.setMonth(now.getMonth() - 1);
        break;
      case 'quarter':
        cutoffDate.setMonth(now.getMonth() - 3);
        break;
      case 'year':
        cutoffDate.setFullYear(now.getFullYear() - 1);
        break;
      case 'all':
        return analyses;
    }
    
    return analyses.filter(analysis => {
      const analysisDate = new Date(analysis.recordedAt || '');
      return analysisDate >= cutoffDate;
    });
  }, [analyses, selectedTimeRange]);

  // 트렌드 데이터 생성
  const trendData: TrendData[] = useMemo(() => {
    return generateTrendData(filteredAnalyses);
  }, [filteredAnalyses]);

  // 상태 분포 데이터 생성
  const statusDistributionData: StatusDistributionData[] = useMemo(() => {
    return generateStatusDistributionData(filteredAnalyses);
  }, [filteredAnalyses]);

  // 전체 통계 계산
  const overallStats = useMemo(() => {
    return calculateOverallStats(filteredAnalyses);
  }, [filteredAnalyses]);

  // 트렌드 변화량 계산
  const trendChange = useMemo(() => {
    if (trendData.length < 2) return { normal: 0, warning: 0, critical: 0 };
    
    const latest = trendData[trendData.length - 1];
    const previous = trendData[trendData.length - 2];
    
    return {
      normal: latest.normal - previous.normal,
      warning: latest.warning - previous.warning,
      critical: latest.critical - previous.critical
    };
  }, [trendData]);

  // 로딩 상태 처리
  if (isLoading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="text-center py-12">
          <LoadingSpinner 
            type="dots" 
            message="시계열 데이터를 불러오는 중..." 
            size="lg"
          />
        </div>
      </div>
    );
  }

  // 에러 상태 처리
  if (error) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="text-center py-12">
          <div className="text-6xl mb-4">⚠️</div>
          <h3 className="text-xl font-semibold text-red-800 mb-2">데이터 로딩 오류</h3>
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  // 데이터가 없는 경우
  if (analyses.length === 0) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="text-center py-12">
          <div className="text-6xl mb-4">📊</div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">시계열 데이터가 없습니다</h3>
          <p className="text-gray-600">통화 기록을 추가하면 시계열 분석을 확인할 수 있습니다</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 시간 범위 선택 및 컨트롤 */}
      <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <h3 className="text-xl font-semibold text-gray-900">
            ⏰ 시계열 데이터 분석
          </h3>
          
          <div className="flex flex-wrap gap-2">
            {/* 시간 범위 선택 */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              {(['week', 'month', 'quarter', 'year', 'all'] as TimeRange[]).map((range) => (
                <button
                  key={range}
                  onClick={() => setSelectedTimeRange(range)}
                  className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                    selectedTimeRange === range
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {range === 'week' ? '1주' : 
                   range === 'month' ? '1개월' :
                   range === 'quarter' ? '3개월' :
                   range === 'year' ? '1년' : '전체'}
                </button>
              ))}
            </div>

            {/* 고급 차트 토글 */}
            <button
              onClick={() => setShowAdvancedCharts(!showAdvancedCharts)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                showAdvancedCharts
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {showAdvancedCharts ? '기본 보기' : '고급 보기'}
            </button>
          </div>
        </div>

        {/* 전체 통계 요약 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-green-50 rounded-lg p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600 mb-1">
                {overallStats.normalCount}
              </div>
              <div className="text-sm text-green-700 font-medium">정상</div>
              <div className="text-xs text-green-600 mt-1">
                {trendChange.normal > 0 ? '+' : ''}{trendChange.normal}
              </div>
            </div>
          </div>
          <div className="bg-yellow-50 rounded-lg p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600 mb-1">
                {overallStats.warningCount}
              </div>
              <div className="text-sm text-yellow-700 font-medium">주의</div>
              <div className="text-xs text-yellow-600 mt-1">
                {trendChange.warning > 0 ? '+' : ''}{trendChange.warning}
              </div>
            </div>
          </div>
          <div className="bg-red-50 rounded-lg p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600 mb-1">
                {overallStats.criticalCount}
              </div>
              <div className="text-sm text-red-700 font-medium">위험</div>
              <div className="text-xs text-red-600 mt-1">
                {trendChange.critical > 0 ? '+' : ''}{trendChange.critical}
              </div>
            </div>
          </div>
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600 mb-1">
                {filteredAnalyses.length}
              </div>
              <div className="text-sm text-blue-700 font-medium">총 분석</div>
              <div className="text-xs text-blue-600 mt-1">
                {selectedTimeRange === 'all' ? '전체' : 
                 selectedTimeRange === 'week' ? '1주' :
                 selectedTimeRange === 'month' ? '1개월' :
                 selectedTimeRange === 'quarter' ? '3개월' : '1년'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 차트 섹션 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 트렌드 차트 */}
        <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
          <h3 className="text-xl font-semibold mb-4 md:mb-6 text-center text-gray-900">
            📈 건강 상태 추이
          </h3>
          {showAdvancedCharts ? (
            <AdvancedTrendChart />
          ) : (
            <TrendChart />
          )}
        </div>

        {/* 상태 분포 차트 */}
        <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
          <h3 className="text-xl font-semibold mb-4 md:mb-6 text-center text-gray-900">
            📊 상태 분포
          </h3>
          <AdvancedStatusDistribution />
        </div>
      </div>

      {/* 트렌드 분석 요약 */}
      {trendData.length > 1 && (
        <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
          <h3 className="text-xl font-semibold mb-4 md:mb-6 text-center text-gray-900">
            📊 트렌드 분석 요약
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600 mb-2">
                {trendChange.normal > 0 ? '+' : ''}{trendChange.normal}
              </div>
              <div className="text-sm text-gray-600">정상 상태 변화</div>
              <div className="text-xs text-gray-500 mt-1">
                {trendChange.normal > 0 ? '개선됨' : trendChange.normal < 0 ? '악화됨' : '변화없음'}
              </div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-yellow-600 mb-2">
                {trendChange.warning > 0 ? '+' : ''}{trendChange.warning}
              </div>
              <div className="text-sm text-gray-600">주의 상태 변화</div>
              <div className="text-xs text-gray-500 mt-1">
                {trendChange.warning > 0 ? '증가함' : trendChange.warning < 0 ? '감소함' : '변화없음'}
              </div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-red-600 mb-2">
                {trendChange.critical > 0 ? '+' : ''}{trendChange.critical}
              </div>
              <div className="text-sm text-gray-600">위험 상태 변화</div>
              <div className="text-xs text-gray-500 mt-1">
                {trendChange.critical > 0 ? '증가함' : trendChange.critical < 0 ? '감소함' : '변화없음'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

export default TimeSeriesSection;
