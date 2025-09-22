'use client';

import { EnhancedAnalysis } from '../hooks/useApiData';
import { StatusIndicator, ScoreBar } from './StatusIndicator';
import ScoreChart from './charts/ScoreChart';
import { MentalHealthScore } from './charts/types';
import { formatDate } from '../utils/dateHelpers';

// 분석 결과를 MentalHealthScore 형식으로 변환하는 함수
const transformToMentalHealthScore = (analysis: EnhancedAnalysis): MentalHealthScore | null => {
  const mentalHealth = analysis.result?.mentalHealthAnalysis;
  if (!mentalHealth) return null;

  const mentalHealthAny = mentalHealth as any;
  return {
    depression: mentalHealthAny.depression?.score || 0,
    anxiety: mentalHealthAny.anxiety?.score || 0,
    stress: mentalHealthAny.stress?.score || 0,
    mentalHealthStatus: mentalHealthAny.mentalHealthStatus?.score || 0,
    emotionManagement: mentalHealthAny.emotionManagement?.score || 0,
    socialRelationship: mentalHealthAny.socialRelationship?.score || 0
  };
};

export interface AnalysisCardProps {
  analysis: EnhancedAnalysis;
  onClick?: (analysisId: string) => void;
  showDetails?: boolean;
  showChart?: boolean;
  compact?: boolean;
}

