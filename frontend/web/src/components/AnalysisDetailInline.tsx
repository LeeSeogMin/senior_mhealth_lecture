'use client';

import { useState } from 'react';
import { EnhancedAnalysis } from '../hooks/useApiData';
import { StatusIndicator, ScoreBar } from './StatusIndicator';
import { formatDate } from '../utils/dateHelpers';
import AnalysisInterpretation from './AnalysisInterpretation';

interface AnalysisDetailInlineProps {
  analysis: EnhancedAnalysis;
  isExpanded: boolean;
  onToggle: () => void;
}

export default function AnalysisDetailInline({ 
  analysis, 
  isExpanded, 
  onToggle 
}: AnalysisDetailInlineProps) {
  // 분석 결과에서 점수 추출
  const mentalHealthAnalysis = analysis.result?.mentalHealthAnalysis as any;
  const depressionScore = mentalHealthAnalysis?.depression?.score || 0;
  const cognitiveScore = mentalHealthAnalysis?.cognitive?.score || 0;
  const anxietyScore = mentalHealthAnalysis?.anxiety?.score || 0;
  
  // 평균 점수 계산
  const averageScore = Math.round((depressionScore + cognitiveScore + anxietyScore) / 3);

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      {/* 헤더 - 항상 표시 (클릭 불가) */}
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center">
              <span className="text-white font-medium text-sm">
                {(analysis.seniorName || 'Unknown').charAt(0)}
              </span>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">
                {analysis.seniorName || '알 수 없음'}
              </h3>
              <p className="text-sm text-gray-500">
                📅 {formatDate(analysis.recordedAt || '')}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <StatusIndicator 
              score={averageScore} 
              showLabel 
              size="sm" 
            />
          </div>
        </div>
      </div>

      {/* 확장된 내용 - 항상 표시 */}
      <div className="border-t border-gray-200 p-4 space-y-4">
        {/* AI 해석 섹션 */}
        <div className="bg-blue-50 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-blue-900 mb-3">
            🤖 AI 총평 및 권장사항
          </h4>
          <AnalysisInterpretation 
            callId={analysis.analysisId}
            seniorId={analysis.analysisId.split('_')[0] || 'default'}
            onInterpretationGenerated={(interpretation) => {
              console.log('해석 생성 완료:', interpretation);
            }}
          />
        </div>

        {/* 점수 섹션 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* 우울증 점수 */}
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-700">우울감</span>
              <span className="text-xs font-semibold text-gray-900">{depressionScore}점</span>
            </div>
            <ScoreBar score={depressionScore} height="sm" showScore={false} />
          </div>

          {/* 인지 점수 */}
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-700">인지기능</span>
              <span className="text-xs font-semibold text-gray-900">{cognitiveScore}점</span>
            </div>
            <ScoreBar score={cognitiveScore} height="sm" showScore={false} />
          </div>

          {/* 불안 점수 */}
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-700">불안감</span>
              <span className="text-xs font-semibold text-gray-900">{anxietyScore}점</span>
            </div>
            <ScoreBar score={anxietyScore} height="sm" showScore={false} />
          </div>
        </div>

        {/* 요약 및 권장사항 */}
        {analysis.result?.summary && (
          <div className="bg-yellow-50 rounded-lg p-3">
            <h4 className="text-xs font-medium text-yellow-900 mb-2">💡 AI 요약</h4>
            <p className="text-xs text-yellow-800 leading-relaxed">
              {analysis.result.summary}
            </p>
          </div>
        )}

        {/* 상세 정보 */}
        <div className="bg-gray-50 rounded-lg p-3">
          <h4 className="text-xs font-medium text-gray-900 mb-2">📋 상세 정보</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-gray-600">분석 ID:</span>
              <span className="ml-1 font-mono">{analysis.analysisId}</span>
            </div>
            <div>
              <span className="text-gray-600">생성 시간:</span>
              <span className="ml-1">{formatDate(analysis.recordedAt || '')}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 