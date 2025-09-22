'use client';

import { useState, useEffect } from 'react';
import {
  VoicePatternChartProps,
  VOICE_PATTERN_RANGES,
  EMOTION_TONE_CONFIG
} from './VoicePatternConstants';
import GaugeChart from './GaugeChart';
import PieChart from './PieChart';
import EmotionTone from './EmotionTone';

export default function VoicePatternChart({
  data,
  size = 'md',
  showLabels = true,
  showTooltips = true,
  className = '',
  onPatternClick
}: VoicePatternChartProps) {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  // VOICE_PATTERN_RANGES 체크
  if (!VOICE_PATTERN_RANGES) {
    console.error('❌ VoicePatternChart: VOICE_PATTERN_RANGES is undefined');
    return (
      <div className={`bg-red-50 rounded-lg p-6 shadow-sm ${className}`}>
        <div className="text-center text-red-600">
          <div className="text-4xl mb-2">⚠️</div>
          <p className="text-lg font-medium">차트 설정 오류</p>
          <p className="text-sm">VOICE_PATTERN_RANGES를 불러올 수 없습니다</p>
        </div>
      </div>
    );
  }

  if (!isClient) {
    return (
      <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  // 데이터 검증 - null/undefined 체크 추가
  if (!data) {
    return (
      <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
        <div className="text-center text-gray-500">
          <div className="text-4xl mb-2">🎤</div>
          <p className="text-lg font-medium">음성 패턴 데이터가 없습니다</p>
          <p className="text-sm">데이터를 불러올 수 없습니다</p>
        </div>
      </div>
    );
  }

  const hasData = Object.values(data).some(value =>
    typeof value === 'number' && !isNaN(value) && value > 0
  );

  if (!hasData) {
    return (
      <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
        <div className="text-center text-gray-500">
          <div className="text-4xl mb-2">🎤</div>
          <p className="text-lg font-medium">음성 패턴 데이터가 없습니다</p>
          <p className="text-sm">분석 결과를 확인할 수 없습니다</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg p-6 shadow-sm ${className}`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          음성 패턴 분석
        </h3>
        {data.emotionTone && (
          <EmotionTone
            tone={
              EMOTION_TONE_CONFIG.hasOwnProperty(data.emotionTone)
                ? data.emotionTone as keyof typeof EMOTION_TONE_CONFIG
                : 'neutral'
            }
            size="sm"
            onClick={() => onPatternClick?.('emotionTone')}
          />
        )}
      </div>

      {/* 차트 그리드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 말하기 속도 게이지 */}
        <GaugeChart
          value={data.speechRate}
          min={VOICE_PATTERN_RANGES.speechRate.min}
          max={VOICE_PATTERN_RANGES.speechRate.max}
          label="말하기 속도"
          unit={VOICE_PATTERN_RANGES.speechRate.unit}
          size={size}
          showTooltip={showTooltips}
          onClick={() => onPatternClick?.('speechRate')}
        />

        {/* 음성 안정성 게이지 */}
        <GaugeChart
          value={data.voiceStability * 100}  // 0-1을 0-100으로 변환
          min={VOICE_PATTERN_RANGES.voiceStability.min * 100}
          max={VOICE_PATTERN_RANGES.voiceStability.max * 100}
          label="음성 안정성"
          unit={VOICE_PATTERN_RANGES.voiceStability.unit}
          size={size}
          showTooltip={showTooltips}
          onClick={() => onPatternClick?.('voiceStability')}
        />

        {/* 일시정지 비율 파이 차트 */}
        <div className="md:col-span-2">
          <PieChart
            value={data.pauseRatio}
            label="일시정지 비율"
            size={size}
            showTooltip={showTooltips}
            onClick={() => onPatternClick?.('pauseRatio')}
          />
        </div>
      </div>

      {/* 추가 정보 */}
      {(data.pitch || data.energy || data.responseTime) && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-700 mb-4">
            추가 음성 특성
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {/* 피치 정보 */}
            {data.pitch && (
              <div className="bg-blue-50 rounded-lg p-3">
                <div className="text-sm font-medium text-blue-900">피치 분석</div>
                <div className="mt-1 space-y-1">
                  <div className="text-sm">
                    <span className="text-blue-700">평균:</span>
                    <span className="ml-2 text-blue-900">{data.pitch.mean.toFixed(1)}</span>
                  </div>
                  <div className="text-sm">
                    <span className="text-blue-700">변동:</span>
                    <span className="ml-2 text-blue-900">{data.pitch.variance.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            )}

            {/* 에너지 정보 */}
            {data.energy && (
              <div className="bg-purple-50 rounded-lg p-3">
                <div className="text-sm font-medium text-purple-900">에너지 분석</div>
                <div className="mt-1 space-y-1">
                  <div className="text-sm">
                    <span className="text-purple-700">평균:</span>
                    <span className="ml-2 text-purple-900">{data.energy.mean.toFixed(1)}</span>
                  </div>
                  <div className="text-sm">
                    <span className="text-purple-700">변동:</span>
                    <span className="ml-2 text-purple-900">{data.energy.variance.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            )}

            {/* 응답 시간 */}
            {data.responseTime && (
              <div className="bg-green-50 rounded-lg p-3">
                <div className="text-sm font-medium text-green-900">응답 시간</div>
                <div className="mt-1">
                  <div className="text-sm">
                    <span className="text-green-700">평균:</span>
                    <span className="ml-2 text-green-900">
                      {(data.responseTime / 1000).toFixed(1)}초
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
} 