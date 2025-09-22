'use client';

import { getRiskLevel } from '../utils/chartDataTransformers';

export interface StatusIndicatorProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  showScore?: boolean;
  className?: string;
}

// 상태별 설정
const statusConfig = {
  normal: {
    color: 'bg-green-500',
    lightColor: 'bg-green-100',
    textColor: 'text-green-800',
    label: '정상',
    borderColor: 'border-green-500',
  },
  warning: {
    color: 'bg-yellow-500',
    lightColor: 'bg-yellow-100',
    textColor: 'text-yellow-800',
    label: '주의',
    borderColor: 'border-yellow-500',
  },
  critical: {
    color: 'bg-red-500',
    lightColor: 'bg-red-100',
    textColor: 'text-red-800',
    label: '위험',
    borderColor: 'border-red-500',
  },
};

// 크기별 설정
const sizeConfig = {
  sm: {
    dot: 'w-2 h-2',
    badge: 'px-2 py-1 text-xs',
    text: 'text-xs',
  },
  md: {
    dot: 'w-3 h-3',
    badge: 'px-2.5 py-1 text-sm',
    text: 'text-sm',
  },
  lg: {
    dot: 'w-4 h-4',
    badge: 'px-3 py-1.5 text-base',
    text: 'text-base',
  },
};

export function StatusIndicator({ 
  score, 
  size = 'md', 
  showLabel = false, 
  showScore = false,
  className = ''
}: StatusIndicatorProps) {
  const riskLevel = getRiskLevel(score);
  const status = statusConfig[riskLevel];
  const sizing = sizeConfig[size];

  // 점만 표시 (기본)
  if (!showLabel && !showScore) {
    return (
      <div className={`flex items-center ${className}`}>
        <div className={`${sizing.dot} ${status.color} rounded-full`} />
      </div>
    );
  }

  // 배지 형태 (라벨 또는 점수 표시)
  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <span className={`
        ${sizing.badge} 
        ${status.lightColor} 
        ${status.textColor}
        rounded-full font-medium inline-flex items-center space-x-1
      `}>
        <div className={`${sizing.dot} ${status.color} rounded-full`} />
        {showLabel && <span>{status.label}</span>}
        {showScore && <span>{score}점</span>}
        {showLabel && showScore && <span>({score}점)</span>}
      </span>
    </div>
  );
}

// 상태별 통계를 위한 컴포넌트
export interface StatusSummaryProps {
  normalCount: number;
  warningCount: number;
  criticalCount: number;
  size?: 'sm' | 'md' | 'lg';
  showCounts?: boolean;
}

export function StatusSummary({
  normalCount,
  warningCount,
  criticalCount,
  size = 'md',
  showCounts = true
}: StatusSummaryProps) {
  const total = normalCount + warningCount + criticalCount;
  
  if (total === 0) {
    return (
      <div className="text-gray-500 text-sm">
        데이터 없음
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-4">
      <div className="flex items-center space-x-1">
        <StatusIndicator score={10} size={size} />
        <span className={`text-gray-700 ${size === 'sm' ? 'text-xs' : size === 'lg' ? 'text-base' : 'text-sm'}`}>
          정상 {showCounts && `(${normalCount})`}
        </span>
      </div>
      
      <div className="flex items-center space-x-1">
        <StatusIndicator score={50} size={size} />
        <span className={`text-gray-700 ${size === 'sm' ? 'text-xs' : size === 'lg' ? 'text-base' : 'text-sm'}`}>
          주의 {showCounts && `(${warningCount})`}
        </span>
      </div>
      
      <div className="flex items-center space-x-1">
        <StatusIndicator score={80} size={size} />
        <span className={`text-gray-700 ${size === 'sm' ? 'text-xs' : size === 'lg' ? 'text-base' : 'text-sm'}`}>
          위험 {showCounts && `(${criticalCount})`}
        </span>
      </div>
    </div>
  );
}

// 점수 범위를 시각적으로 표시하는 컴포넌트
export interface ScoreBarProps {
  score: number;
  maxScore?: number;
  height?: 'sm' | 'md' | 'lg';
  showScore?: boolean;
}

export function ScoreBar({ 
  score, 
  maxScore = 100, 
  height = 'md',
  showScore = true 
}: ScoreBarProps) {
  const riskLevel = getRiskLevel(score);
  const status = statusConfig[riskLevel];
  const percentage = Math.min((score / maxScore) * 100, 100);
  
  const heightClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4',
  };

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-gray-600">위험도</span>
        {showScore && (
          <span className={`text-sm font-medium ${status.textColor}`}>
            {score}/{maxScore}
          </span>
        )}
      </div>
      <div className={`w-full bg-gray-200 rounded-full ${heightClasses[height]}`}>
        <div
          className={`${heightClasses[height]} ${status.color} rounded-full transition-all duration-500 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
} 