export function AnalysisCard({ 
  analysis, 
  onClick, 
  showDetails = true,
  showChart = false,
  compact = false 
}: AnalysisCardProps) {
  const handleClick = () => {
    if (onClick) {
      onClick(analysis.analysisId);
    }
  };

  // 분석 결과에서 점수 추출 - AI가 분석한 실제 점수 사용
  const mentalHealth = analysis.result?.mentalHealthAnalysis;
  let depressionScore = 0;
  let cognitiveScore = 0;
  let anxietyScore = 0;

  if (mentalHealth) {
    // AI가 이미 분석한 점수가 있으면 그것을 사용
    const depValue = typeof mentalHealth.depression === 'object'
      ? mentalHealth.depression.score
      : mentalHealth.depression;
    const cogValue = typeof mentalHealth.cognitive === 'object'
      ? mentalHealth.cognitive.score
      : mentalHealth.cognitive;
    const anxValue = (mentalHealth as any).anxiety
      ? typeof (mentalHealth as any).anxiety === 'object'
        ? (mentalHealth as any).anxiety.score
        : (mentalHealth as any).anxiety
      : 0;

    depressionScore = Math.round(depValue || 0);
    cognitiveScore = Math.round(cogValue || 0);
    anxietyScore = Math.round(anxValue || 0);
  } else {
    // mentalHealthAnalysis가 없으면 coreIndicators 직접 사용 (0-1 범위를 100점으로 변환)
    const indicators = (analysis.result as any)?.coreIndicators;
    if (indicators) {
      const driValue = typeof indicators.DRI === 'number' ? indicators.DRI : (indicators.DRI?.value || 0);
      const cflValue = typeof indicators.CFL === 'number' ? indicators.CFL : (indicators.CFL?.value || 0);
      const esValue = typeof indicators.ES === 'number' ? indicators.ES : (indicators.ES?.value || 0);

      depressionScore = Math.round(driValue * 100);
      cognitiveScore = Math.round(cflValue * 100);
      anxietyScore = Math.round(esValue * 100);
    }
  }
  
  // 평균 점수 계산 (주요 위험도 판정용)
  const averageScore = Math.round((depressionScore + cognitiveScore + anxietyScore) / 3);
  
  // 음성 패턴 정보 - 실제 데이터 구조에 맞게 수정
  const voiceAnalysis = (analysis.result as any)?.voice_analysis || (analysis.result as any)?.voiceAnalysis;
  const librosa = (analysis.result as any)?.analysisMethodologies?.librosa || (analysis as any)?.analysisMethodologies?.librosa;

  console.log('🎵 AnalysisCard - librosa 데이터:', librosa);
  console.log('🎤 AnalysisCard - voiceAnalysis 데이터:', voiceAnalysis);

  const features = librosa?.features || voiceAnalysis?.features || {};
  const indicators = librosa?.indicators || {};

  const speechRate = features.speechRate || indicators.speaking_rate || indicators.speechRate || 0;
  const voiceStability = features.voiceStability || indicators.voice_clarity || 0;
  const pitch = features.pitch?.mean || indicators.pitch || 0;
  const pauseRatio = features.pauseRatio || indicators.pause_ratio || 0;

  console.log('📊 AnalysisCard - 추출된 음성 데이터:', { speechRate, voiceStability, pitch, pauseRatio });

  // 날짜 포맷팅
  const recordedDate = analysis.recordedAt ? new Date(analysis.recordedAt) : new Date();
  const isRecent = (Date.now() - recordedDate.getTime()) < 24 * 60 * 60 * 1000; // 24시간 이내

  if (compact) {
    return (
      <div 
        className={`
          bg-white border border-gray-200 rounded-lg p-4 
          ${onClick ? 'cursor-pointer hover:bg-gray-50 hover:border-gray-300 transition-colors' : ''}
          ${isRecent ? 'ring-2 ring-blue-100' : ''}
        `}
        onClick={handleClick}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <StatusIndicator score={averageScore} size="md" />
            <div>
              <p className="font-medium text-gray-900">
                {analysis.seniorName || '알 수 없음'}
              </p>
              <p className="text-sm text-gray-500">
                {formatDate(analysis.recordedAt || '')}
              </p>
            </div>
          </div>
          
          <div className="text-right">
            <div className="flex items-center space-x-2">
              <StatusIndicator 
                score={averageScore} 
                showLabel 
                showScore 
                size="sm" 
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className={`
        bg-white border border-gray-200 rounded-lg p-6 shadow-sm
        ${onClick ? 'cursor-pointer hover:shadow-md hover:border-gray-300 transition-all' : ''}
        ${isRecent ? 'ring-2 ring-blue-100 border-blue-200' : ''}
      `}
      onClick={handleClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center">
            <span className="text-white font-medium text-lg">
              {(analysis.seniorName || 'Unknown').charAt(0)}
            </span>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 text-lg">
              {analysis.seniorName || '알 수 없음'}
              {isRecent && (
                <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  새 분석
                </span>
              )}
            </h4>
            <p className="text-sm text-gray-500">
              📅 {formatDate(analysis.recordedAt || '')}
            </p>
          </div>
        </div>
        
        <StatusIndicator 
          score={averageScore} 
          showLabel 
          size="lg" 
          className="flex-shrink-0"
        />
      </div>

      {showDetails && (
        <>
          {/* 점수 섹션 */}
          <div className="space-y-3 mb-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 우울증 점수 */}
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">우울감</span>
                  <span className="text-sm font-semibold text-gray-900">{depressionScore}점</span>
                </div>
                <ScoreBar score={depressionScore} height="sm" showScore={false} />
              </div>

              {/* 인지 점수 */}
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">인지기능</span>
                  <span className="text-sm font-semibold text-gray-900">{cognitiveScore}점</span>
                </div>
                <ScoreBar score={cognitiveScore} height="sm" showScore={false} />
              </div>

              {/* 불안 점수 */}
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">불안감</span>
                  <span className="text-sm font-semibold text-gray-900">{anxietyScore}점</span>
                </div>
                <ScoreBar score={anxietyScore} height="sm" showScore={false} />
              </div>
            </div>
          </div>

          {/* 음성 패턴 정보 */}
          {(speechRate > 0 || voiceStability > 0 || pitch > 0 || pauseRatio > 0) && (
            <div className="bg-blue-50 rounded-lg p-3 mb-4">
              <h5 className="text-sm font-medium text-blue-900 mb-2">🎤 음성 패턴</h5>
              <div className="grid grid-cols-2 gap-4 text-sm">
                {speechRate > 0 && (
                  <div>
                    <span className="text-blue-700">말하기 속도:</span>
                    <span className="ml-2 font-medium">{Math.round(speechRate * 100) / 100} wpm</span>
                  </div>
                )}
                {voiceStability > 0 && (
                  <div>
                    <span className="text-blue-700">음성 안정성:</span>
                    <span className="ml-2 font-medium">{Math.round(voiceStability * 100)}%</span>
                  </div>
                )}
                {pitch > 0 && (
                  <div>
                    <span className="text-blue-700">음높이:</span>
                    <span className="ml-2 font-medium">{Math.round(pitch)} Hz</span>
                  </div>
                )}
                {pauseRatio > 0 && (
                  <div>
                    <span className="text-blue-700">휴지 비율:</span>
                    <span className="ml-2 font-medium">{Math.round(pauseRatio * 100)}%</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 정신건강 분석 차트 */}
          {showChart && (() => {
            const chartData = transformToMentalHealthScore(analysis);
            return chartData && (
              <div className="mb-4">
                <ScoreChart
                  scores={chartData}
                  size="medium"
                  showLegend={false}
                  showTooltip={true}
                />
              </div>
            );
          })()}

          {/* 요약 및 권장사항 */}
          {analysis.result?.summary && (
            <div className="border-t pt-3">
              <p className="text-sm text-gray-600 leading-relaxed">
                💡 <strong>AI 요약:</strong> {analysis.result.summary}
              </p>
            </div>
          )}

          {/* 상세보기 버튼 */}
          {onClick && (
            <div className="flex justify-end mt-4">
              <button className="text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors">
                상세보기 →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// 분석 결과 목록을 위한 컴포넌트
export interface AnalysisListProps {
  analyses: EnhancedAnalysis[];
  onAnalysisClick?: (analysisId: string) => void;
  showDetails?: boolean;
  showChart?: boolean;
  compact?: boolean;
  maxItems?: number;
  emptyMessage?: string;
}

export function AnalysisList({ 
  analyses, 
  onAnalysisClick,
  showDetails = true,
  showChart = false,
  compact = false,
  maxItems,
  emptyMessage = "분석 결과가 없습니다"
}: AnalysisListProps) {
  const displayAnalyses = maxItems ? analyses.slice(0, maxItems) : analyses;

  if (analyses.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <div className="text-4xl mb-2">📊</div>
        <p className="text-lg font-medium">{emptyMessage}</p>
        <p className="text-sm">통화 기록을 추가하면 분석 결과를 확인할 수 있습니다</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {displayAnalyses.map((analysis, index) => (
        <AnalysisCard
          key={analysis.analysisId || index}
          analysis={analysis}
          onClick={onAnalysisClick}
          showDetails={showDetails}
          showChart={showChart}
          compact={compact}
        />
      ))}
      
      {maxItems && analyses.length > maxItems && (
        <div className="text-center pt-4">
          <p className="text-sm text-gray-500">
            {analyses.length - maxItems}개의 추가 분석 결과가 있습니다
          </p>
        </div>
      )}
    </div>
  );
} 