'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getAuth, onAuthStateChanged } from 'firebase/auth';
import { useApiData } from '@/hooks/useApiData';

// 간단한 통계 카드 컴포넌트
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

// 간단한 분석 상세 컴포넌트
function AnalysisDetail({ analysis }: { analysis: any }) {
  return (
    <div className="mt-4 p-4 bg-gray-50 rounded-lg">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h5 className="font-medium text-gray-900 mb-2">분석 결과</h5>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium">전체 점수:</span> {analysis.overallScore || 'N/A'}
            </div>
            <div>
              <span className="font-medium">감정 점수:</span> {analysis.emotionalScore || 'N/A'}
            </div>
            <div>
              <span className="font-medium">인지 점수:</span> {analysis.cognitiveScore || 'N/A'}
            </div>
            <div>
              <span className="font-medium">사회 점수:</span> {analysis.socialScore || 'N/A'}
            </div>
          </div>
        </div>
        <div>
          <h5 className="font-medium text-gray-900 mb-2">AI 해석</h5>
          <p className="text-sm text-gray-600 line-clamp-3">
            {analysis.aiInterpretation || '해석 데이터가 없습니다.'}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [user, setUser] = useState<any>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const [selectedAnalysis, setSelectedAnalysis] = useState<any>(null);
  const [showDetail, setShowDetail] = useState(false);

  // API 데이터 사용
  const { 
    seniors, 
    analyses, 
    stats, 
    isLoading, 
    error,
    refreshData
  } = useApiData();

  // 인증 상태 확인
  useEffect(() => {
    const auth = getAuth();
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setIsAuthenticated(!!currentUser);
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  useEffect(() => {
    // 인증 상태 확인 후 리다이렉트
    if (!loading && !isAuthenticated) {
      console.log('인증되지 않음 - 로그인 페이지로 이동');
      router.push('/login');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // 로그인 페이지로 리다이렉트됨
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          상세 분석 대시보드
        </h1>
        <p className="text-gray-600">
          {user?.email}님의 시니어 분석 상세 결과입니다.
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">분석 데이터를 불러오는 중...</p>
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <div className="text-red-600 mb-4">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <p className="text-gray-600">분석 데이터를 불러올 수 없습니다.</p>
          <button
            onClick={refreshData}
            className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
          >
            다시 시도
          </button>
        </div>
      ) : analyses && analyses.length > 0 ? (
        <div className="space-y-8">
          {/* 통계 카드 */}
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

          {/* 차트 섹션 */}
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

          {/* 분석 목록 */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">최근 분석 결과</h3>
            </div>
            <div className="divide-y divide-gray-200">
              {analyses.slice(0, 5).map((analysis: any, index: number) => (
                <div key={analysis.analysisId || index} className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="text-lg font-medium text-gray-900">
                        {analysis.seniorName}
                      </h4>
                      <p className="text-sm text-gray-500">
                        {new Date(analysis.createdAt).toLocaleDateString('ko-KR')}
                      </p>
                    </div>
                    <div className="flex items-center space-x-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        analysis.alertLevel === 'high' ? 'bg-red-100 text-red-800' :
                        analysis.alertLevel === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {analysis.alertLevel === 'high' ? '높음' :
                         analysis.alertLevel === 'medium' ? '보통' : '정상'}
                      </span>
                      <button
                        onClick={() => {
                          setSelectedAnalysis(analysis);
                          setShowDetail(!showDetail);
                        }}
                        className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                      >
                        {showDetail && selectedAnalysis === analysis ? '접기' : '상세보기'}
                      </button>
                    </div>
                  </div>
                  
                  {showDetail && selectedAnalysis === analysis && (
                    <AnalysisDetail analysis={analysis} />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-gray-600">분석 데이터가 없습니다.</p>
        </div>
      )}
    </div>
  );
} 