'use client';

// GitHub Actions 자동 배포 테스트 - Firebase Hosting
import { useState, useEffect, useCallback, useMemo, memo } from 'react';
import Link from 'next/link';
import { useApiData } from '../hooks/useApiData';
import { TrendChart, StatusDistributionChart } from '../components/TrendChart';
import { AnalysisList } from '../components/AnalysisCard';
import { StatusSummary } from '../components/StatusIndicator';
import AdvancedTrendChart from '../components/AdvancedTrendChart';
import AdvancedStatusDistribution from '../components/AdvancedStatusDistribution';
import Auth from '../components/Auth';
import { getAuth, onAuthStateChanged } from 'firebase/auth';
import { logOut } from '../lib/firebase';
import { formatDate } from '../utils/dateHelpers';
import { calculateOverallStats } from '../utils/chartDataTransformers';
import NotificationToast from '../components/NotificationToast';
import { useNotifications } from '../contexts/NotificationContext';
import DashboardStats from '../components/DashboardStats';
import AnalysisDetailInline from '../components/AnalysisDetailInline';
import ComprehensiveAnalysisSection from '../components/ComprehensiveAnalysisSection';
import DetailedDataSection from '../components/DetailedDataSection';
import TimeSeriesSection from '../components/TimeSeriesSection';
import ErrorBoundary from '../components/ErrorBoundary';
import { EnhancedAnalysis } from '../hooks/useApiData';

const Home = memo(function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null); // null은 로딩 상태
  const [expandedAnalysis, setExpandedAnalysis] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState<EnhancedAnalysis | null>(null);

  // API 데이터 훅 사용
  const {
    seniors,
    analyses,
    stats,
    isLoading,
    error,
    refreshData
  } = useApiData();

  // 알림 시스템 사용
  const { checkForAlerts } = useNotifications();

  // 인증 상태 확인
  useEffect(() => {
    const auth = getAuth();

    // 초기 사용자 상태 즉시 확인
    const currentUser = auth.currentUser;
    if (currentUser) {
      console.log('Initial user found:', currentUser.email);
      setIsAuthenticated(true);
    } else {
      console.log('No initial user found');
      // 인증 상태가 아직 로드되지 않았을 수 있으므로 잠시 대기
      setTimeout(() => {
        const checkUser = auth.currentUser;
        if (checkUser) {
          console.log('User found after delay:', checkUser.email);
          setIsAuthenticated(true);
        } else {
          console.log('No user after delay, showing login');
          setIsAuthenticated(false);
        }
      }, 1000);
    }

    const unsubscribe = onAuthStateChanged(auth, (user) => {
      console.log('Auth state changed:', user ? user.email : 'null');
      setIsAuthenticated(!!user);

      if (user) {
        console.log('Authenticated user:', user.email);
        refreshData(); // 인증 후 데이터 새로고침
      }
    });

    return () => unsubscribe();
  }, [refreshData]);

  // selectedAnalysis 초기화
  useEffect(() => {
    if (analyses.length > 0) {
      setSelectedAnalysis(analyses[0]);
    } else {
      setSelectedAnalysis(null);
    }
  }, [analyses]);

  // 알림 체크 - 개발 중 비활성화
  useEffect(() => {
    // 개발 단계에서는 알림 비활성화
    // if (analyses.length > 0 && isAuthenticated) {
    //   checkForAlerts(analyses);
    // }
  }, [analyses, checkForAlerts, isAuthenticated]);

  // 로그아웃 핸들러
  const handleLogout = useCallback(async () => {
    try {
      await logOut();
      setIsAuthenticated(false);
      console.log('로그아웃 성공');
    } catch (error) {
      console.error('로그아웃 실패:', error);
    }
  }, []);

  // 로딩 중일 때 표시
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">인증 확인 중...</p>
        </div>
      </div>
    );
  }

  // 비인증 상태일 때 표시
  if (!isAuthenticated) {
    return <Auth />;
  }

  // 데이터 준비
  const overallStats = calculateOverallStats(analyses);
  const lastAnalysis = analyses[0] || null;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <h1 className="text-3xl font-bold text-gray-900">
              시니어 마음건강 대시보드
            </h1>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
            >
              로그아웃
            </button>
          </div>
        </div>
      </header>

      {/* 3등분 랜딩페이지 메인 콘텐츠 */}
      <main 
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 md:space-y-12"
        role="main"
        aria-label="시니어 마음건강 대시보드"
      >
        
            {/* 첫 번째 파트: 종합해석 섹션 */}
            <section 
              className="w-full"
              aria-labelledby="comprehensive-analysis-heading"
            >
              <div className="text-center mb-6 md:mb-8">
                <h2 
                  id="comprehensive-analysis-heading"
                  className="text-2xl md:text-4xl font-bold text-gray-900 mb-3 md:mb-4"
                >
                  💙 AI 종합해석
                </h2>
                <p className="text-base md:text-lg text-gray-600 max-w-3xl mx-auto px-4">
                  최신 AI 분석 결과를 바탕으로 한 종합적인 건강 상태 해석과 맞춤형 권장사항을 확인하세요
                </p>
              </div>
              
              {/* 종합해석 섹션 컴포넌트 사용 */}
              <ErrorBoundary>
                <ComprehensiveAnalysisSection
                  selectedAnalysis={selectedAnalysis}
                  onAnalysisSelect={setSelectedAnalysis}
                />
              </ErrorBoundary>
            </section>

        {/* 두 번째 파트: 세부 데이터 섹션 */}
        <section className="w-full">
          <div className="text-center mb-6 md:mb-8">
            <h2 className="text-2xl md:text-4xl font-bold text-gray-900 mb-3 md:mb-4">
              📈 세부 데이터 분석
            </h2>
            <p className="text-base md:text-lg text-gray-600 max-w-3xl mx-auto px-4">
              정신건강 점수, 음성 패턴, 상세 분석 결과를 통해 깊이 있는 건강 상태를 파악하세요
            </p>
          </div>
          
          {/* 세부 데이터 섹션 컴포넌트 사용 */}
          <ErrorBoundary>
            <DetailedDataSection
              key={selectedAnalysis?.analysisId || 'no-analysis'}
              selectedAnalysis={selectedAnalysis}
              onAnalysisSelect={setSelectedAnalysis}
            />
          </ErrorBoundary>
        </section>

        {/* 세 번째 파트: 시계열 데이터 섹션 */}
        <section className="w-full">
          <div className="text-center mb-6 md:mb-8">
            <h2 className="text-2xl md:text-4xl font-bold text-gray-900 mb-3 md:mb-4">
              ⏰ 시계열 데이터 분석
            </h2>
            <p className="text-base md:text-lg text-gray-600 max-w-3xl mx-auto px-4">
              시간에 따른 건강 상태 변화 추이와 트렌드 분석을 통해 장기적인 건강 패턴을 확인하세요
            </p>
          </div>
          
          {/* 시계열 데이터 섹션 컴포넌트 사용 */}
          <ErrorBoundary>
            <TimeSeriesSection />
          </ErrorBoundary>
        </section>

        {/* 에러 메시지 */}
        {error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}
      </main>

      {/* 알림 토스트 */}
      <NotificationToast />
    </div>
  );
});

export default Home;