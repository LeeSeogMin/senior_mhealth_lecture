'use client';

import { useState, useEffect } from 'react';
import { GaugeChartProps, CHART_SIZES } from './VoicePatternTypes';

// 값을 0-1 사이로 정규화
const normalizeValue = (value: number, min: number, max: number): number => {
  if (value === null || value === undefined || isNaN(value)) return 0;
  if (max === min) return 0.5;
  return Math.min(1, Math.max(0, (value - min) / (max - min)));
};

// 값의 상태를 판단
const getValueStatus = (value: number, min: number, max: number): 'low' | 'normal' | 'high' => {
  if (value < min) return 'low';
  if (value > max) return 'high';
  return 'normal';
};

// 상태별 색상 매핑
const STATUS_COLORS = {
  low: {
    main: '#f59e0b',
    light: '#fef3c7',
    text: '#92400e'
  },
  normal: {
    main: '#10b981',
    light: '#d1fae5',
    text: '#065f46'
  },
  high: {
    main: '#ef4444',
    light: '#fee2e2',
    text: '#b91c1c'
  }
} as const;

export default function GaugeChart({
  value,
  min,
  max,
  label,
  unit,
  size = 'md',
  showTooltip = true,
  className = '',
  onClick
}: GaugeChartProps) {
  const [isClient, setIsClient] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <div className="animate-pulse bg-gray-200 rounded w-full h-20"></div>
      </div>
    );
  }

  const normalizedValue = normalizeValue(value, min, max);
  const status = getValueStatus(value, min, max);
  const colors = STATUS_COLORS[status];
  const chartSize = CHART_SIZES[size];

  // 게이지의 너비를 값에 따라 계산
  const gaugeWidth = `${normalizedValue * 100}%`;

  return (
    <div 
      className={`relative ${className}`}
      style={{ width: chartSize.width }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      {/* 라벨 */}
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-sm font-semibold" style={{ color: colors.text }}>
          {value} {unit}
        </span>
      </div>

      {/* 게이지 바 */}
      <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full transition-all duration-500 ease-out rounded-full"
          style={{
            width: gaugeWidth,
            backgroundColor: colors.main
          }}
        />
      </div>

      {/* 범위 표시 */}
      <div className="flex justify-between mt-1">
        <span className="text-xs text-gray-500">{min}</span>
        <span className="text-xs text-gray-500">{max}</span>
      </div>

      {/* 툴팁 */}
      {showTooltip && isHovered && (
        <div className="absolute -top-12 left-1/2 transform -translate-x-1/2 bg-white border border-gray-200 rounded-lg shadow-lg p-2 z-10">
          <div className="text-sm">
            <div className="font-medium" style={{ color: colors.text }}>
              {status === 'low' ? '낮음' : status === 'high' ? '높음' : '정상'}
            </div>
            <div className="text-gray-600">
              정상 범위: {min}-{max} {unit}
            </div>
          </div>
        </div>
      )}

      {/* 상태 표시 */}
      <div 
        className="absolute right-0 top-0 px-2 py-1 rounded-full text-xs font-medium"
        style={{ 
          backgroundColor: colors.light,
          color: colors.text
        }}
      >
        {status === 'low' ? '낮음' : status === 'high' ? '높음' : '정상'}
      </div>
    </div>
  );
} 