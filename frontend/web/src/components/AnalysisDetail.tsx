'use client';

import { useState } from 'react';
import { EnhancedAnalysis } from '../hooks/useApiData';
import ScoreChart from './charts/ScoreChart';
import VoicePatternChart from './charts/VoicePatternChart';
import AnalysisInterpretation from './AnalysisInterpretation';
import { formatDate } from '../utils/dateHelpers';
import { VoicePatternData } from './charts/VoicePatternTypes';

interface AnalysisDetailProps {
  analysis: EnhancedAnalysis;
}

export default function AnalysisDetail({ analysis }: AnalysisDetailProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'transcription' | 'charts' | 'summary'>('overview');

  // 음성 패턴 데이터 변환
  const voicePatterns = analysis.result?.voicePatterns as any;
  const voicePatternData: VoicePatternData = {
    speechRate: voicePatterns?.speechRate || 0,
    pauseRatio: voicePatterns?.pauseRatio || 0,
    voiceStability: voicePatterns?.voiceStability || 0,
    emotionTone: voicePatterns?.emotionTone,
    responseTime: voicePatterns?.responseTime,
    pitch: voicePatterns?.pitch,
    energy: voicePatterns?.energy
  };

  // 정신건강 점수 데이터 변환
  const mentalHealthAnalysis = analysis.result?.mentalHealthAnalysis as any;
  const mentalHealthScores = mentalHealthAnalysis ? {
    depression: mentalHealthAnalysis.depression?.score || 0,
    anxiety: mentalHealthAnalysis.anxiety?.score || 0,
    stress: mentalHealthAnalysis.stress?.score || 0,
    mentalHealthStatus: mentalHealthAnalysis.mentalHealthStatus?.score || 0,
    emotionManagement: mentalHealthAnalysis.emotionManagement?.score || 0,
    socialRelationship: mentalHealthAnalysis.socialRelationship?.score || 0
  } : null;

  const tabs = [
    { id: 'overview', label: '개요', icon: '📊' },
    { id: 'transcription', label: '음성 전사', icon: '🎤' },
    { id: 'charts', label: '분석 차트', icon: '📈' },
    { id: 'summary', label: '요약 및 권장', icon: '📝' }
  ];

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="bg-white rounded-lg p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {analysis.seniorName || '시니어'} 분석 결과
            </h1>
            <p className="text-gray-600 mt-1">
              분석 시간: {formatDate(analysis.recordedAt)}
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">분석 ID</div>
            <div className="font-mono text-sm text-gray-700">
              {analysis.analysisId}
            </div>
          </div>
        </div>
      </div>

      {/* AI 종합 해석 */}
      <AnalysisInterpretation 
        callId={analysis.callId}
        seniorId={analysis.seniorName || analysis.callId} // seniorName이 실제로는 seniorId입니다
        onInterpretationGenerated={(interpretation) => {
          console.log('새 해석이 생성되었습니다:', interpretation);
        }}
      />

      {/* 탭 네비게이션 */}
      <div className="bg-white rounded-lg shadow-sm">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* 탭 컨텐츠 */}
        <div className="p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* 요약 통계 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-blue-600">
                    {mentalHealthScores ?
                      Math.round((mentalHealthScores.depression + mentalHealthScores.anxiety + mentalHealthScores.stress) / 3) :
                      'N/A'
                    }
                  </div>
                  <div className="text-sm text-blue-700">평균 점수</div>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-600">
                    {voicePatternData.speechRate || 'N/A'}
                  </div>
                  <div className="text-sm text-green-700">말하기 속도 (WPM)</div>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-purple-600">
                    {voicePatternData.voiceStability ? Math.round(voicePatternData.voiceStability * 100) : 'N/A'}%
                  </div>
                  <div className="text-sm text-purple-700">음성 안정성</div>
                </div>
              </div>

              {/* 주요 지표 */}
              {mentalHealthScores && (
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">정신건강 주요 지표</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {Object.entries(mentalHealthScores).map(([key, score]) => (
                      <div key={key} className="text-center">
                        <div className="text-2xl font-bold" style={{ 
                          color: score.score < 30 ? '#10b981' : score.score < 70 ? '#f59e0b' : '#ef4444' 
                        }}>
                          {score.score}
                        </div>
                        <div className="text-sm text-gray-600 capitalize">
                          {key === 'depression' ? '우울감' : key === 'cognitive' ? '인지기능' : '불안감'}
                        </div>
                        <div className="text-xs text-gray-500">{score.level}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'transcription' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">음성 전사 내용</h3>
              {analysis.result?.transcription ? (
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-gray-800 leading-relaxed">
                    {typeof analysis.result.transcription === 'string' 
                      ? analysis.result.transcription 
                      : analysis.result.transcription?.text || '전사 내용이 없습니다'}
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">
                  <div className="text-4xl mb-2">🎤</div>
                  <p>전사 내용이 없습니다</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'charts' && (
            <div className="space-y-6">
              {/* 정신건강 분석 차트 */}
              {mentalHealthScores && (
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">정신건강 분석 차트</h3>
                  <ScoreChart
                    scores={mentalHealthScores}
                    size="large"
                    showLegend={true}
                    showTooltip={true}
                  />
                </div>
              )}

              {/* 음성 패턴 분석 차트 */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">음성 패턴 분석</h3>
                <VoicePatternChart
                  data={voicePatternData}
                  size="lg"
                  showLabels={true}
                  showTooltips={true}
                />
              </div>
            </div>
          )}

          {activeTab === 'summary' && (
            <div className="space-y-6">
              {/* AI 요약 */}
              {analysis.result?.summary && (
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">AI 분석 요약</h3>
                  <div className="text-gray-800 leading-relaxed">
                    {analysis.result.summary}
                  </div>
                </div>
              )}

              {/* 권장사항 */}
              {analysis.result?.recommendations && analysis.result.recommendations.length > 0 && (
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">권장사항</h3>
                  <ul className="space-y-2">
                    {analysis.result.recommendations.map((recommendation: string, index: number) => (
                      <li key={index} className="flex items-start space-x-3">
                        <div className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                        <span className="text-gray-800">{recommendation}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {!analysis.result?.summary && !analysis.result?.recommendations && (
                <div className="text-center text-gray-500 py-8">
                  <div className="text-4xl mb-2">📝</div>
                  <p>요약 및 권장사항이 없습니다</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
} 