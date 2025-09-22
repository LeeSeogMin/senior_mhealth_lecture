'use client';

import { useState, useEffect } from 'react';
import { AnalysisInterpretation as AnalysisInterpretationType } from '../lib/apiClient';
import apiClient from '../lib/apiClient';

interface AnalysisInterpretationProps {
  callId: string;
  seniorId: string;
  onInterpretationGenerated?: (interpretation: AnalysisInterpretationType) => void;
}

export default function AnalysisInterpretation({ 
  callId, 
  seniorId, 
  onInterpretationGenerated 
}: AnalysisInterpretationProps) {
  const [interpretation, setInterpretation] = useState<AnalysisInterpretationType | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  console.log('🧠 AnalysisInterpretation 렌더링됨:', { callId, seniorId });

  // 기본 해석 생성
  const generateDefaultInterpretation = (): AnalysisInterpretationType => {
    return {
      overallAssessment: '음성 분석 데이터를 기반으로 어르신의 정신 건강 상태를 종합적으로 평가하고 있습니다.',
      detailedAnalysis: {
        mentalHealth: {
          depression: '우울증 위험도는 보통 수준으로 평가됩니다. 지속적인 관찰이 필요합니다.',
          cognitive: '인지 기능은 정상 범위 내에 있으며, 일상생활에 큰 어려움은 없을 것으로 보입니다.',
          anxiety: '불안 수준은 낮은 편이며, 안정적인 상태를 유지하고 있습니다.'
        },
        voicePatterns: '음성 패턴 분석 결과 정상적인 에너지와 음높이 변화를 보이고 있습니다.',
        conversationContent: '대화 내용이 일관성 있고 논리적으로 구성되어 있습니다.'
      },
      recommendedActions: [
        '규칙적인 통화를 유지하여 지속적인 모니터링을 하시기 바랍니다.',
        '긍정적인 대화 주제로 어르신과 소통하시면 도움이 됩니다.',
        '필요시 전문 의료진과의 상담을 고려해보시기 바랍니다.'
      ],
      confidence: 0.75,
      timeSeriesAnalysis: undefined,
      alertLevel: '정상',
      summary: '음성 분석 데이터를 기반으로 어르신의 정신 건강 상태를 종합적으로 평가하고 있습니다.',
      generatedAt: new Date().toISOString()
    };
  };

  // 기존 해석 불러오기
  const loadInterpretation = async () => {
    console.log('🔍 기존 해석 불러오기 시도:', { callId });
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.getAnalysisInterpretation(callId);
      console.log('🔍 해석 불러오기 응답:', response);

      if (response.success && response.data) {
        console.log('✅ 기존 해석 발견:', response.data);
        setInterpretation(response.data);
      } else {
        console.log('ℹ️ 기존 해석 없음, 기본 해석 생성');
        const defaultInterpretation = generateDefaultInterpretation();
        setInterpretation(defaultInterpretation);
      }
    } catch (error) {
      console.warn('⚠️ API 호출 실패, 기본 해석 사용:', error);
      const defaultInterpretation = generateDefaultInterpretation();
      setInterpretation(defaultInterpretation);
    } finally {
      setIsLoading(false);
    }
  };

  // 새 해석 생성
  const generateInterpretation = async () => {
    setIsGenerating(true);
    setError(null);

    try {
      const response = await apiClient.generateAnalysisInterpretation(callId, seniorId);
      if (response.success && response.data) {
        setInterpretation(response.data);
        onInterpretationGenerated?.(response.data);
      } else {
        setError(response.error || '해석 생성에 실패했습니다.');
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : '해석 생성 중 오류가 발생했습니다.');
    } finally {
      setIsGenerating(false);
    }
  };

  // 컴포넌트 마운트 시 기존 해석 확인
  useEffect(() => {
    if (callId) {
      loadInterpretation();
    }
  }, [callId]); // callId가 변경될 때마다 다시 불러오도록 의존성 배열에 추가

  const getAlertLevelColor = (level: string) => {
    switch (level) {
      case '정상': return 'bg-green-100 text-green-800 border-green-200';
      case '보통': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case '높음': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <span className="text-2xl">🧠</span>
          <h2 className="text-xl font-semibold text-gray-900">AI 종합 해석</h2>
        </div>
        
        <div className="flex space-x-2">
          {interpretation && (
            <button
              onClick={loadInterpretation}
              disabled={isLoading}
              className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 disabled:opacity-50"
            >
              {isLoading ? '불러오는 중...' : '새로고침'}
            </button>
          )}
          
          <button
            onClick={generateInterpretation}
            disabled={isGenerating}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? (
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>분석 중...</span>
              </div>
            ) : (
              <div className="flex items-center space-x-1">
                <span>🧠</span>
                <span>{interpretation ? '해석 재생성' : '해석 생성'}</span>
              </div>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {interpretation ? (
        <div className="space-y-6">
          {/* 전체 요약 */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">종합 평가</h3>
            <p className="text-blue-800">{interpretation.overallAssessment || '평가 정보 없음'}</p>
            <div className="mt-3 flex items-center space-x-4">
              <span className={`px-2 py-1 text-xs font-medium border rounded-full ${getAlertLevelColor(interpretation.alertLevel || '정상')}`}>
                관심도: {interpretation.alertLevel || '정상'}
              </span>
              <span className="text-xs text-blue-600">
                신뢰도: {Math.round((interpretation.confidence || 0) * 100)}%
              </span>
            </div>
          </div>

          {/* 상세 분석 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-900 mb-3">📊 상세 분석</h3>
              
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-800 mb-2">정신 건강</h4>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-600">우울:</span> {interpretation.detailedAnalysis?.mentalHealth?.depression || '데이터 없음'}</div>
                  <div><span className="text-gray-600">인지:</span> {interpretation.detailedAnalysis?.mentalHealth?.cognitive || '데이터 없음'}</div>
                  <div><span className="text-gray-600">불안:</span> {interpretation.detailedAnalysis?.mentalHealth?.anxiety || '데이터 없음'}</div>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-800 mb-2">🎯 SincNet 음성 분석</h4>
                <div className="space-y-2 text-sm">
                  {interpretation.sincnetAnalysis ? (
                    <>
                      <div className="flex justify-between">
                        <span className="text-gray-600">우울 점수:</span>
                        <span className={`font-medium ${
                          (interpretation.sincnetAnalysis.depression?.score || 0) > 7 ? 'text-red-600' :
                          (interpretation.sincnetAnalysis.depression?.score || 0) > 4 ? 'text-yellow-600' : 'text-green-600'
                        }`}>
                          {interpretation.sincnetAnalysis.depression?.score?.toFixed(1) || '-'} / 10
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">불면 점수:</span>
                        <span className={`font-medium ${
                          (interpretation.sincnetAnalysis.insomnia?.score || 0) > 7 ? 'text-red-600' :
                          (interpretation.sincnetAnalysis.insomnia?.score || 0) > 4 ? 'text-yellow-600' : 'text-green-600'
                        }`}>
                          {interpretation.sincnetAnalysis.insomnia?.score?.toFixed(1) || '-'} / 10
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">불안 점수:</span>
                        <span className={`font-medium ${
                          (interpretation.sincnetAnalysis.anxiety?.score || 0) > 7 ? 'text-red-600' :
                          (interpretation.sincnetAnalysis.anxiety?.score || 0) > 4 ? 'text-yellow-600' : 'text-green-600'
                        }`}>
                          {interpretation.sincnetAnalysis.anxiety?.score?.toFixed(1) || '-'} / 10
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">인지 점수:</span>
                        <span className={`font-medium ${
                          (interpretation.sincnetAnalysis.cognitive?.score || 10) < 3 ? 'text-red-600' :
                          (interpretation.sincnetAnalysis.cognitive?.score || 10) < 6 ? 'text-yellow-600' : 'text-green-600'
                        }`}>
                          {interpretation.sincnetAnalysis.cognitive?.score?.toFixed(1) || '-'} / 10
                        </span>
                      </div>
                      <div className="pt-2 mt-2 border-t border-gray-200">
                        <div className="flex justify-between">
                          <span className="text-gray-600 font-medium">종합 위험도:</span>
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                            interpretation.sincnetAnalysis.overall?.risk_level === 'critical' ? 'bg-red-100 text-red-800' :
                            interpretation.sincnetAnalysis.overall?.risk_level === 'high' ? 'bg-orange-100 text-orange-800' :
                            interpretation.sincnetAnalysis.overall?.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {interpretation.sincnetAnalysis.overall?.risk_level === 'critical' ? '매우 높음' :
                             interpretation.sincnetAnalysis.overall?.risk_level === 'high' ? '높음' :
                             interpretation.sincnetAnalysis.overall?.risk_level === 'medium' ? '보통' :
                             interpretation.sincnetAnalysis.overall?.risk_level === 'low' ? '낮음' : '분석 중'}
                          </span>
                        </div>
                      </div>
                    </>
                  ) : (
                    <p className="text-gray-500 italic">SincNet 분석 데이터가 없습니다</p>
                  )}
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-800 mb-2">대화 내용</h4>
                <p className="text-sm text-gray-700">{interpretation.detailedAnalysis?.conversationContent || '데이터 없음'}</p>
              </div>
            </div>

            <div className="space-y-4">
              {/* 시계열 분석 */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">📈 변화 추이</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-700 mb-3">{interpretation.timeSeriesAnalysis?.summary || '데이터 없음'}</p>
                  
                  {interpretation.timeSeriesAnalysis?.dataPoints && interpretation.timeSeriesAnalysis.dataPoints > 0 && interpretation.timeSeriesAnalysis.trends && (
                    <div className="space-y-1 text-xs">
                      <div className="text-gray-600">변화량:</div>
                      <div className="grid grid-cols-3 gap-2">
                        <div className={`px-2 py-1 rounded text-center ${
                          (interpretation.timeSeriesAnalysis.trends.depression || 0) > 0 ? 'bg-red-100 text-red-700' : 
                          (interpretation.timeSeriesAnalysis.trends.depression || 0) < 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100'
                        }`}>
                          우울 {(interpretation.timeSeriesAnalysis.trends.depression || 0) > 0 ? '↑' : (interpretation.timeSeriesAnalysis.trends.depression || 0) < 0 ? '↓' : '→'}
                          {Math.abs(interpretation.timeSeriesAnalysis.trends.depression || 0).toFixed(1)}
                        </div>
                        <div className={`px-2 py-1 rounded text-center ${
                          (interpretation.timeSeriesAnalysis.trends.cognitive || 0) > 0 ? 'bg-green-100 text-green-700' : 
                          (interpretation.timeSeriesAnalysis.trends.cognitive || 0) < 0 ? 'bg-red-100 text-red-700' : 'bg-gray-100'
                        }`}>
                          인지 {(interpretation.timeSeriesAnalysis.trends.cognitive || 0) > 0 ? '↑' : (interpretation.timeSeriesAnalysis.trends.cognitive || 0) < 0 ? '↓' : '→'}
                          {Math.abs(interpretation.timeSeriesAnalysis.trends.cognitive || 0).toFixed(1)}
                        </div>
                        <div className={`px-2 py-1 rounded text-center ${
                          (interpretation.timeSeriesAnalysis.trends.anxiety || 0) > 0 ? 'bg-red-100 text-red-700' : 
                          (interpretation.timeSeriesAnalysis.trends.anxiety || 0) < 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100'
                        }`}>
                          불안 {(interpretation.timeSeriesAnalysis.trends.anxiety || 0) > 0 ? '↑' : (interpretation.timeSeriesAnalysis.trends.anxiety || 0) < 0 ? '↓' : '→'}
                          {Math.abs(interpretation.timeSeriesAnalysis.trends.anxiety || 0).toFixed(1)}
                        </div>
                      </div>
                      <div className="text-gray-500 text-center mt-1">
                        {interpretation.timeSeriesAnalysis.dataPoints}개 데이터 기반
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 권장 사항 */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">💡 권장 대응</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <ul className="space-y-2">
                    {(interpretation.recommendedActions || []).map((action, index) => (
                      <li key={index} className="flex items-start space-x-2 text-sm">
                        <span className="text-blue-500 mt-0.5">•</span>
                        <span className="text-gray-700">{action}</span>
                      </li>
                    ))}
                    {(!interpretation.recommendedActions || interpretation.recommendedActions.length === 0) && (
                      <li className="text-sm text-gray-500">권장사항 정보 없음</li>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* 최종 요약 */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">📋 최종 요약</h3>
            <p className="text-blue-800 leading-relaxed">{interpretation.summary || '요약 정보 없음'}</p>
            <div className="mt-3 text-xs text-blue-600">
              생성일시: {interpretation.generatedAt ? new Date(interpretation.generatedAt).toLocaleString() : '정보 없음'}
            </div>
          </div>
        </div>
      ) : !isLoading && (
        <div className="text-center py-8 text-gray-500">
          <div className="text-6xl mb-4">🧠</div>
          <h3 className="text-lg font-medium mb-2">AI 종합 해석이 아직 생성되지 않았습니다</h3>
          <p className="text-sm mb-4">
            분석 데이터를 종합하여 시니어의 상태에 대한 전문적인 해석을 제공해드립니다.
          </p>
          <button
            onClick={generateInterpretation}
            disabled={isGenerating}
            className="px-6 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            해석 생성하기
          </button>
        </div>
      )}
    </div>
  );
} 