'use client';

import { useState, useEffect } from 'react';
import { PieChartProps, CHART_SIZES } from './VoicePatternTypes';

// SVG 원형 경로 생성
const createArc = (value: number, radius: number): string => {
  const angle = value * 360;
  const angleInRadians = (angle - 90) * Math.PI / 180;
  const x = radius + radius * Math.cos(angleInRadians);
  const y = radius + radius * Math.sin(angleInRadians);
  const largeArc = angle > 180 ? 1 : 0;

  return `
    M ${radius},${radius}
    L ${radius},0
    A ${radius},${radius} 0 ${largeArc},1 ${x},${y}
    Z
  `;
};

export default function PieChart({
  value,
  label,
  size = 'md',
  showTooltip = true,
  className = '',
  onClick
}: PieChartProps) {
  const [isClient, setIsClient] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <div className="animate-pulse bg-gray-200 rounded-full w-32 h-32"></div>
      </div>
    );
  }

  const chartSize = CHART_SIZES[size];
  const radius = Math.min(chartSize.width, chartSize.height) / 2;
  const normalizedValue = Math.min(1, Math.max(0, value));
  const percentage = Math.round(normalizedValue * 100);

  // 값에 따른 색상 결정
  const getColor = (value: number) => {
    if (value < 0.1) return '#ef4444';  // 빨간색 - 너무 적음
    if (value > 0.3) return '#f59e0b';  // 노란색 - 너무 많음
    return '#10b981';                    // 녹색 - 정상
  };

  const color = getColor(normalizedValue);

  return (
    <div 
      className={`relative flex flex-col items-center ${className}`}
      style={{ width: chartSize.width }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      {/* 라벨 */}
      <div className="text-sm font-medium text-gray-700 mb-2">
        {label}
      </div>

      {/* SVG 파이 차트 */}
      <div className="relative">
        <svg 
          width={radius * 2} 
          height={radius * 2} 
          viewBox={`0 0 ${radius * 2} ${radius * 2}`}
          className="transform -rotate-90"
        >
          {/* 배경 원 */}
          <circle
            cx={radius}
            cy={radius}
            r={radius - 2}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="4"
          />

          {/* 값을 나타내는 호 */}
          <path
            d={createArc(normalizedValue, radius - 2)}
            fill={color}
            className="transition-all duration-500 ease-out"
          />

          {/* 중앙 원 (도넛 모양을 위해) */}
          <circle
            cx={radius}
            cy={radius}
            r={radius * 0.65}
            fill="white"
          />
        </svg>

        {/* 중앙 퍼센트 표시 */}
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
          <div className="text-2xl font-bold" style={{ color }}>
            {percentage}%
          </div>
        </div>
      </div>

      {/* 툴팁 */}
      {showTooltip && isHovered && (
        <div className="absolute -top-12 left-1/2 transform -translate-x-1/2 bg-white border border-gray-200 rounded-lg shadow-lg p-2 z-10">
          <div className="text-sm">
            <div className="font-medium" style={{ color }}>
              {percentage}% 일시정지
            </div>
            <div className="text-gray-600">
              {normalizedValue < 0.1 ? '너무 적음' : 
               normalizedValue > 0.3 ? '너무 많음' : '정상'}
            </div>
          </div>
        </div>
      )}

      {/* 상태 설명 */}
      <div className="mt-2 text-center">
        <div 
          className="inline-block px-2 py-1 rounded-full text-xs font-medium"
          style={{ 
            backgroundColor: `${color}20`,
            color: color
          }}
        >
          {normalizedValue < 0.1 ? '일시정지 부족' : 
           normalizedValue > 0.3 ? '일시정지 과다' : '적절한 일시정지'}
        </div>
      </div>
    </div>
  );
} 