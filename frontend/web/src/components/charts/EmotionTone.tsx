'use client';

import { useState, useEffect } from 'react';
import { EmotionToneProps, EMOTION_TONE_CONFIG } from './VoicePatternTypes';

export default function EmotionTone({
  tone,
  size = 'md',
  showLabel = true,
  className = '',
  onClick
}: EmotionToneProps) {
  const [isClient, setIsClient] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <div className="animate-pulse bg-gray-200 rounded w-12 h-12"></div>
      </div>
    );
  }

  const config = EMOTION_TONE_CONFIG[tone] || EMOTION_TONE_CONFIG.neutral;
  const iconSize = size === 'sm' ? 'text-2xl' : size === 'lg' ? 'text-4xl' : 'text-3xl';
  const labelSize = size === 'sm' ? 'text-xs' : size === 'lg' ? 'text-base' : 'text-sm';

  // 방어적 코딩: config가 undefined인 경우 처리
  if (!config) {
    console.error('EMOTION_TONE_CONFIG is undefined for tone:', tone);
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <div className="text-gray-400">감정 톤 오류</div>
      </div>
    );
  }

  return (
    <div 
      className={`relative flex flex-col items-center ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      {/* 아이콘 */}
      <div 
        className={`${iconSize} p-3 rounded-full transition-colors duration-300`}
        style={{ 
          backgroundColor: `${config.color}10`,
          color: config.color
        }}
      >
        {config.icon}
      </div>

      {/* 라벨 */}
      {showLabel && (
        <div 
          className={`${labelSize} font-medium mt-2`}
          style={{ color: config.color }}
        >
          {config.label}
        </div>
      )}

      {/* 툴팁 */}
      {isHovered && (
        <div className="absolute -top-12 left-1/2 transform -translate-x-1/2 bg-white border border-gray-200 rounded-lg shadow-lg p-2 z-10">
          <div className="text-sm">
            <div className="font-medium" style={{ color: config.color }}>
              {config.label} 톤
            </div>
            <div className="text-gray-600">
              {config.description}
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 