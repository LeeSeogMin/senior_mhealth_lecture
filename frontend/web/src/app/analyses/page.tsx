'use client';

import { useApiData } from '../../hooks/useApiData';
import Link from 'next/link';
import { useState } from 'react';

// 간단한 통계 카드 컴포넌트 (대시보드에서 가져옴)
function StatCard({ title, value, change, changeType }: {
  title: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
}) {
  const getChangeColor = () => {
    switch (changeType) {
      case 'positive': return 'text-green-600';
      case 'negative': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
        </div>
        {change && (
          <div className={`text-sm font-medium ${getChangeColor()}`}>
            {change}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AnalysesPage() {
  const { analyses, seniors, stats, isLoading, error } = useApiData();
  const [showPastResults, setShowPastResults] = useState(false);
  
  // 최신 분석 결과
  const latestAnalysis = analyses.length > 0 ? analyses[0] : null;
  // 과거 분석 결과들 (최신 제외)
  const pastAnalyses = analyses.length > 1 ? analyses.slice(1) : [];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-64 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-red-800">오류가 발생했습니다</h2>
            <p className="text-red-600 mt-2">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">분석 결과</h1>
          <p className="text-gray-600">총 {analyses.length}개의 분석 결과가 있습니다.</p>
        </div>
        
        {/* 1. 최신 분석 결과 (상단에 보통 크기로 표시) */}
        {latestAnalysis && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">📊 최근 분석 결과</h2>
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-gray-900">
                    {latestAnalysis.seniorName || '알 수 없음'}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {latestAnalysis.recordedAt ? new Date(latestAnalysis.recordedAt).toLocaleString('ko-KR') : '날짜 없음'}
                  </p>
                </div>
                <Link 
                  href={`/analyses-detail?id=${latestAnalysis.analysisId}`}
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors text-sm"
                >
                  상세 보기
                </Link>
              </div>
              
              {/* AI 종합해석 */}
              {(latestAnalysis.result as any)?.aiSummary && (
                <div className="mb-4 p-3 bg-yellow-50 rounded-lg">
                  <p className="text-sm text-gray-700">
                    <span className="font-medium">AI 종합해석:</span> {(latestAnalysis.result as any).aiSummary}
                  </p>
                </div>
              )}
              
              {/* 정신건강 점수 */}
              {latestAnalysis.result?.mentalHealthAnalysis && (
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-blue-50 rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-blue-600">
                      {(latestAnalysis.result.mentalHealthAnalysis as any).depression?.score || 0}
                    </div>
                    <div className="text-sm text-blue-700">우울증</div>
                  </div>
                  <div className="bg-green-50 rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-green-600">
                      {(latestAnalysis.result.mentalHealthAnalysis as any).cognitive?.score || 0}
                    </div>
                    <div className="text-sm text-green-700">인지능력</div>
                  </div>
                  <div className="bg-red-50 rounded-lg p-3 text-center">
                    <div className="text-xl font-bold text-red-600">
                      {(latestAnalysis.result.mentalHealthAnalysis as any).anxiety?.score || 0}
                    </div>
                    <div className="text-sm text-red-700">불안</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* 2. 기존 대시보드 내용 (통계 카드) */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">📈 통계 현황</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="총 분석 수"
              value={analyses.length}
              change="+12%"
              changeType="positive"
            />
            <StatCard
              title="등록된 시니어"
              value={seniors.length}
              change="+2"
              changeType="positive"
            />
            <StatCard
              title="정상 상태"
              value={stats?.normalStatus || 0}
              change="+5%"
              changeType="positive"
            />
            <StatCard
              title="주의 필요"
              value={stats?.warningStatus || 0}
              change="-2%"
              changeType="negative"
            />
          </div>
        </div>
        
        {/* 차트 섹션 */}
        <div className="mb-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">상태 분포</h3>
              <div className="text-center py-8">
                <p className="text-gray-500">차트 데이터 준비 중...</p>
              </div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">트렌드 분석</h3>
              <div className="text-center py-8">
                <p className="text-gray-500">차트 데이터 준비 중...</p>
              </div>
            </div>
          </div>
        </div>
        
        {/* 3. 과거 결과 조회 (하단) */}
        <div className="mb-8">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-800">🔍 과거 결과 조회</h2>
              <button 
                onClick={() => setShowPastResults(!showPastResults)}
                className="text-blue-600 hover:text-blue-700 font-medium"
              >
                {showPastResults ? '닫기' : `${pastAnalyses.length}개 결과 보기`}
              </button>
            </div>
            
            {pastAnalyses.length === 0 && (
              <p className="text-gray-500 text-center py-4">과거 분석 결과가 없습니다.</p>
            )}
          </div>
        </div>
        
        {/* 과거 결과 목록 (토글) */}
        {showPastResults && pastAnalyses.length > 0 && (
          <div className="mt-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">📋 과거 분석 결과</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {pastAnalyses.map((analysis) => (
                <div key={analysis.analysisId} className="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow">
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {analysis.seniorName || '알 수 없음'}
                      </h3>
                      <span className="text-sm text-gray-500">
                        {analysis.recordedAt ? new Date(analysis.recordedAt).toLocaleDateString('ko-KR') : '날짜 없음'}
                      </span>
                    </div>
                    
                    <div className="space-y-3 mb-4">
                      {analysis.result?.mentalHealthAnalysis && (
                        <div className="grid grid-cols-3 gap-2 text-sm">
                          <div className="text-center">
                            <div className="font-medium text-blue-600">우울증</div>
                            <div className="text-gray-600">
                              {(analysis.result.mentalHealthAnalysis as any).depression?.score || 0}
                            </div>
                          </div>
                          <div className="text-center">
                            <div className="font-medium text-green-600">인지능력</div>
                            <div className="text-gray-600">
                              {(analysis.result.mentalHealthAnalysis as any).cognitive?.score || 0}
                            </div>
                          </div>
                          <div className="text-center">
                            <div className="font-medium text-red-600">불안</div>
                            <div className="text-gray-600">
                              {(analysis.result.mentalHealthAnalysis as any).anxiety?.score || 0}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                    
                    <Link 
                      href={`/analyses-detail?id=${analysis.analysisId}`}
                      className="block w-full text-center bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
                    >
                      상세 보기
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}