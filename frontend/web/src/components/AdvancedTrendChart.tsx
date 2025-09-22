'use client';

import { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea
} from 'recharts';
import { useApiData } from '../hooks/useApiData';
import { EnhancedAnalysis } from '../hooks/useApiData';
import { formatDate } from '../utils/dateHelpers';

type PeriodFilter = 'week' | 'month' | 'year' | 'all';

interface TrendPoint {
  date: string;
  depression: number;
  cognitive: number;
  anxiety: number;
  average: number;
  analysisId: string;
  seniorName: string;
  hasSignificantChange: boolean;
}

interface AdvancedTrendChartProps {
  className?: string;
}

export default function AdvancedTrendChart({ className = '' }: AdvancedTrendChartProps) {
  const [periodFilter, setPeriodFilter] = useState<PeriodFilter>('month');
  const [isClient, setIsClient] = useState(false);
  const { analyses, isLoading } = useApiData();

  // 클라이언트 사이드 렌더링
  useMemo(() => {
    setIsClient(true);
  }, []);

  // 기간별 데이터 필터링
  const filteredAnalyses = useMemo(() => {
    if (!analyses.length) return [];
    
    const now = new Date();
    const filterDate = new Date();
    
    switch (periodFilter) {
      case 'week':
        filterDate.setDate(now.getDate() - 7);
        break;
      case 'month':
        filterDate.setMonth(now.getMonth() - 1);
        break;
      case 'year':
        filterDate.setFullYear(now.getFullYear() - 1);
        break;
      case 'all':
        return analyses;
    }
    
    return analyses.filter(analysis => 
      analysis.recordedAt && new Date(analysis.recordedAt) >= filterDate
    );
  }, [analyses, periodFilter]);

  // 추세 데이터 생성
  const trendData = useMemo(() => {
    if (!filteredAnalyses.length) return [];

    const sortedAnalyses = [...filteredAnalyses].sort(
      (a, b) => {
        const dateA = a.recordedAt ? new Date(a.recordedAt).getTime() : 0;
        const dateB = b.recordedAt ? new Date(b.recordedAt).getTime() : 0;
        return dateA - dateB;
      }
    );

    return sortedAnalyses.map((analysis, index) => {
      const mentalHealth = analysis.result?.mentalHealthAnalysis;
      const depression = mentalHealth?.depression?.score || 0;
      const cognitive = mentalHealth?.cognitive?.score || 0;
      const anxiety = (mentalHealth as any)?.anxiety?.score || 0;
      const average = Math.round((depression + cognitive + anxiety) / 3);

      // 급격한 변화 감지 (이전 점수와 비교)
      let hasSignificantChange = false;
      if (index > 0) {
        const prevAnalysis = sortedAnalyses[index - 1];
        const prevMentalHealth = prevAnalysis.result?.mentalHealthAnalysis;
        const prevAverage = Math.round((
          (prevMentalHealth?.depression?.score || 0) +
          (prevMentalHealth?.cognitive?.score || 0) +
          ((prevMentalHealth as any)?.anxiety?.score || 0)
        ) / 3);
        
        hasSignificantChange = Math.abs(average - prevAverage) >= 20;
      }

      return {
        date: formatDate(analysis.recordedAt),
        depression,
        cognitive,
        anxiety,
        average,
        analysisId: analysis.analysisId,
        seniorName: analysis.seniorName || '시니어',
        hasSignificantChange
      };
    });
  }, [filteredAnalyses]);

  // 평균값 계산
  const averageValues = useMemo(() => {
    if (!trendData.length) return { depression: 0, cognitive: 0, anxiety: 0 };
    
    const totals = trendData.reduce((acc, point) => ({
      depression: acc.depression + point.depression,
      cognitive: acc.cognitive + point.cognitive,
      anxiety: acc.anxiety + point.anxiety
    }), { depression: 0, cognitive: 0, anxiety: 0 });

    return {
      depression: Math.round(totals.depression / trendData.length),
      cognitive: Math.round(totals.cognitive / trendData.length),
      anxiety: Math.round(totals.anxiety / trendData.length)
    };
  }, [trendData]);

  if (!isClient) {
    return (
      <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">정신건강 추세 분석</h3>
        <div className="h-64 flex items-center justify-center">
          <div className="flex items-center space-x-2">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span className="text-gray-500">데이터를 불러오는 중...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!trendData.length) {
    return (
      <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">정신건강 추세 분석</h3>
        <div className="h-64 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="text-4xl mb-2">📊</div>
            <p className="text-lg font-medium">분석 데이터가 없습니다</p>
            <p className="text-sm">통화 기록을 추가하면 추세를 확인할 수 있습니다</p>
          </div>
        </div>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload as TrendPoint;
      return (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-4">
          <p className="font-medium text-gray-900 mb-2">{label}</p>
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-red-600">우울감:</span>
              <span className="font-medium">{data.depression}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-blue-600">인지기능:</span>
              <span className="font-medium">{data.cognitive}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-yellow-600">불안감:</span>
              <span className="font-medium">{data.anxiety}</span>
            </div>
            <div className="flex justify-between border-t pt-1">
              <span className="text-gray-700 font-medium">평균:</span>
              <span className="font-bold">{data.average}</span>
            </div>
            {data.hasSignificantChange && (
              <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
                <p className="text-xs text-yellow-800 font-medium">⚠️ 급격한 변화 감지</p>
              </div>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          정신건강 추세 분석
          <span className="ml-2 text-sm font-normal text-gray-500">
            ({filteredAnalyses.length}건의 분석)
          </span>
        </h3>
        
        {/* 기간 필터 */}
        <div className="flex space-x-2">
          {(['week', 'month', 'year', 'all'] as PeriodFilter[]).map((period) => (
            <button
              key={period}
              onClick={() => setPeriodFilter(period)}
              className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                periodFilter === period
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {period === 'week' && '주간'}
              {period === 'month' && '월간'}
              {period === 'year' && '연간'}
              {period === 'all' && '전체'}
            </button>
          ))}
        </div>
      </div>

      {/* 평균값 표시 */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center p-3 bg-red-50 rounded-lg">
          <div className="text-2xl font-bold text-red-600">{averageValues.depression}</div>
          <div className="text-sm text-red-700">평균 우울감</div>
        </div>
        <div className="text-center p-3 bg-blue-50 rounded-lg">
          <div className="text-2xl font-bold text-blue-600">{averageValues.cognitive}</div>
          <div className="text-sm text-blue-700">평균 인지기능</div>
        </div>
        <div className="text-center p-3 bg-yellow-50 rounded-lg">
          <div className="text-2xl font-bold text-yellow-600">{averageValues.anxiety}</div>
          <div className="text-sm text-yellow-700">평균 불안감</div>
        </div>
      </div>

      {/* 차트 */}
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={trendData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="date" 
            angle={-45}
            textAnchor="end"
            height={80}
            fontSize={12}
          />
          <YAxis 
            domain={[0, 100]}
            tickFormatter={(value) => `${value}점`}
          />
          <Tooltip content={<CustomTooltip />} />
          
          {/* 기준선 */}
          <ReferenceLine y={30} stroke="#10b981" strokeDasharray="3 3" />
          <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" />
          
          {/* 선 그래프 */}
          <Line 
            type="monotone" 
            dataKey="depression" 
            stroke="#ef4444" 
            strokeWidth={3}
            name="우울감"
            dot={{ r: 4, fill: '#ef4444' }}
            activeDot={{ r: 6, stroke: '#ef4444', strokeWidth: 2 }}
          />
          <Line 
            type="monotone" 
            dataKey="cognitive" 
            stroke="#3b82f6" 
            strokeWidth={3}
            name="인지기능"
            dot={{ r: 4, fill: '#3b82f6' }}
            activeDot={{ r: 6, stroke: '#3b82f6', strokeWidth: 2 }}
          />
          <Line 
            type="monotone" 
            dataKey="anxiety" 
            stroke="#f59e0b" 
            strokeWidth={3}
            name="불안감"
            dot={{ r: 4, fill: '#f59e0b' }}
            activeDot={{ r: 6, stroke: '#f59e0b', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* 범례 */}
      <div className="flex justify-center space-x-6 mt-4 text-sm">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-red-500 rounded"></div>
          <span>우울감</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-blue-500 rounded"></div>
          <span>인지기능</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-yellow-500 rounded"></div>
          <span>불안감</span>
        </div>
      </div>
    </div>
  );
} 