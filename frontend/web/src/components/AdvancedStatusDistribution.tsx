'use client';

import { useState, useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend
} from 'recharts';
import { useApiData } from '../hooks/useApiData';
import { getRiskLevel } from '../utils/chartDataTransformers';

interface StatusData {
  name: string;
  value: number;
  color: string;
  percentage: number;
  pattern: string;
}

interface AdvancedStatusDistributionProps {
  className?: string;
}

export default function AdvancedStatusDistribution({ className = '' }: AdvancedStatusDistributionProps) {
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'recent' | 'month'>('all');
  const [isClient, setIsClient] = useState(false);
  const { analyses, isLoading } = useApiData();

  // 클라이언트 사이드 렌더링
  useMemo(() => {
    setIsClient(true);
  }, []);

  // 필터링된 분석 데이터
  const filteredAnalyses = useMemo(() => {
    if (!analyses.length) return [];
    
    const now = new Date();
    const filterDate = new Date();
    
    switch (selectedFilter) {
      case 'recent':
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
  }, [analyses, selectedFilter]);

  // 상태 분포 데이터 생성
  const statusData = useMemo(() => {
    if (!filteredAnalyses.length) return [];

    const statusCounts = {
      normal: 0,
      warning: 0,
      critical: 0
    };

    filteredAnalyses.forEach(analysis => {
      const mentalHealth = analysis.result?.mentalHealthAnalysis;
      if (mentalHealth) {
        const depression = mentalHealth.depression?.score || 0;
        const cognitive = mentalHealth.cognitive?.score || 0;
        const anxiety = (mentalHealth as any).anxiety?.score || 0;
        
        // 평균 점수로 전체 상태 판단
        const averageScore = (depression + cognitive + anxiety) / 3;
        const riskLevel = getRiskLevel(averageScore);
        
        statusCounts[riskLevel]++;
      }
    });

    const total = statusCounts.normal + statusCounts.warning + statusCounts.critical;
    
    if (total === 0) return [];

    return [
      {
        name: '정상',
        value: statusCounts.normal,
        color: '#10b981',
        percentage: Math.round((statusCounts.normal / total) * 100),
        pattern: 'diagonal'
      },
      {
        name: '주의',
        value: statusCounts.warning,
        color: '#f59e0b',
        percentage: Math.round((statusCounts.warning / total) * 100),
        pattern: 'dots'
      },
      {
        name: '위험',
        value: statusCounts.critical,
        color: '#ef4444',
        percentage: Math.round((statusCounts.critical / total) * 100),
        pattern: 'cross'
      }
    ].filter(item => item.value > 0);
  }, [filteredAnalyses]);

  // 커스텀 툴팁
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      return (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-4">
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <div 
                className="w-4 h-4 rounded"
                style={{ backgroundColor: data.payload.color }}
              ></div>
              <span className="font-medium text-gray-900">{data.payload.name}</span>
            </div>
            <div className="text-sm text-gray-600">
              <div>건수: {data.payload.value}건</div>
              <div>비율: {data.payload.percentage}%</div>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  // 커스텀 범례
  const CustomLegend = ({ payload }: any) => {
    return (
      <div className="flex justify-center space-x-6 mt-4">
        {payload?.map((entry: any, index: number) => (
          <div key={index} className="flex items-center space-x-2">
            <div 
              className="w-4 h-4 rounded"
              style={{ backgroundColor: entry.color }}
            ></div>
            <span className="text-sm text-gray-700">{entry.value}</span>
            <span className="text-xs text-gray-500">
              ({statusData.find(d => d.name === entry.value)?.percentage || 0}%)
            </span>
          </div>
        ))}
      </div>
    );
  };

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
        <h3 className="text-lg font-semibold text-gray-900 mb-4">상태 분포 분석</h3>
        <div className="h-64 flex items-center justify-center">
          <div className="flex items-center space-x-2">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span className="text-gray-500">데이터를 불러오는 중...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!statusData.length) {
    return (
      <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">상태 분포 분석</h3>
        <div className="h-64 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="text-4xl mb-2">📊</div>
            <p className="text-lg font-medium">분석 데이터가 없습니다</p>
            <p className="text-sm">통화 기록을 추가하면 분포를 확인할 수 있습니다</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          상태 분포 분석
          <span className="ml-2 text-sm font-normal text-gray-500">
            ({filteredAnalyses.length}건 기준)
          </span>
        </h3>
        
        {/* 필터 */}
        <div className="flex space-x-2">
          {[
            { key: 'all', label: '전체' },
            { key: 'recent', label: '최근 7일' },
            { key: 'month', label: '최근 1개월' }
          ].map((filter) => (
            <button
              key={filter.key}
              onClick={() => setSelectedFilter(filter.key as any)}
              className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                selectedFilter === filter.key
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {/* 통계 요약 */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {statusData.map((item) => (
          <div key={item.name} className="text-center p-3 rounded-lg" style={{ backgroundColor: `${item.color}10` }}>
            <div className="text-2xl font-bold" style={{ color: item.color }}>
              {item.value}
            </div>
            <div className="text-sm" style={{ color: item.color }}>
              {item.name} ({item.percentage}%)
            </div>
          </div>
        ))}
      </div>

      {/* 도넛 차트 */}
      <div className="relative">
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={statusData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={120}
              paddingAngle={5}
              dataKey="value"
              animationDuration={1000}
              animationBegin={0}
            >
              {statusData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.color}
                  stroke={entry.color}
                  strokeWidth={2}
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend content={<CustomLegend />} />
          </PieChart>
        </ResponsiveContainer>
        
        {/* 중앙 통계 */}
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
          <div className="text-3xl font-bold text-gray-900">
            {statusData.reduce((sum, item) => sum + item.value, 0)}
          </div>
          <div className="text-sm text-gray-600">총 분석</div>
        </div>
      </div>

      {/* 상세 정보 */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-700 mb-3">분포 상세 정보</h4>
        <div className="space-y-2">
          {statusData.map((item) => (
            <div key={item.name} className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div 
                  className="w-3 h-3 rounded"
                  style={{ backgroundColor: item.color }}
                ></div>
                <span className="text-sm text-gray-700">{item.name}</span>
              </div>
              <div className="text-sm text-gray-600">
                {item.value}건 ({item.percentage}%)
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
} 