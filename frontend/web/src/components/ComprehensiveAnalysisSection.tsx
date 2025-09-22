'use client';

import { useState, useEffect, useMemo, memo } from 'react';
import { useApiData } from '../hooks/useApiData';
import { AnalysisInterpretation as AnalysisInterpretationType } from '../lib/apiClient';
import AnalysisInterpretation from './AnalysisInterpretation';
import LoadingSpinner from './LoadingSpinner';
import { calculateOverallStats } from '../utils/chartDataTransformers';

interface ComprehensiveAnalysisSectionProps {
  className?: string;
  selectedAnalysis?: any;
  onAnalysisSelect?: (analysis: any) => void;
}

const ComprehensiveAnalysisSection = memo(function ComprehensiveAnalysisSection({
  className = '',
  selectedAnalysis: propSelectedAnalysis,
  onAnalysisSelect
}: ComprehensiveAnalysisSectionProps) {
  const { analyses, isLoading, error } = useApiData();
  const [localSelectedAnalysis, setLocalSelectedAnalysis] = useState<any>(null);

  // props에서 받은 selectedAnalysis가 있으면 사용, 없으면 로컬 상태 사용
  const selectedAnalysis = propSelectedAnalysis || localSelectedAnalysis;
  const setSelectedAnalysis = onAnalysisSelect || setLocalSelectedAnalysis;

  // 전체 통계 계산
  const overallStats = useMemo(() => {
    return calculateOverallStats(analyses);
  }, [analyses]);

  // 최신 분석 결과 선택 (props로 받지 않은 경우에만)
  useEffect(() => {
    if (!propSelectedAnalysis && analyses.length > 0) {
      setSelectedAnalysis(analyses[0]);
    }
  }, [analyses, propSelectedAnalysis, setSelectedAnalysis]);

  // 로딩 상태 처리
  if (isLoading) {
    return (
      <div className={`bg-gradient-to-br from-blue-50 to-indigo-100 rounded-2xl p-4 md:p-8 shadow-lg ${className}`}>
        <div className="text-center py-12">
          <LoadingSpinner 
            type="dots" 
            message="AI 종합해석을 불러오는 중..." 
            size="lg"
          />
        </div>
      </div>
    );
  }

  // 에러 상태 처리
  if (error) {
    return (
      <div className={`bg-gradient-to-br from-red-50 to-pink-100 rounded-2xl p-4 md:p-8 shadow-lg ${className}`}>
        <div className="text-center py-12">
          <div className="text-6xl mb-4">⚠️</div>
          <h3 className="text-xl font-semibold text-red-800 mb-2">데이터 로딩 오류</h3>
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  // 데이터가 없는 경우
  if (analyses.length === 0) {
    return (
      <div className={`bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl p-4 md:p-8 shadow-lg ${className}`}>
        <div className="text-center py-12">
          <div className="text-6xl mb-4">📊</div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">분석 데이터가 없습니다</h3>
          <p className="text-gray-600">통화 기록을 추가하면 AI 종합해석을 확인할 수 있습니다</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-gradient-to-br from-blue-50 to-indigo-100 rounded-2xl p-4 md:p-8 shadow-lg ${className}`}>
      {/* 전체 건강 상태 요약 카드 */}
      <div className="mb-8">
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <h3 className="text-2xl font-semibold mb-6 text-center text-gray-900">
            📊 전체 건강 상태 요약
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* 총 분석 수 */}
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-3xl font-bold text-blue-600 mb-2">
                {overallStats.totalAnalyses}
              </div>
              <div className="text-sm text-blue-700 font-medium">총 분석 수</div>
            </div>

            {/* 정상 상태 비율 */}
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-3xl font-bold text-green-600 mb-2">
                {overallStats.normalPercentage}%
              </div>
              <div className="text-sm text-green-700 font-medium">정상 상태</div>
              <div className="text-xs text-green-600 mt-1">
                ({overallStats.normalCount}건)
              </div>
            </div>

            {/* 주의/긴급 상태 비율 */}
            <div className="text-center p-4 bg-orange-50 rounded-lg">
              <div className="text-3xl font-bold text-orange-600 mb-2">
                {overallStats.warningPercentage + overallStats.criticalPercentage}%
              </div>
              <div className="text-sm text-orange-700 font-medium">주의/긴급</div>
              <div className="text-xs text-orange-600 mt-1">
                ({overallStats.warningCount + overallStats.criticalCount}건)
              </div>
            </div>
          </div>

          {/* 상태별 상세 정보 */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center justify-between p-3 bg-green-100 rounded-lg">
              <span className="text-green-800 font-medium">정상</span>
              <span className="text-green-600 font-bold">{overallStats.normalCount}건</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-yellow-100 rounded-lg">
              <span className="text-yellow-800 font-medium">주의</span>
              <span className="text-yellow-600 font-bold">{overallStats.warningCount}건</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-red-100 rounded-lg">
              <span className="text-red-800 font-medium">긴급</span>
              <span className="text-red-600 font-bold">{overallStats.criticalCount}건</span>
            </div>
          </div>
        </div>
      </div>

      {/* AI 종합해석 - 실제 데이터 사용 */}
      {selectedAnalysis && (
        <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm">
          <h3 className="text-2xl font-semibold mb-6 text-center text-gray-900">
            💙 AI 종합해석
          </h3>

          {/* 실제 분석 데이터 표시 */}
          <div className="space-y-6">
            {/* 종합 평가 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">종합 평가</h3>
              <p className="text-blue-800">
                {selectedAnalysis.result?.legacy?.report?.narrative ||
                 selectedAnalysis.result?.summary ||
                 '음성 분석 데이터를 기반으로 어르신의 정신 건강 상태를 평가한 결과입니다.'}
              </p>

              {/* 위험도 평가 */}
              {selectedAnalysis.result?.risk_assessment && (
                <div className="mt-3 flex items-center space-x-4">
                  <span className={`px-3 py-1 text-sm font-medium rounded-full ${
                    selectedAnalysis.result.risk_assessment.overall_risk === 'high' ? 'bg-red-100 text-red-800 border border-red-200' :
                    selectedAnalysis.result.risk_assessment.overall_risk === 'moderate' ? 'bg-yellow-100 text-yellow-800 border border-yellow-200' :
                    'bg-green-100 text-green-800 border border-green-200'
                  }`}>
                    위험도: {selectedAnalysis.result.risk_assessment.overall_risk === 'high' ? '높음' :
                            selectedAnalysis.result.risk_assessment.overall_risk === 'moderate' ? '중간' : '낮음'}
                  </span>
                  {selectedAnalysis.result?.integratedResults?.confidence && (
                    <span className="text-sm text-blue-600">
                      신뢰도: {Math.round(selectedAnalysis.result.integratedResults.confidence * 100)}%
                    </span>
                  )}
                </div>
              )}

              {/* 핵심 지표 표시 */}
              {selectedAnalysis.result?.coreIndicators && (
                <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-2">
                  {Object.entries(selectedAnalysis.result.coreIndicators).map(([key, indicator]) => {
                    const value = typeof indicator === 'object' ? (indicator as any).value : indicator;
                    const level = typeof indicator === 'object' ? (indicator as any).level : '';
                    const description = key === 'DRI' ? '우울 위험도' :
                                       key === 'CFL' ? '인지 기능' :
                                       key === 'ES' ? '정서 안정성' :
                                       key === 'OV' ? '전반적 활력' :
                                       key === 'SDI' ? '수면 장애' : key;

                    return (
                      <div key={key} className="bg-white rounded p-2 text-center">
                        <div className="text-xs text-gray-600">{description}</div>
                        <div className="text-lg font-bold text-blue-600">
                          {Math.round(value * 100)}%
                        </div>
                        {level && (
                          <div className={`text-xs mt-1 ${
                            level === 'high' || level === 'severe' ? 'text-red-600' :
                            level === 'moderate' ? 'text-yellow-600' : 'text-green-600'
                          }`}>
                            {level === 'mild' ? '경미' : level === 'moderate' ? '중간' : level === 'high' ? '높음' : level}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* 상세 분석 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* 정신 건강 분석 */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-800 mb-3">📊 정신 건강 분석</h4>
                {selectedAnalysis.result?.legacy?.report?.indicators ? (
                  <div className="space-y-2 text-sm">
                    {Object.entries(selectedAnalysis.result.legacy.report.indicators).map(([key, data]: [string, any]) => {
                      return (
                        <div key={key}>
                          <div className="flex justify-between items-center">
                            <span className="text-gray-600">{data.description?.split(' - ')[0] || key}:</span>
                            <div className="text-right">
                              <span className="font-medium">{data.percentage}%</span>
                              <span className={`ml-2 text-xs px-2 py-1 rounded ${
                                data.status === '주의필요' ? 'bg-yellow-100 text-yellow-700' :
                                data.status === '보통' ? 'bg-blue-100 text-blue-700' :
                                'bg-green-100 text-green-700'
                              }`}>
                                {data.status}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : selectedAnalysis.result?.mentalHealthAnalysis ? (
                  <div className="space-y-2 text-sm">
                    {Object.entries(selectedAnalysis.result.mentalHealthAnalysis).map(([key, data]) => {
                      const score = (data as any)?.score || data || 0;
                      return (
                        <div key={key}>
                          <div className="flex justify-between">
                            <span className="text-gray-600 capitalize">{key}:</span>
                            <span className="font-medium">{Math.round(score)}점</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">정신건강 분석 데이터가 없습니다</p>
                )}
              </div>

              {/* 음성 분석 */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-800 mb-3">🎤 음성 패턴 분석</h4>
                {(() => {
                  // Check for librosa data first (new structure)
                  const librosa = selectedAnalysis.result?.analysisMethodologies?.librosa;
                  const librosaFeatures = librosa?.features || {};
                  const librosaIndicators = librosa?.indicators || {};

                  // Fall back to old voice_analysis structure
                  const voiceData = selectedAnalysis.result?.voice_analysis || selectedAnalysis.result?.voiceAnalysis;
                  const voiceFeatures = voiceData?.features || {};

                  // Combine all possible sources
                  const speechRate = librosaFeatures.speechRate || librosaIndicators.speaking_rate ||
                                     voiceFeatures.speaking_rate || 0;
                  const pitchMean = librosaFeatures.pitch?.mean || librosaIndicators.average_pitch ||
                                    voiceFeatures.pitch_mean || 0;
                  const pauseRatio = librosaFeatures.pauseRatio || librosaIndicators.pause_ratio ||
                                     voiceFeatures.pause_ratio || 0;
                  const voiceStability = librosaFeatures.voiceStability || librosaIndicators.voice_stability || 0;

                  const hasData = speechRate > 0 || pitchMean > 0 || pauseRatio > 0 || voiceStability > 0;

                  if (hasData) {
                    return (
                      <div className="space-y-2 text-sm">
                        {speechRate > 0 && (
                          <div className="flex justify-between">
                            <span className="text-gray-600">말하기 속도:</span>
                            <span className="font-medium">{speechRate.toFixed(2)} wpm</span>
                          </div>
                        )}
                        {pitchMean > 0 && (
                          <div className="flex justify-between">
                            <span className="text-gray-600">음높이:</span>
                            <span className="font-medium">{pitchMean.toFixed(1)} Hz</span>
                          </div>
                        )}
                        {pauseRatio > 0 && (
                          <div className="flex justify-between">
                            <span className="text-gray-600">휴지 비율:</span>
                            <span className="font-medium">{(pauseRatio * 100).toFixed(1)}%</span>
                          </div>
                        )}
                        {voiceStability > 0 && (
                          <div className="flex justify-between">
                            <span className="text-gray-600">음성 안정성:</span>
                            <span className="font-medium">{(voiceStability * 100).toFixed(0)}%</span>
                          </div>
                        )}
                      </div>
                    );
                  } else {
                    return <p className="text-sm text-gray-500">음성 분석 데이터가 없습니다</p>;
                  }
                })()}
              </div>
            </div>

            {/* SincNet 음성 분석 */}
            {selectedAnalysis.result?.sincnet_analysis && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <h3 className="font-semibold text-purple-900 mb-2">🎯 SincNet 음성 분석</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-purple-700">우울 확률:</span>
                    <div className="mt-1">
                      <div className="flex items-center">
                        <div className="flex-1 bg-purple-200 rounded-full h-2 mr-2">
                          <div
                            className="bg-purple-600 h-2 rounded-full"
                            style={{ width: `${(selectedAnalysis.result.sincnet_analysis.depression_probability || 0) * 100}%` }}
                          />
                        </div>
                        <span className="font-medium text-purple-900">
                          {((selectedAnalysis.result.sincnet_analysis.depression_probability || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                  <div>
                    <span className="text-purple-700">불면증 확률:</span>
                    <div className="mt-1">
                      <div className="flex items-center">
                        <div className="flex-1 bg-purple-200 rounded-full h-2 mr-2">
                          <div
                            className="bg-purple-600 h-2 rounded-full"
                            style={{ width: `${(selectedAnalysis.result.sincnet_analysis.insomnia_probability || 0) * 100}%` }}
                          />
                        </div>
                        <span className="font-medium text-purple-900">
                          {((selectedAnalysis.result.sincnet_analysis.insomnia_probability || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                  <div>
                    <span className="text-purple-700">신뢰도:</span>
                    <span className="ml-2 font-medium text-purple-900">
                      {((selectedAnalysis.result.sincnet_analysis.confidence || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-purple-700">위험 수준:</span>
                    <span className={`ml-2 font-medium ${
                      selectedAnalysis.result.sincnet_analysis.risk_level === 'high' ? 'text-red-600' :
                      selectedAnalysis.result.sincnet_analysis.risk_level === 'medium' ? 'text-yellow-600' :
                      'text-green-600'
                    }`}>
                      {selectedAnalysis.result.sincnet_analysis.risk_level === 'high' ? '높음' :
                       selectedAnalysis.result.sincnet_analysis.risk_level === 'medium' ? '중간' : '낮음'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* 텍스트 분석 - 주요 발견사항 */}
            {selectedAnalysis.result?.text_analysis?.analysis?.key_findings && (
              <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
                <h3 className="font-semibold text-indigo-900 mb-2">📝 대화 내용 분석</h3>
                <ul className="space-y-1 text-indigo-800">
                  {selectedAnalysis.result.text_analysis.analysis.key_findings.map((finding: string, index: number) => (
                    <li key={index} className="flex items-start">
                      <span className="mr-2">•</span>
                      <span className="text-sm">{finding}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* AI 종합 해석 (GPT-4o) */}
            {selectedAnalysis.result?.ai_narrative && (
              <div className="bg-gradient-to-br from-purple-50 to-indigo-50 border border-purple-200 rounded-lg p-6">
                <div className="flex items-center mb-4">
                  <div className="flex items-center space-x-2">
                    <span className="text-2xl">🤖</span>
                    <h3 className="font-semibold text-purple-900">AI 전문가 종합 해석</h3>
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      selectedAnalysis.result.ai_narrative.status === 'success'
                        ? 'bg-green-100 text-green-700 border border-green-200'
                        : 'bg-yellow-100 text-yellow-700 border border-yellow-200'
                    }`}>
                      {selectedAnalysis.result.ai_narrative.model === 'gpt-4o' ? 'GPT-4o' : '규칙기반'}
                    </span>
                  </div>
                </div>

                <div className="space-y-4">
                  {/* 종합 해석 */}
                  {selectedAnalysis.result.ai_narrative.narrative?.comprehensive_interpretation && (
                    <div className="bg-white rounded-lg p-4 border border-purple-100">
                      <h4 className="font-medium text-purple-800 mb-2">📋 종합 해석</h4>
                      <p className="text-gray-800 text-sm leading-relaxed">
                        {selectedAnalysis.result.ai_narrative.narrative.comprehensive_interpretation}
                      </p>
                    </div>
                  )}

                  {/* 주요 발견사항 */}
                  {selectedAnalysis.result.ai_narrative.narrative?.key_findings?.length > 0 && (
                    <div className="bg-white rounded-lg p-4 border border-purple-100">
                      <h4 className="font-medium text-purple-800 mb-3">🔍 주요 발견사항</h4>
                      <ul className="space-y-2">
                        {selectedAnalysis.result.ai_narrative.narrative.key_findings.map((finding: string, index: number) => (
                          <li key={index} className="flex items-start text-sm">
                            <span className="mr-2 text-purple-600 font-bold">•</span>
                            <span className="text-gray-800">{finding}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* 임상적 통찰 */}
                  {selectedAnalysis.result.ai_narrative.narrative?.clinical_insights && (
                    <div className="bg-white rounded-lg p-4 border border-purple-100">
                      <h4 className="font-medium text-purple-800 mb-2">🩺 임상적 통찰</h4>
                      <p className="text-gray-800 text-sm leading-relaxed">
                        {selectedAnalysis.result.ai_narrative.narrative.clinical_insights}
                      </p>
                    </div>
                  )}

                  {/* 상황별 분석 */}
                  {selectedAnalysis.result.ai_narrative.narrative?.contextual_analysis && (
                    <div className="bg-white rounded-lg p-4 border border-purple-100">
                      <h4 className="font-medium text-purple-800 mb-2">📊 상황별 분석</h4>
                      <p className="text-gray-800 text-sm leading-relaxed">
                        {selectedAnalysis.result.ai_narrative.narrative.contextual_analysis}
                      </p>
                    </div>
                  )}

                  {/* 모니터링 권장사항 */}
                  {selectedAnalysis.result.ai_narrative.narrative?.monitoring_recommendations && (
                    <div className="bg-white rounded-lg p-4 border border-purple-100">
                      <h4 className="font-medium text-purple-800 mb-2">📈 모니터링 권장사항</h4>
                      <p className="text-gray-800 text-sm leading-relaxed">
                        {selectedAnalysis.result.ai_narrative.narrative.monitoring_recommendations}
                      </p>
                    </div>
                  )}

                  {/* 생성 정보 */}
                  <div className="flex items-center justify-between text-xs text-purple-600 mt-4 pt-4 border-t border-purple-100">
                    <span>
                      생성 모델: {selectedAnalysis.result.ai_narrative.model === 'gpt-4o' ? 'GPT-4o' : '규칙 기반'}
                    </span>
                    {selectedAnalysis.result.ai_narrative.generated_at && (
                      <span>
                        생성 시간: {new Date(selectedAnalysis.result.ai_narrative.generated_at).toLocaleString('ko-KR')}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 권장 대응 */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="font-semibold text-green-900 mb-2">💡 권장 대응</h3>
              {(selectedAnalysis.result?.risk_assessment?.recommendations?.length > 0 ||
                selectedAnalysis.result?.recommendations?.length > 0) ? (
                <ul className="space-y-1 text-green-800">
                  {(selectedAnalysis.result?.risk_assessment?.recommendations ||
                    selectedAnalysis.result?.recommendations || []).slice(0, 6).map((rec: string, index: number) => (
                    <li key={index} className="flex items-start">
                      <span className="mr-2">•</span>
                      <span className="text-sm">{rec}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <ul className="space-y-1 text-green-800">
                  <li className="flex items-start">
                    <span className="mr-2">•</span>
                    <span className="text-sm">규칙적인 통화를 유지하여 지속적인 모니터링을 하시기 바랍니다.</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2">•</span>
                    <span className="text-sm">긍정적인 대화 주제로 어르신과 소통하시면 도움이 됩니다.</span>
                  </li>
                </ul>
              )}
            </div>

            {/* 최종 요약 */}
            {selectedAnalysis.result?.finalSummary && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h3 className="font-semibold text-yellow-900 mb-2">📝 최종 요약</h3>
                <p className="text-yellow-800 text-sm">
                  {selectedAnalysis.result.finalSummary}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 분석 선택 옵션 (여러 분석이 있는 경우) */}
      {analyses.length > 1 && (
        <div className="mt-6 bg-white rounded-xl p-4 md:p-6 shadow-sm">
          <h4 className="text-lg font-semibold mb-4 text-gray-900">
            📋 다른 분석 결과 보기
          </h4>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {analyses.slice(0, 6).map((analysis, index) => {
              const isSelected = selectedAnalysis?.analysisId === analysis.analysisId;
              const recordedDate = analysis.recordedAt ? new Date(analysis.recordedAt) : new Date();
              
              return (
                <button
                  key={analysis.analysisId}
                  onClick={() => setSelectedAnalysis(analysis)}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    isSelected 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="text-left">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-600">
                        분석 #{index + 1}
                      </span>
                      {isSelected && (
                        <span className="text-blue-600 text-sm">✓ 선택됨</span>
                      )}
                    </div>
                    <div className="text-sm text-gray-500">
                      {recordedDate.toLocaleDateString('ko-KR')}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {analysis.seniorName || '알 수 없음'}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
});

export default ComprehensiveAnalysisSection;
