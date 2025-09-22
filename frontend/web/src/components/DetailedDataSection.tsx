'use client';

import { useState, useEffect, useMemo, memo } from 'react';
import { useApiData } from '../hooks/useApiData';
import { AnalysisCard } from './AnalysisCard';
import LoadingSpinner from './LoadingSpinner';
import { StatusIndicator } from './StatusIndicator';

interface DetailedDataSectionProps {
  className?: string;
  selectedAnalysis?: any;
  onAnalysisSelect?: (analysis: any) => void;
}

const DetailedDataSection = memo(function DetailedDataSection({
  className = '',
  selectedAnalysis: propSelectedAnalysis,
  onAnalysisSelect
}: DetailedDataSectionProps) {
  console.log('🚀 DetailedDataSection Component Mounted');
  const { analyses, isLoading, error } = useApiData();
  console.log('📊 DetailedDataSection - Data from hook:', {
    analysesCount: analyses?.length,
    isLoading,
    error,
    firstAnalysis: analyses?.[0]
  });
  const [localSelectedAnalysis, setLocalSelectedAnalysis] = useState<any>(null);

  // props에서 받은 selectedAnalysis가 있으면 사용, 없으면 로컬 상태 사용
  const selectedAnalysis = propSelectedAnalysis || localSelectedAnalysis;
  const setSelectedAnalysis = onAnalysisSelect || setLocalSelectedAnalysis;

  // 최신 분석 결과 선택 (props로 받지 않은 경우에만)
  useEffect(() => {
    if (!propSelectedAnalysis) {
      if (analyses.length > 0) {
        setSelectedAnalysis(analyses[0]);
      } else {
        setSelectedAnalysis(null);
      }
    }
  }, [analyses, propSelectedAnalysis, setSelectedAnalysis]);

  // selectedAnalysis 변경 추적
  useEffect(() => {
    if (selectedAnalysis) {
      console.log('✅ DetailedDataSection - selectedAnalysis 변경됨:', {
        analysisId: selectedAnalysis.analysisId,
        seniorName: selectedAnalysis.seniorName,
        recordedAt: selectedAnalysis.recordedAt,
        hasResult: !!selectedAnalysis.result,
        hasMentalHealth: !!selectedAnalysis.result?.mentalHealthAnalysis,
        hasCoreIndicators: !!selectedAnalysis.result?.coreIndicators
      });
    }
  }, [selectedAnalysis]);


  // 정신건강 점수 추출 - AI가 분석한 실제 점수 사용
  const mentalHealthScores = useMemo(() => {
    console.log('🔄 RECALCULATING mentalHealthScores for analysisId:', selectedAnalysis?.analysisId);
    try {
      // 디버깅을 위한 전체 분석 데이터 로깅
      console.log('🔍 DetailedDataSection - 전체 분석 데이터:', selectedAnalysis);
      console.log('📊 DetailedDataSection - result 구조:', selectedAnalysis?.result);
      console.log('🎵 DetailedDataSection - analysisMethodologies:', selectedAnalysis?.result?.analysisMethodologies);
      console.log('🎤 DetailedDataSection - librosa:', selectedAnalysis?.result?.analysisMethodologies?.librosa);

    // 먼저 AI가 분석한 mentalHealthAnalysis 데이터 확인
    const mentalHealth = selectedAnalysis?.result?.mentalHealthAnalysis;
    console.log('🧠 DetailedDataSection - mentalHealthAnalysis:', mentalHealth);
    console.log('🧠 DetailedDataSection - mentalHealthAnalysis keys:', mentalHealth ? Object.keys(mentalHealth) : 'null');

    if (mentalHealth) {
      // AI가 이미 분석한 점수가 있으면 그것을 사용
      const getScore = (value: any): number => {
        console.log('점수 추출 시도:', { value, type: typeof value, keys: value && typeof value === 'object' ? Object.keys(value) : null });
        if (typeof value === 'number') {
          console.log('✅ 숫자 값 발견:', value);
          return Math.max(0, Math.min(100, value)); // 0-100 범위로 제한
        }
        if (typeof value === 'object' && value !== null) {
          if (value.score !== undefined) {
            console.log('✅ score 속성 발견:', value.score);
            return Math.max(0, Math.min(100, value.score));
          }
          if (value.value !== undefined) {
            console.log('✅ value 속성 발견:', value.value);
            return Math.max(0, Math.min(100, value.value * 100)); // 0-1 범위를 0-100으로 변환
          }
          // 객체의 다른 속성들 확인
          console.log('⚠️ 객체에서 score/value 찾을 수 없음, 모든 속성:', value);
        }
        console.log('❌ 점수 추출 실패, 기본값 0 반환');
        return 0;
      };

      const scores = {
        depression: Math.round(getScore(mentalHealth.depression)),
        cognitive: Math.round(getScore(mentalHealth.cognitive)),
        anxiety: Math.round(getScore((mentalHealth as any).anxiety || (mentalHealth as any).anxietyLevel))
      };

      console.log('✅ mentalHealthAnalysis에서 추출한 점수 (analysisId: ' + selectedAnalysis?.analysisId + '):', scores);

      // 모든 점수가 0인 경우 경고 로그
      const totalScore = Object.values(scores).reduce((sum, score) => sum + score, 0);
      if (totalScore === 0) {
        console.warn('⚠️ 모든 정신건강 점수가 0점입니다. mentalHealthAnalysis 데이터 구조를 확인해주세요:', mentalHealth);
      }

      return scores;
    }

    // mentalHealthAnalysis가 없으면 coreIndicators를 기반으로 점수 계산
    const coreIndicators = selectedAnalysis?.result?.coreIndicators;
    console.log('📈 coreIndicators:', coreIndicators);

    // legacy 데이터 확인
    const legacy = selectedAnalysis?.result?.legacy;
    console.log('🏛️ legacy 데이터:', legacy);

    // integratedResults 확인
    const integratedResults = selectedAnalysis?.result?.integratedResults;
    console.log('🔗 integratedResults:', integratedResults);

    // risk_assessment 확인
    const riskAssessment = selectedAnalysis?.result?.risk_assessment;
    console.log('⚠️ risk_assessment:', riskAssessment);

    // analysisMethodologies 확인 (librosa 포함)
    const methodologies = selectedAnalysis?.result?.analysisMethodologies;
    console.log('🔬 analysisMethodologies:', methodologies);

    // librosa에서 직접 점수 확인
    if (methodologies?.librosa) {
      console.log('🎵 librosa 데이터 상세:', methodologies.librosa);

      // librosa에서 정신건강 점수 추출 시도 - librosa 자체는 음성 데이터만 포함
      // 정신건강 점수는 mentalHealthAnalysis에서 가져와야 함
    }

    if (!coreIndicators) {
      // 기본값 반환 (데이터가 없는 경우)
      console.log('⚠️ 정신건강 점수 데이터를 찾을 수 없음 - 기본값 반환');
      return {
        depression: 0,
        cognitive: 0,
        anxiety: 0
      };
    }

    // coreIndicators의 값을 직접 사용 (이미 0-1 범위의 점수)
    const getDRIScore = () => {
      const dri = coreIndicators?.DRI;
      console.log('📊 DRI 원본:', dri);
      const value = typeof dri === 'number' ? dri : (dri?.value || 0);
      const score = Math.round(value * 100);
      console.log('📊 DRI 계산:', { dri, value, score });
      return score;
    };

    const getCFLScore = () => {
      const cfl = coreIndicators?.CFL;
      console.log('📊 CFL 원본:', cfl);
      const value = typeof cfl === 'number' ? cfl : (cfl?.value || 0);
      const score = Math.round(value * 100);
      console.log('📊 CFL 계산:', { cfl, value, score });
      return score;
    };

    const getESScore = () => {
      const es = coreIndicators?.ES;
      console.log('📊 ES 원본:', es);
      const value = typeof es === 'number' ? es : (es?.value || 0);
      const score = Math.round(value * 100);
      console.log('📊 ES 계산:', { es, value, score });
      return score;
    };


    // coreIndicators를 적절하게 매핑 (백엔드 실제 데이터 구조에 맞춤)
    const finalScores = {
      depression: getDRIScore(),
      cognitive: getCFLScore(),
      anxiety: getESScore()
    };
    console.log('📈 최종 계산된 정신건강 점수:', finalScores);

    // 모든 점수가 0인 경우 추가 디버깅
    const totalFinalScore = Object.values(finalScores).reduce((sum, score) => sum + score, 0);
    if (totalFinalScore === 0) {
      console.warn('⚠️ coreIndicators에서도 모든 점수가 0점입니다.');
      console.warn('⚠️ coreIndicators 전체 구조:', JSON.stringify(coreIndicators, null, 2));
      console.warn('⚠️ selectedAnalysis.result 전체 구조:', JSON.stringify(selectedAnalysis?.result, null, 2));
    }

    return finalScores;
    } catch (error) {
      console.error('❌ DetailedDataSection - Error extracting mental health scores:', error);
      return {
        depression: 0,
        cognitive: 0,
        anxiety: 0
      };
    }
  }, [selectedAnalysis, selectedAnalysis?.analysisId]);

  // 평균 점수 계산
  const averageScore = useMemo(() => {
    if (!mentalHealthScores) return 0;
    const scores = [mentalHealthScores.depression, mentalHealthScores.cognitive, mentalHealthScores.anxiety];
    const avg = Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length);
    console.log('📊 평균 점수 계산:', { scores, avg, analysisId: selectedAnalysis?.analysisId });
    return avg;
  }, [mentalHealthScores, selectedAnalysis?.analysisId]);

  // 로딩 상태 처리
  if (isLoading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="text-center py-12">
          <LoadingSpinner 
            type="dots" 
            message="세부 데이터를 불러오는 중..." 
            size="lg"
          />
        </div>
      </div>
    );
  }

  // 에러 상태 처리
  if (error) {
    return (
      <div className={`space-y-6 ${className}`}>
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
      <div className={`space-y-6 ${className}`}>
        <div className="text-center py-12">
          <div className="text-6xl mb-4">📊</div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">분석 데이터가 없습니다</h3>
          <p className="text-gray-600">통화 기록을 추가하면 세부 데이터를 확인할 수 있습니다</p>
        </div>
      </div>
    );
  }

  console.log('🔍🔍 DetailedDataSection Render - analyses:', analyses.length);
  console.log('🔍🔍 DetailedDataSection Render - selectedAnalysis:', selectedAnalysis);
  console.log('🔍🔍 DetailedDataSection Render - mentalHealthScores:', mentalHealthScores);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 분석 선택 섹션 */}
      {analyses.length > 1 && (
        <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
          <h3 className="text-lg font-semibold mb-4 text-gray-900">
            📋 분석 결과 선택
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {analyses.slice(0, 6).map((analysis, index) => {
              const isSelected = selectedAnalysis?.analysisId === analysis.analysisId;
              const recordedDate = analysis.recordedAt ? new Date(analysis.recordedAt) : new Date();
              
              // 해당 분석의 평균 점수 계산 - AI가 분석한 실제 점수 사용
              let analysisScores = [0, 0, 0];
              const analysisMentalHealth = analysis.result?.mentalHealthAnalysis;

              if (analysisMentalHealth) {
                // AI가 이미 분석한 점수가 있으면 그것을 사용
                const getAnalysisScore = (value: any): number => {
                  if (typeof value === 'number') return value;
                  if (typeof value === 'object' && value?.score !== undefined) return value.score;
                  return 0;
                };

                analysisScores = [
                  Math.round(getAnalysisScore(analysisMentalHealth.depression)),
                  Math.round(getAnalysisScore(analysisMentalHealth.cognitive)),
                  Math.round(getAnalysisScore((analysisMentalHealth as any).anxiety))
                ];
              } else {
                // mentalHealthAnalysis가 없으면 coreIndicators 직접 사용
                const analysisIndicators = analysis.result?.coreIndicators;
                if (analysisIndicators) {
                  const driValue = typeof analysisIndicators.DRI === 'number' ? analysisIndicators.DRI : (analysisIndicators.DRI?.value || 0);
                  const cflValue = typeof analysisIndicators.CFL === 'number' ? analysisIndicators.CFL : (analysisIndicators.CFL?.value || 0);
                  const esValue = typeof analysisIndicators.ES === 'number' ? analysisIndicators.ES : (analysisIndicators.ES?.value || 0);

                  analysisScores = [
                    Math.round(driValue * 100),
                    Math.round(cflValue * 100),
                    Math.round(esValue * 100)
                  ];
                }
              }
              const analysisAverageScore = Math.round(analysisScores.reduce((sum, score) => sum + score, 0) / analysisScores.length);
              
              return (
                <button
                  key={analysis.analysisId}
                  onClick={() => {
                    console.log('🔄 DetailedDataSection - 분석 변경:', analysis.analysisId);
                    console.log('📊 새로운 분석 데이터:', analysis);
                    console.log('🎯 사용 중인 setSelectedAnalysis:', onAnalysisSelect ? 'props (공유)' : 'local');
                    setSelectedAnalysis(analysis);
                  }}
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
                      <StatusIndicator 
                        score={analysisAverageScore} 
                        size="sm" 
                        showLabel={false}
                      />
                    </div>
                    <div className="text-sm text-gray-500">
                      {recordedDate.toLocaleDateString('ko-KR')}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {analysis.seniorName || '알 수 없음'}
                    </div>
                    {isSelected && (
                      <div className="mt-2 text-blue-600 text-sm font-medium">
                        ✓ 선택됨
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* 선택된 분석의 세부 데이터 */}
      {selectedAnalysis && (
        <div className="grid grid-cols-1 gap-6">
          {/* 정신건강 점수 상세 */}
          <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-gray-900">
                🧠 정신건강 점수
              </h3>
              <StatusIndicator
                score={averageScore}
                size="md"
                showLabel={true}
              />
            </div>

            {mentalHealthScores ? (
              <div className="space-y-4">
                {/* 주요 점수들 */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-red-50 rounded-lg p-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-600 mb-1">
                        {mentalHealthScores.depression}
                      </div>
                      <div className="text-sm text-red-700 font-medium">우울감</div>
                    </div>
                  </div>
                  <div className="bg-blue-50 rounded-lg p-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600 mb-1">
                        {mentalHealthScores.cognitive}
                      </div>
                      <div className="text-sm text-blue-700 font-medium">인지기능</div>
                    </div>
                  </div>
                  <div className="bg-yellow-50 rounded-lg p-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-yellow-600 mb-1">
                        {mentalHealthScores.anxiety}
                      </div>
                      <div className="text-sm text-yellow-700 font-medium">불안감</div>
                    </div>
                  </div>
                </div>

              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-2">🧠</div>
                <p>정신건강 점수 데이터가 없습니다</p>
              </div>
            )}
          </div>

          {/* 위험도 평가 */}
          {selectedAnalysis.result?.risk_assessment && (
            <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                ⚠️ 위험도 평가
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(selectedAnalysis.result.risk_assessment).map(([key, value]: [string, any]) => (
                  <div key={key} className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm font-medium text-gray-600 mb-2">
                      {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                    </div>
                    <div className="text-lg font-semibold text-gray-900">
                      {typeof value === 'object' ? JSON.stringify(value) : value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 핵심 지표 (Core Indicators) */}
          {selectedAnalysis.result?.coreIndicators && (
            <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                📊 핵심 지표 (Core Indicators)
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {Object.entries(selectedAnalysis.result.coreIndicators).map(([key, value]: [string, any]) => {
                  const score = typeof value === 'number' ? value : (value?.value || 0);
                  const percentage = Math.round(score * 100);
                  return (
                    <div key={key} className="bg-blue-50 rounded-lg p-4 text-center">
                      <div className="text-lg font-bold text-blue-600 mb-1">
                        {key}
                      </div>
                      <div className="text-2xl font-bold text-blue-900">
                        {percentage}
                      </div>
                      <div className="text-xs text-blue-700">점</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 음성 분석 결과 (Librosa) */}
          {selectedAnalysis.result?.analysisMethodologies?.librosa && (
            <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                🎵 음성 분석 결과
              </h3>
              <div className="space-y-4">
                {selectedAnalysis.result.analysisMethodologies.librosa.indicators && (
                  <div>
                    <h4 className="text-lg font-medium text-gray-800 mb-3">음성 특성 지표</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {Object.entries(selectedAnalysis.result.analysisMethodologies.librosa.indicators).map(([key, value]: [string, any]) => (
                        <div key={key} className="bg-purple-50 rounded-lg p-3">
                          <div className="text-sm font-medium text-purple-700">
                            {key.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1').toLowerCase()}
                          </div>
                          <div className="text-lg font-semibold text-purple-900">
                            {typeof value === 'number' ? value.toFixed(3) : JSON.stringify(value)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 음성 특성 분석 */}
          {(selectedAnalysis.result?.voice_analysis || selectedAnalysis.result?.voiceAnalysis) && (
            <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                🎤 음성 특성 분석
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(selectedAnalysis.result.voice_analysis || selectedAnalysis.result.voiceAnalysis || {}).map(([key, value]: [string, any]) => (
                  <div key={key} className="bg-green-50 rounded-lg p-4">
                    <div className="text-sm font-medium text-green-700 mb-2">
                      {key.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1')}
                    </div>
                    <div className="text-lg font-semibold text-green-900">
                      {typeof value === 'number' ? value.toFixed(3) :
                       typeof value === 'object' ? JSON.stringify(value) : value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 통합 결과 */}
          {selectedAnalysis.result?.integratedResults && (
            <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                🔗 통합 분석 결과
              </h3>
              <div className="space-y-4">
                {Object.entries(selectedAnalysis.result.integratedResults).map(([key, value]: [string, any]) => (
                  <div key={key} className="border-l-4 border-indigo-500 pl-4">
                    <div className="text-sm font-medium text-indigo-700 mb-1">
                      {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                    </div>
                    <div className="text-gray-900">
                      {typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 전사 텍스트 */}
          {selectedAnalysis.result?.transcription?.text && (
            <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                📝 통화 전사 텍스트
              </h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-gray-800 leading-relaxed">
                  {selectedAnalysis.result.transcription.text}
                </div>
                {selectedAnalysis.result.transcription.confidence && (
                  <div className="mt-3 text-sm text-gray-600">
                    신뢰도: {Math.round(selectedAnalysis.result.transcription.confidence * 100)}%
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 요약 및 추천사항 */}
          {(selectedAnalysis.result?.summary || selectedAnalysis.result?.recommendations) && (
            <div className="bg-white rounded-xl p-4 md:p-6 shadow-lg">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                💡 요약 및 추천사항
              </h3>
              <div className="space-y-6">
                {selectedAnalysis.result.summary && (
                  <div>
                    <h4 className="text-lg font-medium text-gray-800 mb-3">분석 요약</h4>
                    <div className="bg-blue-50 rounded-lg p-4">
                      <p className="text-gray-800 leading-relaxed">
                        {selectedAnalysis.result.summary}
                      </p>
                    </div>
                  </div>
                )}
                {selectedAnalysis.result.recommendations && Array.isArray(selectedAnalysis.result.recommendations) && (
                  <div>
                    <h4 className="text-lg font-medium text-gray-800 mb-3">추천사항</h4>
                    <div className="space-y-2">
                      {selectedAnalysis.result.recommendations.map((recommendation: string, index: number) => (
                        <div key={index} className="flex items-start space-x-3 bg-green-50 rounded-lg p-3">
                          <div className="text-green-600 font-semibold">{index + 1}.</div>
                          <p className="text-gray-800">{recommendation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Legacy 데이터 - 시각화된 카드들 */}
          {selectedAnalysis.result?.legacy && (
            <div className="space-y-6">
              <h3 className="text-xl font-semibold text-gray-900 mb-6 text-center">
                🏛️ Legacy 분석 데이터
              </h3>

              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {/* 1. 건강 지표 대시보드 */}
                {selectedAnalysis.result.legacy.indicators && (
                  <div className="bg-white rounded-xl p-6 shadow-lg border border-blue-100">
                    <h4 className="text-lg font-semibold text-blue-900 mb-4 flex items-center">
                      🧠 인지 & 정신건강 지표
                    </h4>
                    <div className="space-y-4">
                      {Object.entries(selectedAnalysis.result.legacy.indicators).map(([key, value]: [string, any]) => {
                        const percentage = Math.round(value * 100);
                        const getStatusColor = (val: number) => {
                          if (val >= 70) return 'text-green-600 bg-green-100';
                          if (val >= 50) return 'text-yellow-600 bg-yellow-100';
                          return 'text-red-600 bg-red-100';
                        };

                        return (
                          <div key={key} className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex justify-between items-center mb-2">
                                <span className="text-sm font-medium text-gray-700">{key}</span>
                                <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(percentage)}`}>
                                  {percentage}%
                                </span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div
                                  className={`h-2 rounded-full transition-all duration-300 ${
                                    percentage >= 70 ? 'bg-green-500' :
                                    percentage >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                                  }`}
                                  style={{ width: `${percentage}%` }}
                                ></div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 2. 음성 & 언어 분석 카드 */}
                {(selectedAnalysis.result.legacy.voice_analysis?.features || selectedAnalysis.result.legacy.text_analysis) && (
                  <div className="bg-white rounded-xl p-6 shadow-lg border border-purple-100">
                    <h4 className="text-lg font-semibold text-purple-900 mb-4 flex items-center">
                      🎤 음성 & 언어 분석
                    </h4>
                    <div className="space-y-4">
                      {/* 음성 특성 */}
                      {selectedAnalysis.result.legacy.voice_analysis?.features && (
                        <div className="bg-purple-50 rounded-lg p-4">
                          <h5 className="font-medium text-purple-800 mb-3">음성 특성</h5>
                          <div className="grid grid-cols-2 gap-3 text-sm">
                            {selectedAnalysis.result.legacy.voice_analysis.features.pitch_mean && (
                              <div>
                                <span className="text-gray-600">피치:</span>
                                <span className="ml-2 font-medium">
                                  {Math.round(selectedAnalysis.result.legacy.voice_analysis.features.pitch_mean)}Hz
                                </span>
                              </div>
                            )}
                            {selectedAnalysis.result.legacy.voice_analysis.features.speaking_rate && (
                              <div>
                                <span className="text-gray-600">말하기 속도:</span>
                                <span className="ml-2 font-medium">
                                  {selectedAnalysis.result.legacy.voice_analysis.features.speaking_rate.toFixed(1)}/s
                                </span>
                              </div>
                            )}
                            {selectedAnalysis.result.legacy.voice_analysis.features.voice_quality && (
                              <div>
                                <span className="text-gray-600">음성 품질:</span>
                                <span className="ml-2 font-medium">
                                  {Math.round(selectedAnalysis.result.legacy.voice_analysis.features.voice_quality * 100)}%
                                </span>
                              </div>
                            )}
                            {selectedAnalysis.result.legacy.voice_analysis.features.pause_ratio && (
                              <div>
                                <span className="text-gray-600">일시정지 비율:</span>
                                <span className="ml-2 font-medium">
                                  {Math.round(selectedAnalysis.result.legacy.voice_analysis.features.pause_ratio * 100)}%
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* 감정 분석 */}
                      {selectedAnalysis.result.legacy.text_analysis?.analysis?.emotion_analysis && (
                        <div className="bg-blue-50 rounded-lg p-4">
                          <h5 className="font-medium text-blue-800 mb-3">감정 상태</h5>
                          <div className="space-y-2">
                            {Object.entries(selectedAnalysis.result.legacy.text_analysis.analysis.emotion_analysis)
                              .sort(([,a]: [string, any], [,b]: [string, any]) => b - a)
                              .slice(0, 3)
                              .map(([emotion, value]: [string, any]) => {
                                const emotionNames: {[key: string]: string} = {
                                  happiness: '기쁨',
                                  sadness: '슬픔',
                                  anger: '분노',
                                  fear: '두려움',
                                  surprise: '놀람',
                                  disgust: '혐오'
                                };
                                const percentage = Math.round(value * 100);
                                return (
                                  <div key={emotion} className="flex items-center justify-between">
                                    <span className="text-sm text-gray-700">{emotionNames[emotion] || emotion}</span>
                                    <div className="flex items-center space-x-2">
                                      <div className="w-16 bg-gray-200 rounded-full h-2">
                                        <div
                                          className="h-2 bg-blue-500 rounded-full transition-all duration-300"
                                          style={{ width: `${percentage}%` }}
                                        ></div>
                                      </div>
                                      <span className="text-xs text-gray-600 w-8">{percentage}%</span>
                                    </div>
                                  </div>
                                );
                              })}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 3. AI 권고사항 & 위험도 */}
                {(selectedAnalysis.result.legacy.risk_assessment || selectedAnalysis.result.legacy.report?.recommendations) && (
                  <div className="bg-white rounded-xl p-6 shadow-lg border border-green-100">
                    <h4 className="text-lg font-semibold text-green-900 mb-4 flex items-center">
                      ⚠️ 위험도 & AI 권고사항
                    </h4>
                    <div className="space-y-4">
                      {/* 전체 위험도 */}
                      {selectedAnalysis.result.legacy.risk_assessment?.overall_risk && (
                        <div className="bg-green-50 rounded-lg p-4">
                          <h5 className="font-medium text-green-800 mb-2">전체 위험도</h5>
                          <div className="flex items-center space-x-3">
                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                              selectedAnalysis.result.legacy.risk_assessment.overall_risk === 'low' ? 'bg-green-200 text-green-800' :
                              selectedAnalysis.result.legacy.risk_assessment.overall_risk === 'moderate' ? 'bg-yellow-200 text-yellow-800' :
                              'bg-red-200 text-red-800'
                            }`}>
                              {selectedAnalysis.result.legacy.risk_assessment.overall_risk === 'low' ? '낮음' :
                               selectedAnalysis.result.legacy.risk_assessment.overall_risk === 'moderate' ? '보통' : '높음'}
                            </span>
                          </div>
                        </div>
                      )}

                      {/* AI 권고사항 */}
                      {selectedAnalysis.result.legacy.risk_assessment?.recommendations && (
                        <div className="bg-blue-50 rounded-lg p-4">
                          <h5 className="font-medium text-blue-800 mb-3">AI 권고사항</h5>
                          <ul className="space-y-2">
                            {selectedAnalysis.result.legacy.risk_assessment.recommendations.slice(0, 3).map((rec: string, index: number) => (
                              <li key={index} className="flex items-start space-x-2">
                                <span className="text-blue-600 mt-1">•</span>
                                <span className="text-sm text-gray-700">{rec}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* SincNet 분석 결과 */}
                      {selectedAnalysis.result.legacy.sincnet_analysis && (
                        <div className="bg-purple-50 rounded-lg p-4">
                          <h5 className="font-medium text-purple-800 mb-3">AI 예측 분석</h5>
                          <div className="space-y-2 text-sm">
                            {selectedAnalysis.result.legacy.sincnet_analysis.depression_probability && (
                              <div className="flex justify-between">
                                <span className="text-gray-600">우울 확률:</span>
                                <span className="font-medium">
                                  {Math.round(selectedAnalysis.result.legacy.sincnet_analysis.depression_probability * 100)}%
                                </span>
                              </div>
                            )}
                            {selectedAnalysis.result.legacy.sincnet_analysis.insomnia_probability && (
                              <div className="flex justify-between">
                                <span className="text-gray-600">불면 확률:</span>
                                <span className="font-medium">
                                  {Math.round(selectedAnalysis.result.legacy.sincnet_analysis.insomnia_probability * 100)}%
                                </span>
                              </div>
                            )}
                            {selectedAnalysis.result.legacy.sincnet_analysis.confidence && (
                              <div className="flex justify-between">
                                <span className="text-gray-600">신뢰도:</span>
                                <span className="font-medium">
                                  {Math.round(selectedAnalysis.result.legacy.sincnet_analysis.confidence * 100)}%
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* 대화 내용 (별도 섹션) */}
              {selectedAnalysis.result.legacy.transcription && (
                <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-100 mt-6">
                  <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    📝 대화 내용
                  </h4>
                  <div className="bg-gray-50 rounded-lg p-4 max-h-40 overflow-y-auto">
                    <p className="text-sm text-gray-700 leading-relaxed">
                      {selectedAnalysis.result.legacy.transcription.replace(/▁/g, ' ').trim()}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

    </div>
  );
});

export default DetailedDataSection;
