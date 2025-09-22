'use client';

import { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell
} from 'recharts';
import { useApiData } from '../hooks/useApiData';
import { 
  generateTrendData,
  generateStatusDistributionData,
  TrendData,
  StatusDistributionData
} from '../utils/chartDataTransformers';
import LoadingSpinner from './LoadingSpinner';

export function TrendChart() {
  const [isClient, setIsClient] = useState(false);
  const { analyses, isLoading } = useApiData();

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return (
      <div className="bg-white rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">주간 상태 트렌드</h3>
        <div className="h-[300px] flex items-center justify-center">
          <div className="animate-pulse bg-gray-200 rounded w-full h-full"></div>
        </div>
      </div>
    );
  }

  // 로딩 중일 때
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">주간 상태 트렌드</h3>
        <div className="h-[300px] flex items-center justify-center">
          <LoadingSpinner 
            type="dots" 
            message="데이터를 불러오는 중..." 
            size="lg"
          />
        </div>
      </div>
    );
  }

  // 실제 분석 데이터를 기반으로 트렌드 데이터 생성
  const trendData: TrendData[] = generateTrendData(analyses);

  // 데이터가 없을 때
  if (analyses.length === 0) {
    return (
      <div className="bg-white rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">주간 상태 트렌드</h3>
        <div className="h-[300px] flex items-center justify-center">
          <div className="text-center text-gray-500">
            <p className="text-lg mb-2">📊</p>
            <p>분석 데이터가 없습니다</p>
            <p className="text-sm">통화 기록을 추가하면 추세를 확인할 수 있습니다</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        주간 상태 트렌드
        <span className="ml-2 text-sm font-normal text-gray-500">
          (총 {analyses.length}건의 분석 결과)
        </span>
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={trendData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip 
            labelFormatter={(label) => `날짜: ${label}`}
            formatter={(value, name) => [value, name]}
          />
          <Line 
            type="monotone" 
            dataKey="normal" 
            stroke="#10b981" 
            strokeWidth={2}
            name="정상"
          />
          <Line 
            type="monotone" 
            dataKey="warning" 
            stroke="#f59e0b" 
            strokeWidth={2}
            name="주의"
          />
          <Line 
            type="monotone" 
            dataKey="critical" 
            stroke="#ef4444" 
            strokeWidth={2}
            name="긴급"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StatusDistributionChart() {
  const [isClient, setIsClient] = useState(false);
  const { analyses, isLoading } = useApiData();

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return (
      <div className="bg-white rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">현재 상태 분포</h3>
        <div className="h-[250px] flex items-center justify-center">
          <div className="animate-pulse bg-gray-200 rounded w-full h-full"></div>
        </div>
      </div>
    );
  }

  // 로딩 중일 때
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">현재 상태 분포</h3>
        <div className="h-[250px] flex items-center justify-center">
          <LoadingSpinner 
            type="dots" 
            message="데이터를 불러오는 중..." 
            size="md"
          />
        </div>
      </div>
    );
  }

  // 실제 분석 데이터를 기반으로 상태 분포 데이터 생성
  const statusData: StatusDistributionData[] = generateStatusDistributionData(analyses);

  // 데이터가 없을 때
  if (analyses.length === 0) {
    return (
      <div className="bg-white rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">현재 상태 분포</h3>
        <div className="h-[250px] flex items-center justify-center">
          <div className="text-center text-gray-500">
            <p className="text-lg mb-2">📈</p>
            <p>분석 데이터가 없습니다</p>
            <p className="text-sm">통화 기록을 추가하면 분포를 확인할 수 있습니다</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        현재 상태 분포
        <span className="ml-2 text-sm font-normal text-gray-500">
          (총 {analyses.length}건 기준)
        </span>
      </h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={statusData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip 
            formatter={(value, name) => [value, '건수']}
            labelFormatter={(label) => `${label} 상태`}
          />
          <Bar 
            dataKey="value" 
            radius={[4, 4, 0, 0]}
          >
            {statusData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
} 